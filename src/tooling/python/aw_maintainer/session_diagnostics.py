"""Read and export existing native diagnostic evidence; never capture or register sessions."""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import json
import os
import re
import shlex
import sys
import time
import uuid
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SESSION_LOG_ROOT = Path(".agentic-workspace") / "local" / "logs"


SESSION_RECORD_KIND = "agentic-workspace/session-logging-record/v1"


SESSION_REGISTRY_PATH = Path(".agentic-workspace") / "local" / "session-logging" / "sessions.json"


SESSION_REGISTRY_LOCK_PATH = Path(".agentic-workspace") / "local" / "session-logging" / ".sessions.lock"


SESSION_LOGICAL_STREAM_ROOT = Path(".agentic-workspace") / "local" / "session-logging" / "logical-sessions"


SESSION_REGISTRY_KIND = "agentic-workspace/session-logging-registry/v1"


LOGICAL_SESSION_IDENTITY_ENV = "AW_SESSION_LOGICAL_IDENTITY"


SESSION_LOG_EVENT_KIND = "agentic-workspace/session-log-event/v1"


SESSION_LOG_EVENT_SCHEMA_VERSION = 1


SESSION_LOG_EVENT_STREAM_NAME = "events.jsonl"


SESSION_LOG_INDEX_KIND = "agentic-workspace/session-log-index/v2"


SESSION_LOG_INDEX_KINDS = {SESSION_LOG_INDEX_KIND, "agentic-workspace/session-log-index/v1"}


DEFAULT_MAX_INLINE_OUTPUT_BYTES = 64 * 1024


DEFAULT_SLOW_COMMAND_DURATION_MS = 120000


LARGE_OUTPUT_SUMMARY_LIMIT = 5


DEFAULT_ANALYSIS_ENTRY_SAMPLE_LIMIT = 2


FRICTION_CANDIDATE_LIMIT = 10


DEFAULT_ANALYSIS_PAGE_SIZE = 25


MAX_ANALYSIS_PAGE_SIZE = 100


DEFAULT_ANALYSIS_SERIALIZATION_BUDGET_BYTES = 64 * 1024


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
    """An explicit diagnostic read target, independent of capture configuration."""

    target_root: Path


def target_from_argv(argv: Sequence[str], *, cwd: Path | None = None) -> Path:
    for index, token in enumerate(argv):
        if token == "--target" and index + 1 < len(argv):
            return Path(argv[index + 1]).expanduser().resolve()
        if token.startswith("--target="):
            return Path(token.split("=", 1)[1]).expanduser().resolve()
    return (cwd or Path.cwd()).resolve()


def load_state_for_argv(argv: Sequence[str], *, cwd: Path | None = None) -> SessionLoggingState:
    return SessionLoggingState(target_root=target_from_argv(argv, cwd=cwd))


def _improvement_signal_fingerprint(*, signal_kind: str, symptom: str, owner_hint: str) -> str:
    def normalize(value: str) -> str:
        text = re.sub(r"https?://\S+", "<url>", value.strip().lower())
        text = re.sub(r"#[0-9]+", "#<issue>", text)
        text = re.sub(r"\b[0-9a-f]{8,}\b", "<identity>", text)
        text = re.sub(r"\b\d+\b", "<n>", text)
        return " ".join(text.split())

    identity = {"kind": signal_kind, "owner": normalize(owner_hint), "symptom": normalize(symptom)}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:20]


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


@contextlib.contextmanager
def _session_registry_lock(*, target_root: Path) -> Iterator[None]:
    native_lock = target_root / SESSION_REGISTRY_PATH.parent / ".native-publication.lock"
    if native_lock.exists():
        raise RuntimeError("native session registry publication requires its current owner; legacy writer preserved it")
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
        if native_lock.exists():
            raise RuntimeError("native session registry publication requires its current owner; legacy writer preserved it")
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


def _event_path_for_session(session: dict[str, str]) -> Path:
    configured = _valid_event_stream_path(str(session.get("event_stream_path", "")))
    return Path(configured) if configured else Path(session["log_path"]).parent / SESSION_LOG_EVENT_STREAM_NAME


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


def _index_path_for_session(session: dict[str, str]) -> Path:
    return Path(session["log_path"]).parent / "index.json"


def _artifact_root_for_session(session: dict[str, str]) -> Path:
    return Path(session["log_path"]).parent / "artifacts"


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
        if any(entry.get("command") == command and entry.get("omissions") for entry in entries):
            candidates.append(
                {
                    "id": "repetition-intent-unknown",
                    "summary": f"Recorded {item['count']} occurrences of {command}; omitted arguments/intent prevent a redundancy judgment.",
                    "owner": "session-log evidence",
                    "confidence": "unknown",
                }
            )
            continue
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
    for index, token in enumerate(tokens):
        if token.replace("\\", "/").endswith("scripts/maintainer/session_diagnostics.py"):
            return tokens[index + 1 : index + 2] == ["analyze"]
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


def _capture_quality(observations: tuple[str, ...]) -> dict[str, Any]:
    allowed = {"identity-unavailable", "capture-failed", "disabled"}
    if len(observations) > 32 or any(value not in allowed for value in observations):
        raise ValueError("capture observations must be bounded portable capture statuses")
    return {
        "known_observations": sorted(set(observations)),
        "provenance": "caller-supplied context, not reconstructed events",
        "whole_task_coverage": "unknown",
        "absence_rule": "No recorded gap does not establish absence of uncaptured host work.",
        "authoritative": False,
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
        "subject": "recorded entries versus derived index; not whole-task capture",
        "whole_task_coverage": "unknown",
        "markdown_command_count": len(markdown_entries),
        "indexed_command_count": len(indexed_entries),
        "missing_entry_ids": [entry_id for entry_id in markdown_ids if entry_id not in indexed_set],
        "extra_entry_ids": [entry_id for entry_id in indexed_ids if entry_id not in markdown_set],
        "repair_available": status in {"missing", "partial", "stale"},
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
        "recovered_from": payload.get("recovery_basis", "legacy-derived-view"),
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
                payload=(
                    {"created_at": session.get("created_at", ""), "recovery_basis": "recorded-stream-session-metadata"}
                    if events
                    else {"created_at": session.get("created_at", ""), "migration": "legacy-session"}
                ),
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
    combined = events + recovered
    return combined, _command_entries_from_events(combined), issues


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
    capture_observations: tuple[str, ...] = (),
) -> dict[str, Any]:
    logical_identity = _logical_session_identity()
    session = _session_for_caller(target_root=state.target_root, logical_identity=logical_identity)
    # Export selects existing evidence. Capture/registration retains its native
    # owner even when logging is enabled for this diagnostic reader.
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
    source_command_ids: set[tuple[str, str]] = set()
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
        source_command_ids.update((event_stream_path, str(entry.get("id", ""))) for entry in entries)
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
        "capture_quality": _capture_quality(capture_observations),
        "gaps": [event.get("payload", {}) for event in gap_events],
        "source_stream_issues": source_issues,
        "time_coverage": {"started_at": min(timestamps) if timestamps else "", "finished_at": max(timestamps) if timestamps else ""},
        "evidence_profile": {
            "id": "recorded-stream-with-output-chunks" if include_artifacts else "recorded-stream-summary",
            "subject": "known recorded streams only; uncaptured host work cannot be inferred",
            "whole_task_coverage": "unknown",
            "command_selection": "recorded-logical-session-tree-commands"
            if not explicit_selection
            else "recorded-physical-session-commands",
            "detail_policy": "include-available-artifact-output-chunks" if include_artifacts else "omit-artifact-bytes-retain-digests",
            "source_command_count": len(source_command_ids),
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
    capture_observations: tuple[str, ...] = (),
) -> dict[str, Any]:
    session = _session_for_caller(target_root=state.target_root, logical_identity=_logical_session_identity())
    log_path = _analysis_log_path(state=state, path=path, session_id=session_id, session=session)
    if log_path is None:
        if not path and not session_id and not _logical_session_identity():
            return _identity_required_payload(kind="agentic-workspace/session-log-analysis/v1")
        return {
            "kind": "agentic-workspace/session-log-analysis/v1",
            "status": "missing-log",
            "path": "",
            "index_status": "missing",
            "rule": "Pass --path or --id for an existing captured session to the source-maintenance diagnostic reader.",
        }

    # Routes are source-checkout diagnostics and retain the selected log even
    # when the caller used an explicit path or a different repository target.
    diagnostic = "uv run --frozen --active --no-sync python scripts/maintainer/session_diagnostics.py"
    selection = f"--target {shlex.quote(str(state.target_root))} --path {shlex.quote(log_path.relative_to(state.target_root).as_posix())}"
    analyze_route = f"{diagnostic} analyze {selection}"
    export_route = f"{diagnostic} export {selection}"

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
            "detail_route": (f"{analyze_route} --origin {partition} --detail entries --page 1 --page-size 25 --format json"),
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
        "detail_route": (f"{analyze_route} --origin {origin_scope} --detail entries --page 1 --page-size 25 --format json"),
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
        "download_or_share": f"{export_route} --format json",
        "artifact_class": "normalized-share-safe",
        "raw_local_route": "Keep the source session directory local; it is not the share artifact.",
        "authority": "The source-maintenance session_diagnostics.py export operation produces the normalized share artifact; it does not transfer it.",
        "transfer_approval": "not-granted",
        "review_required": "Review the normalized archive for secrets and external-transfer policy before sharing.",
    }
    common_payload = {
        "kind": "agentic-workspace/session-log-analysis/v1",
        "status": "analyzed",
        "path": log_path.relative_to(state.target_root).as_posix(),
        "index_status": coverage["status"],
        "index_presence": "present" if index is not None else "markdown-fallback",
        "chronology_source": "canonical-event-stream" if canonical_entries else "legacy-derived-view",
        "event_stream_path": _event_path_for_session(effective_session).as_posix(),
        "event_stream_issues": event_issues,
        "session_scope": session_scope,
        "coverage": coverage,
        "capture_quality": _capture_quality(capture_observations),
        "recorded_stream_integrity": {
            "subject": "known canonical stream only",
            "status": "incomplete"
            if event_issues or any(e.get("event_type") == "logging.gap" for e in canonical_events)
            else "complete"
            if canonical_events
            else "unavailable",
            "whole_task_coverage": "unknown",
        },
        "index_path": str(index.get("path", "")) if isinstance(index, dict) else "",
        "summary": summary_payload,
        "analysis_scope": analysis_scope,
        "origin_breakdown": dict(sorted(origin_breakdown.items())),
        "origin_partitions": origin_partitions,
        "analyzer_overhead": {
            "command_count": len(analyzer_overhead),
            "detail_route": f"{analyze_route} --origin {origin_scope} --detail entries --format json",
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
            "command": f"{analyze_route} --origin {origin_scope} --detail summary --format json",
            "rule": "A detail selector returns only its bounded page and compact session counts; broad analysis requires the explicit summary route.",
        },
    }


def serialise_value(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if is_dataclass(value) and (not isinstance(value, type)):
        return serialise_value(asdict(value))
    if isinstance(value, dict):
        return {key: serialise_value(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialise_value(item) for item in value]
    return value
