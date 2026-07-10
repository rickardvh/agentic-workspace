from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import shlex
import subprocess
import sys
import time
import tomllib
import uuid
import zipfile
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Sequence
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
SESSION_REGISTRY_PATH = Path(".agentic-workspace") / "local" / "session-logging" / "sessions.json"
SESSION_REGISTRY_LOCK_PATH = Path(".agentic-workspace") / "local" / "session-logging" / ".sessions.lock"
SESSION_REGISTRY_KIND = "agentic-workspace/session-logging-registry/v1"
LOGICAL_SESSION_IDENTITY_ENV = "AW_SESSION_LOGICAL_IDENTITY"
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
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0


@dataclass(frozen=True)
class OutputSummary:
    stream: str
    kind: str
    bytes: int
    lines: int
    sha256: str
    first_line: str
    top_level_kind: str
    packet_kinds: tuple[str, ...]
    domain_kinds: tuple[str, ...]


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
    record_command = not (argv_list and argv_list[0] == "session-log" and any(token in {"repair", "export"} for token in argv_list[1:]))

    output_stdout = stdout or sys.stdout
    output_stderr = stderr or sys.stderr
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    capture = CommandCapture(exit_code=0, stdout="", stderr="")
    started_at = datetime.now(UTC).isoformat()
    started = time.monotonic()
    try:
        try:
            with (
                contextlib.redirect_stdout(captured_stdout),
                contextlib.redirect_stderr(captured_stderr),
                _session_parent_environment(argv_list),
            ):
                exit_code = int(runner(argv_list))
            capture = CommandCapture(
                exit_code=exit_code,
                stdout=captured_stdout.getvalue(),
                stderr=captured_stderr.getvalue(),
                started_at=started_at,
                finished_at=datetime.now(UTC).isoformat(),
                duration_ms=max(0, round((time.monotonic() - started) * 1000)),
            )
            return exit_code
        except SystemExit as exc:
            exit_code = _system_exit_code(exc)
            capture = CommandCapture(
                exit_code=exit_code,
                stdout=captured_stdout.getvalue(),
                stderr=captured_stderr.getvalue(),
                exception="SystemExit" if exit_code != 0 else None,
                started_at=started_at,
                finished_at=datetime.now(UTC).isoformat(),
                duration_ms=max(0, round((time.monotonic() - started) * 1000)),
            )
            raise
        except Exception as exc:
            capture = CommandCapture(
                exit_code=1,
                stdout=captured_stdout.getvalue(),
                stderr=captured_stderr.getvalue(),
                exception=exc.__class__.__name__,
                started_at=started_at,
                finished_at=datetime.now(UTC).isoformat(),
                duration_ms=max(0, round((time.monotonic() - started) * 1000)),
            )
            raise
    finally:
        if capture.stdout:
            print(capture.stdout, end="", file=output_stdout)
        if capture.stderr:
            print(capture.stderr, end="", file=output_stderr)
        warning = append_command_entry(state=state, argv=argv_list, capture=capture) if record_command else None
        if warning:
            print(f"AW session logging warning: {warning}", file=output_stderr)


@contextlib.contextmanager
def _session_parent_environment(argv: Sequence[str]) -> Iterator[None]:
    updates = {
        "AW_SESSION_LOG_PARENT_COMMAND": "agentic-workspace " + shlex.join(list(argv)),
        "AW_SESSION_LOG_PARENT_CONTEXT": os.environ.get("PYTEST_CURRENT_TEST", "") or "aw-command",
    }
    previous = {key: os.environ.get(key) for key in updates}
    os.environ.update(updates)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


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
            payload = analyze_session_log(
                state=state,
                path=str(getattr(args, "path", "") or ""),
                session_id=str(getattr(args, "id", "") or ""),
                segment_id=str(getattr(args, "segment", "") or ""),
            )
        elif command == "repair":
            payload = repair_session_log_index(
                state=state,
                path=str(getattr(args, "path", "") or ""),
                session_id=str(getattr(args, "id", "") or ""),
            )
        elif command == "export":
            payload = export_session_log(
                state=state,
                path=str(getattr(args, "path", "") or ""),
                session_id=str(getattr(args, "id", "") or ""),
                include_artifacts=not bool(getattr(args, "no_artifacts", False)),
            )
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
        index = _read_index(state=state, session=session) or {}
        prior_entries = _entries_from_index(index)
        origin = _command_origin()
        provenance = _command_provenance(state=state)
        segment = _segment_metadata(
            state=state,
            argv=argv,
            command_text=command_text,
            capture=capture,
            provenance=provenance,
            prior_entries=prior_entries,
        )
        expected_failure = capture.exit_code != 0 and _expected_fixture_failure(origin)
        entry = _command_entry_markdown(
            state=state,
            session=session,
            entry_id=entry_id,
            timestamp=timestamp,
            command_text=command_text,
            capture=capture,
            origin=origin,
            expected_failure=expected_failure,
            provenance=provenance,
            segment=segment,
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
            origin=origin,
            expected_failure=expected_failure,
            provenance=provenance,
            segment=segment,
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
    logical_identity = _logical_session_identity()
    session = _session_for_caller(target_root=state.target_root, logical_identity=logical_identity)
    return {
        "kind": "agentic-workspace/session-logging-status/v1",
        "enabled": state.enabled,
        "target": state.target_root.as_posix(),
        "config_source": _logging_config_source(state),
        "path": session.get("log_path", "") if session else "",
        "index_path": _index_path_for_session(session).as_posix() if session else "",
        "session_id": session.get("session_id", "") if session else "",
        "logical_session_resolution": "identity-registry" if logical_identity else "legacy-default-bucket",
        "logical_session_identity_source": LOGICAL_SESSION_IDENTITY_ENV if logical_identity else "",
        "raw_logical_session_identity_stored": False,
        "path_redaction": _path_redaction_payload(state),
        "local_only": True,
        "authoritative": False,
        "rule": "Session logs are local dogfooding evidence, not Planning state, Memory, proof receipts, or closeout authorization.",
    }


def ensure_session(*, state: SessionLoggingState, force_new: bool = False, logical_identity: str | None = None) -> dict[str, str]:
    identity = _logical_session_identity() if logical_identity is None else logical_identity.strip()
    with _session_registry_lock(target_root=state.target_root):
        registry_existed = (state.target_root / SESSION_REGISTRY_PATH).is_file()
        registry = _read_session_registry(target_root=state.target_root)
        sessions = registry.setdefault("sessions", {})
        legacy_pointer = read_session_pointer(target_root=state.target_root)
        if not registry_existed and isinstance(sessions, dict) and "default" not in sessions and legacy_pointer is not None:
            sessions["default"] = legacy_pointer
            registry["updated_at"] = datetime.now(UTC).isoformat()
        registry_key = _logical_identity_fingerprint(identity=identity, registry=registry) if identity else "default"
        current = None
        if not force_new:
            current = _registered_session(registry=registry, registry_key=registry_key, target_root=state.target_root)
            if current is None and not identity:
                current = read_session_pointer(target_root=state.target_root)
        if current:
            if isinstance(sessions, dict) and sessions.get(registry_key) != current:
                sessions[registry_key] = current
                registry["updated_at"] = datetime.now(UTC).isoformat()
                _write_json_atomic(state.target_root / SESSION_REGISTRY_PATH, registry)
            _write_session_pointer(target_root=state.target_root, session=current)
            return current
        session = _create_session(state=state)
        if isinstance(sessions, dict):
            sessions[registry_key] = session
        registry["updated_at"] = datetime.now(UTC).isoformat()
        _write_json_atomic(state.target_root / SESSION_REGISTRY_PATH, registry)
        _write_session_pointer(target_root=state.target_root, session=session)
        return session


def _create_session(*, state: SessionLoggingState) -> dict[str, str]:
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
    _write_index(state=state, session=session, entries=(), notes=())
    return session


def _logical_session_identity() -> str:
    return os.environ.get(LOGICAL_SESSION_IDENTITY_ENV, "").strip()


def _new_session_registry() -> dict[str, Any]:
    return {
        "kind": SESSION_REGISTRY_KIND,
        "salt": uuid.uuid4().hex,
        "sessions": {},
        "updated_at": datetime.now(UTC).isoformat(),
        "local_only": True,
        "authoritative": False,
    }


def _read_session_registry(*, target_root: Path) -> dict[str, Any]:
    path = target_root / SESSION_REGISTRY_PATH
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return _new_session_registry()
    if (
        not isinstance(payload, dict)
        or payload.get("kind") != SESSION_REGISTRY_KIND
        or not isinstance(payload.get("salt"), str)
        or not isinstance(payload.get("sessions"), dict)
    ):
        return _new_session_registry()
    return payload


def _logical_identity_fingerprint(*, identity: str, registry: dict[str, Any]) -> str:
    salt = str(registry.get("salt", ""))
    return hashlib.sha256(f"{salt}\0{identity}".encode()).hexdigest()


def _registered_session(*, registry: dict[str, Any], registry_key: str, target_root: Path) -> dict[str, str] | None:
    sessions = registry.get("sessions", {})
    candidate = sessions.get(registry_key) if isinstance(sessions, dict) else None
    session = _validated_session(candidate)
    if session and (target_root / session["log_path"]).is_file():
        return session
    return None


def _session_for_caller(*, target_root: Path, logical_identity: str) -> dict[str, str] | None:
    registry = _read_session_registry(target_root=target_root)
    registry_key = _logical_identity_fingerprint(identity=logical_identity, registry=registry) if logical_identity else "default"
    registered = _registered_session(registry=registry, registry_key=registry_key, target_root=target_root)
    if registered is not None or logical_identity:
        return registered
    return read_session_pointer(target_root=target_root)


def _write_session_pointer(*, target_root: Path, session: dict[str, str]) -> None:
    _write_json_atomic(target_root / SESSION_POINTER_PATH, session)


@contextlib.contextmanager
def _session_registry_lock(*, target_root: Path) -> Iterator[None]:
    lock_path = target_root / SESSION_REGISTRY_LOCK_PATH
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 5
    while True:
        try:
            lock_path.mkdir()
            break
        except FileExistsError:
            try:
                stale = time.time() - lock_path.stat().st_mtime > 30
            except OSError:
                stale = False
            if stale:
                with contextlib.suppress(OSError):
                    lock_path.rmdir()
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"timed out waiting for session registry lock: {lock_path}")
            time.sleep(0.01)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            lock_path.rmdir()


def read_session_pointer(*, target_root: Path) -> dict[str, str] | None:
    pointer_path = target_root / SESSION_POINTER_PATH
    if not pointer_path.exists():
        return None
    try:
        payload = json.loads(pointer_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return _validated_session(payload)


def _validated_session(payload: Any) -> dict[str, str] | None:
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
            "logical_session": {
                "resolution": "identity-registry" if _logical_session_identity() else "legacy-default-bucket",
                "identity_source": LOGICAL_SESSION_IDENTITY_ENV if _logical_session_identity() else "",
                "raw_identity_stored": False,
            },
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
            "argv0": _normalize_for_log(state, sys.argv[0] if sys.argv else ""),
            "python_executable": _normalize_for_log(state, sys.executable),
        },
        "session_logging": {
            "enabled": config.local_override.session_logging.enabled,
            "redact_local_paths": config.local_override.session_logging.redact_local_paths,
            "path_mode": config.local_override.session_logging.path_mode,
            "source": config.local_override.session_logging.source,
            "config_path": _normalize_for_log(
                state,
                config.local_override.path.as_posix() if config.local_override.path is not None else "",
            ),
        },
        "warnings": list(config.warnings),
    }


def _command_origin() -> dict[str, Any]:
    explicit = os.environ.get("AW_SESSION_LOG_ORIGIN", "").strip().lower()
    allowed = {"agent", "pytest", "validation", "nested-aw", "unknown"}
    if explicit:
        return {
            "classification": explicit if explicit in allowed else "unknown",
            "source": "AW_SESSION_LOG_ORIGIN",
            "detail": explicit if explicit not in allowed else "",
        }
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return {"classification": "pytest", "source": "PYTEST_CURRENT_TEST", "detail": ""}
    if os.environ.get("AW_VALIDATION_CONTEXT") or os.environ.get("AW_VALIDATION"):
        return {"classification": "validation", "source": "AW_VALIDATION_CONTEXT", "detail": ""}
    if os.environ.get("AW_SESSION_LOG_PARENT_COMMAND") or os.environ.get("AW_SESSION_LOG_PARENT_ENTRY_ID"):
        return {"classification": "nested-aw", "source": "AW_SESSION_LOG_PARENT_COMMAND", "detail": ""}
    return {"classification": "agent", "source": "ordinary-cli", "detail": ""}


def _expected_fixture_failure(origin: dict[str, Any]) -> bool:
    explicit = os.environ.get("AW_SESSION_LOG_EXPECTED_FAILURE", "").strip().lower()
    return explicit in {"1", "true", "yes"}


def _parent_context() -> dict[str, str]:
    return {
        "entry_id": os.environ.get("AW_SESSION_LOG_PARENT_ENTRY_ID", ""),
        "command": os.environ.get("AW_SESSION_LOG_PARENT_COMMAND", ""),
        "context": os.environ.get("AW_SESSION_LOG_PARENT_CONTEXT", ""),
    }


def _git_value(target_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=target_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _command_provenance(*, state: SessionLoggingState) -> dict[str, Any]:
    head = _git_value(state.target_root, "rev-parse", "HEAD")
    branch = _git_value(state.target_root, "branch", "--show-current")
    dirty_output = _git_value(state.target_root, "status", "--porcelain", "--untracked-files=no")
    return {
        "aw_package": "agentic-workspace",
        "aw_version": __version__,
        "source_commit": os.environ.get("AW_SOURCE_COMMIT", "") or head,
        "branch": branch,
        "head": head,
        "dirty": bool(dirty_output),
        "python": _normalize_for_log(state, sys.executable),
    }


def _option_value(argv: Sequence[str], name: str) -> str:
    tokens = list(argv)
    for index, token in enumerate(tokens):
        if token == name and index + 1 < len(tokens):
            return tokens[index + 1]
        if token.startswith(f"{name}="):
            return token.split("=", 1)[1]
    return ""


def _active_plan_id(target_root: Path) -> str:
    state_path = target_root / ".agentic-workspace" / "planning" / "state.toml"
    try:
        payload = tomllib.loads(state_path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError):
        return ""
    todo = payload.get("todo", {})
    items = todo.get("active_items", []) if isinstance(todo, dict) else []
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        return ""
    return str(items[0].get("id", ""))


def _is_closeout_transition(argv: Sequence[str]) -> bool:
    tokens = list(argv)
    return len(tokens) >= 2 and tokens[:2] in (["planning", "archive-plan"], ["planning", "closeout"]) and "--dry-run" not in tokens


def _segment_metadata(
    *,
    state: SessionLoggingState,
    argv: Sequence[str],
    command_text: str,
    capture: CommandCapture,
    provenance: dict[str, Any],
    prior_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    prior_segment = prior_entries[-1].get("segment", {}) if prior_entries else {}
    if not isinstance(prior_segment, dict):
        prior_segment = {}
    task = _option_value(argv, "--task") or str(prior_segment.get("task", ""))
    plan_id = _active_plan_id(state.target_root) or str(prior_segment.get("plan_id", ""))
    if "new-plan" in argv:
        plan_id = _option_value(argv, "--id") or plan_id
    explicit_pr = os.environ.get("AW_SESSION_LOG_PR", "").lstrip("#")
    pr_matches = re.findall(r"\bPR\s+#?(\d+)\b", f"{task} {command_text}", flags=re.I)
    pr_ref = (
        f"#{explicit_pr or (pr_matches[-1] if pr_matches else '')}" if explicit_pr or pr_matches else str(prior_segment.get("pr_ref", ""))
    )
    refs = sorted({f"#{value}" for value in re.findall(r"#(\d+)", f"{task} {command_text}")})
    issue_refs = [ref for ref in refs if ref != pr_ref]
    if not issue_refs and isinstance(prior_segment.get("issue_refs"), list):
        issue_refs = [str(ref) for ref in prior_segment["issue_refs"]]
    if _is_closeout_transition(argv):
        closeout_status = "closed" if capture.exit_code == 0 else "attempted"
    else:
        closeout_status = str(prior_segment.get("closeout_status", "open") or "open")
    identity = {
        "task": task,
        "plan_id": plan_id,
        "branch": str(provenance.get("branch", "")),
        "head": str(provenance.get("head", "")),
        "pr_ref": pr_ref,
        "closeout_status": closeout_status,
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return {
        "id": f"segment-{digest}",
        **identity,
        "issue_refs": issue_refs,
        "authoritative": False,
    }


def _command_entry_markdown(
    *,
    state: SessionLoggingState,
    session: dict[str, str],
    entry_id: str,
    timestamp: str,
    command_text: str,
    capture: CommandCapture,
    origin: dict[str, Any],
    expected_failure: bool,
    provenance: dict[str, Any],
    segment: dict[str, Any],
) -> str:
    normalized_capture = _normalized_capture(state, capture)
    output_size = _output_size(normalized_capture)
    output_digest = _output_digest(normalized_capture)
    stdout_summary = _summarize_stream(stream="stdout", text=normalized_capture.stdout)
    stderr_summary = _summarize_stream(stream="stderr", text=normalized_capture.stderr)
    should_artifact = output_size > DEFAULT_MAX_INLINE_OUTPUT_BYTES or _structured_output_present(stdout_summary, stderr_summary)
    lines = [
        f"\n## Command - {timestamp}",
        "",
        f"- id: `{entry_id}`",
        f"- target: `{_normalize_for_log(state, state.target_root.as_posix())}`",
        f"- exit_status: `{normalized_capture.exit_code}`",
        f"- origin: `{origin['classification']}`",
        f"- expected_failure: `{'true' if expected_failure else 'false'}`",
        f"- segment_id: `{segment['id']}`",
        f"- provenance: `{json.dumps(serialise_value(provenance), sort_keys=True)}`",
        f"- segment: `{json.dumps(serialise_value(segment), sort_keys=True)}`",
    ]
    if normalized_capture.exception:
        lines.append(f"- exception: `{normalized_capture.exception}`")
    lines.extend(["", "```sh", _normalize_for_log(state, command_text), "```"])
    if should_artifact:
        raw_output = {"stdout": capture.stdout, "stderr": capture.stderr}
        artifact = _write_output_artifact(
            state=state,
            session=session,
            entry_id=entry_id,
            output=raw_output,
            output_digest=output_digest,
        )
        lines.extend(
            [
                "",
                "Output stored as local artifact:",
                f"- path: `{artifact['path']}`",
                f"- sha256: `{artifact['sha256']}`",
                f"- bytes: `{artifact['bytes']}`",
            ]
        )
        if artifact.get("duplicate_of"):
            lines.append(f"- duplicate_of: `{artifact['duplicate_of']}`")
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
    output_digest: str,
) -> dict[str, Any]:
    existing = _artifact_for_output_digest(state=state, session=session, output_digest=output_digest)
    if existing is not None:
        return {
            **existing,
            "duplicate_of": str(existing.get("entry_id", "")),
            "storage_mode": "reused-duplicate",
        }
    artifact_path = SESSION_LOG_ROOT / "artifacts" / session["session_id"] / f"{entry_id}-output.json"
    payload = {
        "kind": "agentic-workspace/session-log-output-artifact/v1",
        "entry_id": entry_id,
        "storage_mode": "raw-local-artifact",
        "share_safe": False,
        "rule": "Raw command output is recoverable locally from ignored session-log artifacts; markdown and indexes use the configured path mode.",
        "stdout": output["stdout"],
        "stderr": output["stderr"],
    }
    raw = json.dumps(payload, indent=2)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    absolute_path = state.target_root / artifact_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_text(raw + "\n", encoding="utf-8")
    return {
        "path": artifact_path.as_posix(),
        "sha256": digest,
        "bytes": len(raw.encode("utf-8")),
        "entry_id": entry_id,
        "storage_mode": "raw-local-artifact",
    }


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
    _write_json_atomic(absolute_path, payload)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.{uuid.uuid4().hex}.tmp")
    temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_path.replace(path)


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
    origin: dict[str, Any],
    expected_failure: bool,
    provenance: dict[str, Any],
    segment: dict[str, Any],
) -> None:
    index = _read_index(state=state, session=session) or {}
    entries = _entries_from_index(index)
    notes = index.get("notes", []) if isinstance(index.get("notes"), list) else []
    normalized_capture = _normalized_capture(state, capture)
    stdout_summary = _summarize_stream(stream="stdout", text=normalized_capture.stdout)
    stderr_summary = _summarize_stream(stream="stderr", text=normalized_capture.stderr)
    output_digest = _output_digest(normalized_capture)
    artifact = _artifact_for_entry(state=state, session=session, entry_id=entry_id)
    if artifact is None:
        artifact = _artifact_for_output_digest(state=state, session=session, output_digest=output_digest)
        if artifact is not None:
            artifact = {**artifact, "duplicate_of": str(artifact.get("entry_id", "")), "storage_mode": "reused-duplicate"}
    failure_class = _failure_class(command_text=command_text, capture=normalized_capture)
    entries.append(
        {
            "id": entry_id,
            "timestamp": timestamp,
            "started_at": capture.started_at or timestamp,
            "finished_at": capture.finished_at or timestamp,
            "duration_ms": capture.duration_ms,
            "command": _normalize_for_log(state, command_text),
            "argv": [_normalize_for_log(state, item) for item in argv],
            "target": _normalize_for_log(state, state.target_root.as_posix()),
            "exit_status": normalized_capture.exit_code,
            "exit_class": "success" if normalized_capture.exit_code == 0 else "failure",
            "failure_class": failure_class,
            "expected_failure": expected_failure,
            "origin": origin,
            "parent_context": _parent_context(),
            "provenance": provenance,
            "segment": segment,
            "exception": normalized_capture.exception or "",
            "stdout": _summary_payload(stdout_summary),
            "stderr": _summary_payload(stderr_summary),
            "output_bytes": _output_size(normalized_capture),
            "output_digest": output_digest,
            "storage_mode": artifact.get("storage_mode", "inline") if isinstance(artifact, dict) else "inline",
            "top_level_kinds": sorted({value for value in (stdout_summary.top_level_kind, stderr_summary.top_level_kind) if value}),
            "packet_kinds": sorted(set(stdout_summary.packet_kinds + stderr_summary.packet_kinds)),
            "domain_kinds": sorted(set(stdout_summary.domain_kinds + stderr_summary.domain_kinds)),
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
        started_at=capture.started_at,
        finished_at=capture.finished_at,
        duration_ms=capture.duration_ms,
    )


def _normalize_for_log(state: SessionLoggingState, text: str) -> str:
    if not text or state.config is None:
        return text
    mode = state.config.local_override.session_logging.path_mode
    if mode == "absolute":
        return text
    normalized = text
    target_native = str(state.target_root)
    target_escaped = target_native.replace("\\", "\\\\")
    home_native = str(Path.home())
    home_escaped = home_native.replace("\\", "\\\\")
    python_native = sys.executable
    python_escaped = python_native.replace("\\", "\\\\")
    if mode == "repo-relative":
        replacements = {
            f"{state.target_root.as_posix()}/": "./",
            f"{target_native}\\": ".\\",
            f"{target_escaped}\\\\": ".\\\\",
            state.target_root.as_posix(): ".",
            target_native: ".",
            target_escaped: ".",
        }
    elif mode == "redacted":
        replacements = {
            state.target_root.as_posix(): "<target>",
            target_native: "<target>",
            target_escaped: "<target>",
            home_native: "<home>",
            Path.home().as_posix(): "<home>",
            home_escaped: "<home>",
            python_native: "<python>",
            Path(python_native).as_posix(): "<python>",
            python_escaped: "<python>",
        }
    else:
        return text
    for value, replacement in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        if value:
            normalized = normalized.replace(value, replacement)
    return normalized


def _path_redaction_payload(state: SessionLoggingState) -> dict[str, Any]:
    mode = state.config.local_override.session_logging.path_mode if state.config else "absolute"
    placeholders = {
        "absolute": [],
        "repo-relative": ["."],
        "redacted": ["<target>", "<home>", "<python>"],
    }.get(mode, [])
    return {
        "mode": mode,
        "local_paths": "absolute" if mode == "absolute" else "normalized",
        "placeholders": placeholders,
        "raw_artifact_recoverability": "raw output may remain in ignored local artifacts; do not share .agentic-workspace/local artifacts without review",
        "limitations": "Only known AW command text, target-root, user-home, and Python executable path strings are normalized.",
        "rule": "Logs capture AW command argv and AW stdout/stderr only; environment variables and secrets are not logged by default.",
    }


def _summarize_stream(*, stream: str, text: str) -> OutputSummary:
    raw = text.encode("utf-8")
    stripped = text.strip()
    kind = "empty"
    top_level_kind = ""
    packet_kinds: tuple[str, ...] = ()
    domain_kinds: tuple[str, ...] = ()
    if stripped:
        parsed = _parse_jsonish(stripped)
        if parsed is not None:
            kind = "json"
            top_level_kind, packet_values, domain_values = _kind_classes(parsed)
            packet_kinds = tuple(sorted(packet_values))
            domain_kinds = tuple(sorted(domain_values))
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
        top_level_kind=top_level_kind,
        packet_kinds=packet_kinds,
        domain_kinds=domain_kinds,
    )


def _parse_jsonish(text: str) -> Any | None:
    if not text or text[0] not in "[{":
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _is_schema_packet_kind(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)+/v\d+", value, flags=re.I))


def _kind_classes(value: Any) -> tuple[str, set[str], set[str]]:
    top_level = str(value.get("kind", "")) if isinstance(value, dict) and isinstance(value.get("kind"), str) else ""
    packet_kinds: set[str] = set()
    domain_kinds: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            kind = item.get("kind")
            if isinstance(kind, str) and kind:
                (packet_kinds if _is_schema_packet_kind(kind) else domain_kinds).add(kind)
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return top_level, packet_kinds, domain_kinds


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
        "top_level_kind": summary.top_level_kind,
        "packet_kinds": list(summary.packet_kinds),
        "domain_kinds": list(summary.domain_kinds),
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
    if summary.domain_kinds:
        lines.append(f"- domain_kinds: `{', '.join(summary.domain_kinds)}`")
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
    return {
        "path": artifact_path.as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "entry_id": entry_id,
        "storage_mode": "raw-local-artifact",
    }


def _artifact_for_output_digest(*, state: SessionLoggingState, session: dict[str, str], output_digest: str) -> dict[str, Any] | None:
    index = _read_index(state=state, session=session) or {}
    for entry in _entries_from_index(index):
        if str(entry.get("output_digest", "")) != output_digest:
            continue
        artifact = entry.get("artifact")
        if not isinstance(artifact, dict) or not artifact.get("path"):
            continue
        return {**artifact, "entry_id": str(entry.get("id", ""))}
    return None


def _failure_class(*, command_text: str, capture: CommandCapture) -> str:
    if capture.exit_code == 0:
        return ""
    parsed = _parse_jsonish(capture.stdout.strip()) or _parse_jsonish(capture.stderr.strip())
    if isinstance(parsed, dict) and str(parsed.get("kind", "")).endswith("/retryable-cli-error/v1"):
        return str(parsed.get("failure_class") or "retryable-cli-usage")
    command = command_text.lower()
    stderr = capture.stderr.lower()
    if "--verbose" in command and "--section" in command:
        return "selector-conflict"
    if "invalid choice" in stderr or "did you mean" in stderr:
        return "invalid-command"
    if "usage:" in stderr or "error:" in stderr:
        return "usage-error"
    return "command-failure"


def _analysis_log_path(*, state: SessionLoggingState, path: str, session_id: str = "", session: dict[str, str] | None) -> Path | None:
    if path:
        valid = _valid_session_log_path(path)
        if not valid:
            return None
        candidate = state.target_root / valid
        return candidate if candidate.exists() else None
    if session_id:
        cleaned = session_id.strip()
        if cleaned.startswith("aw-session-") and cleaned.endswith(".md"):
            candidate_name = cleaned
        elif cleaned.startswith("aw-session-"):
            candidate_name = f"{cleaned}.md"
        else:
            candidate_name = f"aw-session-{cleaned}.md"
        candidate = state.target_root / SESSION_LOG_ROOT / candidate_name
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
        if not entry_id:
            entry_id = "legacy-" + hashlib.sha256(f"{timestamp}\n{command}".encode("utf-8")).hexdigest()[:16]
        stdout = _markdown_labeled_fence(section, "stdout")
        stderr = _markdown_labeled_fence(section, "stderr")
        exit_status = int(status or 0)
        capture = CommandCapture(exit_code=exit_status, stdout=stdout, stderr=stderr)
        stdout_summary = _summarize_stream(stream="stdout", text=stdout)
        stderr_summary = _summarize_stream(stream="stderr", text=stderr)
        artifact = _regex_value(section, r"- path: `([^`]+)`")
        artifact_sha256 = _regex_value(section, r"- sha256: `([^`]+)`")
        artifact_bytes = int(_regex_value(section, r"- bytes: `?([0-9]+)`?") or 0)
        output_bytes = _output_size(capture) or artifact_bytes
        packet_kinds = sorted(set(stdout_summary.packet_kinds + stderr_summary.packet_kinds))
        domain_kinds = sorted(set(stdout_summary.domain_kinds + stderr_summary.domain_kinds))
        top_level_kinds = sorted({value for value in (stdout_summary.top_level_kind, stderr_summary.top_level_kind) if value})
        provenance = _json_markdown_metadata(section, "provenance")
        segment = _json_markdown_metadata(section, "segment")
        origin = _regex_value(section, r"- origin: `([^`]+)`") or "unknown"
        expected_failure = _regex_value(section, r"- expected_failure: `([^`]+)`").lower() == "true"
        entries.append(
            {
                "id": entry_id,
                "timestamp": timestamp,
                "command": command,
                "exit_status": exit_status,
                "exit_class": "success" if exit_status == 0 else "failure",
                "failure_class": _failure_class(command_text=command, capture=capture),
                "expected_failure": expected_failure,
                "origin": {"classification": origin, "source": "markdown", "detail": ""},
                "provenance": provenance,
                "segment": segment,
                "output_bytes": output_bytes,
                "output_digest": _output_digest(capture) if output_bytes else "",
                "stdout": _summary_payload(stdout_summary),
                "stderr": _summary_payload(stderr_summary),
                "packet_kinds": packet_kinds,
                "domain_kinds": domain_kinds,
                "top_level_kinds": top_level_kinds,
                "artifact": {
                    "path": artifact,
                    "bytes": artifact_bytes,
                    "sha256": artifact_sha256,
                    "storage_mode": "raw-local-artifact",
                }
                if artifact
                else None,
                "storage_mode": "raw-local-artifact" if artifact else "inline-markdown",
            }
        )
    return entries


def _markdown_labeled_fence(section: str, label: str) -> str:
    match = re.search(rf"\n{re.escape(label)}:\s*\n```[^\n]*\n(?P<body>.*?)\n```", section, re.S)
    return match.group("body") if match else ""


def _regex_value(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _json_markdown_metadata(text: str, label: str) -> dict[str, Any]:
    raw = _regex_value(text, rf"- {re.escape(label)}: `(\{{.*\}})`")
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _entry_brief(entry: dict[str, Any]) -> dict[str, Any]:
    artifact = entry.get("artifact") if isinstance(entry.get("artifact"), dict) else {}
    return {
        "id": entry.get("id", ""),
        "timestamp": entry.get("timestamp", ""),
        "command": entry.get("command", ""),
        "exit_status": entry.get("exit_status", 0),
        "exit_class": entry.get("exit_class", ""),
        "failure_class": entry.get("failure_class", ""),
        "expected_failure": bool(entry.get("expected_failure", False)),
        "origin": entry.get("origin", {}),
        "segment_id": entry.get("segment", {}).get("id", "") if isinstance(entry.get("segment"), dict) else "",
        "output_bytes": entry.get("output_bytes", 0),
        "artifact_path": artifact.get("path", "") if isinstance(artifact, dict) else "",
        "packet_kinds": entry.get("packet_kinds", []),
        "domain_kinds": entry.get("domain_kinds", []),
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


def _session_for_log(*, state: SessionLoggingState, log_path: Path, session: dict[str, str] | None) -> dict[str, str]:
    if session and (state.target_root / session.get("log_path", "")) == log_path:
        return session
    match = re.match(r"aw-session-(?P<session_id>.+)\.md$", log_path.name)
    return {
        "kind": SESSION_POINTER_KIND,
        "session_id": match.group("session_id") if match else hashlib.sha256(log_path.as_posix().encode()).hexdigest()[:12],
        "created_at": "",
        "log_path": log_path.relative_to(state.target_root).as_posix(),
    }


def _coverage_payload(*, markdown_entries: list[dict[str, Any]], index: dict[str, Any] | None) -> dict[str, Any]:
    markdown_ids = [str(entry.get("id", "")) for entry in markdown_entries]
    indexed_entries = _entries_from_index(index or {})
    indexed_ids = [str(entry.get("id", "")) for entry in indexed_entries]
    markdown_set = set(markdown_ids)
    indexed_set = set(indexed_ids)
    if index is None:
        status = "missing"
    elif isinstance(index.get("repair"), dict) and markdown_ids == indexed_ids:
        status = "repaired"
    elif markdown_ids == indexed_ids:
        status = "complete"
    elif indexed_set.issubset(markdown_set):
        status = "partial"
    else:
        status = "stale"
    return {
        "status": status,
        "markdown_command_count": len(markdown_entries),
        "indexed_command_count": len(indexed_entries),
        "missing_entry_ids": [entry_id for entry_id in markdown_ids if entry_id not in indexed_set],
        "extra_entry_ids": [entry_id for entry_id in indexed_ids if entry_id not in markdown_set],
        "repair_available": status in {"missing", "partial", "stale"},
    }


def repair_session_log_index(*, state: SessionLoggingState, path: str = "", session_id: str = "") -> dict[str, Any]:
    session = _session_for_caller(target_root=state.target_root, logical_identity=_logical_session_identity())
    log_path = _analysis_log_path(state=state, path=path, session_id=session_id, session=session)
    if log_path is None:
        return {"kind": "agentic-workspace/session-log-index-repair/v1", "status": "missing-log", "path": ""}
    effective_session = _session_for_log(state=state, log_path=log_path, session=session)
    index = _read_index_for_log(state=state, log_path=log_path, session=session)
    existing = _entries_from_index(index or {})
    markdown_entries = _entries_from_markdown(log_path)
    existing_by_id = {str(entry.get("id", "")): entry for entry in existing}
    markdown_ids = {str(entry.get("id", "")) for entry in markdown_entries}
    missing = [entry for entry in markdown_entries if str(entry.get("id", "")) not in existing_by_id]
    quarantined = [entry for entry in existing if str(entry.get("id", "")) not in markdown_ids]
    notes = index.get("notes", []) if isinstance(index, dict) and isinstance(index.get("notes"), list) else []
    merged = [existing_by_id.get(str(entry.get("id", "")), entry) for entry in markdown_entries]
    _write_index(state=state, session=effective_session, entries=merged, notes=notes)
    index_path = state.target_root / _index_path_for_session(effective_session)
    repaired_index = json.loads(index_path.read_text(encoding="utf-8"))
    repaired_index["repair"] = {
        "status": "repaired",
        "repaired_at": datetime.now(UTC).isoformat(),
        "added_entry_count": len(missing),
        "preserved_entry_count": len(merged) - len(missing),
        "quarantined_entry_count": len(quarantined),
        "quarantined_entry_ids": [str(entry.get("id", "")) for entry in quarantined],
        "quarantined_entries": quarantined,
        "source": effective_session["log_path"],
    }
    _write_json_atomic(index_path, repaired_index)
    coverage = _coverage_payload(markdown_entries=markdown_entries, index=repaired_index)
    return {
        "kind": "agentic-workspace/session-log-index-repair/v1",
        "status": "repaired" if missing or quarantined else "already-covered",
        "path": effective_session["log_path"],
        "index_path": _index_path_for_session(effective_session).as_posix(),
        "added_entry_count": len(missing),
        "quarantined_entry_count": len(quarantined),
        "coverage": coverage,
        "local_only": True,
        "authoritative": False,
    }


def _share_safe_text(*, state: SessionLoggingState, text: str) -> str:
    configured = [item for item in os.environ.get("AW_SESSION_LOG_REDACT_PATHS", "").split(os.pathsep) if item]
    replacements = [
        (state.target_root.as_posix(), "<target>"),
        (str(state.target_root), "<target>"),
        (str(Path.home()), "<home>"),
        (Path.home().as_posix(), "<home>"),
        (sys.executable, "<python>"),
        (Path(sys.executable).as_posix(), "<python>"),
        *[(value, f"<local-path-{index + 1}>") for index, value in enumerate(configured)],
    ]
    normalized = text
    expanded: list[tuple[str, str]] = []
    for value, replacement in replacements:
        expanded.extend(((value, replacement), (value.replace("\\", "\\\\"), replacement)))
    for value, replacement in sorted(expanded, key=lambda item: len(item[0]), reverse=True):
        if value:
            normalized = normalized.replace(value, replacement)
    return normalized


def _share_safe_value(*, state: SessionLoggingState, value: Any) -> Any:
    if isinstance(value, str):
        return _share_safe_text(state=state, text=value)
    if isinstance(value, dict):
        return {key: _share_safe_value(state=state, value=child) for key, child in value.items()}
    if isinstance(value, list):
        return [_share_safe_value(state=state, value=child) for child in value]
    return value


def export_session_log(
    *, state: SessionLoggingState, path: str = "", session_id: str = "", include_artifacts: bool = True
) -> dict[str, Any]:
    session = _session_for_caller(target_root=state.target_root, logical_identity=_logical_session_identity())
    log_path = _analysis_log_path(state=state, path=path, session_id=session_id, session=session)
    if log_path is None:
        return {"kind": "agentic-workspace/session-log-export/v1", "status": "missing-log", "path": ""}
    effective_session = _session_for_log(state=state, log_path=log_path, session=session)
    index = _read_index_for_log(state=state, log_path=log_path, session=session)
    entries = _entries_from_index(index) if index is not None else _entries_from_markdown(log_path)
    files: dict[str, bytes] = {"session.md": _share_safe_text(state=state, text=log_path.read_text(encoding="utf-8-sig")).encode("utf-8")}
    if index is not None:
        safe_index = _share_safe_value(state=state, value=index)
        files["index.json"] = (json.dumps(safe_index, indent=2, sort_keys=True) + "\n").encode("utf-8")
    included_artifacts: list[str] = []
    if include_artifacts:
        artifact_paths = {
            str(entry.get("artifact", {}).get("path", ""))
            for entry in entries
            if isinstance(entry.get("artifact"), dict) and entry.get("artifact", {}).get("path")
        }
        artifact_root = (state.target_root / SESSION_LOG_ROOT / "artifacts").resolve()
        for artifact_path in sorted(artifact_paths):
            candidate = (state.target_root / artifact_path).resolve()
            try:
                candidate.relative_to(artifact_root)
                raw = candidate.read_text(encoding="utf-8-sig")
            except (OSError, ValueError):
                continue
            archive_name = f"artifacts/{candidate.name}"
            try:
                artifact_payload = json.loads(raw)
                safe_raw = json.dumps(_share_safe_value(state=state, value=artifact_payload), indent=2, sort_keys=True) + "\n"
            except json.JSONDecodeError:
                safe_raw = _share_safe_text(state=state, text=raw)
            files[archive_name] = safe_raw.encode("utf-8")
            included_artifacts.append(archive_name)
    source_hashes = {"session.md": hashlib.sha256(log_path.read_bytes()).hexdigest()}
    if index is not None:
        source_index_path = state.target_root / _index_path_for_session(effective_session)
        if source_index_path.exists():
            source_hashes["index.json"] = hashlib.sha256(source_index_path.read_bytes()).hexdigest()
    exported_hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}
    manifest = {
        "kind": "agentic-workspace/session-log-export-manifest/v1",
        "source_session_id": effective_session["session_id"],
        "source_log_path": effective_session["log_path"],
        "created_at": datetime.now(UTC).isoformat(),
        "redaction_mode": "share-safe-known-local-paths",
        "included_files": sorted(files),
        "included_artifacts": included_artifacts,
        "source_hashes": source_hashes,
        "exported_hashes": exported_hashes,
        "originals_mutated": False,
        "local_only": True,
        "authoritative": False,
        "limitations": "Known target, home, Python executable, and configured local paths are redacted; arbitrary secrets in command output are not detected.",
    }
    files["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    export_path = (
        SESSION_LOG_ROOT
        / "exports"
        / (
            f"aw-session-{effective_session['session_id']}-share-safe-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}.zip"
        )
    )
    absolute_export = state.target_root / export_path
    absolute_export.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(absolute_export, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            archive.writestr(name, raw)
    return {
        "kind": "agentic-workspace/session-log-export/v1",
        "status": "exported",
        "path": export_path.as_posix(),
        "source_log_path": effective_session["log_path"],
        "session_id": effective_session["session_id"],
        "artifact_count": len(included_artifacts),
        "sha256": hashlib.sha256(absolute_export.read_bytes()).hexdigest(),
        "manifest": manifest,
        "local_only": True,
        "authoritative": False,
    }


def _origin_name(entry: dict[str, Any]) -> str:
    origin = entry.get("origin", {})
    return str(origin.get("classification", "unknown")) if isinstance(origin, dict) else str(origin or "unknown")


def _segment_summaries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        segment = entry.get("segment", {}) if isinstance(entry.get("segment"), dict) else {}
        segment_id = str(segment.get("id", "unknown") or "unknown")
        grouped.setdefault(segment_id, []).append(entry)
    summaries = []
    for segment_id, members in grouped.items():
        segment = members[-1].get("segment", {}) if isinstance(members[-1].get("segment"), dict) else {}
        summaries.append(
            {
                **segment,
                "id": segment_id,
                "command_count": len(members),
                "failure_count": sum(1 for entry in members if int(entry.get("exit_status", 0) or 0) != 0),
                "started_at": str(members[0].get("timestamp", "")),
                "finished_at": str(members[-1].get("timestamp", "")),
            }
        )
    return summaries


def analyze_session_log(*, state: SessionLoggingState, path: str = "", session_id: str = "", segment_id: str = "") -> dict[str, Any]:
    session = _session_for_caller(target_root=state.target_root, logical_identity=_logical_session_identity())
    log_path = _analysis_log_path(state=state, path=path, session_id=session_id, session=session)
    if log_path is None:
        return {
            "kind": "agentic-workspace/session-log-analysis/v1",
            "status": "missing-log",
            "enabled": state.enabled,
            "path": "",
            "index_status": "missing",
            "rule": "Pass --path, --id, or create a session with session-log new-session before analyzing logs.",
        }

    index = _read_index_for_log(state=state, log_path=log_path, session=session)
    markdown_entries = _entries_from_markdown(log_path)
    coverage = _coverage_payload(markdown_entries=markdown_entries, index=index)
    all_entries = _entries_from_index(index) if index is not None else markdown_entries
    segment_summaries = _segment_summaries(all_entries)
    entries = [
        entry
        for entry in all_entries
        if not segment_id or (isinstance(entry.get("segment"), dict) and str(entry["segment"].get("id", "")) == segment_id)
    ]
    notes = index.get("notes", []) if isinstance(index, dict) and isinstance(index.get("notes"), list) else []
    command_counter = Counter(str(entry.get("command", "")) for entry in entries if entry.get("command"))
    digest_counter = Counter(str(entry.get("output_digest", "")) for entry in entries if entry.get("output_digest"))
    failures = [entry for entry in entries if int(entry.get("exit_status", 0) or 0) != 0]
    live_failures = [entry for entry in failures if _origin_name(entry) == "agent" and not bool(entry.get("expected_failure", False))]
    repeated_failure_counter = Counter(str(entry.get("command", "")) for entry in live_failures if entry.get("command"))
    repeated_failures = [
        {"command": command, "count": count} for command, count in repeated_failure_counter.most_common() if count > 1 and command
    ]
    usage_mistakes = [
        entry
        for entry in failures
        if str(entry.get("failure_class", "")) in {"invalid-command", "selector-conflict", "usage-error", "retryable-cli-usage"}
    ]
    largest = sorted(entries, key=lambda entry: int(entry.get("output_bytes", 0) or 0), reverse=True)[:LARGE_OUTPUT_SUMMARY_LIMIT]
    repeated = [{"command": command, "count": count} for command, count in command_counter.most_common() if count > 1 and command]
    duplicates = [{"sha256": digest, "count": count} for digest, count in digest_counter.most_common() if count > 1 and digest]
    packet_kinds = Counter(
        packet_kind for entry in entries for packet_kind in entry.get("packet_kinds", []) if isinstance(packet_kind, str) and packet_kind
    )
    domain_kinds = Counter(value for entry in entries for value in entry.get("domain_kinds", []) if isinstance(value, str) and value)
    top_level_kinds = Counter(value for entry in entries for value in entry.get("top_level_kinds", []) if isinstance(value, str) and value)
    failures_by_origin = Counter(_origin_name(entry) for entry in failures)
    repeated_failures_by_origin: dict[str, list[dict[str, Any]]] = {}
    for origin in sorted({_origin_name(entry) for entry in failures}):
        counter = Counter(str(entry.get("command", "")) for entry in failures if _origin_name(entry) == origin and entry.get("command"))
        repeated_failures_by_origin[origin] = [
            {"command": command, "count": count} for command, count in counter.most_common() if count > 1
        ]
    friction_candidates = _friction_candidates(
        entries=entries,
        failures=live_failures,
        repeated=repeated,
        duplicates=duplicates,
        index_present=index is not None,
    )
    return {
        "kind": "agentic-workspace/session-log-analysis/v1",
        "status": "analyzed",
        "enabled": state.enabled,
        "path": log_path.relative_to(state.target_root).as_posix(),
        "index_status": coverage["status"],
        "index_presence": "present" if index is not None else "markdown-fallback",
        "coverage": coverage,
        "index_path": str(index.get("path", "")) if isinstance(index, dict) else "",
        "summary": {
            "command_count": len(entries),
            "note_count": len(notes),
            "failure_count": len(failures),
            "failed_count": len(failures),
            "live_agent_failure_count": len(live_failures),
            "expected_failure_count": sum(1 for entry in failures if bool(entry.get("expected_failure", False))),
            "usage_mistake_count": len(usage_mistakes),
            "repeated_command_count": len(repeated),
            "repeated_failure_count": len(repeated_failures),
            "duplicate_output_count": len(duplicates),
            "artifact_count": sum(1 for entry in entries if entry.get("artifact")),
        },
        "failed_commands": [_entry_brief(entry) for entry in failures],
        "live_failed_commands": [_entry_brief(entry) for entry in live_failures],
        "failures_by_origin": dict(sorted(failures_by_origin.items())),
        "repeated_failures_by_origin": repeated_failures_by_origin,
        "usage_mistakes": [_entry_brief(entry) for entry in usage_mistakes],
        "repeated_commands": repeated[:LARGE_OUTPUT_SUMMARY_LIMIT],
        "repeated_failures": repeated_failures[:LARGE_OUTPUT_SUMMARY_LIMIT],
        "largest_outputs": [_entry_brief(entry) for entry in largest],
        "duplicate_outputs": duplicates[:LARGE_OUTPUT_SUMMARY_LIMIT],
        "packet_kinds": dict(sorted(packet_kinds.items())),
        "parsed_packet_kinds": dict(sorted(packet_kinds.items())),
        "top_level_kinds": dict(sorted(top_level_kinds.items())),
        "domain_kinds": dict(sorted(domain_kinds.items())),
        "segments": segment_summaries,
        "selected_segment": segment_id,
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
