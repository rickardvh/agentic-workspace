from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import shlex
import sys
import uuid
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
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
SESSION_LOG_INDEX_KIND = "agentic-workspace/session-log-index/v1"
DEFAULT_MAX_INLINE_OUTPUT_BYTES = 64 * 1024
LARGE_OUTPUT_SUMMARY_LIMIT = 5


@dataclass(frozen=True)
class CommandCapture:
    exit_code: int
    stdout: str
    stderr: str
    exception: str | None = None


@dataclass(frozen=True)
class OutputSummary:
    stream: str
    kind: str
    bytes: int
    lines: int
    sha256: str
    first_line: str
    packet_kinds: tuple[str, ...]


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
    state = load_state_for_argv(argv_list, cwd=cwd)
    if not state.enabled:
        return runner(argv_list)

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


def _run_session_log_adapter(args: Any) -> int:
    target = getattr(args, "target", None)
    effective_argv = ["--target", str(target)] if target else []
    state = load_state_for_argv(effective_argv)
    output_stderr = sys.stderr
    try:
        command = str(getattr(args, "session_log_command", "status") or "status")
        if command == "note":
            payload = append_note(state=state, text=str(getattr(args, "text", "")))
        elif command == "new-session":
            payload = reset_session(state=state)
        elif command == "analyze":
            payload = analyze_session_log(state=state, path=str(getattr(args, "path", "") or ""))
        else:
            payload = status_payload(state=state)
    except Exception as exc:  # pragma: no cover - non-fatal command wrapper guard
        print(f"AW session logging warning: {exc}", file=output_stderr)
        return 0
    if getattr(args, "format", "text") == "json":
        print(json.dumps(serialise_value(payload), indent=2))
    else:
        print(_log_command_text(payload))
    return 0


def append_command_entry(*, state: SessionLoggingState, argv: Sequence[str], capture: CommandCapture) -> str | None:
    if not state.enabled:
        return None
    try:
        session = ensure_session(state=state)
        entry_id = f"cmd-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        command_text = "agentic-workspace " + shlex.join(list(argv))
        timestamp = datetime.now(UTC).isoformat()
        entry = _command_entry_markdown(
            state=state,
            session=session,
            entry_id=entry_id,
            timestamp=timestamp,
            command_text=command_text,
            capture=capture,
        )
        _append_text(state.target_root / session["log_path"], entry)
        _append_index_command(
            state=state,
            session=session,
            entry_id=entry_id,
            timestamp=timestamp,
            command_text=command_text,
            argv=argv,
            capture=capture,
        )
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
    note = _normalize_for_log(state, text.strip())
    _append_text(
        state.target_root / session["log_path"],
        f"\n## Agent Note - {timestamp}\n\n{note}\n",
    )
    _append_index_note(state=state, session=session, timestamp=timestamp, text=note)
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
        "index_path": _index_path_for_session(session).as_posix() if session else "",
        "session_id": session.get("session_id", "") if session else "",
        "path_redaction": _path_redaction_payload(state),
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
    _write_index(state=state, session=session, entries=(), notes=())
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
    log_path = _valid_session_log_path(str(payload.get("log_path", "")).strip())
    if not session_id or not log_path:
        return None
    return {
        "kind": SESSION_POINTER_KIND,
        "session_id": session_id,
        "created_at": str(payload.get("created_at", "")),
        "log_path": log_path,
    }


def _valid_session_log_path(value: str) -> str:
    if not value:
        return ""
    path = Path(value)
    if path.is_absolute() or path.drive or any(part == ".." for part in path.parts):
        return ""
    normalized = Path(*path.parts).as_posix()
    log_root = SESSION_LOG_ROOT.as_posix()
    if normalized == log_root or normalized.startswith(f"{log_root}/"):
        return normalized
    return ""


def _session_prelude(*, state: SessionLoggingState, session: dict[str, str]) -> str:
    snapshot = {
        "kind": SESSION_LOG_KIND,
        "session_id": session["session_id"],
        "created_at": session["created_at"],
        "target": _normalize_for_log(state, state.target_root.as_posix()),
        "package": {"name": "agentic-workspace", "version": __version__},
        "effective_config": _effective_config_snapshot(state),
        "logging_policy": {
            "enabled": state.enabled,
            "source": _logging_config_source(state),
            "root": SESSION_LOG_ROOT.as_posix(),
            "local_only": True,
            "authoritative": False,
            "redaction": _path_redaction_payload(state),
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
            "redact_local_paths": config.local_override.session_logging.redact_local_paths,
            "source": config.local_override.session_logging.source,
            "config_path": _normalize_for_log(
                state,
                config.local_override.path.as_posix() if config.local_override.path is not None else "",
            ),
        },
        "warnings": list(config.warnings),
    }


def _command_entry_markdown(
    *,
    state: SessionLoggingState,
    session: dict[str, str],
    entry_id: str,
    timestamp: str,
    command_text: str,
    capture: CommandCapture,
) -> str:
    normalized_capture = _normalized_capture(state, capture)
    output = {"stdout": normalized_capture.stdout, "stderr": normalized_capture.stderr}
    output_size = _output_size(normalized_capture)
    stdout_summary = _summarize_stream(stream="stdout", text=normalized_capture.stdout)
    stderr_summary = _summarize_stream(stream="stderr", text=normalized_capture.stderr)
    should_artifact = output_size > DEFAULT_MAX_INLINE_OUTPUT_BYTES or _structured_output_present(stdout_summary, stderr_summary)
    lines = [
        f"\n## Command - {timestamp}",
        "",
        f"- id: `{entry_id}`",
        f"- target: `{_normalize_for_log(state, state.target_root.as_posix())}`",
        f"- exit_status: `{normalized_capture.exit_code}`",
    ]
    if normalized_capture.exception:
        lines.append(f"- exception: `{normalized_capture.exception}`")
    lines.extend(["", "```sh", _normalize_for_log(state, command_text), "```"])
    if should_artifact:
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
        lines.extend(["", *_output_summary_lines(stdout_summary), *_output_summary_lines(stderr_summary)])
    else:
        lines.extend(
            [
                "",
                *_output_summary_lines(stdout_summary),
                *_output_summary_lines(stderr_summary),
                "",
                "stdout:",
                "```text",
                normalized_capture.stdout,
                "```",
                "",
                "stderr:",
                "```text",
                normalized_capture.stderr,
                "```",
            ]
        )
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


def _index_path_for_session(session: dict[str, str]) -> Path:
    return SESSION_LOG_ROOT / "indexes" / f"{session['session_id']}.json"


def _write_index(
    *, state: SessionLoggingState, session: dict[str, str], entries: Iterable[dict[str, Any]], notes: Iterable[dict[str, Any]]
) -> None:
    index_path = _index_path_for_session(session)
    payload = {
        "kind": SESSION_LOG_INDEX_KIND,
        "session_id": session["session_id"],
        "log_path": session["log_path"],
        "path": index_path.as_posix(),
        "created_at": session.get("created_at", ""),
        "updated_at": datetime.now(UTC).isoformat(),
        "path_redaction": _path_redaction_payload(state),
        "entries": list(entries),
        "notes": list(notes),
        "local_only": True,
        "authoritative": False,
    }
    absolute_path = state.target_root / index_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_index(*, state: SessionLoggingState, session: dict[str, str]) -> dict[str, Any] | None:
    path = state.target_root / _index_path_for_session(session)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("kind") != SESSION_LOG_INDEX_KIND:
        return None
    return payload


def _append_index_command(
    *,
    state: SessionLoggingState,
    session: dict[str, str],
    entry_id: str,
    timestamp: str,
    command_text: str,
    argv: Sequence[str],
    capture: CommandCapture,
) -> None:
    index = _read_index(state=state, session=session) or {}
    entries = _entries_from_index(index)
    notes = index.get("notes", []) if isinstance(index.get("notes"), list) else []
    normalized_capture = _normalized_capture(state, capture)
    stdout_summary = _summarize_stream(stream="stdout", text=normalized_capture.stdout)
    stderr_summary = _summarize_stream(stream="stderr", text=normalized_capture.stderr)
    output_digest = _output_digest(normalized_capture)
    artifact = _artifact_for_entry(state=state, session=session, entry_id=entry_id)
    entries.append(
        {
            "id": entry_id,
            "timestamp": timestamp,
            "command": _normalize_for_log(state, command_text),
            "argv": [_normalize_for_log(state, item) for item in argv],
            "target": _normalize_for_log(state, state.target_root.as_posix()),
            "exit_status": normalized_capture.exit_code,
            "exception": normalized_capture.exception or "",
            "stdout": _summary_payload(stdout_summary),
            "stderr": _summary_payload(stderr_summary),
            "output_bytes": _output_size(normalized_capture),
            "output_digest": output_digest,
            "packet_kinds": sorted(set(stdout_summary.packet_kinds + stderr_summary.packet_kinds)),
            "artifact": artifact,
        }
    )
    _write_index(state=state, session=session, entries=entries, notes=notes)


def _append_index_note(*, state: SessionLoggingState, session: dict[str, str], timestamp: str, text: str) -> None:
    index = _read_index(state=state, session=session) or {}
    entries = _entries_from_index(index)
    notes = index.get("notes", []) if isinstance(index.get("notes"), list) else []
    notes.append(
        {
            "timestamp": timestamp,
            "bytes": len(text.encode("utf-8")),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
    )
    _write_index(state=state, session=session, entries=entries, notes=notes)


def _entries_from_index(index: dict[str, Any]) -> list[dict[str, Any]]:
    entries = index.get("entries", [])
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def _normalized_capture(state: SessionLoggingState, capture: CommandCapture) -> CommandCapture:
    return CommandCapture(
        exit_code=capture.exit_code,
        stdout=_normalize_for_log(state, capture.stdout),
        stderr=_normalize_for_log(state, capture.stderr),
        exception=capture.exception,
    )


def _normalize_for_log(state: SessionLoggingState, text: str) -> str:
    if not text or state.config is None or not state.config.local_override.session_logging.redact_local_paths:
        return text
    replacements = {
        state.target_root.as_posix(),
        str(state.target_root),
        str(state.target_root).replace("\\", "\\\\"),
    }
    normalized = text
    for value in sorted(replacements, key=len, reverse=True):
        if value:
            normalized = normalized.replace(value, "<target>")
    return normalized


def _path_redaction_payload(state: SessionLoggingState) -> dict[str, Any]:
    enabled = bool(state.config and state.config.local_override.session_logging.redact_local_paths)
    return {
        "local_paths": "target-root-normalized" if enabled else "none",
        "placeholder": "<target>" if enabled else "",
        "rule": "Logs capture AW command argv and AW stdout/stderr only; environment variables and secrets are not logged by default.",
    }


def _summarize_stream(*, stream: str, text: str) -> OutputSummary:
    raw = text.encode("utf-8")
    stripped = text.strip()
    kind = "empty"
    packet_kinds: tuple[str, ...] = ()
    if stripped:
        parsed = _parse_jsonish(stripped)
        if parsed is not None:
            kind = "json"
            packet_kinds = tuple(sorted(_packet_kinds(parsed)))
        else:
            kind = "text"
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    return OutputSummary(
        stream=stream,
        kind=kind,
        bytes=len(raw),
        lines=len(text.splitlines()),
        sha256=hashlib.sha256(raw).hexdigest(),
        first_line=first_line[:160],
        packet_kinds=packet_kinds,
    )


def _parse_jsonish(text: str) -> Any | None:
    if not text or text[0] not in "[{":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _packet_kinds(value: Any) -> set[str]:
    kinds: set[str] = set()
    if isinstance(value, dict):
        kind = value.get("kind")
        if isinstance(kind, str) and kind:
            kinds.add(kind)
        for child in value.values():
            kinds.update(_packet_kinds(child))
    elif isinstance(value, list):
        for child in value:
            kinds.update(_packet_kinds(child))
    return kinds


def _structured_output_present(*summaries: OutputSummary) -> bool:
    return any(summary.kind == "json" and summary.bytes > 0 for summary in summaries)


def _output_size(capture: CommandCapture) -> int:
    return len(capture.stdout.encode("utf-8")) + len(capture.stderr.encode("utf-8"))


def _output_digest(capture: CommandCapture) -> str:
    raw = json.dumps({"stdout": capture.stdout, "stderr": capture.stderr}, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _summary_payload(summary: OutputSummary) -> dict[str, Any]:
    return {
        "kind": summary.kind,
        "bytes": summary.bytes,
        "lines": summary.lines,
        "sha256": summary.sha256,
        "first_line": summary.first_line,
        "packet_kinds": list(summary.packet_kinds),
    }


def _output_summary_lines(summary: OutputSummary) -> list[str]:
    lines = [
        f"{summary.stream} summary:",
        f"- kind: `{summary.kind}`",
        f"- bytes: `{summary.bytes}`",
        f"- lines: `{summary.lines}`",
    ]
    if summary.packet_kinds:
        lines.append(f"- packet_kinds: `{', '.join(summary.packet_kinds)}`")
    if summary.first_line:
        lines.append(f"- first_line: `{summary.first_line}`")
    return lines


def _artifact_for_entry(*, state: SessionLoggingState, session: dict[str, str], entry_id: str) -> dict[str, Any] | None:
    artifact_path = SESSION_LOG_ROOT / "artifacts" / session["session_id"] / f"{entry_id}-output.json"
    absolute_path = state.target_root / artifact_path
    if not absolute_path.exists():
        return None
    try:
        raw = absolute_path.read_bytes()
    except OSError:
        return {"path": artifact_path.as_posix()}
    return {"path": artifact_path.as_posix(), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _analysis_log_path(*, state: SessionLoggingState, path: str, session: dict[str, str] | None) -> Path | None:
    if path:
        valid = _valid_session_log_path(path)
        if not valid:
            return None
        candidate = state.target_root / valid
        return candidate if candidate.exists() else None
    if not session:
        return None
    candidate = state.target_root / session["log_path"]
    return candidate if candidate.exists() else None


def _read_index_for_log(*, state: SessionLoggingState, log_path: Path, session: dict[str, str] | None) -> dict[str, Any] | None:
    if session and (state.target_root / session.get("log_path", "")) == log_path:
        index = _read_index(state=state, session=session)
        if index is not None:
            return index
    match = re.match(r"aw-session-(?P<session_id>.+)\.md$", log_path.name)
    if not match:
        return None
    pseudo_session = {"session_id": match.group("session_id"), "log_path": log_path.relative_to(state.target_root).as_posix()}
    return _read_index(state=state, session=pseudo_session)


def _entries_from_markdown(log_path: Path) -> list[dict[str, Any]]:
    try:
        text = log_path.read_text(encoding="utf-8-sig")
    except OSError:
        return []
    entries: list[dict[str, Any]] = []
    sections = re.split(r"\n## Command - ", text)
    for section in sections[1:]:
        timestamp = section.splitlines()[0].strip()
        entry_id = _regex_value(section, r"- id: `([^`]+)`")
        status = _regex_value(section, r"- exit_status: `([^`]+)`")
        command_match = re.search(r"```sh\n(?P<command>.*?)\n```", section, re.S)
        command = command_match.group("command").strip() if command_match else ""
        artifact = _regex_value(section, r"- path: `([^`]+)`")
        output_bytes = int(_regex_value(section, r"- bytes: `?([0-9]+)`?") or 0)
        entries.append(
            {
                "id": entry_id,
                "timestamp": timestamp,
                "command": command,
                "exit_status": int(status or 0),
                "output_bytes": output_bytes,
                "output_digest": "",
                "packet_kinds": [],
                "artifact": {"path": artifact} if artifact else None,
            }
        )
    return entries


def _regex_value(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _entry_brief(entry: dict[str, Any]) -> dict[str, Any]:
    artifact = entry.get("artifact") if isinstance(entry.get("artifact"), dict) else {}
    return {
        "id": entry.get("id", ""),
        "timestamp": entry.get("timestamp", ""),
        "command": entry.get("command", ""),
        "exit_status": entry.get("exit_status", 0),
        "output_bytes": entry.get("output_bytes", 0),
        "artifact_path": artifact.get("path", "") if isinstance(artifact, dict) else "",
        "packet_kinds": entry.get("packet_kinds", []),
    }


def _friction_candidates(
    *,
    entries: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    repeated: list[dict[str, Any]],
    duplicates: list[dict[str, Any]],
    index_present: bool,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if not index_present:
        candidates.append(
            {
                "id": "missing-index",
                "summary": "Log has no machine-readable index; analysis used markdown fallback.",
                "owner": "session-log format",
            }
        )
    for entry in failures[:LARGE_OUTPUT_SUMMARY_LIMIT]:
        candidates.append(
            {
                "id": "failed-command",
                "summary": f"Command exited {entry.get('exit_status')}: {entry.get('command', '')}",
                "owner": "command/runtime",
            }
        )
    for item in repeated[:LARGE_OUTPUT_SUMMARY_LIMIT]:
        candidates.append(
            {
                "id": "repeated-command",
                "summary": f"Repeated {item['count']} times: {item['command']}",
                "owner": "operating-loop",
            }
        )
    for item in duplicates[:LARGE_OUTPUT_SUMMARY_LIMIT]:
        candidates.append(
            {
                "id": "duplicate-output",
                "summary": f"Same output digest appeared {item['count']} times.",
                "owner": "operating-loop",
            }
        )
    for entry in entries:
        if int(entry.get("output_bytes", 0) or 0) > DEFAULT_MAX_INLINE_OUTPUT_BYTES:
            command = str(entry.get("command", ""))
            candidates.append(
                {
                    "id": "large-output",
                    "summary": f"Large command output ({entry.get('output_bytes')} bytes): {command}",
                    "owner": "command-output",
                }
            )
            if " modules" in command or command.endswith(" modules"):
                candidates.append(
                    {
                        "id": "oversized-modules-output",
                        "summary": "modules output exceeded the inline threshold; use #2133 for compact section-addressable output.",
                        "owner": "#2133",
                    }
                )
    return candidates[:20]


def analyze_session_log(*, state: SessionLoggingState, path: str = "") -> dict[str, Any]:
    session = read_session_pointer(target_root=state.target_root)
    log_path = _analysis_log_path(state=state, path=path, session=session)
    if log_path is None:
        return {
            "kind": "agentic-workspace/session-log-analysis/v1",
            "status": "missing-log",
            "enabled": state.enabled,
            "path": "",
            "index_status": "missing",
            "rule": "Pass --path or create a session with session-log new-session before analyzing logs.",
        }

    index = _read_index_for_log(state=state, log_path=log_path, session=session)
    entries = _entries_from_index(index) if index is not None else _entries_from_markdown(log_path)
    notes = index.get("notes", []) if isinstance(index, dict) and isinstance(index.get("notes"), list) else []
    command_counter = Counter(str(entry.get("command", "")) for entry in entries if entry.get("command"))
    digest_counter = Counter(str(entry.get("output_digest", "")) for entry in entries if entry.get("output_digest"))
    failures = [entry for entry in entries if int(entry.get("exit_status", 0) or 0) != 0]
    largest = sorted(entries, key=lambda entry: int(entry.get("output_bytes", 0) or 0), reverse=True)[:LARGE_OUTPUT_SUMMARY_LIMIT]
    repeated = [{"command": command, "count": count} for command, count in command_counter.most_common() if count > 1 and command]
    duplicates = [{"sha256": digest, "count": count} for digest, count in digest_counter.most_common() if count > 1 and digest]
    packet_kinds = Counter(
        packet_kind for entry in entries for packet_kind in entry.get("packet_kinds", []) if isinstance(packet_kind, str) and packet_kind
    )
    friction_candidates = _friction_candidates(
        entries=entries,
        failures=failures,
        repeated=repeated,
        duplicates=duplicates,
        index_present=index is not None,
    )
    return {
        "kind": "agentic-workspace/session-log-analysis/v1",
        "status": "analyzed",
        "enabled": state.enabled,
        "path": log_path.relative_to(state.target_root).as_posix(),
        "index_status": "present" if index is not None else "markdown-fallback",
        "index_path": str(index.get("path", "")) if isinstance(index, dict) else "",
        "summary": {
            "command_count": len(entries),
            "note_count": len(notes),
            "failure_count": len(failures),
            "repeated_command_count": len(repeated),
            "duplicate_output_count": len(duplicates),
            "artifact_count": sum(1 for entry in entries if entry.get("artifact")),
        },
        "failed_commands": [_entry_brief(entry) for entry in failures],
        "repeated_commands": repeated[:LARGE_OUTPUT_SUMMARY_LIMIT],
        "largest_outputs": [_entry_brief(entry) for entry in largest],
        "duplicate_outputs": duplicates[:LARGE_OUTPUT_SUMMARY_LIMIT],
        "packet_kinds": dict(sorted(packet_kinds.items())),
        "friction_candidates": friction_candidates,
        "local_only": True,
        "authoritative": False,
        "rule": "Session-log analysis is dogfooding evidence only; promote durable facts into Planning, Memory, docs, proof, or issues intentionally.",
    }


def _system_exit_code(exc: SystemExit) -> int:
    if isinstance(exc.code, int):
        return exc.code
    if exc.code in (None, ""):
        return 0
    return 1


def _log_command_text(payload: dict[str, Any]) -> str:
    if payload.get("kind") == "agentic-workspace/session-log-analysis/v1":
        summary = payload.get("summary", {})
        if not isinstance(summary, dict):
            summary = {}
        return (
            f"analyzed: {payload.get('path', '')}\n"
            f"commands: {summary.get('command_count', 0)}, failures: {summary.get('failure_count', 0)}, "
            f"repeated: {summary.get('repeated_command_count', 0)}, duplicates: {summary.get('duplicate_output_count', 0)}"
        )
    status = str(payload.get("status", "unknown"))
    path = str(payload.get("path", ""))
    if path:
        return f"{status}: {path}"
    if payload.get("enabled") is False:
        return "disabled: session logging is not enabled"
    return status
