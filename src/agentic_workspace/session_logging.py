from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shlex
import sys
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentic_workspace import __version__
from agentic_workspace import config as config_lib
from agentic_workspace.result_adapter import serialise_value

SESSION_LOG_ROOT = Path(".agentic-workspace") / "local" / "logs"
SESSION_POINTER_PATH = Path(".agentic-workspace") / "local" / "session-logging" / "current.json"
SESSION_POINTER_KIND = "agentic-workspace/session-logging-current/v1"
SESSION_LOG_KIND = "agentic-workspace/session-log/v1"
DEFAULT_MAX_INLINE_OUTPUT_BYTES = 64 * 1024


@dataclass(frozen=True)
class CommandCapture:
    exit_code: int
    stdout: str
    stderr: str
    exception: str | None = None


@dataclass(frozen=True)
class SessionLoggingState:
    enabled: bool
    target_root: Path
    config: config_lib.WorkspaceConfig | None
    config_warning: str | None = None


def target_from_argv(argv: Sequence[str], *, cwd: Path | None = None) -> Path:
    argv_list = list(argv)
    for index, token in enumerate(argv_list):
        if token == "--target" and index + 1 < len(argv_list):
            return Path(argv_list[index + 1]).expanduser().resolve()
        if token.startswith("--target="):
            return Path(token.split("=", 1)[1]).expanduser().resolve()
    discovered = config_lib.discover_workspace_root(cwd or Path.cwd())
    return (discovered or (cwd or Path.cwd())).resolve()


def load_state_for_argv(argv: Sequence[str], *, cwd: Path | None = None) -> SessionLoggingState:
    target_root = target_from_argv(argv, cwd=cwd)
    if os.environ.get("AW_SESSION_LOGGING_DISABLE") == "1":
        return SessionLoggingState(enabled=False, target_root=target_root, config=None)
    try:
        config = config_lib.load_workspace_config(target_root=target_root)
    except Exception as exc:  # pragma: no cover - best-effort side channel
        return SessionLoggingState(enabled=False, target_root=target_root, config=None, config_warning=str(exc))
    return SessionLoggingState(
        enabled=bool(config.local_override.session_logging.enabled),
        target_root=target_root,
        config=config,
    )


def run_with_session_logging(
    argv: Sequence[str],
    runner: Callable[[list[str]], int],
    *,
    cwd: Path | None = None,
    stdout: Any | None = None,
    stderr: Any | None = None,
) -> int:
    argv_list = list(argv)
    if argv_list and argv_list[0] == "log":
        return run_log_command(argv_list[1:], cwd=cwd, stdout=stdout, stderr=stderr)

    state = load_state_for_argv(argv_list, cwd=cwd)
    output_stdout = stdout or sys.stdout
    output_stderr = stderr or sys.stderr
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    capture = CommandCapture(exit_code=0, stdout="", stderr="")
    try:
        try:
            with contextlib.redirect_stdout(captured_stdout), contextlib.redirect_stderr(captured_stderr):
                exit_code = int(runner(argv_list))
            capture = CommandCapture(
                exit_code=exit_code,
                stdout=captured_stdout.getvalue(),
                stderr=captured_stderr.getvalue(),
            )
            return exit_code
        except SystemExit as exc:
            exit_code = _system_exit_code(exc)
            capture = CommandCapture(
                exit_code=exit_code,
                stdout=captured_stdout.getvalue(),
                stderr=captured_stderr.getvalue(),
                exception="SystemExit",
            )
            raise
        except Exception as exc:
            capture = CommandCapture(
                exit_code=1,
                stdout=captured_stdout.getvalue(),
                stderr=captured_stderr.getvalue(),
                exception=exc.__class__.__name__,
            )
            raise
    finally:
        if capture.stdout:
            print(capture.stdout, end="", file=output_stdout)
        if capture.stderr:
            print(capture.stderr, end="", file=output_stderr)
        warning = append_command_entry(state=state, argv=argv_list, capture=capture)
        if warning:
            print(f"AW session logging warning: {warning}", file=output_stderr)


def run_log_command(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    stdout: Any | None = None,
    stderr: Any | None = None,
) -> int:
    output_stderr = stderr or sys.stderr
    try:
        args = _read_log_command_options(argv)
    except ValueError as exc:
        print(f"agentic-workspace log: {exc}", file=output_stderr)
        return 2
    effective_argv: list[str] = []
    if args["target"]:
        effective_argv.extend(["--target", str(args["target"])])
    state = load_state_for_argv(effective_argv, cwd=cwd)
    output_stdout = stdout or sys.stdout
    try:
        if args["subcommand"] == "note":
            payload = append_note(state=state, text=str(args["text"]))
        elif args["subcommand"] == "new-session":
            payload = reset_session(state=state)
        else:
            payload = status_payload(state=state)
    except Exception as exc:  # pragma: no cover - non-fatal command wrapper guard
        print(f"AW session logging warning: {exc}", file=output_stderr)
        return 0
    if args["format"] == "json":
        print(json.dumps(serialise_value(payload), indent=2), file=output_stdout)
    else:
        print(_log_command_text(payload), file=output_stdout)
    return 0


def _read_log_command_options(argv: Sequence[str]) -> dict[str, str]:
    tokens = list(argv)
    options = {"target": "", "format": "text", "subcommand": "", "text": ""}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--target":
            index += 1
            if index >= len(tokens):
                raise ValueError("--target requires a value")
            options["target"] = tokens[index]
        elif token.startswith("--target="):
            options["target"] = token.split("=", 1)[1]
        elif token == "--format":
            index += 1
            if index >= len(tokens):
                raise ValueError("--format requires a value")
            options["format"] = _validate_log_output_format(tokens[index])
        elif token.startswith("--format="):
            options["format"] = _validate_log_output_format(token.split("=", 1)[1])
        elif token in {"note", "new-session", "status"}:
            options["subcommand"] = token
            index += 1
            break
        else:
            raise ValueError(f"unknown option or subcommand: {token}")
        index += 1
    if not options["subcommand"]:
        raise ValueError("expected one of: note, new-session, status")
    if options["subcommand"] == "note":
        while index < len(tokens):
            token = tokens[index]
            if token == "--text":
                index += 1
                if index >= len(tokens):
                    raise ValueError("--text requires a value")
                options["text"] = tokens[index]
            elif token.startswith("--text="):
                options["text"] = token.split("=", 1)[1]
            else:
                raise ValueError(f"unknown note option: {token}")
            index += 1
        if not options["text"]:
            raise ValueError("note requires --text")
    elif index < len(tokens):
        raise ValueError(f"{options['subcommand']} does not accept extra arguments")
    return options


def _validate_log_output_format(value: str) -> str:
    if value not in {"text", "json"}:
        raise ValueError("--format must be one of: text, json")
    return value


def append_command_entry(*, state: SessionLoggingState, argv: Sequence[str], capture: CommandCapture) -> str | None:
    if not state.enabled:
        return None
    try:
        session = ensure_session(state=state)
        entry_id = f"cmd-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        command_text = "agentic-workspace " + shlex.join(list(argv))
        entry = _command_entry_markdown(
            state=state,
            session=session,
            entry_id=entry_id,
            command_text=command_text,
            capture=capture,
        )
        _append_text(state.target_root / session["log_path"], entry)
    except Exception as exc:  # pragma: no cover - intentionally best effort
        return str(exc)
    return None


def append_note(*, state: SessionLoggingState, text: str) -> dict[str, Any]:
    if not state.enabled:
        return {
            "kind": "agentic-workspace/session-log-note/v1",
            "status": "disabled",
            "enabled": False,
            "path": "",
            "rule": "Notes are optional and local-only; disabled logging is not a warning.",
        }
    session = ensure_session(state=state)
    timestamp = datetime.now(UTC).isoformat()
    note = text.strip()
    _append_text(
        state.target_root / session["log_path"],
        f"\n## Agent Note - {timestamp}\n\n{note}\n",
    )
    return {
        "kind": "agentic-workspace/session-log-note/v1",
        "status": "appended",
        "enabled": True,
        "path": session["log_path"],
        "session_id": session["session_id"],
        "timestamp": timestamp,
    }


def reset_session(*, state: SessionLoggingState) -> dict[str, Any]:
    if not state.enabled:
        return status_payload(state=state)
    session = ensure_session(state=state, force_new=True)
    return {
        "kind": "agentic-workspace/session-log-session/v1",
        "status": "created",
        "enabled": True,
        "path": session["log_path"],
        "session_id": session["session_id"],
    }


def status_payload(*, state: SessionLoggingState) -> dict[str, Any]:
    session = read_session_pointer(target_root=state.target_root)
    return {
        "kind": "agentic-workspace/session-logging-status/v1",
        "enabled": state.enabled,
        "target": state.target_root.as_posix(),
        "config_source": _logging_config_source(state),
        "path": session.get("log_path", "") if session else "",
        "session_id": session.get("session_id", "") if session else "",
        "local_only": True,
        "authoritative": False,
        "rule": "Session logs are local dogfooding evidence, not Planning state, Memory, proof receipts, or closeout authorization.",
    }


def ensure_session(*, state: SessionLoggingState, force_new: bool = False) -> dict[str, str]:
    current = None if force_new else read_session_pointer(target_root=state.target_root)
    if current:
        log_path = state.target_root / current["log_path"]
        if log_path.exists():
            return current
    created_at = datetime.now(UTC)
    session_id = f"{created_at.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    log_path = SESSION_LOG_ROOT / f"aw-session-{session_id}.md"
    session = {
        "kind": SESSION_POINTER_KIND,
        "session_id": session_id,
        "created_at": created_at.isoformat(),
        "log_path": log_path.as_posix(),
    }
    absolute_log_path = state.target_root / log_path
    absolute_log_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_log_path.write_text(_session_prelude(state=state, session=session), encoding="utf-8")
    pointer_path = state.target_root / SESSION_POINTER_PATH
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(json.dumps(session, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return session


def read_session_pointer(*, target_root: Path) -> dict[str, str] | None:
    pointer_path = target_root / SESSION_POINTER_PATH
    if not pointer_path.exists():
        return None
    try:
        payload = json.loads(pointer_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("kind") != SESSION_POINTER_KIND:
        return None
    session_id = str(payload.get("session_id", "")).strip()
    log_path = str(payload.get("log_path", "")).strip()
    if not session_id or not log_path:
        return None
    return {
        "kind": SESSION_POINTER_KIND,
        "session_id": session_id,
        "created_at": str(payload.get("created_at", "")),
        "log_path": log_path,
    }


def _session_prelude(*, state: SessionLoggingState, session: dict[str, str]) -> str:
    snapshot = {
        "kind": SESSION_LOG_KIND,
        "session_id": session["session_id"],
        "created_at": session["created_at"],
        "target": state.target_root.as_posix(),
        "package": {"name": "agentic-workspace", "version": __version__},
        "effective_config": _effective_config_snapshot(state),
        "logging_policy": {
            "enabled": state.enabled,
            "source": _logging_config_source(state),
            "root": SESSION_LOG_ROOT.as_posix(),
            "local_only": True,
            "authoritative": False,
            "redaction": "Logs capture AW command argv and AW stdout/stderr only; environment variables and secrets are not logged by default.",
            "failure_behavior": "Logging failures are warning-only and must not block ordinary AW operation, proof, or closeout claims.",
            "promotion_boundary": "Logs are dogfooding evidence only until explicitly promoted into checked-in Planning, Memory, docs, or proof receipts.",
        },
    }
    return "# Agentic Workspace Session Log\n\n```json\n" + json.dumps(serialise_value(snapshot), indent=2) + "\n```\n"


def _effective_config_snapshot(state: SessionLoggingState) -> dict[str, Any]:
    config = state.config
    if config is None:
        return {"status": "unavailable", "warning": state.config_warning or ""}
    return {
        "status": "present",
        "enabled_modules": list(config.enabled_modules),
        "workspace": {
            "enabled": config.enabled,
            "enabled_source": config.enabled_source,
            "workflow_artifact_profile": config.workflow_artifact_profile,
            "improvement_latitude": config.improvement_latitude,
            "optimization_bias": config.optimization_bias,
            "cli_invoke": config.cli_invoke,
            "cli_invoke_source": config.cli_invoke_source,
        },
        "assurance": {
            "default_level": config.assurance.default_level,
            "strict_closeout": config.assurance.strict_closeout,
        },
        "payload": {
            "target_release": config.payload_target.target_release,
            "policy": config.payload_target.policy,
            "dogfood_latest": config.payload_target.dogfood_latest,
        },
        "cli_identity": {
            "package": "agentic-workspace",
            "version": __version__,
            "argv0": sys.argv[0] if sys.argv else "",
            "python_executable": sys.executable,
        },
        "session_logging": {
            "enabled": config.local_override.session_logging.enabled,
            "source": config.local_override.session_logging.source,
            "config_path": config.local_override.path.as_posix() if config.local_override.path is not None else "",
        },
        "warnings": list(config.warnings),
    }


def _command_entry_markdown(
    *,
    state: SessionLoggingState,
    session: dict[str, str],
    entry_id: str,
    command_text: str,
    capture: CommandCapture,
) -> str:
    timestamp = datetime.now(UTC).isoformat()
    output = {"stdout": capture.stdout, "stderr": capture.stderr}
    output_size = len(capture.stdout.encode("utf-8")) + len(capture.stderr.encode("utf-8"))
    lines = [
        f"\n## Command - {timestamp}",
        "",
        f"- id: `{entry_id}`",
        f"- target: `{state.target_root.as_posix()}`",
        f"- exit_status: `{capture.exit_code}`",
    ]
    if capture.exception:
        lines.append(f"- exception: `{capture.exception}`")
    lines.extend(["", "```sh", command_text, "```"])
    if output_size > DEFAULT_MAX_INLINE_OUTPUT_BYTES:
        artifact = _write_output_artifact(state=state, session=session, entry_id=entry_id, output=output)
        lines.extend(
            [
                "",
                "Output stored as local artifact:",
                f"- path: `{artifact['path']}`",
                f"- sha256: `{artifact['sha256']}`",
                f"- bytes: `{artifact['bytes']}`",
            ]
        )
    else:
        lines.extend(["", "stdout:", "```text", capture.stdout, "```", "", "stderr:", "```text", capture.stderr, "```"])
    return "\n".join(lines) + "\n"


def _write_output_artifact(
    *,
    state: SessionLoggingState,
    session: dict[str, str],
    entry_id: str,
    output: dict[str, str],
) -> dict[str, Any]:
    artifact_path = SESSION_LOG_ROOT / "artifacts" / session["session_id"] / f"{entry_id}-output.json"
    payload = {
        "kind": "agentic-workspace/session-log-output-artifact/v1",
        "entry_id": entry_id,
        "stdout": output["stdout"],
        "stderr": output["stderr"],
    }
    raw = json.dumps(payload, indent=2)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    absolute_path = state.target_root / artifact_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_text(raw + "\n", encoding="utf-8")
    return {"path": artifact_path.as_posix(), "sha256": digest, "bytes": len(raw.encode("utf-8"))}


def _append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)


def _logging_config_source(state: SessionLoggingState) -> str:
    if state.config is None:
        return "unavailable"
    return state.config.local_override.session_logging.source


def _system_exit_code(exc: SystemExit) -> int:
    if isinstance(exc.code, int):
        return exc.code
    if exc.code in (None, ""):
        return 0
    return 1


def _log_command_text(payload: dict[str, Any]) -> str:
    status = str(payload.get("status", "unknown"))
    path = str(payload.get("path", ""))
    if path:
        return f"{status}: {path}"
    if payload.get("enabled") is False:
        return "disabled: session logging is not enabled"
    return status
