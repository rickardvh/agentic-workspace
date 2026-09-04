from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

SESSION_LOG_ENV = "AW_SESSION_LOG"
SESSION_LOG_GAP_ENV = "AW_SESSION_LOG_GAP"
SESSION_LOG_PARENT_ENV = "AW_SESSION_LOG_PARENT_EVENT"
SESSION_LOG_CORRELATION_ENV = "AW_SESSION_LOG_CORRELATION"
SESSION_LOG_ROOT = Path(".agentic-workspace") / "local" / "logs"
MAX_CAPTURE_BYTES = 32_768
LARGE_OUTPUT_BYTES = 16_384
SLOW_COMMAND_SECONDS = 1.0
_SESSION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def _digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _session_id(value: str) -> str:
    candidate = value.strip()
    if not _SESSION_ID.fullmatch(candidate):
        raise ValueError("session ID must be 1-64 characters containing only letters, digits, '.', '_', or '-'")
    return candidate


def enabled_session_id() -> str | None:
    value = os.environ.get(SESSION_LOG_ENV, "").strip()
    return _session_id(value) if value else None


def session_log_path(target: str | Path, session_id: str) -> Path:
    return Path(target).resolve() / SESSION_LOG_ROOT / f"aw-session-{_session_id(session_id)}.jsonl"


def _append(path: Path, event: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(dict(event), sort_keys=True, separators=(",", ":")) + "\n")


def append_gap(*, target: str | Path, session_id: str, reason: str) -> Path:
    if not reason.strip():
        raise ValueError("gap reason must not be empty")
    path = session_log_path(target, session_id)
    _append(
        path,
        {
            "kind": "agentic-workspace/maintainer-session-event/v1",
            "event_type": "capture.gap",
            "event_id": f"event-{uuid4().hex}",
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": _session_id(session_id),
            "reason": reason.strip()[:512],
            "coverage": "explicit-gap",
        },
    )
    return path


def append_session_event(
    *,
    target: str | Path,
    argv: Sequence[str],
    command: str,
    payload: Mapping[str, Any],
    exit_code: int,
    started_at: str,
    duration_seconds: float,
) -> Path | None:
    session_id = enabled_session_id()
    if session_id is None:
        return None
    path = session_log_path(target, session_id)
    gap_reason = os.environ.get(SESSION_LOG_GAP_ENV, "").strip()
    if gap_reason:
        append_gap(target=target, session_id=session_id, reason=gap_reason)
    encoded_payload = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    encoded_argv = json.dumps(list(argv), separators=(",", ":")).encode("utf-8")
    output = {
        "bytes": len(encoded_payload),
        "sha256": _digest(encoded_payload),
        "captured": len(encoded_payload) <= MAX_CAPTURE_BYTES,
        "large": len(encoded_payload) >= LARGE_OUTPUT_BYTES,
        "kind": str(payload.get("kind") or ""),
        "status": str(payload.get("status") or ""),
        "operation_id": str(payload.get("operation_id") or ""),
    }
    event = {
        "kind": "agentic-workspace/maintainer-session-event/v1",
        "event_type": "command.completed",
        "event_id": f"event-{uuid4().hex}",
        "timestamp": datetime.now(UTC).isoformat(),
        "started_at": started_at,
        "duration_seconds": round(max(duration_seconds, 0.0), 6),
        "session_id": session_id,
        "command": command,
        "invocation_id": _digest(encoded_argv),
        "argv": list(argv),
        "exit_code": exit_code,
        "outcome": "success" if exit_code == 0 else "failure",
        "output": output,
        "payload": dict(payload) if output["captured"] else None,
        "parent_event_id": os.environ.get(SESSION_LOG_PARENT_ENV, "").strip(),
        "correlation_id": os.environ.get(SESSION_LOG_CORRELATION_ENV, "").strip(),
        "coverage": "observed-events-only",
        "authority": "local-diagnostic-only",
    }
    _append(path, event)
    return path


def _events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ValueError(f"session log does not exist: {path}")
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid session event at line {line_number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"session event at line {line_number} must be an object")
        events.append(value)
    return events


def analyze_session(*, target: str | Path, session_id: str) -> dict[str, Any]:
    path = session_log_path(target, session_id)
    events = _events(path)
    commands = [event for event in events if event.get("event_type") == "command.completed"]
    invocation_counts = Counter(str(event.get("invocation_id") or "") for event in commands)
    result_counts = Counter(str(event.get("output", {}).get("sha256") or "") for event in commands)
    return {
        "kind": "agentic-workspace/maintainer-session-analysis/v1",
        "session_id": _session_id(session_id),
        "coverage": "partial" if any(event.get("event_type") == "capture.gap" for event in events) else "observed-only",
        "event_count": len(events),
        "command_count": len(commands),
        "failure_count": sum(event.get("outcome") == "failure" for event in commands),
        "gap_count": sum(event.get("event_type") == "capture.gap" for event in events),
        "repeated_invocations": sorted(key for key, count in invocation_counts.items() if key and count > 1),
        "repeated_results": sorted(key for key, count in result_counts.items() if key and count > 1),
        "slow_event_ids": [
            str(event.get("event_id"))
            for event in commands
            if float(event.get("duration_seconds") or 0) >= SLOW_COMMAND_SECONDS
        ],
        "large_output_event_ids": [
            str(event.get("event_id")) for event in commands if bool(event.get("output", {}).get("large"))
        ],
        "authority": "local-diagnostic-only",
    }


def _normalize(value: Any, *, target: Path) -> Any:
    if isinstance(value, str):
        normalized = value
        for source, replacement in (
            (str(target), "<target>"),
            (target.as_posix(), "<target>"),
            (str(Path.home()), "<home>"),
            (Path.home().as_posix(), "<home>"),
        ):
            normalized = normalized.replace(source, replacement)
        return normalized
    if isinstance(value, list):
        return [_normalize(item, target=target) for item in value]
    if isinstance(value, dict):
        return {key: _normalize(item, target=target) for key, item in value.items()}
    return value


def export_session(*, target: str | Path, session_id: str, destination: str | Path | None = None) -> Path:
    root = Path(target).resolve()
    events = _events(session_log_path(root, session_id))
    destination_path = (
        Path(destination).resolve()
        if destination is not None
        else root / SESSION_LOG_ROOT / "exports" / f"aw-session-{_session_id(session_id)}-share-safe.jsonl.gz"
    )
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "kind": "agentic-workspace/maintainer-session-export/v1",
        "session_id": _session_id(session_id),
        "created_at": datetime.now(UTC).isoformat(),
        "coverage": "partial" if any(event.get("event_type") == "capture.gap" for event in events) else "observed-only",
        "source_event_count": len(events),
        "omissions": ["raw argv", "raw result payload"],
        "normalization": ["target path", "user home path"],
        "authority": "share-safe-diagnostic-only",
    }
    with destination_path.open("wb") as raw_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as handle:
            handle.write((json.dumps(manifest, sort_keys=True) + "\n").encode())
            for event in events:
                shared = {key: value for key, value in event.items() if key not in {"argv", "payload"}}
                handle.write((json.dumps(_normalize(shared, target=root), sort_keys=True) + "\n").encode())
    return destination_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Maintainer-only local AW session diagnostics.")
    parser.add_argument("command", choices=("path", "analyze", "export", "gap"))
    parser.add_argument("--target", default=".")
    parser.add_argument("--session", required=True)
    parser.add_argument("--destination")
    parser.add_argument("--reason")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "path":
        result: Any = {"path": str(session_log_path(args.target, args.session))}
    elif args.command == "analyze":
        result = analyze_session(target=args.target, session_id=args.session)
    elif args.command == "export":
        result = {
            "path": str(export_session(target=args.target, session_id=args.session, destination=args.destination))
        }
    else:
        result = {"path": str(append_gap(target=args.target, session_id=args.session, reason=args.reason or ""))}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
