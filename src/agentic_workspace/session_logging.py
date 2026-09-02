from __future__ import annotations

import contextlib
import functools
import gzip
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
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agentic_workspace import __version__
from agentic_workspace import config as config_lib
from agentic_workspace.current_work_context import resolve_current_work_context
from agentic_workspace.result_adapter import serialise_value

SESSION_LOG_ROOT = Path(".agentic-workspace") / "local" / "logs"
SESSION_RECORD_KIND = "agentic-workspace/session-logging-record/v1"
SESSION_REGISTRY_PATH = Path(".agentic-workspace") / "local" / "session-logging" / "sessions.json"
SESSION_REGISTRY_LOCK_PATH = Path(".agentic-workspace") / "local" / "session-logging" / ".sessions.lock"
SESSION_CAPTURE_STATUS_PATH = Path(".agentic-workspace") / "local" / "session-logging" / "capture-status.json"
SESSION_CAPTURE_STATUS_KIND = "agentic-workspace/session-logging-capture-status/v1"
SESSION_LOGICAL_STREAM_ROOT = Path(".agentic-workspace") / "local" / "session-logging" / "logical-sessions"
SESSION_REGISTRY_KIND = "agentic-workspace/session-logging-registry/v1"
LOGICAL_SESSION_IDENTITY_ENV = "AW_SESSION_LOGICAL_IDENTITY"
PARENT_LOGICAL_SESSION_IDENTITY_ENV = "AW_SESSION_LOG_PARENT_LOGICAL_IDENTITY"
SESSION_CORRELATION_ID_ENV = "AW_SESSION_LOG_CORRELATION_ID"
SESSION_GAP_REASON_ENV = "AW_SESSION_LOG_GAP_REASON"
PYTEST_DETAIL_CAPTURE_ENV = "AW_SESSION_LOG_CAPTURE_DETAIL"
PYTEST_CAPTURE_MODE_ENV = "AW_SESSION_LOG_PYTEST_CAPTURE"
SESSION_LOG_KIND = "agentic-workspace/session-log/v1"
SESSION_LOG_EVENT_KIND = "agentic-workspace/session-log-event/v1"
SESSION_LOG_EVENT_SCHEMA_VERSION = 1
SESSION_LOG_EVENT_STREAM_NAME = "events.jsonl"
SESSION_LOG_INDEX_KIND = "agentic-workspace/session-log-index/v2"
SESSION_LOG_INDEX_KINDS = {SESSION_LOG_INDEX_KIND, "agentic-workspace/session-log-index/v1"}
SESSION_IMPROVEMENT_SIGNAL_CACHE_PATH = Path(".agentic-workspace") / "local" / "cache" / "dogfooding-signal-status.json"
SESSION_IMPROVEMENT_SIGNAL_CACHE_KIND = "agentic-workspace/session-improvement-signal-cache/v1"
DEFAULT_MAX_INLINE_OUTPUT_BYTES = 64 * 1024
DEFAULT_SLOW_COMMAND_DURATION_MS = 120000
LARGE_OUTPUT_SUMMARY_LIMIT = 5
DEFAULT_ANALYSIS_ENTRY_SAMPLE_LIMIT = 2
FRICTION_CANDIDATE_LIMIT = 10
DEFAULT_ANALYSIS_PAGE_SIZE = 25
MAX_ANALYSIS_PAGE_SIZE = 100
DEFAULT_ANALYSIS_SERIALIZATION_BUDGET_BYTES = 64 * 1024
MAX_SESSION_PARENT_COMMAND_BYTES = 8 * 1024
ATOMIC_REPLACE_RETRY_SECONDS = 1.0
SESSION_LOG_NON_AUTHORITATIVE_FOR = ("Planning", "Memory", "current owner", "proof", "closeout")
SESSION_LOG_LOCAL_BOUNDARY = {
    "scope": "package-owned local diagnostic state",
    "local_only": True,
    "authoritative": False,
    "non_authoritative_for": SESSION_LOG_NON_AUTHORITATIVE_FOR,
    "manual_handoff": "outside-aw-logger-responsibility",
    "raw_capture_policy": "raw local capture remains unchanged unless the user runs an explicit local export",
    "rule": (
        "Session logs are local diagnostic evidence only; durable workflow facts must be recorded in their owning "
        "Planning, Memory, proof, closeout, docs, issue, or PR surface."
    ),
}


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
    identity = _logical_session_identity()
    continuity_session, continuity_source = _session_for_continuity(target_root=state.target_root) if not identity else (None, "")
    if not state.enabled:
        disabled_session = _session_for_caller(target_root=state.target_root, logical_identity=identity) if identity else continuity_session
        if disabled_session:
            with contextlib.suppress(Exception):
                _append_event(
                    state=state,
                    session=disabled_session,
                    event_type="logging.gap",
                    payload={
                        "reason": "capture-disabled",
                        "continuity_source": continuity_source,
                        "command_sha256": hashlib.sha256(("agentic-workspace " + shlex.join(argv_list)).encode()).hexdigest(),
                        "recoverable": False,
                    },
                )
        return runner(argv_list)
    if not identity:
        if _suppress_pytest_origin_capture():
            return runner(argv_list)
        if continuity_session:
            with contextlib.suppress(Exception):
                declared_reason = os.environ.get(SESSION_GAP_REASON_ENV, "").strip()
                _append_event(
                    state=state,
                    session=continuity_session,
                    event_type="logging.gap",
                    payload={
                        "reason": declared_reason or "logical-identity-missing",
                        "continuity_source": continuity_source,
                        "declared_gap_source": SESSION_GAP_REASON_ENV if declared_reason else "",
                        "command_sha256": hashlib.sha256(("agentic-workspace " + shlex.join(argv_list)).encode()).hexdigest(),
                        "recoverable": False,
                    },
                )
                if declared_reason and os.environ.get(SESSION_GAP_REASON_ENV, "").strip() == declared_reason:
                    os.environ.pop(SESSION_GAP_REASON_ENV, None)
        persistence_failed = False
        try:
            capture_status, emit_warning = _record_missing_identity_capture_status(state=state, argv=argv_list)
        except Exception:  # pragma: no cover - exercised through failure injection
            capture_status = _missing_identity_capture_status_payload(argv=argv_list)
            emit_warning = True
            persistence_failed = True
        if emit_warning:
            signal = {
                "kind": capture_status["kind"],
                "status": capture_status["status"],
                "required_environment": capture_status["required_environment"],
                "recovery": capture_status["recovery"],
                "recurrence_rule": capture_status["recurrence_rule"],
                "local_only": True,
                "authoritative": False,
            }
            if persistence_failed:
                signal["diagnostic_persistence"] = "unavailable"
            print(f"AW session logging capture gap: {json.dumps(signal, sort_keys=True)}", file=stderr or sys.stderr)
        return runner(argv_list)
    try:
        _resolve_missing_identity_capture_status(state=state)
    except Exception:  # pragma: no cover - exercised through failure injection
        signal = {
            "kind": SESSION_CAPTURE_STATUS_KIND,
            "status": "recovery-persistence-unavailable",
            "capture_effect": "future-commands-captured",
            "local_only": True,
            "authoritative": False,
        }
        print(f"AW session logging warning: {json.dumps(signal, sort_keys=True)}", file=stderr or sys.stderr)
    if _suppress_pytest_origin_capture():
        return runner(argv_list)
    record_command = not (argv_list and argv_list[0] == "session-log" and any(token in {"repair", "export"} for token in argv_list[1:]))

    output_stdout = stdout or sys.stdout
    output_stderr = stderr or sys.stderr
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    capture = CommandCapture(exit_code=0, stdout="", stderr="")
    started_at = datetime.now(UTC).isoformat()
    started = time.monotonic()
    parent_context = _entry_parent_context(argv_list)
    command_session: dict[str, str] | None = None
    command_entry_id = ""
    start_warning = ""
    if record_command:
        try:
            command_session = ensure_session(state=state)
            _append_declared_gap(state=state, session=command_session)
            command_entry_id = f"cmd-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
            command_text = _normalize_for_log(state, "agentic-workspace " + shlex.join(argv_list))
            _append_event(
                state=state,
                session=command_session,
                event_type="command.started",
                timestamp=started_at,
                payload={
                    "entry_id": command_entry_id,
                    "command": command_text,
                    "argv": [_normalize_for_log(state, token) for token in argv_list],
                    "parent": parent_context,
                },
            )
        except Exception as exc:  # pragma: no cover - intentionally best effort
            start_warning = str(exc)
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
        warning = (
            append_command_entry(
                state=state,
                argv=argv_list,
                capture=capture,
                parent_context=parent_context,
                session=command_session,
                entry_id=command_entry_id,
            )
            if record_command
            else None
        )
        warning = "; ".join(item for item in (start_warning, warning or "") if item)
        if warning:
            print(f"AW session logging warning: {warning}", file=output_stderr)


@contextlib.contextmanager
def _session_parent_environment(argv: Sequence[str]) -> Iterator[None]:
    parent_command = _session_parent_command(argv)
    updates = {
        "AW_SESSION_LOG_PARENT_COMMAND": parent_command,
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


def _session_parent_command(argv: Sequence[str]) -> str:
    rendered = "agentic-workspace " + shlex.join(list(argv))
    encoded = rendered.encode("utf-8")
    if len(encoded) <= MAX_SESSION_PARENT_COMMAND_BYTES:
        return rendered
    command_identity = [value for value in list(argv)[:2] if len(value) <= 64 and re.fullmatch(r"[A-Za-z0-9._-]+", value)]
    identity = " ".join(("agentic-workspace", *command_identity))
    return f"{identity} [oversized arguments omitted; utf8_bytes={len(encoded)}; sha256:{hashlib.sha256(encoded).hexdigest()}]"


def _entry_parent_context(argv: Sequence[str]) -> dict[str, str]:
    current = _parent_context()
    if any(current.values()):
        return current
    pytest_context = os.environ.get("PYTEST_CURRENT_TEST", "")
    if pytest_context:
        return {
            "entry_id": "",
            "command": "agentic-workspace " + shlex.join(list(argv)),
            "context": pytest_context,
        }
    return current


def _truthy_capture_value(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on", "full", "detail", "detailed"}


def _pytest_detail_capture_enabled() -> bool:
    return _truthy_capture_value(os.environ.get(PYTEST_DETAIL_CAPTURE_ENV, "")) or _truthy_capture_value(
        os.environ.get(PYTEST_CAPTURE_MODE_ENV, "")
    )


def _suppress_pytest_origin_capture() -> bool:
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    explicit_origin = os.environ.get("AW_SESSION_LOG_ORIGIN", "").strip().lower()
    if explicit_origin and explicit_origin != "pytest":
        return False
    return not _pytest_detail_capture_enabled()


def _run_session_log_adapter(args: Any) -> int:
    target = getattr(args, "target", None)
    effective_argv = ["--target", str(target)] if target else []
    state = load_state_for_argv(effective_argv)
    output_stderr = sys.stderr
    try:
        command = str(getattr(args, "session_log_command", "status") or "status")
        if command == "note":
            payload = append_note(state=state, text=str(getattr(args, "text", "")))
        elif command == "signal":
            payload = capture_improvement_signal(
                state=state,
                signal_kind=str(getattr(args, "kind", "workaround") or "workaround"),
                symptom=str(getattr(args, "symptom", "") or ""),
                cost=str(getattr(args, "cost", "") or ""),
                expected_benefit=str(getattr(args, "expected_benefit", "") or ""),
                evidence_class=str(getattr(args, "evidence_class", "agent_observed") or "agent_observed"),
                owner_hint=str(getattr(args, "owner_hint", "unknown") or "unknown"),
                scope_relation=str(getattr(args, "scope_relation", "current-scope") or "current-scope"),
                recurrence=str(getattr(args, "recurrence", "first_seen") or "first_seen"),
                evidence_refs=[str(item) for item in (getattr(args, "evidence_ref", []) or [])],
                likely_remediation=str(getattr(args, "likely_remediation", "unknown") or "unknown"),
            )
        elif command == "new-session":
            payload = reset_session(state=state)
        elif command == "analyze":
            payload = analyze_session_log(
                state=state,
                path=str(getattr(args, "path", "") or ""),
                session_id=str(getattr(args, "id", "") or ""),
                segment_id=str(getattr(args, "segment", "") or ""),
                origin_scope=str(getattr(args, "origin", "agent") or "agent"),
                detail=str(getattr(args, "detail", "summary") or "summary"),
                page=max(1, int(getattr(args, "page", 1) or 1)),
                page_size=max(
                    1,
                    min(MAX_ANALYSIS_PAGE_SIZE, int(getattr(args, "page_size", DEFAULT_ANALYSIS_PAGE_SIZE) or DEFAULT_ANALYSIS_PAGE_SIZE)),
                ),
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


def append_command_entry(
    *,
    state: SessionLoggingState,
    argv: Sequence[str],
    capture: CommandCapture,
    parent_context: dict[str, str] | None = None,
    session: dict[str, str] | None = None,
    entry_id: str = "",
) -> str | None:
    if not state.enabled or not _logical_session_identity():
        return None
    try:
        session = session or ensure_session(state=state)
        _append_declared_gap(state=state, session=session)
        with _session_index_lock(state=state, session=session):
            entry_id = entry_id or f"cmd-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
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
            invocation_intent = _invocation_intent(origin=origin, argv=argv)
            entry = _command_entry_markdown(
                state=state,
                session=session,
                entry_id=entry_id,
                timestamp=timestamp,
                command_text=command_text,
                capture=capture,
                origin=origin,
                expected_failure=expected_failure,
                invocation_intent=invocation_intent,
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
                invocation_intent=invocation_intent,
                provenance=provenance,
                segment=segment,
                parent_context=parent_context,
            )
            current_index = _read_index(state=state, session=session) or {}
            indexed_entry = next(
                (item for item in _entries_from_index(current_index) if str(item.get("id", "")) == entry_id),
                None,
            )
            if indexed_entry is None:
                _append_event(
                    state=state,
                    session=session,
                    event_type="logging.gap",
                    timestamp=timestamp,
                    payload={
                        "entry_id": entry_id,
                        "reason": "command-view-missing-after-write",
                        "recoverable": True,
                    },
                )
            else:
                _append_event(
                    state=state,
                    session=session,
                    event_type="command.completed",
                    timestamp=capture.finished_at or timestamp,
                    payload={"entry": indexed_entry},
                )
                surface = str(argv[0]) if argv else ""
                if surface in {"start", "implement", "proof", "closeout"}:
                    _append_event(
                        state=state,
                        session=session,
                        event_type="workflow.transition",
                        timestamp=capture.finished_at or timestamp,
                        payload={
                            "entry_id": entry_id,
                            "surface": surface,
                            "exit_status": capture.exit_code,
                            "result": "completed" if capture.exit_code == 0 else "failed",
                        },
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
    if not _logical_session_identity():
        return _identity_required_payload(kind="agentic-workspace/session-log-note/v1")
    session = ensure_session(state=state)
    _append_declared_gap(state=state, session=session)
    timestamp = datetime.now(UTC).isoformat()
    note = _normalize_for_log(state, text.strip())
    note_event = _append_event(
        state=state,
        session=session,
        event_type="note.appended",
        timestamp=timestamp,
        payload={
            "text": note,
            "bytes": len(note.encode("utf-8")),
            "sha256": hashlib.sha256(note.encode("utf-8")).hexdigest(),
        },
    )
    with _session_index_lock(state=state, session=session):
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
        "event_id": note_event["event_id"],
    }


def _improvement_signal_fingerprint(*, signal_kind: str, symptom: str, owner_hint: str) -> str:
    def normalize(value: str) -> str:
        text = re.sub(r"https?://\S+", "<url>", value.strip().lower())
        text = re.sub(r"#[0-9]+", "#<issue>", text)
        text = re.sub(r"\b[0-9a-f]{8,}\b", "<identity>", text)
        text = re.sub(r"\b\d+\b", "<n>", text)
        return " ".join(text.split())

    identity = {"kind": signal_kind, "owner": normalize(owner_hint), "symptom": normalize(symptom)}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:20]


def _read_improvement_signal_cache(*, state: SessionLoggingState) -> dict[str, Any]:
    path = state.target_root / SESSION_IMPROVEMENT_SIGNAL_CACHE_PATH
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def capture_improvement_signal(
    *,
    state: SessionLoggingState,
    signal_kind: str,
    symptom: str,
    cost: str,
    expected_benefit: str,
    evidence_class: str,
    owner_hint: str,
    scope_relation: str,
    recurrence: str,
    evidence_refs: list[str],
    likely_remediation: str,
) -> dict[str, Any]:
    """Capture one compact local observation for the existing improvement intake."""
    symptom = " ".join(symptom.split())
    cost = " ".join(cost.split())
    expected_benefit = " ".join(expected_benefit.split())
    if not symptom or not cost:
        return {
            "kind": "agentic-workspace/session-improvement-signal-capture/v1",
            "status": "rejected",
            "reason": "symptom and concrete cost are required; preference-only observations are not admitted",
            "mutation_authorized": False,
        }
    if signal_kind == "opportunity" and not expected_benefit:
        return {
            "kind": "agentic-workspace/session-improvement-signal-capture/v1",
            "status": "rejected",
            "reason": "opportunity signals require a concrete expected future-cost or operability benefit",
            "mutation_authorized": False,
        }
    normalized_kind = "improvement_opportunity" if signal_kind == "opportunity" else "workflow_cost"
    fingerprint = _improvement_signal_fingerprint(
        signal_kind=normalized_kind,
        symptom=symptom,
        owner_hint=owner_hint,
    )
    cache = _read_improvement_signal_cache(state=state)
    raw_signals = cache.get("signals", [])
    signals = [dict(item) for item in raw_signals if isinstance(item, dict)] if isinstance(raw_signals, list) else []
    existing = next((item for item in signals if str(item.get("evidence_fingerprint") or "") == fingerprint), None)
    now = datetime.now(UTC).isoformat()
    if existing is None:
        existing = {
            "signal": symptom,
            "kind": normalized_kind,
            "symptom": symptom,
            "cost": cost,
            "expected_benefit": expected_benefit,
            "evidence_classes": [evidence_class],
            "evidence_refs": sorted({item.strip() for item in evidence_refs if item.strip()}),
            "owner_hint": owner_hint.strip() or "unknown",
            "scope_relation": scope_relation,
            "recurrence": recurrence,
            "occurrence_count": 1,
            "likely_remediation": likely_remediation,
            "evidence_fingerprint": fingerprint,
            "outcome": "unresolved",
            "first_seen_at": now,
            "last_seen_at": now,
        }
        signals.append(existing)
        outcome = "captured"
    else:
        existing["occurrence_count"] = max(1, int(existing.get("occurrence_count") or 1)) + 1
        existing["last_seen_at"] = now
        existing["evidence_classes"] = sorted(
            {str(item) for item in existing.get("evidence_classes", []) if str(item).strip()} | {evidence_class}
        )
        existing["evidence_refs"] = sorted(
            {str(item) for item in existing.get("evidence_refs", []) if str(item).strip()}
            | {item.strip() for item in evidence_refs if item.strip()}
        )
        if evidence_class == "human_confirmed":
            existing["recurrence"] = "human_confirmed"
        elif existing["occurrence_count"] > 1 and existing.get("recurrence") == "first_seen":
            existing["recurrence"] = "repeated"
        outcome = "strengthened"
    payload = {
        "kind": SESSION_IMPROVEMENT_SIGNAL_CACHE_KIND,
        "status": "unresolved",
        "signals": signals,
        "routing_decision": "route_now",
        "updated_at": now,
        "local_only": True,
        "authoritative": False,
        "mutation_authorized": False,
    }
    _write_json_atomic(state.target_root / SESSION_IMPROVEMENT_SIGNAL_CACHE_PATH, payload)
    return {
        "kind": "agentic-workspace/session-improvement-signal-capture/v1",
        "status": outcome,
        "evidence_fingerprint": fingerprint,
        "occurrence_count": existing["occurrence_count"],
        "recurrence": existing["recurrence"],
        "evidence_classes": existing["evidence_classes"],
        "cache_path": SESSION_IMPROVEMENT_SIGNAL_CACHE_PATH.as_posix(),
        "candidate_only": True,
        "mutation_authorized": False,
        "next_route": "agentic-workspace report --target . --section improvement_intake --format json",
    }


def reset_session(*, state: SessionLoggingState) -> dict[str, Any]:
    if not state.enabled:
        return status_payload(state=state)
    if not _logical_session_identity():
        return _identity_required_payload(kind="agentic-workspace/session-log-session/v1")
    session = ensure_session(state=state, force_new=True)
    return {
        "kind": "agentic-workspace/session-log-session/v1",
        "status": "created",
        "enabled": True,
        "path": session["log_path"],
        "event_stream_path": _event_path_for_session(session).as_posix(),
        "session_id": session["session_id"],
        "logical_session_id": session.get("logical_session_id", ""),
    }


def status_payload(*, state: SessionLoggingState) -> dict[str, Any]:
    logical_identity = _logical_session_identity()
    session = _session_for_caller(target_root=state.target_root, logical_identity=logical_identity)
    session_scope = _session_scope_payload(session=session, explicit_selection=False)
    return {
        "kind": "agentic-workspace/session-logging-status/v1",
        "status": "ready" if logical_identity else "logical-session-identity-required",
        "enabled": state.enabled,
        "target": state.target_root.as_posix(),
        "config_source": _logging_config_source(state),
        "path": session.get("log_path", "") if session else "",
        "event_stream_path": _event_path_for_session(session).as_posix() if session else "",
        "index_path": _index_path_for_session(session).as_posix() if session else "",
        "session_id": session.get("session_id", "") if session else "",
        "logical_session_id": session.get("logical_session_id", "") if session else "",
        "logical_session_resolution": "identity-registry" if logical_identity else "identity-required",
        "session_scope": session_scope,
        "logical_session_identity_source": LOGICAL_SESSION_IDENTITY_ENV if logical_identity else "",
        "capture_posture": _capture_status_payload(state=state, logical_identity=logical_identity),
        "raw_logical_session_identity_stored": False,
        "path_normalization": _path_normalization_payload(state),
        "local_diagnostic_boundary": _session_log_local_boundary(),
        "local_only": True,
        "authoritative": False,
        "rule": SESSION_LOG_LOCAL_BOUNDARY["rule"],
    }


def ensure_session(*, state: SessionLoggingState, force_new: bool = False, logical_identity: str | None = None) -> dict[str, str]:
    identity = _logical_session_identity() if logical_identity is None else logical_identity.strip()
    if not identity:
        raise ValueError(f"{LOGICAL_SESSION_IDENTITY_ENV} is required for session logging")
    with _session_registry_lock(target_root=state.target_root):
        registry = _read_session_registry(target_root=state.target_root)
        sessions = registry.setdefault("sessions", {})
        logical_sessions = registry.setdefault("logical_sessions", {})
        registry_key = _logical_identity_fingerprint(identity=identity, registry=registry)
        logical_session_id = _logical_session_id(registry_key)
        parent_identity = os.environ.get(PARENT_LOGICAL_SESSION_IDENTITY_ENV, "").strip()
        parent_key = _logical_identity_fingerprint(identity=parent_identity, registry=registry) if parent_identity else ""
        parent_logical_session_id = _logical_session_id(parent_key) if parent_key else ""
        raw_correlation_id = os.environ.get(SESSION_CORRELATION_ID_ENV, "").strip()
        correlation_id = _private_correlation_id(value=raw_correlation_id, registry=registry) if raw_correlation_id else ""
        group = logical_sessions.get(registry_key) if isinstance(logical_sessions, dict) else None
        if not isinstance(group, dict):
            group = {
                "kind": "agentic-workspace/logical-session-record/v1",
                "logical_session_id": logical_session_id,
                "parent_logical_session_id": parent_logical_session_id,
                "correlation_id": correlation_id,
                "event_stream_path": _logical_event_path(logical_session_id).as_posix(),
                "sessions": [],
                "created_at": datetime.now(UTC).isoformat(),
            }
        else:
            group = dict(group)
            group.setdefault("logical_session_id", logical_session_id)
            if parent_logical_session_id:
                group["parent_logical_session_id"] = parent_logical_session_id
            if correlation_id:
                group["correlation_id"] = correlation_id
        event_stream_path = (
            _valid_event_stream_path(str(group.get("event_stream_path", ""))) or _logical_event_path(logical_session_id).as_posix()
        )
        group["event_stream_path"] = event_stream_path
        registered_current = _registered_session(registry=registry, registry_key=registry_key, target_root=state.target_root)
        group_sessions = group.setdefault("sessions", [])
        if isinstance(group_sessions, list):
            if registered_current and not any(
                isinstance(item, dict) and item.get("session_id") == registered_current["session_id"] for item in group_sessions
            ):
                group_sessions.append(registered_current)
            group["sessions"] = [
                {**item, "event_stream_path": event_stream_path} if isinstance(item, dict) else item for item in group_sessions
            ]
        _migrate_logical_event_stream(state=state, group=group, event_stream_path=event_stream_path)
        current = None if force_new else registered_current
        if current:
            current = {
                **current,
                "logical_session_id": logical_session_id,
                "parent_logical_session_id": str(group.get("parent_logical_session_id", "")),
                "correlation_id": str(group.get("correlation_id", "")),
                "event_stream_path": event_stream_path,
            }
            group_sessions = group.setdefault("sessions", [])
            if isinstance(group_sessions, list) and not any(
                isinstance(item, dict) and item.get("session_id") == current["session_id"] for item in group_sessions
            ):
                group_sessions.append(current)
            if isinstance(sessions, dict) and sessions.get(registry_key) != current:
                sessions[registry_key] = current
            if isinstance(logical_sessions, dict):
                logical_sessions[registry_key] = group
            registry["updated_at"] = datetime.now(UTC).isoformat()
            _write_json_atomic(state.target_root / SESSION_REGISTRY_PATH, registry)
            return current
        prior = registered_current if force_new else None
        session = _create_session(
            state=state,
            logical_session_id=logical_session_id,
            parent_logical_session_id=str(group.get("parent_logical_session_id", "")),
            correlation_id=str(group.get("correlation_id", "")),
            prior_session_id=str(prior.get("session_id", "")) if prior else "",
            event_stream_path=event_stream_path,
        )
        if prior:
            _append_event(
                state=state,
                session={
                    **prior,
                    "logical_session_id": logical_session_id,
                    "parent_logical_session_id": str(group.get("parent_logical_session_id", "")),
                    "correlation_id": str(group.get("correlation_id", "")),
                    "event_stream_path": event_stream_path,
                },
                event_type="session.rotated",
                payload={"next_physical_session_id": session["session_id"], "reason": "explicit-new-session"},
            )
        group_sessions = group.setdefault("sessions", [])
        if isinstance(group_sessions, list):
            if prior and not any(isinstance(item, dict) and item.get("session_id") == prior["session_id"] for item in group_sessions):
                group_sessions.append(prior)
            group_sessions.append(session)
        group["updated_at"] = datetime.now(UTC).isoformat()
        if isinstance(sessions, dict):
            sessions[registry_key] = session
        if isinstance(logical_sessions, dict):
            logical_sessions[registry_key] = group
        registry["updated_at"] = datetime.now(UTC).isoformat()
        _write_json_atomic(state.target_root / SESSION_REGISTRY_PATH, registry)
        return session


def _create_session(
    *,
    state: SessionLoggingState,
    logical_session_id: str,
    parent_logical_session_id: str = "",
    correlation_id: str = "",
    prior_session_id: str = "",
    event_stream_path: str = "",
) -> dict[str, str]:
    created_at = datetime.now(UTC)
    session_id = f"{created_at.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    log_path = SESSION_LOG_ROOT / f"aw-session-{session_id}" / "session.md"
    session = {
        "kind": SESSION_RECORD_KIND,
        "session_id": session_id,
        "created_at": created_at.isoformat(),
        "log_path": log_path.as_posix(),
        "logical_session_id": logical_session_id,
        "parent_logical_session_id": parent_logical_session_id,
        "correlation_id": correlation_id,
        "prior_session_id": prior_session_id,
        "event_stream_path": event_stream_path or _logical_event_path(logical_session_id).as_posix(),
    }
    absolute_log_path = state.target_root / log_path
    absolute_log_path.parent.mkdir(parents=True, exist_ok=True)
    _append_event(
        state=state,
        session=session,
        event_type="session.started",
        timestamp=created_at.isoformat(),
        payload={
            "created_at": created_at.isoformat(),
            "prior_physical_session_id": prior_session_id,
            "package": {"name": "agentic-workspace", "version": __version__},
            "logging_policy": {
                "path_normalization": _path_normalization_payload(state),
                "failure_behavior": "warning-only",
            },
        },
    )
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
        "logical_sessions": {},
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


def _logical_session_id(registry_key: str) -> str:
    return f"logical-{registry_key[:24]}" if registry_key else ""


def _private_correlation_id(*, value: str, registry: dict[str, Any]) -> str:
    salt = str(registry.get("salt", ""))
    return "correlation-" + hashlib.sha256(f"{salt}\0{value}".encode()).hexdigest()[:24]


def _registered_session(*, registry: dict[str, Any], registry_key: str, target_root: Path) -> dict[str, str] | None:
    sessions = registry.get("sessions", {})
    candidate = sessions.get(registry_key) if isinstance(sessions, dict) else None
    session = _validated_session(candidate)
    if session and (target_root / session["log_path"]).is_file():
        return session
    return None


def _session_for_caller(*, target_root: Path, logical_identity: str) -> dict[str, str] | None:
    if not logical_identity:
        return None
    registry = _read_session_registry(target_root=target_root)
    registry_key = _logical_identity_fingerprint(identity=logical_identity, registry=registry)
    session = _registered_session(registry=registry, registry_key=registry_key, target_root=target_root)
    groups = registry.get("logical_sessions", {})
    group = groups.get(registry_key) if isinstance(groups, dict) else None
    if session and isinstance(group, dict):
        event_stream_path = _valid_event_stream_path(str(group.get("event_stream_path", "")))
        return {**session, "event_stream_path": event_stream_path or session.get("event_stream_path", "")}
    return session


def _session_for_continuity(*, target_root: Path) -> tuple[dict[str, str] | None, str]:
    parent_identity = os.environ.get(PARENT_LOGICAL_SESSION_IDENTITY_ENV, "").strip()
    raw_correlation_id = os.environ.get(SESSION_CORRELATION_ID_ENV, "").strip()
    if not parent_identity and not raw_correlation_id:
        return None, ""
    registry = _read_session_registry(target_root=target_root)
    groups = registry.get("logical_sessions", {})
    if not isinstance(groups, dict):
        return None, ""
    candidates: list[tuple[dict[str, Any], str]] = []
    parent_resolved = False
    if parent_identity:
        parent_key = _logical_identity_fingerprint(identity=parent_identity, registry=registry)
        parent_group = groups.get(parent_key)
        if isinstance(parent_group, dict):
            candidates.append((parent_group, PARENT_LOGICAL_SESSION_IDENTITY_ENV))
            parent_resolved = True
    if raw_correlation_id:
        private_correlation_id = _private_correlation_id(value=raw_correlation_id, registry=registry)
        candidates.extend(
            (group, SESSION_CORRELATION_ID_ENV)
            for group in groups.values()
            if isinstance(group, dict) and str(group.get("correlation_id", "")) == private_correlation_id
        )
    if parent_resolved:
        candidates = candidates[:1]
    else:
        unique_candidates = {str(group.get("logical_session_id", "")): (group, source) for group, source in candidates}
        if len(unique_candidates) != 1:
            return None, ""
        candidates = list(unique_candidates.values())
    for group, source in candidates:
        event_stream_path = _valid_event_stream_path(str(group.get("event_stream_path", "")))
        sessions = [_validated_session(item) for item in group.get("sessions", [])]
        valid_sessions = [item for item in sessions if item and (target_root / item["log_path"]).is_file()]
        if valid_sessions:
            current = max(valid_sessions, key=lambda item: (item.get("created_at", ""), item["session_id"]))
            return {**current, "event_stream_path": event_stream_path or current.get("event_stream_path", "")}, source
    return None, ""


def _session_scope_payload(
    *,
    session: dict[str, str] | None,
    explicit_selection: bool,
) -> dict[str, Any]:
    logical_identity = _logical_session_identity()
    if explicit_selection:
        scope_kind = "explicit-artifact"
        breadth = "one-selected-artifact"
    elif logical_identity and session:
        scope_kind = "distinct-logical-session"
        breadth = "one-logical-session"
    else:
        scope_kind = "unavailable"
        breadth = "none"
    return {
        "kind": scope_kind,
        "breadth": breadth,
        "selection": "explicit" if explicit_selection else "caller-identity",
        "distinct_logical_session": scope_kind == "distinct-logical-session",
        "current_logical_session": scope_kind == "distinct-logical-session",
        "rule": (
            "The selected path/id is an explicit local artifact, not proof of current-session identity."
            if scope_kind == "explicit-artifact"
            else "This scope is one caller identity registered by the host."
            if scope_kind == "distinct-logical-session"
            else f"Session logging requires a host-provided {LOGICAL_SESSION_IDENTITY_ENV}."
        ),
    }


def _identity_required_payload(*, kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "status": "logical-session-identity-required",
        "enabled": True,
        "path": "",
        "session_id": "",
        "required_environment": LOGICAL_SESSION_IDENTITY_ENV,
        "local_only": True,
        "authoritative": False,
        "rule": f"Session logging does not capture or create state without {LOGICAL_SESSION_IDENTITY_ENV}.",
    }


def _capture_status_path(*, state: SessionLoggingState) -> Path:
    return state.target_root / SESSION_CAPTURE_STATUS_PATH


def _read_capture_status(*, state: SessionLoggingState) -> dict[str, Any]:
    path = _capture_status_path(state=state)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict) or payload.get("kind") != SESSION_CAPTURE_STATUS_KIND:
        return {}
    return payload


def _missing_identity_capture_status_payload(*, argv: Sequence[str], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    previous = previous or {}
    same_episode = previous.get("status") == "identity-required"
    now = datetime.now(UTC).isoformat()
    command_sha256 = hashlib.sha256(("agentic-workspace " + shlex.join(list(argv))).encode()).hexdigest()
    return {
        "kind": SESSION_CAPTURE_STATUS_KIND,
        "status": "identity-required",
        "episode_id": str(previous.get("episode_id") or f"capture-gap-{uuid.uuid4().hex[:12]}")
        if same_episode
        else f"capture-gap-{uuid.uuid4().hex[:12]}",
        "started_at": str(previous.get("started_at") or now) if same_episode else now,
        "last_observed_at": now,
        "missing_identity_invocation_count": int(previous.get("missing_identity_invocation_count") or 0) + 1 if same_episode else 1,
        "last_command_sha256": command_sha256,
        "required_environment": LOGICAL_SESSION_IDENTITY_ENV,
        "recovery": f"Set {LOGICAL_SESSION_IDENTITY_ENV} through the host or repo-local adapter, then run the next AW command normally.",
        "recurrence_rule": "Emit once per unresolved target-local episode; identity recovery resets the warning for a later episode.",
        "capture_effect": "command-not-captured",
        "recoverable": True,
        "local_only": True,
        "authoritative": False,
        "non_authoritative_for": list(SESSION_LOG_NON_AUTHORITATIVE_FOR),
        "parent_lane": "#2707",
    }


def _record_missing_identity_capture_status(*, state: SessionLoggingState, argv: Sequence[str]) -> tuple[dict[str, Any], bool]:
    path = _capture_status_path(state=state)
    previous = _read_capture_status(state=state)
    same_episode = previous.get("status") == "identity-required"
    payload = _missing_identity_capture_status_payload(argv=argv, previous=previous)
    _write_json_atomic(path, payload)
    return payload, not same_episode


def _resolve_missing_identity_capture_status(*, state: SessionLoggingState) -> None:
    previous = _read_capture_status(state=state)
    if previous.get("status") != "identity-required":
        return
    payload = dict(previous)
    payload.update(
        {
            "status": "recovered",
            "resolved_at": datetime.now(UTC).isoformat(),
            "capture_effect": "future-commands-captured",
            "recovery_rule": "Earlier commands remain classified as uncaptured; no missing history is fabricated.",
        }
    )
    _write_json_atomic(_capture_status_path(state=state), payload)


def _capture_status_payload(*, state: SessionLoggingState, logical_identity: str) -> dict[str, Any]:
    if not state.enabled:
        return {"kind": SESSION_CAPTURE_STATUS_KIND, "status": "disabled"}
    payload = _read_capture_status(state=state)
    if payload:
        return payload
    if logical_identity:
        return {"kind": SESSION_CAPTURE_STATUS_KIND, "status": "ready"}
    return {
        "kind": SESSION_CAPTURE_STATUS_KIND,
        "status": "identity-required",
        "required_environment": LOGICAL_SESSION_IDENTITY_ENV,
        "capture_effect": "command-not-captured",
        "local_only": True,
        "authoritative": False,
    }


@contextlib.contextmanager
def _session_registry_lock(*, target_root: Path) -> Iterator[None]:
    lock_path = target_root / SESSION_REGISTRY_LOCK_PATH
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.perf_counter() + 5
    while True:
        try:
            lock_path.mkdir()
            break
        except (FileExistsError, PermissionError):
            # Windows can report an existing directory lock as access denied
            # while another thread is creating or removing it. Treat that
            # transient shape as ordinary lock contention.
            try:
                stale = time.time() - lock_path.stat().st_mtime > 30
            except OSError:
                stale = False
            if stale:
                with contextlib.suppress(OSError):
                    lock_path.rmdir()
                continue
            if time.perf_counter() >= deadline:
                raise TimeoutError(f"timed out waiting for session registry lock: {lock_path}")
            time.sleep(0.01)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            lock_path.rmdir()


def _validated_session(payload: Any) -> dict[str, str] | None:
    if not isinstance(payload, dict) or payload.get("kind") != SESSION_RECORD_KIND:
        return None
    session_id = str(payload.get("session_id", "")).strip()
    log_path = _valid_session_log_path(str(payload.get("log_path", "")).strip())
    if not session_id or not log_path:
        return None
    return {
        "kind": SESSION_RECORD_KIND,
        "session_id": session_id,
        "created_at": str(payload.get("created_at", "")),
        "log_path": log_path,
        "logical_session_id": str(payload.get("logical_session_id", "")),
        "parent_logical_session_id": str(payload.get("parent_logical_session_id", "")),
        "correlation_id": str(payload.get("correlation_id", "")),
        "prior_session_id": str(payload.get("prior_session_id", "")),
        "event_stream_path": _valid_event_stream_path(str(payload.get("event_stream_path", ""))),
    }


def _valid_session_log_path(value: str) -> str:
    if not value:
        return ""
    path = Path(value)
    if path.is_absolute() or path.drive or any(part == ".." for part in path.parts):
        return ""
    normalized = Path(*path.parts).as_posix()
    log_root = SESSION_LOG_ROOT.as_posix()
    if not normalized.startswith(f"{log_root}/"):
        return ""
    relative = Path(normalized).relative_to(SESSION_LOG_ROOT)
    if len(relative.parts) != 2 or relative.name != "session.md" or not relative.parent.name.startswith("aw-session-"):
        return ""
    return normalized


def _logical_event_path(logical_session_id: str) -> Path:
    return SESSION_LOGICAL_STREAM_ROOT / logical_session_id / SESSION_LOG_EVENT_STREAM_NAME


def _valid_event_stream_path(value: str) -> str:
    if not value:
        return ""
    path = Path(value)
    if path.is_absolute() or path.drive or any(part == ".." for part in path.parts):
        return ""
    normalized = Path(*path.parts).as_posix()
    root = SESSION_LOGICAL_STREAM_ROOT.as_posix()
    if not normalized.startswith(f"{root}/"):
        return ""
    relative = Path(normalized).relative_to(SESSION_LOGICAL_STREAM_ROOT)
    if len(relative.parts) != 2 or relative.name != SESSION_LOG_EVENT_STREAM_NAME or not relative.parent.name.startswith("logical-"):
        return ""
    return normalized


def _migrate_logical_event_stream(*, state: SessionLoggingState, group: dict[str, Any], event_stream_path: str) -> None:
    canonical_path = state.target_root / event_stream_path
    if canonical_path.is_file():
        return
    migrated: list[dict[str, Any]] = []
    for candidate in group.get("sessions", []):
        session = _validated_session(candidate)
        if not session:
            continue
        legacy_path = state.target_root / Path(session["log_path"]).parent / SESSION_LOG_EVENT_STREAM_NAME
        events, _ = _read_event_stream(legacy_path)
        migrated.extend(events)
    if not migrated:
        return
    migrated.sort(
        key=lambda event: (
            str(event.get("timestamp", "")),
            str(event.get("physical_session_id", "")),
            int(event.get("sequence", 0) or 0),
            str(event.get("event_id", "")),
        )
    )
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = canonical_path.with_suffix(canonical_path.suffix + f".{uuid.uuid4().hex}.tmp")
    with temporary.open("wb") as handle:
        for sequence, event in enumerate(migrated, start=1):
            normalized = {**event, "source_sequence": int(event.get("sequence", 0) or 0), "sequence": sequence}
            handle.write((json.dumps(serialise_value(normalized), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(canonical_path)


def _event_path_for_session(session: dict[str, str]) -> Path:
    configured = _valid_event_stream_path(str(session.get("event_stream_path", "")))
    return Path(configured) if configured else Path(session["log_path"]).parent / SESSION_LOG_EVENT_STREAM_NAME


def _event_lock_path_for_session(session: dict[str, str]) -> Path:
    return _event_path_for_session(session).parent / ".events.lock"


@contextlib.contextmanager
def _event_stream_lock(*, state: SessionLoggingState, session: dict[str, str]) -> Iterator[None]:
    lock_path = state.target_root / _event_lock_path_for_session(session)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.perf_counter() + 5
    while True:
        try:
            lock_path.mkdir()
            break
        except (FileExistsError, PermissionError):
            try:
                stale = time.time() - lock_path.stat().st_mtime > 30
            except OSError:
                stale = False
            if stale:
                with contextlib.suppress(OSError):
                    lock_path.rmdir()
                continue
            if time.perf_counter() >= deadline:
                raise TimeoutError(f"timed out waiting for session event-stream lock: {lock_path}")
            time.sleep(0.01)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            lock_path.rmdir()


def _read_event_stream(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not path.is_file():
        return [], []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return [], [{"reason": "event-stream-unreadable", "detail": exc.__class__.__name__}]
    events: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    lines = raw.splitlines(keepends=True)
    for line_number, raw_line in enumerate(lines, start=1):
        complete = raw_line.endswith((b"\n", b"\r"))
        try:
            payload = json.loads(raw_line.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            issues.append(
                {
                    "reason": "partial-event" if not complete and line_number == len(lines) else "invalid-event",
                    "line": line_number,
                    "sha256": hashlib.sha256(raw_line).hexdigest(),
                }
            )
            continue
        if not isinstance(payload, dict) or payload.get("kind") != SESSION_LOG_EVENT_KIND:
            issues.append({"reason": "unsupported-event", "line": line_number})
            continue
        events.append(payload)
    return events, issues


def _new_event(
    *,
    session: dict[str, str],
    event_type: str,
    sequence: int,
    timestamp: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": SESSION_LOG_EVENT_KIND,
        "schema_version": SESSION_LOG_EVENT_SCHEMA_VERSION,
        "event_id": f"event-{session['session_id']}-{sequence:08d}-{uuid.uuid4().hex[:8]}",
        "event_type": event_type,
        "timestamp": timestamp,
        "sequence": sequence,
        "logical_session_id": str(session.get("logical_session_id", "")),
        "physical_session_id": session["session_id"],
        "parent_logical_session_id": str(session.get("parent_logical_session_id", "")),
        "correlation_id": str(session.get("correlation_id", "")),
        "payload": payload,
        "local_only": True,
        "authoritative": False,
    }


def _append_event(
    *,
    state: SessionLoggingState,
    session: dict[str, str],
    event_type: str,
    payload: dict[str, Any],
    timestamp: str = "",
) -> dict[str, Any]:
    event_path = state.target_root / _event_path_for_session(session)
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with _event_stream_lock(state=state, session=session):
        events, issues = _read_event_stream(event_path)
        sequence = max((int(event.get("sequence", 0) or 0) for event in events), default=0) + 1
        append_payloads: list[dict[str, Any]] = []
        if issues:
            issue_digest = hashlib.sha256(json.dumps(issues, sort_keys=True).encode()).hexdigest()
            already_reported = any(
                event.get("event_type") == "logging.gap"
                and isinstance(event.get("payload"), dict)
                and event["payload"].get("issue_digest") == issue_digest
                for event in events
            )
            if not already_reported:
                append_payloads.append(
                    _new_event(
                        session=session,
                        event_type="logging.gap",
                        sequence=sequence,
                        timestamp=datetime.now(UTC).isoformat(),
                        payload={
                            "reason": "event-stream-recovery",
                            "issue_digest": issue_digest,
                            "issues": issues,
                            "recoverable": True,
                        },
                    )
                )
                sequence += 1
        event = _new_event(
            session=session,
            event_type=event_type,
            sequence=sequence,
            timestamp=timestamp or datetime.now(UTC).isoformat(),
            payload=payload,
        )
        append_payloads.append(event)
        needs_separator = event_path.exists() and event_path.stat().st_size > 0 and not event_path.read_bytes().endswith(b"\n")
        with event_path.open("ab") as handle:
            if needs_separator:
                handle.write(b"\n")
            for item in append_payloads:
                handle.write((json.dumps(serialise_value(item), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        return event


def _append_declared_gap(*, state: SessionLoggingState, session: dict[str, str]) -> None:
    reason = os.environ.get(SESSION_GAP_REASON_ENV, "").strip()
    if not reason:
        return
    events, _ = _read_event_stream(state.target_root / _event_path_for_session(session))
    if any(
        event.get("event_type") == "logging.gap" and isinstance(event.get("payload"), dict) and event["payload"].get("reason") == reason
        for event in events
    ):
        return
    _append_event(
        state=state,
        session=session,
        event_type="logging.gap",
        payload={"reason": reason, "source": SESSION_GAP_REASON_ENV, "recoverable": False},
    )
    if os.environ.get(SESSION_GAP_REASON_ENV, "").strip() == reason:
        os.environ.pop(SESSION_GAP_REASON_ENV, None)


def _command_entries_from_events(events: Iterable[dict[str, Any]], *, physical_session_id: str = "") -> list[dict[str, Any]]:
    entries = []
    for event in events:
        if event.get("event_type") != "command.completed" or not isinstance(event.get("payload"), dict):
            continue
        if physical_session_id and str(event.get("physical_session_id", "")) != physical_session_id:
            continue
        entry = event["payload"].get("entry")
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def _session_prelude(*, state: SessionLoggingState, session: dict[str, str]) -> str:
    snapshot = {
        "kind": SESSION_LOG_KIND,
        "session_id": session["session_id"],
        "logical_session_id": session.get("logical_session_id", ""),
        "event_stream": _event_path_for_session(session).as_posix(),
        "canonical_chronology": "events.jsonl",
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
            "path_normalization": _path_normalization_payload(state),
            "local_diagnostic_boundary": _session_log_local_boundary(),
            "failure_behavior": "Logging failures are warning-only and must not block ordinary AW operation, proof, or closeout claims.",
            "logical_session": {
                "resolution": "identity-registry",
                "identity_source": LOGICAL_SESSION_IDENTITY_ENV,
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


@functools.lru_cache(maxsize=1)
def _declared_workspace_command_interfaces() -> tuple[dict[str, Any], ...]:
    from agentic_workspace.contract_tooling import command_package_ir_manifest

    package = next(
        (
            item
            for item in command_package_ir_manifest().get("packages", [])
            if isinstance(item, dict) and item.get("id") == "root-workspace"
        ),
        {},
    )
    return tuple(item for item in package.get("commands", []) if isinstance(item, dict))


def _declared_operation_intent(argv: Sequence[str]) -> dict[str, str]:
    """Resolve structured argv through generated command IR, not command prose."""
    if not argv:
        return {}
    command = next(
        (item for item in _declared_workspace_command_interfaces() if str(item.get("interface", {}).get("name") or "") == str(argv[0])),
        None,
    )
    if command is None:
        return {}
    interface = command.get("interface", {}) if isinstance(command.get("interface"), dict) else {}
    operation_ref = command.get("operation_ref", {}) if isinstance(command.get("operation_ref"), dict) else {}
    for token in argv[1:]:
        if str(token).startswith("-"):
            break
        subcommands = [item for item in interface.get("subcommands", []) if isinstance(item, dict)]
        selected = next((item for item in subcommands if str(item.get("name") or "") == str(token)), None)
        if selected is None:
            break
        interface = selected
        nested_ref = selected.get("operation_ref", {}) if isinstance(selected.get("operation_ref"), dict) else {}
        if nested_ref:
            operation_ref = nested_ref
    operation_id = str(operation_ref.get("id") or "").strip()
    if not operation_id:
        return {}
    return {
        "operation_id": operation_id,
        "purpose_id": operation_id,
        "purpose_summary": str(interface.get("help") or "").strip(),
        "source": "generated-command-package-ir",
    }


def _invocation_intent(*, origin: dict[str, Any], argv: Sequence[str] = ()) -> dict[str, Any]:
    expected_failure = _expected_fixture_failure(origin)
    expected_exit = os.environ.get("AW_SESSION_LOG_EXPECTED_EXIT", "").strip().lower()
    if not expected_exit and expected_failure:
        expected_exit = "failure"
    declared_operation = _declared_operation_intent(argv)
    invocation_class = os.environ.get("AW_SESSION_LOG_INVOCATION_CLASS", "").strip().lower()
    allowed_classes = {
        "product-operation",
        "probe",
        "negative-fixture",
        "recovery-attempt",
        "analyzer-action",
        "synthetic-check",
    }
    if invocation_class not in allowed_classes:
        invocation_class = "product-operation" if declared_operation else "unknown"
    scenario_id = os.environ.get("AW_SESSION_LOG_SCENARIO_ID", "").strip()
    if not scenario_id and expected_failure and os.environ.get("PYTEST_CURRENT_TEST"):
        scenario_id = os.environ["PYTEST_CURRENT_TEST"].split(" ", 1)[0]
    supplied = any(
        (
            os.environ.get("AW_SESSION_LOG_PURPOSE_ID"),
            scenario_id,
            expected_exit,
            os.environ.get("AW_SESSION_LOG_EXPECTED_REASON_CLASS"),
            invocation_class != "unknown",
            declared_operation,
        )
    )
    return {
        "kind": "agentic-workspace/invocation-intent/v1",
        "status": "declared" if supplied else "unknown",
        "purpose_id": os.environ.get("AW_SESSION_LOG_PURPOSE_ID", "").strip() or str(declared_operation.get("purpose_id") or ""),
        "purpose_summary": str(declared_operation.get("purpose_summary") or ""),
        "operation_id": str(declared_operation.get("operation_id") or ""),
        "scenario_id": scenario_id,
        "invocation_class": invocation_class,
        "expected": {
            "exit_class": expected_exit if expected_exit in {"success", "failure"} else "success" if declared_operation else "unknown",
            "reason_class": os.environ.get("AW_SESSION_LOG_EXPECTED_REASON_CLASS", "").strip() or "unknown",
        },
        "provenance": {
            "producer": str(origin.get("classification") or "unknown"),
            "source": (
                "producer-environment+generated-command-package-ir"
                if declared_operation
                and any(os.environ.get(name) for name in ("AW_SESSION_LOG_PURPOSE_ID", "AW_SESSION_LOG_INVOCATION_CLASS"))
                else "generated-command-package-ir"
                if declared_operation
                else "producer-environment"
                if supplied
                else "not-supplied"
            ),
            "fields": [
                name
                for name in (
                    "AW_SESSION_LOG_PURPOSE_ID",
                    "AW_SESSION_LOG_SCENARIO_ID",
                    "AW_SESSION_LOG_INVOCATION_CLASS",
                    "AW_SESSION_LOG_EXPECTED_EXIT",
                    "AW_SESSION_LOG_EXPECTED_REASON_CLASS",
                    "AW_SESSION_LOG_EXPECTED_FAILURE",
                )
                if os.environ.get(name)
            ],
        },
        "rule": "Producer-declared expectation remains separate from observed execution and is never inferred from command text.",
    }


def _invocation_outcome(*, intent: dict[str, Any], exit_class: str, reason_class: str) -> dict[str, Any]:
    expected = intent.get("expected", {}) if isinstance(intent.get("expected"), dict) else {}
    expected_exit = str(expected.get("exit_class") or "unknown")
    expected_reason = str(expected.get("reason_class") or "unknown")
    if expected_exit == "unknown" and expected_reason == "unknown":
        match = "unknown"
    elif expected_exit not in {"unknown", exit_class} or expected_reason not in {"unknown", reason_class}:
        match = "unmatched"
    else:
        match = "matched"
    return {
        "kind": "agentic-workspace/invocation-outcome/v1",
        "match": match,
        "expected": expected,
        "observed": {"exit_class": exit_class, "reason_class": reason_class},
        "expectation_provenance": intent.get("provenance", {}),
        "rule": "Observed execution is immutable evidence; producer expectation only classifies whether it behaved as declared.",
    }


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
    explicit_task = _option_value(argv, "--task")
    task = explicit_task or str(prior_segment.get("task", ""))
    binding = resolve_current_work_context(
        root=state.target_root,
        task=task,
        argv=argv,
        explicit_pr=os.environ.get("AW_SESSION_LOG_PR", ""),
    )
    plan_id = str(binding.get("plan_id") or "")
    if "new-plan" in argv:
        plan_id = _option_value(argv, "--id") or plan_id
    explicit_pr = os.environ.get("AW_SESSION_LOG_PR", "").lstrip("#")
    pr_matches = re.findall(r"\bPR\s+#?(\d+)\b", f"{task} {command_text}", flags=re.I)
    pr_ref = f"#{explicit_pr or (pr_matches[-1] if pr_matches else '')}" if explicit_pr or pr_matches else str(binding.get("pr_ref") or "")
    refs = sorted({f"#{value}" for value in re.findall(r"#(\d+)", f"{task} {command_text}")})
    issue_refs = [ref for ref in refs if ref != pr_ref]
    if not issue_refs:
        issue_refs = [str(ref) for ref in binding.get("issue_refs", [])]
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
        "work_context": binding,
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
    invocation_intent: dict[str, Any],
    provenance: dict[str, Any],
    segment: dict[str, Any],
) -> str:
    normalized_capture = _normalized_capture(state, capture)
    failure_class = _failure_class(command_text=command_text, capture=normalized_capture)
    invocation_outcome = _invocation_outcome(
        intent=invocation_intent,
        exit_class="success" if normalized_capture.exit_code == 0 else "failure",
        reason_class=failure_class or "none",
    )
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
        f"- invocation_intent: `{json.dumps(serialise_value(invocation_intent), sort_keys=True)}`",
        f"- invocation_outcome: `{json.dumps(serialise_value(invocation_outcome), sort_keys=True)}`",
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
    artifact_path = _artifact_root_for_session(session) / f"{entry_id}-output.json"
    payload = {
        "kind": "agentic-workspace/session-log-output-artifact/v1",
        "entry_id": entry_id,
        "storage_mode": "raw-local-artifact",
        "local_diagnostic_boundary": _session_log_local_boundary(),
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
    return Path(session["log_path"]).parent / "index.json"


def _index_lock_path_for_session(session: dict[str, str]) -> Path:
    return _index_path_for_session(session).parent / ".index.lock"


@contextlib.contextmanager
def _session_index_lock(*, state: SessionLoggingState, session: dict[str, str]) -> Iterator[None]:
    lock_path = state.target_root / _index_lock_path_for_session(session)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.perf_counter() + 5
    while True:
        try:
            lock_path.mkdir()
            break
        except (FileExistsError, PermissionError):
            try:
                stale = time.time() - lock_path.stat().st_mtime > 30
            except OSError:
                stale = False
            if stale:
                with contextlib.suppress(OSError):
                    lock_path.rmdir()
                continue
            if time.perf_counter() >= deadline:
                raise TimeoutError(f"timed out waiting for session index lock: {lock_path}")
            time.sleep(0.01)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            lock_path.rmdir()


def _artifact_root_for_session(session: dict[str, str]) -> Path:
    return Path(session["log_path"]).parent / "artifacts"


def _write_index(
    *, state: SessionLoggingState, session: dict[str, str], entries: Iterable[dict[str, Any]], notes: Iterable[dict[str, Any]]
) -> None:
    index_path = _index_path_for_session(session)
    normalized_entries, records = _normalized_index_entries(entries)
    payload = {
        "kind": SESSION_LOG_INDEX_KIND,
        "session_id": session["session_id"],
        "log_path": session["log_path"],
        "path": index_path.as_posix(),
        "created_at": session.get("created_at", ""),
        "updated_at": datetime.now(UTC).isoformat(),
        "path_normalization": _path_normalization_payload(state),
        "local_diagnostic_boundary": _session_log_local_boundary(),
        "session_header": {
            "session_id": session["session_id"],
            "log_path": session["log_path"],
            "created_at": session.get("created_at", ""),
        },
        "records": records,
        "entries": normalized_entries,
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
    deadline = time.perf_counter() + ATOMIC_REPLACE_RETRY_SECONDS
    try:
        while True:
            try:
                temporary_path.replace(path)
                break
            except PermissionError:
                if time.perf_counter() >= deadline:
                    raise
                time.sleep(0.01)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary_path.unlink()


def _read_index(*, state: SessionLoggingState, session: dict[str, str]) -> dict[str, Any] | None:
    path = state.target_root / _index_path_for_session(session)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("kind") not in SESSION_LOG_INDEX_KINDS:
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
    invocation_intent: dict[str, Any],
    provenance: dict[str, Any],
    segment: dict[str, Any],
    parent_context: dict[str, str] | None = None,
) -> None:
    index = _read_index(state=state, session=session) or {}
    indexed_by_id = {str(entry.get("id", "")): entry for entry in _entries_from_index(index)}
    log_path = state.target_root / session["log_path"]
    # Markdown is the append chronology and survives supported index schema
    # transitions.  Reconcile it at the writer boundary before adding the rich
    # current entry so a partial v1 index cannot silently replace history.
    entries = [
        indexed_by_id.get(str(entry.get("id", "")), entry)
        for entry in _entries_from_markdown(log_path)
        if str(entry.get("id", "")) != entry_id
    ]
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
    invocation_outcome = _invocation_outcome(
        intent=invocation_intent,
        exit_class="success" if normalized_capture.exit_code == 0 else "failure",
        reason_class=failure_class or "none",
    )
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
            "invocation_intent": invocation_intent,
            "invocation_outcome": invocation_outcome,
            "origin": origin,
            "parent_context": parent_context or _parent_context(),
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
    if not isinstance(entries, list):
        return []
    records = index.get("records", {}) if isinstance(index.get("records"), dict) else {}
    tables = {
        name: value if isinstance(value, dict) else {}
        for name, value in records.items()
        if name in {"provenance", "contexts", "segments", "invocation_intents"}
    }
    hydrated = []
    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        entry = dict(raw_entry)
        provenance = tables.get("provenance", {}).get(str(entry.get("provenance_ref", "")), {})
        intent = tables.get("invocation_intents", {}).get(str(entry.get("invocation_intent_ref", "")), {})
        segment = tables.get("segments", {}).get(str(entry.get("segment_ref", "")), {})
        if isinstance(segment, dict):
            segment = dict(segment)
            context = tables.get("contexts", {}).get(str(segment.pop("context_ref", "")), {})
            if context:
                segment["work_context"] = context
        entry.setdefault("provenance", provenance)
        entry.setdefault("invocation_intent", intent)
        entry.setdefault("segment", segment)
        hydrated.append(entry)
    return hydrated


def _record_identity(prefix: str, payload: dict[str, Any]) -> str:
    identity_payload = payload
    if prefix == "context" and isinstance(payload.get("freshness"), dict):
        identity_payload = {
            **payload,
            "freshness": {key: value for key, value in payload["freshness"].items() if key != "resolved_at"},
        }
    digest = hashlib.sha256(json.dumps(identity_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    raw_revision = payload.get("revision")
    revision = str(raw_revision if isinstance(raw_revision, (str, int)) else payload.get("head") or "unversioned")[:12]
    revision = re.sub(r"[^A-Za-z0-9._-]", "-", revision)
    return f"{prefix}:{revision}:{digest}"


def _normalized_index_entries(entries: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    records: dict[str, dict[str, Any]] = {
        "provenance": {},
        "contexts": {},
        "segments": {},
        "invocation_intents": {},
    }
    normalized = []
    for source in entries:
        entry = dict(source)
        provenance = entry.pop("provenance", {}) if isinstance(entry.get("provenance"), dict) else {}
        intent = entry.pop("invocation_intent", {}) if isinstance(entry.get("invocation_intent"), dict) else {}
        segment = entry.pop("segment", {}) if isinstance(entry.get("segment"), dict) else {}
        context = segment.pop("work_context", {}) if isinstance(segment.get("work_context"), dict) else {}
        for field, prefix, payload, table in (
            ("provenance_ref", "provenance", provenance, "provenance"),
            ("context_ref", "context", context, "contexts"),
            ("invocation_intent_ref", "intent", intent, "invocation_intents"),
        ):
            if payload:
                identity = _record_identity(prefix, payload)
                records[table].setdefault(identity, payload)
                if field == "context_ref":
                    segment[field] = identity
                else:
                    entry[field] = identity
        if segment:
            segment_ref = _record_identity("segment", segment)
            records["segments"][segment_ref] = segment
            entry["segment_ref"] = segment_ref
        normalized.append(entry)
    return normalized, records


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


def _session_log_local_boundary() -> dict[str, Any]:
    return {
        "scope": SESSION_LOG_LOCAL_BOUNDARY["scope"],
        "local_only": True,
        "authoritative": False,
        "non_authoritative_for": list(SESSION_LOG_NON_AUTHORITATIVE_FOR),
        "manual_handoff": SESSION_LOG_LOCAL_BOUNDARY["manual_handoff"],
        "raw_capture_policy": SESSION_LOG_LOCAL_BOUNDARY["raw_capture_policy"],
        "rule": SESSION_LOG_LOCAL_BOUNDARY["rule"],
    }


def _path_normalization_payload(state: SessionLoggingState) -> dict[str, Any]:
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
        "raw_artifact_recoverability": "raw output may remain unchanged in ignored local artifacts",
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
    artifact_path = _artifact_root_for_session(session) / f"{entry_id}-output.json"
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
    if isinstance(parsed, dict) and str(parsed.get("kind", "")) == "agentic-workspace/runtime-error/v1":
        return str(parsed.get("failure_class") or "unexpected-runtime-exception")
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
        session_name = cleaned if cleaned.startswith("aw-session-") else f"aw-session-{cleaned}"
        candidate = state.target_root / SESSION_LOG_ROOT / session_name / "session.md"
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
    session_id = _session_id_from_log_path(log_path)
    if not session_id:
        return None
    pseudo_session = {"session_id": session_id, "log_path": log_path.relative_to(state.target_root).as_posix()}
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
        invocation_intent = _json_markdown_metadata(section, "invocation_intent")
        invocation_outcome = _json_markdown_metadata(section, "invocation_outcome")
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
                "invocation_intent": invocation_intent,
                "invocation_outcome": invocation_outcome,
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
    parent = entry.get("parent_context") if isinstance(entry.get("parent_context"), dict) else entry.get("parent", {})
    return {
        "id": entry.get("id", ""),
        "timestamp": entry.get("timestamp", ""),
        "command": _bounded_text(str(entry.get("command", ""))),
        "exit_status": entry.get("exit_status", 0),
        "exit_class": entry.get("exit_class", ""),
        "failure_class": entry.get("failure_class", ""),
        "expected_failure": bool(entry.get("expected_failure", False)),
        "invocation_intent": entry.get("invocation_intent", {}),
        "invocation_outcome": entry.get("invocation_outcome", {}),
        "origin": entry.get("origin", {}),
        "parent": parent,
        "segment_id": entry.get("segment", {}).get("id", "") if isinstance(entry.get("segment"), dict) else "",
        "provenance_ref": entry.get("provenance_ref", ""),
        "segment_ref": entry.get("segment_ref", ""),
        "invocation_intent_ref": entry.get("invocation_intent_ref", ""),
        "output_bytes": entry.get("output_bytes", 0),
        "artifact_path": artifact.get("path", "") if isinstance(artifact, dict) else "",
        "packet_kinds": entry.get("packet_kinds", []),
        "domain_kinds": entry.get("domain_kinds", []),
    }


def _bounded_text(value: str, *, limit: int = 512) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 18] + "…<truncated>"


def _bounded_counter(counter: Counter[str], *, limit: int = 20) -> dict[str, int]:
    return {_bounded_text(key): count for key, count in counter.most_common(limit)}


def _bounded_value(value: Any) -> Any:
    if isinstance(value, str):
        return _bounded_text(value)
    if isinstance(value, dict):
        return {key: _bounded_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_bounded_value(child) for child in value[:10]]
    return value


def _slow_command_friction_candidates(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for entry in entries:
        duration_ms = int(entry.get("duration_ms", 0) or 0)
        if duration_ms < DEFAULT_SLOW_COMMAND_DURATION_MS:
            continue
        command = str(entry.get("command", "")).strip()
        normalized_class = (
            "validation-command" if "pytest" in command or " make test" in command or command.startswith("make test") else "command"
        )
        group_key = f"{normalized_class}\0{command}"
        group = groups.setdefault(
            group_key,
            {
                "command": command,
                "normalized_command_class": normalized_class,
                "durations": [],
                "evidence_refs": [],
                "timestamps": [],
                "host_impact_classes": [],
            },
        )
        group["durations"].append(duration_ms)
        entry_id = str(entry.get("id", "")).strip()
        if entry_id:
            group["evidence_refs"].append(entry_id)
        timestamp = str(entry.get("started_at") or entry.get("timestamp") or entry.get("finished_at") or "").strip()
        if timestamp:
            group["timestamps"].append(timestamp)
        host_impact_class = str(entry.get("host_impact_class") or entry.get("impact_class") or "").strip()
        if host_impact_class:
            group["host_impact_classes"].append(host_impact_class)

    candidates: list[dict[str, Any]] = []
    for group in sorted(groups.values(), key=lambda item: max(item["durations"]), reverse=True):
        durations = [int(item) for item in group["durations"]]
        occurrence_count = len(durations)
        duration_ms_max = max(durations)
        duration_ms_total = sum(durations)
        recurrence = "recurring" if occurrence_count > 1 else "single-observation"
        command = str(group["command"])
        digest = hashlib.sha256(f"{group['normalized_command_class']}\n{command}".encode("utf-8")).hexdigest()[:10]
        timestamps = sorted(str(item) for item in group["timestamps"] if str(item).strip())
        host_impact_classes = list(dict.fromkeys(str(item) for item in group["host_impact_classes"] if str(item).strip()))
        severe_host_impact = any(
            item.lower().replace("_", "-") in {"severe-host-impact", "host-impact-severe", "severe"} for item in host_impact_classes
        )
        severity = "protective-action" if recurrence == "recurring" or severe_host_impact else "attention"
        signal_recurrence = "repeated" if recurrence == "recurring" else "first_seen"
        signal_state = "active" if severity == "protective-action" else "active"
        normalized_command_class = str(group["normalized_command_class"])
        applicability = "applicable-to-proof-route-maintenance" if normalized_command_class == "validation-command" else "review-before-use"
        lifecycle_status = "live-applicable" if severity == "protective-action" else "candidate-local-observation"
        symptom = f"{command} exceeded the slow-command threshold."
        evidence_fingerprint = _improvement_signal_fingerprint(
            signal_kind="validation_friction", symptom=symptom, owner_hint="proof-router"
        )
        candidates.append(
            {
                "id": f"slow-command:{digest}",
                "summary": f"{recurrence} slow command ({occurrence_count} run(s), max {duration_ms_max}ms): {command}",
                "command": command,
                "owner": "proof-route-maintenance",
                "remediation_owner": "proof-router",
                "lifecycle_status": lifecycle_status,
                "recurrence": recurrence,
                "occurrence_count": occurrence_count,
                "duration_ms": duration_ms_max,
                "duration_ms_max": duration_ms_max,
                "duration_ms_total": duration_ms_total,
                "threshold_ms": DEFAULT_SLOW_COMMAND_DURATION_MS,
                "normalized_command_class": normalized_command_class,
                "host_impact_class": "severe-host-impact" if severe_host_impact else "none",
                "host_impact_classes": host_impact_classes,
                "severity": severity,
                "route_identity": f"proof-route-friction:{digest}",
                "treatment": "prefer focused proof; require structured escalation before promoting broad/high-cost proof",
                "evidence_refs": list(dict.fromkeys(str(item) for item in group["evidence_refs"] if str(item).strip())),
                "first_seen_at": timestamps[0] if timestamps else "",
                "last_seen_at": timestamps[-1] if timestamps else "",
                "evidence_destinations": ["Memory improvement signal", "proof-route refinement"],
                "promotion_boundary": "Session-log friction is local diagnostic evidence; durable routing changes need Planning, Memory, issue, or PR evidence.",
                "improvement_signal": {
                    "candidate_kind": "improvement_signal_candidate",
                    "kind": "validation_friction",
                    "state": signal_state,
                    "lifecycle_state": signal_state,
                    "lifecycle_source": "session_log.slow_command",
                    "applicability": applicability,
                    "applicable_live": lifecycle_status == "live-applicable",
                    "applicable_to_current_route": normalized_command_class == "validation-command",
                    "observed_during": "session-log analyze",
                    "symptom": symptom,
                    "cost": f"{occurrence_count} run(s), total {duration_ms_total}ms, max {duration_ms_max}ms.",
                    "expected_benefit": "Select a dependency-bound focused proof route and avoid unrelated broad reruns.",
                    "suspected_owner": "proof-router",
                    "likely_remediation": "validation",
                    "confidence": "medium" if severity == "protective-action" else "low",
                    "recurrence": signal_recurrence,
                    "host_impact_class": "severe-host-impact" if severe_host_impact else "none",
                    "immediate_action": "route" if severity == "protective-action" else "review",
                    "retention": "shrink_after_fix",
                    "source": "session_log.slow_command",
                    "scope_relation": "current-scope",
                    "occurrence_count": occurrence_count,
                    "evidence_classes": ["machine_observed"],
                    "mutation_authorized": False,
                    "route_identity": f"proof-route-friction:{digest}",
                    "evidence_fingerprint": evidence_fingerprint,
                    "allowed_lifecycle_states": ["active", "mitigated", "accepted-risk", "promoted-to-issue", "obsolete"],
                    "consumption_rule": (
                        "Only active, applicable validation-friction signals may influence proof-route escalation; "
                        "candidate-local observations require review or durable routing before they become live escalation inputs."
                    ),
                    "retire_when": "focused proof route or test strategy removes the repeated slow-command pressure",
                    "evidence_refs": list(dict.fromkeys(str(item) for item in group["evidence_refs"] if str(item).strip())),
                },
            }
        )
    return candidates


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
        command = str(item["command"])
        digest = hashlib.sha256(command.encode("utf-8")).hexdigest()[:10]
        symptom = f"{command} was re-entered {item['count']} times in one session."
        fingerprint = _improvement_signal_fingerprint(signal_kind="workflow_cost", symptom=symptom, owner_hint="operating-loop")
        candidates.append(
            {
                "id": "repeated-command",
                "summary": f"Repeated {item['count']} times: {command}",
                "owner": "operating-loop",
                "improvement_signal": {
                    "candidate_kind": "improvement_signal_candidate",
                    "kind": "workflow_cost",
                    "observed_during": "session-log analyze",
                    "symptom": symptom,
                    "cost": "Repeated routing or maintenance re-entry adds command, reconstruction, and correction cost.",
                    "expected_benefit": "Route the task once through the existing owner and avoid repeated maintenance entry.",
                    "suspected_owner": "operating-loop",
                    "likely_remediation": "agent_aid",
                    "confidence": "medium",
                    "recurrence": "repeated",
                    "immediate_action": "route",
                    "retention": "shrink_after_fix",
                    "source": "session_log.repeated_command",
                    "scope_relation": "current-scope",
                    "occurrence_count": int(item["count"]),
                    "evidence_classes": ["machine_observed"],
                    "evidence_refs": [f"session-log:repeated-command:{digest}"],
                    "evidence_fingerprint": fingerprint,
                    "mutation_authorized": False,
                },
            }
        )
    for item in duplicates[:LARGE_OUTPUT_SUMMARY_LIMIT]:
        symptom = "Equivalent AW output was produced repeatedly in one logical session."
        fingerprint = _improvement_signal_fingerprint(signal_kind="workflow_cost", symptom=symptom, owner_hint="operating-loop")
        candidates.append(
            {
                "id": "duplicate-output",
                "summary": f"Same output digest appeared {item['count']} times.",
                "owner": "operating-loop",
                "improvement_signal": {
                    "candidate_kind": "improvement_signal_candidate",
                    "kind": "workflow_cost",
                    "observed_during": "session-log analyze",
                    "symptom": symptom,
                    "cost": f"The same result was reconstructed {item['count']} times instead of being reused.",
                    "expected_benefit": "Reuse the admitted result or route once through its canonical owner.",
                    "suspected_owner": "operating-loop",
                    "likely_remediation": "agent_aid",
                    "confidence": "medium",
                    "recurrence": "repeated",
                    "immediate_action": "route",
                    "retention": "shrink_after_fix",
                    "source": "session_log.duplicate_output",
                    "scope_relation": "current-scope",
                    "occurrence_count": int(item["count"]),
                    "evidence_classes": ["machine_observed"],
                    "evidence_refs": [f"session-log:duplicate-output:{str(item.get('sha256') or '')[:12]}"],
                    "evidence_fingerprint": fingerprint,
                    "mutation_authorized": False,
                },
            }
        )
    receipt_entries = [
        entry
        for entry in entries
        if any(
            str(token).lower() == marker or str(token).lower().startswith("--receipt-")
            for token in entry.get("argv", [])
            for marker in ("--record-receipt", "--record-proof-receipt", "--proof-receipt")
        )
    ]
    if len(receipt_entries) >= 3:
        symptom = "Proof evidence required repeated receipt-write choreography after proof selection."
        fingerprint = _improvement_signal_fingerprint(
            signal_kind="workflow_cost", symptom=symptom, owner_hint="proof-receipt-reconciliation"
        )
        candidates.append(
            {
                "id": "receipt-choreography",
                "summary": f"Proof evidence used {len(receipt_entries)} separate receipt-oriented commands.",
                "owner": "proof-receipt-reconciliation",
                "improvement_signal": {
                    "candidate_kind": "improvement_signal_candidate",
                    "kind": "workflow_cost",
                    "observed_during": "session-log analyze",
                    "symptom": symptom,
                    "cost": f"{len(receipt_entries)} separate receipt-oriented commands increased closeout choreography.",
                    "expected_benefit": "Execute and reconcile selected proof through one supported transaction.",
                    "suspected_owner": "proof-receipt-reconciliation",
                    "likely_remediation": "validation",
                    "confidence": "high",
                    "recurrence": "repeated",
                    "immediate_action": "route",
                    "retention": "shrink_after_fix",
                    "source": "session_log.receipt_choreography",
                    "scope_relation": "current-scope",
                    "occurrence_count": len(receipt_entries),
                    "evidence_classes": ["machine_observed"],
                    "evidence_refs": [str(entry.get("id") or "") for entry in receipt_entries if entry.get("id")],
                    "evidence_fingerprint": fingerprint,
                    "mutation_authorized": False,
                },
            }
        )
    candidates.extend(_slow_command_friction_candidates(entries))
    for entry in entries:
        if _is_session_log_analyzer_entry(entry):
            continue
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


def _is_session_log_analyzer_entry(entry: dict[str, Any]) -> bool:
    try:
        tokens = shlex.split(str(entry.get("command", "")))
    except ValueError:
        tokens = str(entry.get("command", "")).split()
    try:
        surface_index = tokens.index("session-log")
    except ValueError:
        return False
    return "analyze" in tokens[surface_index + 1 :]


def _session_for_log(*, state: SessionLoggingState, log_path: Path, session: dict[str, str] | None) -> dict[str, str]:
    if session and (state.target_root / session.get("log_path", "")) == log_path:
        return session
    registry = _read_session_registry(target_root=state.target_root)
    groups = registry.get("logical_sessions", {})
    if isinstance(groups, dict):
        for group in groups.values():
            if not isinstance(group, dict):
                continue
            event_stream_path = _valid_event_stream_path(str(group.get("event_stream_path", "")))
            for candidate in group.get("sessions", []):
                registered = _validated_session(candidate)
                if registered and (state.target_root / registered["log_path"]) == log_path:
                    return {**registered, "event_stream_path": event_stream_path or registered.get("event_stream_path", "")}
    session_id = _session_id_from_log_path(log_path)
    return {
        "kind": SESSION_RECORD_KIND,
        "session_id": session_id or hashlib.sha256(log_path.as_posix().encode()).hexdigest()[:12],
        "created_at": "",
        "log_path": log_path.relative_to(state.target_root).as_posix(),
    }


def _session_id_from_log_path(log_path: Path) -> str:
    match = re.match(r"aw-session-(?P<session_id>.+)$", log_path.parent.name) if log_path.name == "session.md" else None
    return match.group("session_id") if match else ""


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
        if not path and not session_id and not _logical_session_identity():
            return _identity_required_payload(kind="agentic-workspace/session-log-index-repair/v1")
        return {"kind": "agentic-workspace/session-log-index-repair/v1", "status": "missing-log", "path": ""}
    effective_session = _session_for_log(state=state, log_path=log_path, session=session)
    with _session_index_lock(state=state, session=effective_session):
        return _repair_session_log_index_locked(state=state, log_path=log_path, session=session, effective_session=effective_session)


def _repair_session_log_index_locked(
    *, state: SessionLoggingState, log_path: Path, session: dict[str, str] | None, effective_session: dict[str, str]
) -> dict[str, Any]:
    index = _read_index_for_log(state=state, log_path=log_path, session=session)
    existing = _entries_from_index(index or {})
    markdown_entries = _entries_from_markdown(log_path)
    canonical_events, event_issues = _read_event_stream(state.target_root / _event_path_for_session(effective_session))
    canonical_entries = _command_entries_from_events(canonical_events, physical_session_id=effective_session["session_id"])
    source_entries = canonical_entries or markdown_entries
    existing_by_id = {str(entry.get("id", "")): entry for entry in existing}
    source_ids = {str(entry.get("id", "")) for entry in source_entries}
    missing = [entry for entry in source_entries if str(entry.get("id", "")) not in existing_by_id]
    quarantined = [entry for entry in existing if str(entry.get("id", "")) not in source_ids]
    notes = index.get("notes", []) if isinstance(index, dict) and isinstance(index.get("notes"), list) else []
    merged = [existing_by_id.get(str(entry.get("id", "")), entry) for entry in source_entries]
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
        "source": _event_path_for_session(effective_session).as_posix() if canonical_entries else effective_session["log_path"],
        "source_event_issues": event_issues,
    }
    _write_json_atomic(index_path, repaired_index)
    coverage = _coverage_payload(markdown_entries=source_entries, index=repaired_index)
    return {
        "kind": "agentic-workspace/session-log-index-repair/v1",
        "status": "repaired" if missing or quarantined else "already-covered",
        "path": effective_session["log_path"],
        "index_path": _index_path_for_session(effective_session).as_posix(),
        "added_entry_count": len(missing),
        "quarantined_entry_count": len(quarantined),
        "coverage": coverage,
        "repair_source": "canonical-event-stream" if canonical_entries else "markdown-fallback",
        "event_stream_issues": event_issues,
        "local_only": True,
        "authoritative": False,
    }


def _normalized_export_text(*, state: SessionLoggingState, text: str) -> str:
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


def _normalized_export_value(*, state: SessionLoggingState, value: Any) -> Any:
    if isinstance(value, str):
        return _normalized_export_text(state=state, text=value)
    if isinstance(value, dict):
        return {key: _normalized_export_value(state=state, value=child) for key, child in value.items()}
    if isinstance(value, list):
        return [_normalized_export_value(state=state, value=child) for child in value]
    return value


def _export_index_payload(
    *, state: SessionLoggingState, session: dict[str, str], markdown_entries: list[dict[str, Any]], index: dict[str, Any] | None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    indexed_entries = _entries_from_index(index or {})
    indexed_by_id = {str(entry.get("id", "")): entry for entry in indexed_entries}
    entries = [indexed_by_id.get(str(entry.get("id", "")), entry) for entry in markdown_entries]
    normalized_entries, records = _normalized_index_entries(entries)
    payload = {
        "kind": SESSION_LOG_INDEX_KIND,
        "session_id": session["session_id"],
        "log_path": session["log_path"],
        "path": _index_path_for_session(session).as_posix(),
        "created_at": str((index or {}).get("created_at", session.get("created_at", ""))),
        "updated_at": str((index or {}).get("updated_at", "")),
        "path_normalization": _path_normalization_payload(state),
        "local_diagnostic_boundary": _session_log_local_boundary(),
        "session_header": {
            "session_id": session["session_id"],
            "log_path": session["log_path"],
            "created_at": session.get("created_at", ""),
        },
        "records": records,
        "entries": normalized_entries,
        "notes": list((index or {}).get("notes", [])) if isinstance((index or {}).get("notes"), list) else [],
        "export_projection": {
            "profile": "all-command-summary",
            "selection_mode": "all-source-session-commands",
            "source_command_count": len(markdown_entries),
            "exported_command_count": len(normalized_entries),
            "complete_for_profile": len(markdown_entries) == len(normalized_entries),
        },
        "local_only": False,
        "authoritative": False,
    }
    return payload, entries


def _logical_export_sessions(*, state: SessionLoggingState, current: dict[str, str], explicit_selection: bool) -> list[dict[str, str]]:
    if explicit_selection:
        return [current]
    registry = _read_session_registry(target_root=state.target_root)
    groups = registry.get("logical_sessions", {})
    if not isinstance(groups, dict):
        return [current]
    root_id = str(current.get("logical_session_id", ""))
    if not root_id:
        identity = _logical_session_identity()
        key = _logical_identity_fingerprint(identity=identity, registry=registry) if identity else ""
        root_id = _logical_session_id(key)
    included_ids = {root_id}
    changed = True
    while changed:
        changed = False
        for group in groups.values():
            if not isinstance(group, dict):
                continue
            logical_id = str(group.get("logical_session_id", ""))
            parent_id = str(group.get("parent_logical_session_id", ""))
            if parent_id in included_ids and logical_id and logical_id not in included_ids:
                included_ids.add(logical_id)
                changed = True
    sessions: dict[str, dict[str, str]] = {current["session_id"]: current}
    for group in groups.values():
        if not isinstance(group, dict) or str(group.get("logical_session_id", "")) not in included_ids:
            continue
        for candidate in group.get("sessions", []):
            session = _validated_session(candidate)
            if session and (state.target_root / session["log_path"]).is_file():
                sessions[session["session_id"]] = session
    return sorted(sessions.values(), key=lambda item: (item.get("created_at", ""), item["session_id"]))


def _synthetic_export_event(
    *, session: dict[str, str], event_type: str, sequence: int, timestamp: str, payload: dict[str, Any]
) -> dict[str, Any]:
    identity = hashlib.sha256(
        json.dumps(
            {"session": session["session_id"], "type": event_type, "sequence": sequence, "payload": payload},
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()[:16]
    return {
        "kind": SESSION_LOG_EVENT_KIND,
        "schema_version": SESSION_LOG_EVENT_SCHEMA_VERSION,
        "event_id": f"recovered-{identity}",
        "event_type": event_type,
        "timestamp": timestamp,
        "sequence": sequence,
        "logical_session_id": str(session.get("logical_session_id", "")),
        "physical_session_id": session["session_id"],
        "parent_logical_session_id": str(session.get("parent_logical_session_id", "")),
        "correlation_id": str(session.get("correlation_id", "")),
        "payload": payload,
        "local_only": False,
        "authoritative": False,
        "recovered_from": "legacy-derived-view",
    }


def _events_for_export(
    *, state: SessionLoggingState, session: dict[str, str], physical_only: bool = False
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    event_path = state.target_root / _event_path_for_session(session)
    events, issues = _read_event_stream(event_path)
    if physical_only:
        events = [event for event in events if str(event.get("physical_session_id", "")) == session["session_id"]]
    log_path = state.target_root / session["log_path"]
    index = _read_index_for_log(state=state, log_path=log_path, session=session)
    markdown_entries = _entries_from_markdown(log_path)
    indexed_entries = _entries_from_index(index or {})
    indexed_by_id = {str(entry.get("id", "")): entry for entry in indexed_entries}
    legacy_entries = [indexed_by_id.get(str(entry.get("id", "")), entry) for entry in markdown_entries]
    command_ids = {str(entry.get("id", "")) for entry in _command_entries_from_events(events)}
    started_command_ids = {
        str(event.get("payload", {}).get("entry_id", ""))
        for event in events
        if event.get("event_type") == "command.started" and isinstance(event.get("payload"), dict)
    }
    incomplete_command_ids = sorted(started_command_ids - command_ids)
    sequence = max((int(event.get("sequence", 0) or 0) for event in events), default=0)
    recovered: list[dict[str, Any]] = []
    if not any(event.get("event_type") == "session.started" for event in events):
        sequence += 1
        recovered.append(
            _synthetic_export_event(
                session=session,
                event_type="session.started",
                sequence=sequence,
                timestamp=session.get("created_at", ""),
                payload={"created_at": session.get("created_at", ""), "migration": "legacy-session"},
            )
        )
    missing_entries = [entry for entry in legacy_entries if str(entry.get("id", "")) not in command_ids]
    if issues or missing_entries or incomplete_command_ids:
        sequence += 1
        recovered.append(
            _synthetic_export_event(
                session=session,
                event_type="logging.gap",
                sequence=sequence,
                timestamp=datetime.now(UTC).isoformat(),
                payload={
                    "reason": "legacy-migration" if not events else "canonical-stream-incomplete",
                    "issues": issues,
                    "recovered_command_count": len(missing_entries),
                    "incomplete_command_ids": incomplete_command_ids,
                    "recoverable": True,
                },
            )
        )
    for entry in missing_entries:
        sequence += 1
        recovered.append(
            _synthetic_export_event(
                session=session,
                event_type="command.completed",
                sequence=sequence,
                timestamp=str(entry.get("finished_at") or entry.get("timestamp") or session.get("created_at", "")),
                payload={"entry": entry, "migration": "legacy-session"},
            )
        )
    return events + recovered, legacy_entries, issues


def _artifact_chunk_events(
    *, state: SessionLoggingState, session: dict[str, str], entries: list[dict[str, Any]], include_artifacts: bool
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    result: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    seen: set[str] = set()
    artifact_root = (state.target_root / _artifact_root_for_session(session)).resolve()
    for entry in entries:
        artifact = entry.get("artifact") if isinstance(entry.get("artifact"), dict) else None
        artifact_path = str((artifact or {}).get("path", ""))
        if not artifact_path or artifact_path in seen:
            continue
        seen.add(artifact_path)
        record = {
            "source_path": artifact_path,
            "sha256": str((artifact or {}).get("sha256", "")),
            "bytes": int((artifact or {}).get("bytes", 0) or 0),
            "physical_session_id": session["session_id"],
        }
        if not include_artifacts:
            coverage.append({**record, "status": "digest-only" if record["sha256"] else "omitted"})
            continue
        candidate = (state.target_root / artifact_path).resolve()
        try:
            candidate.relative_to(artifact_root)
            payload = json.loads(candidate.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError, json.JSONDecodeError):
            coverage.append({**record, "status": "missing"})
            continue
        coverage.append({**record, "status": "included-as-output-chunks"})
        for stream in ("stdout", "stderr"):
            text = _normalized_export_text(state=state, text=str(payload.get(stream, "")))
            chunks = [text[index : index + 32768] for index in range(0, len(text), 32768)] or [""]
            for chunk_index, chunk in enumerate(chunks):
                result.append(
                    _synthetic_export_event(
                        session=session,
                        event_type="output.chunk",
                        sequence=chunk_index + 1,
                        timestamp=str(entry.get("finished_at") or entry.get("timestamp") or session.get("created_at", "")),
                        payload={
                            "entry_id": str(entry.get("id", "")),
                            "artifact_sha256": record["sha256"],
                            "stream": stream,
                            "chunk_index": chunk_index,
                            "chunk_count": len(chunks),
                            "text": chunk,
                        },
                    )
                )
    return result, coverage


def export_session_log(
    *,
    state: SessionLoggingState,
    path: str = "",
    session_id: str = "",
    include_artifacts: bool = True,
) -> dict[str, Any]:
    logical_identity = _logical_session_identity()
    session = _session_for_caller(target_root=state.target_root, logical_identity=logical_identity)
    if state.enabled and session:
        session = ensure_session(state=state)
    log_path = _analysis_log_path(state=state, path=path, session_id=session_id, session=session)
    if log_path is None:
        if not path and not session_id and not _logical_session_identity():
            return _identity_required_payload(kind="agentic-workspace/session-log-export/v1")
        return {"kind": "agentic-workspace/session-log-export/v1", "status": "missing-log", "path": ""}
    effective_session = _session_for_log(state=state, log_path=log_path, session=session)
    explicit_selection = bool(path or session_id)
    physical_sessions = _logical_export_sessions(state=state, current=effective_session, explicit_selection=explicit_selection)
    session_scope = _session_scope_payload(session=effective_session, explicit_selection=explicit_selection)
    if not explicit_selection:
        session_scope = {
            **session_scope,
            "breadth": "logical-session-tree",
            "physical_session_count": len(physical_sessions),
            "includes_rotations": len(physical_sessions) > 1,
            "includes_delegated_children": any(item.get("parent_logical_session_id") for item in physical_sessions),
        }
    all_events: list[dict[str, Any]] = []
    artifact_coverage: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    source_command_count = 0
    source_issues: list[dict[str, Any]] = []
    read_event_streams: set[str] = set()
    for physical in physical_sessions:
        event_stream_path = _event_path_for_session(physical).as_posix()
        events, entries, issues = _events_for_export(
            state=state,
            session=physical,
            physical_only=explicit_selection,
        )
        if event_stream_path not in read_event_streams:
            all_events.extend(events)
            source_issues.extend({"event_stream_path": event_stream_path, **issue} for issue in issues)
            read_event_streams.add(event_stream_path)
        else:
            all_events.extend(event for event in events if event.get("recovered_from"))
        source_command_count += len(entries)
        for source_path in (
            physical["log_path"],
            _event_path_for_session(physical).as_posix(),
            _index_path_for_session(physical).as_posix(),
        ):
            absolute_source = state.target_root / source_path
            if absolute_source.is_file():
                source_hashes[source_path] = hashlib.sha256(absolute_source.read_bytes()).hexdigest()
        chunks, coverage = _artifact_chunk_events(
            state=state,
            session=physical,
            entries=entries,
            include_artifacts=include_artifacts,
        )
        all_events.extend(chunks)
        artifact_coverage.extend(coverage)
    all_events.sort(
        key=lambda event: (
            str(event.get("timestamp", "")),
            str(event.get("physical_session_id", "")),
            int(event.get("sequence", 0) or 0),
            str(event.get("event_type", "")),
            str(event.get("event_id", "")),
        )
    )
    normalized_events = []
    for index, event in enumerate(all_events):
        source_sequence = int(event.get("sequence", 0) or 0)
        normalized_events.append(
            _normalized_export_value(
                state=state,
                value={
                    **event,
                    "source_sequence": source_sequence,
                    "sequence": index + 1,
                    "export_sequence": index + 1,
                    "local_only": False,
                },
            )
        )
    timestamps = [str(event.get("timestamp", "")) for event in normalized_events if event.get("timestamp")]
    gap_events = [event for event in normalized_events if event.get("event_type") == "logging.gap"]
    delegated_child_session_ids = [item["session_id"] for item in physical_sessions if item.get("parent_logical_session_id")]
    rotated_session_ids = [item["session_id"] for item in physical_sessions if item.get("prior_session_id")]
    excluded_artifacts = [item for item in artifact_coverage if item.get("status") != "included-as-output-chunks"]
    manifest = {
        "kind": "agentic-workspace/session-log-export-manifest/v2",
        "artifact_class": "normalized-share-safe-jsonl",
        "source_artifact_class": "raw-local-diagnostic",
        "canonical_format": "jsonl",
        "compression": "gzip",
        "source_session_id": effective_session["session_id"],
        "source_session_ids": [item["session_id"] for item in physical_sessions],
        "source_log_path": effective_session["log_path"],
        "source_log_paths": [item["log_path"] for item in physical_sessions],
        "source_event_stream_paths": sorted(read_event_streams),
        "source_logical_stream_count": len(read_event_streams),
        "delegated_child_session_ids": delegated_child_session_ids,
        "rotated_session_ids": rotated_session_ids,
        "logical_session_id": effective_session.get("logical_session_id", ""),
        "session_scope": session_scope,
        "created_at": datetime.now(UTC).isoformat(),
        "path_normalization_mode": "known-local-paths",
        "event_count": len(normalized_events),
        "event_type_counts": dict(sorted(Counter(str(event.get("event_type", "")) for event in normalized_events).items())),
        "gap_count": len(gap_events),
        "gaps": [event.get("payload", {}) for event in gap_events],
        "source_stream_issues": source_issues,
        "time_coverage": {"started_at": min(timestamps) if timestamps else "", "finished_at": max(timestamps) if timestamps else ""},
        "evidence_profile": {
            "id": "complete-logical-session-with-output-chunks" if include_artifacts else "complete-logical-session-summary",
            "command_selection": "all-logical-session-tree-commands" if not explicit_selection else "one-physical-session",
            "detail_policy": "include-available-artifact-output-chunks" if include_artifacts else "omit-artifact-bytes-retain-digests",
            "source_command_count": source_command_count,
            "exported_command_count": sum(1 for event in normalized_events if event.get("event_type") == "command.completed"),
            "canonical_event_stream_complete": not source_issues and not gap_events,
            "suitable_for": ["summary-analysis", "human-chronology", "stream-processing"],
        },
        "artifact_coverage": artifact_coverage,
        "excluded_artifact_count": len(excluded_artifacts),
        "excluded_artifacts": excluded_artifacts,
        "source_hashes": source_hashes,
        "originals_mutated": False,
        "local_only": False,
        "artifact_route": "Use this normalized JSONL stream as the review candidate; keep raw local diagnostics local.",
        "transfer_review": {
            "status": "required",
            "approval": "not-granted",
            "rule": "Path normalization does not approve external transfer; review the stream for secrets and policy before sharing.",
        },
        "authoritative": False,
        "local_diagnostic_boundary": _session_log_local_boundary(),
        "limitations": "Known local paths are normalized; export is not a secret scan or transfer approval.",
    }
    manifest_event = {
        "kind": SESSION_LOG_EVENT_KIND,
        "schema_version": SESSION_LOG_EVENT_SCHEMA_VERSION,
        "event_id": "export-manifest-" + uuid.uuid4().hex[:16],
        "event_type": "export.manifest",
        "timestamp": manifest["created_at"],
        "sequence": 0,
        "export_sequence": 0,
        "logical_session_id": effective_session.get("logical_session_id", ""),
        "physical_session_id": "export",
        "parent_logical_session_id": "",
        "correlation_id": effective_session.get("correlation_id", ""),
        "payload": manifest,
        "local_only": False,
        "authoritative": False,
    }
    export_identity = effective_session.get("logical_session_id", "") or effective_session["session_id"]
    export_path = (
        SESSION_LOG_ROOT
        / "exports"
        / f"aw-session-{export_identity}-share-safe-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}.jsonl.gz"
    )
    absolute_export = state.target_root / export_path
    absolute_export.parent.mkdir(parents=True, exist_ok=True)
    temporary_export = absolute_export.with_suffix(absolute_export.suffix + f".{uuid.uuid4().hex}.tmp")
    with temporary_export.open("wb") as raw_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as compressed:
            for event in [manifest_event, *normalized_events]:
                compressed.write((json.dumps(serialise_value(event), sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
    temporary_export.replace(absolute_export)
    return {
        "kind": "agentic-workspace/session-log-export/v2",
        "status": "exported",
        "artifact_class": "normalized-share-safe-jsonl",
        "source_artifact_class": "raw-local-diagnostic",
        "artifact_route": "The path identifies one normalized JSONL chronology for the selected logical session scope.",
        "transfer_approval": "not-granted",
        "path": export_path.as_posix(),
        "source_log_path": effective_session["log_path"],
        "source_log_paths": manifest["source_log_paths"],
        "session_id": effective_session["session_id"],
        "session_ids": manifest["source_session_ids"],
        "logical_session_id": effective_session.get("logical_session_id", ""),
        "artifact_count": sum(1 for item in artifact_coverage if item["status"] == "included-as-output-chunks"),
        "event_count": len(normalized_events) + 1,
        "gap_count": len(gap_events),
        "sha256": hashlib.sha256(absolute_export.read_bytes()).hexdigest(),
        "manifest": manifest,
        "session_scope": session_scope,
        "local_diagnostic_boundary": _session_log_local_boundary(),
        "local_only": False,
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
                **{
                    key: _bounded_value(segment.get(key))
                    for key in ("task", "plan_id", "branch", "head", "pr_ref", "closeout_status", "issue_refs")
                },
                "id": segment_id,
                "command_count": len(members),
                "failure_count": sum(1 for entry in members if int(entry.get("exit_status", 0) or 0) != 0),
                "started_at": str(members[0].get("timestamp", "")),
                "finished_at": str(members[-1].get("timestamp", "")),
            }
        )
    return summaries


def _episode_summaries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        intent = entry.get("invocation_intent", {}) if isinstance(entry.get("invocation_intent"), dict) else {}
        segment = entry.get("segment", {}) if isinstance(entry.get("segment"), dict) else {}
        purpose = str(intent.get("purpose_id", "") or "unknown-purpose")
        scenario = str(intent.get("scenario_id", "") or "unknown-scenario")
        segment_id = str(segment.get("id", "") or "unknown-segment")
        key = f"{purpose}\0{scenario}\0{segment_id}"
        grouped.setdefault(key, []).append(entry)
    summaries = []
    for key, members in grouped.items():
        purpose, scenario, segment_id = key.split("\0", 2)
        classes = Counter(
            str(entry.get("invocation_intent", {}).get("invocation_class", "unknown"))
            for entry in members
            if isinstance(entry.get("invocation_intent"), dict)
        )
        summaries.append(
            {
                "id": _record_identity("episode", {"purpose": purpose, "scenario": scenario, "segment": segment_id}),
                "purpose_id": purpose,
                "scenario_id": scenario,
                "segment_id": segment_id,
                "command_count": len(members),
                "failure_count": sum(1 for entry in members if int(entry.get("exit_status", 0) or 0) != 0),
                "invocation_classes": dict(sorted(classes.items())),
                "started_at": str(members[0].get("timestamp", "")),
                "finished_at": str(members[-1].get("timestamp", "")),
            }
        )
    return summaries


def _paged_detail(*, values: list[Any], page: int, page_size: int) -> dict[str, Any]:
    start = (page - 1) * page_size
    return {
        "page": page,
        "page_size": page_size,
        "total_count": len(values),
        "has_more": start + page_size < len(values),
        "items": values[start : start + page_size],
    }


def analyze_session_log(
    *,
    state: SessionLoggingState,
    path: str = "",
    session_id: str = "",
    segment_id: str = "",
    origin_scope: str = "agent",
    detail: str = "summary",
    page: int = 1,
    page_size: int = DEFAULT_ANALYSIS_PAGE_SIZE,
) -> dict[str, Any]:
    session = _session_for_caller(target_root=state.target_root, logical_identity=_logical_session_identity())
    log_path = _analysis_log_path(state=state, path=path, session_id=session_id, session=session)
    if log_path is None:
        if not path and not session_id and not _logical_session_identity():
            return _identity_required_payload(kind="agentic-workspace/session-log-analysis/v1")
        return {
            "kind": "agentic-workspace/session-log-analysis/v1",
            "status": "missing-log",
            "enabled": state.enabled,
            "path": "",
            "index_status": "missing",
            "rule": "Pass --path, --id, or create a session with session-log new-session before analyzing logs.",
        }

    effective_session = _session_for_log(state=state, log_path=log_path, session=session)
    session_scope = _session_scope_payload(session=effective_session, explicit_selection=bool(path or session_id))
    index = _read_index_for_log(state=state, log_path=log_path, session=session)
    markdown_entries = _entries_from_markdown(log_path)
    coverage = _coverage_payload(markdown_entries=markdown_entries, index=index)
    canonical_events, event_issues = _read_event_stream(state.target_root / _event_path_for_session(effective_session))
    canonical_entries = _command_entries_from_events(
        canonical_events,
        physical_session_id=effective_session["session_id"] if path or session_id else "",
    )
    all_entries = canonical_entries or (_entries_from_index(index) if index is not None else markdown_entries)
    selected_entries = [
        entry
        for entry in all_entries
        if not segment_id or (isinstance(entry.get("segment"), dict) and str(entry["segment"].get("id", "")) == segment_id)
    ]
    origin_groups = {
        "agent": {"agent"},
        "test": {"pytest"},
        "synthetic": {"validation", "nested-aw"},
        "unknown": {"unknown"},
        "all": {"agent", "pytest", "validation", "nested-aw", "unknown"},
    }
    origin_scope = origin_scope if origin_scope in origin_groups else "agent"
    supported_details = {"summary", "entries", "segments", "episodes", "contexts", "candidates"}
    selected_detail = detail if detail in supported_details else "summary"
    entries = [entry for entry in selected_entries if _origin_name(entry) in origin_groups[origin_scope]]
    notes = index.get("notes", []) if isinstance(index, dict) and isinstance(index.get("notes"), list) else []
    command_counter = Counter(str(entry.get("command", "")) for entry in entries if entry.get("command"))
    digest_counter = Counter(str(entry.get("output_digest", "")) for entry in entries if entry.get("output_digest"))
    failures = [entry for entry in entries if int(entry.get("exit_status", 0) or 0) != 0]
    matched_expectations = [
        entry
        for entry in entries
        if isinstance(entry.get("invocation_outcome"), dict) and entry["invocation_outcome"].get("match") == "matched"
    ]
    unmatched_expectations = [
        entry
        for entry in entries
        if isinstance(entry.get("invocation_outcome"), dict) and entry["invocation_outcome"].get("match") == "unmatched"
    ]
    expected_success_failures = [
        entry
        for entry in unmatched_expectations
        if isinstance(entry.get("invocation_outcome"), dict)
        and isinstance(entry["invocation_outcome"].get("expected"), dict)
        and isinstance(entry["invocation_outcome"].get("observed"), dict)
        and entry["invocation_outcome"]["expected"].get("exit_class") == "success"
        and entry["invocation_outcome"]["observed"].get("exit_class") == "failure"
    ]
    expected_failure_successes = [
        entry
        for entry in unmatched_expectations
        if isinstance(entry.get("invocation_outcome"), dict)
        and isinstance(entry["invocation_outcome"].get("expected"), dict)
        and isinstance(entry["invocation_outcome"].get("observed"), dict)
        and entry["invocation_outcome"]["expected"].get("exit_class") == "failure"
        and entry["invocation_outcome"]["observed"].get("exit_class") == "success"
    ]
    unknown_expectations = [
        entry
        for entry in entries
        if not isinstance(entry.get("invocation_outcome"), dict) or entry["invocation_outcome"].get("match") in {None, "", "unknown"}
    ]
    unexpected_failures = [entry for entry in failures if entry not in matched_expectations]
    live_failures = [
        entry for entry in unexpected_failures if _origin_name(entry) == "agent" and not bool(entry.get("expected_failure", False))
    ]
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
    all_failures = [entry for entry in selected_entries if int(entry.get("exit_status", 0) or 0) != 0]
    failures_by_origin = Counter(_origin_name(entry) for entry in all_failures)
    origin_breakdown = Counter(_origin_name(entry) for entry in selected_entries)
    repeated_failures_by_origin: dict[str, list[dict[str, Any]]] = {}
    for origin in sorted({_origin_name(entry) for entry in all_failures}):
        counter = Counter(str(entry.get("command", "")) for entry in all_failures if _origin_name(entry) == origin and entry.get("command"))
        repeated_failures_by_origin[origin] = [
            {"command": command, "count": count} for command, count in counter.most_common() if count > 1
        ]
    origin_partitions = {}
    for partition, origins in origin_groups.items():
        if partition == "all":
            continue
        members = [entry for entry in selected_entries if _origin_name(entry) in origins]
        partition_failures = [entry for entry in members if int(entry.get("exit_status", 0) or 0) != 0]
        origin_partitions[partition] = {
            "origins": sorted(origins),
            "command_count": len(members),
            "failure_count": len(partition_failures),
            "detail_route": (
                f"agentic-workspace session-log analyze --origin {partition} --detail entries --page 1 --page-size 25 --format json"
            ),
        }
    analyzer_overhead = [entry for entry in selected_entries if _is_session_log_analyzer_entry(entry)]
    product_entries = [entry for entry in entries if not _is_session_log_analyzer_entry(entry)]
    product_commands = Counter(str(entry.get("command", "")) for entry in product_entries if entry.get("command"))
    product_digests = Counter(str(entry.get("output_digest", "")) for entry in product_entries if entry.get("output_digest"))
    friction_candidates = _friction_candidates(
        entries=product_entries,
        failures=[entry for entry in (live_failures if origin_scope == "agent" else failures) if not _is_session_log_analyzer_entry(entry)],
        repeated=[{"command": command, "count": count} for command, count in product_commands.most_common() if count > 1],
        duplicates=[{"sha256": digest, "count": count} for digest, count in product_digests.most_common() if count > 1],
        index_present=index is not None,
    )
    summary_payload = {
        "command_count": len(entries),
        "note_count": len(notes),
        "failure_count": len(live_failures) if origin_scope == "agent" else len(unexpected_failures),
        "failed_count": len(live_failures) if origin_scope == "agent" else len(unexpected_failures),
        "observed_nonzero_exit_count": len(failures),
        "live_agent_failure_count": len(live_failures),
        "expected_failure_count": sum(1 for entry in failures if bool(entry.get("expected_failure", False))),
        "matched_expectation_count": len(matched_expectations),
        "unmatched_expectation_count": len(unmatched_expectations),
        "expected_success_failure_count": len(expected_success_failures),
        "expected_failure_success_count": len(expected_failure_successes),
        "unknown_expectation_count": len(unknown_expectations),
        "unexpected_failure_count": len(unexpected_failures),
        "usage_mistake_count": len(usage_mistakes),
        "repeated_command_count": len(repeated),
        "repeated_failure_count": len(repeated_failures),
        "duplicate_output_count": len(duplicates),
        "artifact_count": sum(1 for entry in entries if entry.get("artifact")),
    }
    analysis_scope = {
        "origin": origin_scope,
        "default": "agent",
        "included_origins": sorted(origin_groups[origin_scope]),
        "detail_route": (
            "agentic-workspace session-log analyze "
            "--detail <entries|segments|episodes|contexts|candidates> --page 1 --page-size 25 --format json"
        ),
        "rule": "The ordinary packet is live-agent-first; other origins remain available through explicit origin scope.",
    }
    bounded_collections = {
        "sample_limit": LARGE_OUTPUT_SUMMARY_LIMIT,
        "entry_sample_limit": DEFAULT_ANALYSIS_ENTRY_SAMPLE_LIMIT,
        "candidate_limit": FRICTION_CANDIDATE_LIMIT,
        "default_serialization_budget_bytes": DEFAULT_ANALYSIS_SERIALIZATION_BUDGET_BYTES,
        "full_detail_requires_selector": True,
        "available": sorted(supported_details - {"summary"}),
    }
    export_routing = {
        "download_or_share": "agentic-workspace session-log export --target ./repo --format json",
        "artifact_class": "normalized-share-safe",
        "raw_local_route": "Keep the source session directory local; it is not the share artifact.",
        "authority": "session-log export is the sole share/download route for session evidence",
        "transfer_approval": "not-granted",
        "review_required": "Review the normalized archive for secrets and external-transfer policy before sharing.",
    }
    common_payload = {
        "kind": "agentic-workspace/session-log-analysis/v1",
        "status": "analyzed",
        "enabled": state.enabled,
        "path": log_path.relative_to(state.target_root).as_posix(),
        "index_status": coverage["status"],
        "index_presence": "present" if index is not None else "markdown-fallback",
        "chronology_source": "canonical-event-stream" if canonical_entries else "legacy-derived-view",
        "event_stream_path": _event_path_for_session(effective_session).as_posix(),
        "event_stream_issues": event_issues,
        "session_scope": session_scope,
        "coverage": coverage,
        "index_path": str(index.get("path", "")) if isinstance(index, dict) else "",
        "summary": summary_payload,
        "analysis_scope": analysis_scope,
        "origin_breakdown": dict(sorted(origin_breakdown.items())),
        "origin_partitions": origin_partitions,
        "analyzer_overhead": {
            "command_count": len(analyzer_overhead),
            "detail_route": "agentic-workspace session-log analyze --detail entries --format json",
            "rule": "session-log analyze traffic is classified separately and cannot become default product-friction evidence.",
        },
        "failures_by_origin": _bounded_counter(failures_by_origin),
        "repeated_failures_by_origin": repeated_failures_by_origin,
        "repeated_commands": [_bounded_value(value) for value in repeated[:LARGE_OUTPUT_SUMMARY_LIMIT]],
        "repeated_failures": [_bounded_value(value) for value in repeated_failures[:LARGE_OUTPUT_SUMMARY_LIMIT]],
        "duplicate_outputs": duplicates[:LARGE_OUTPUT_SUMMARY_LIMIT],
        "packet_kinds": _bounded_counter(packet_kinds),
        "parsed_packet_kinds": _bounded_counter(packet_kinds),
        "top_level_kinds": _bounded_counter(top_level_kinds),
        "domain_kinds": _bounded_counter(domain_kinds),
        "detail": selected_detail,
        "bounded_collections": bounded_collections,
        "selected_segment": segment_id,
        "export_routing": export_routing,
        "local_diagnostic_boundary": _session_log_local_boundary(),
        "local_only": True,
        "authoritative": False,
        "rule": SESSION_LOG_LOCAL_BOUNDARY["rule"],
    }
    if selected_detail == "summary":
        return {
            **common_payload,
            "detail_page": None,
            "current_findings": {
                "largest_output": _entry_brief(largest[0]) if largest else None,
                "friction_candidates": [_bounded_value(value) for value in friction_candidates[:DEFAULT_ANALYSIS_ENTRY_SAMPLE_LIMIT]],
                "rule": "The default route includes only the most material current findings; use a detail route for pages.",
            },
        }

    page_number = max(1, page)
    bounded_page_size = max(1, min(MAX_ANALYSIS_PAGE_SIZE, page_size))
    if selected_detail == "entries":
        start = (page_number - 1) * bounded_page_size
        detail_values = [_entry_brief(entry) for entry in entries[start : start + bounded_page_size]]
        detail_payload = {
            "page": page_number,
            "page_size": bounded_page_size,
            "total_count": len(entries),
            "has_more": start + bounded_page_size < len(entries),
            "items": detail_values,
        }
    elif selected_detail == "segments":
        detail_payload = _paged_detail(values=_segment_summaries(all_entries), page=page_number, page_size=bounded_page_size)
    elif selected_detail == "episodes":
        detail_payload = _paged_detail(values=_episode_summaries(all_entries), page=page_number, page_size=bounded_page_size)
    elif selected_detail == "contexts":
        index_records = index.get("records", {}) if isinstance(index, dict) and isinstance(index.get("records"), dict) else {}
        context_records = index_records.get("contexts", {}) if isinstance(index_records.get("contexts"), dict) else {}
        detail_payload = _paged_detail(
            values=[{"id": identity, **value} for identity, value in context_records.items() if isinstance(value, dict)],
            page=page_number,
            page_size=bounded_page_size,
        )
    else:
        detail_payload = _paged_detail(values=friction_candidates, page=page_number, page_size=bounded_page_size)

    return {
        **common_payload,
        "kind": "agentic-workspace/session-log-analysis-detail/v1",
        "detail_page": detail_payload,
        "full_analysis": {
            "status": "omitted",
            "command": "agentic-workspace session-log analyze --detail summary --format json",
            "rule": "A detail selector returns only its bounded page and compact session counts; broad analysis requires the explicit summary route.",
        },
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
