"""Shared improvement-pressure consequence lifecycle helpers."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IMPROVEMENT_CONSEQUENCE_HISTORY_RELATIVE_PATH = Path(".agentic-workspace") / "local" / "improvement-pressure" / "consequence-history.jsonl"


class ConsequenceStoreUnavailable(RuntimeError):
    """Raised when the consequence lifecycle store cannot be safely read or written."""


def _lock_path(target_root: Path) -> Path:
    return target_root / IMPROVEMENT_CONSEQUENCE_HISTORY_RELATIVE_PATH.parent / "consequence-history.lock"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ConsequenceStoreUnavailable(f"consequence store is unreadable: {path}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ConsequenceStoreUnavailable(f"consequence store is corrupt at line {line_number}: {path}") from exc
        if not isinstance(value, dict):
            raise ConsequenceStoreUnavailable(f"consequence store record is not an object at line {line_number}: {path}")
        records.append(value)
    return records


def read_consequence_history(*, target_root: Path | None, allow_locked: bool = False) -> list[dict[str, Any]]:
    if target_root is None:
        return []
    lock_path = _lock_path(target_root)
    if lock_path.exists() and not allow_locked:
        raise ConsequenceStoreUnavailable(
            "consequence store write is in progress; lifecycle readers must fail closed until the writer exits."
        )
    path = target_root / IMPROVEMENT_CONSEQUENCE_HISTORY_RELATIVE_PATH
    if not path.is_file():
        return []
    return _read_jsonl(path)


def append_consequence_record(*, target_root: Path, record: dict[str, Any]) -> None:
    path = target_root / IMPROVEMENT_CONSEQUENCE_HISTORY_RELATIVE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")


def record_consequence_event(*, target_root: Path | None, event: dict[str, Any]) -> dict[str, Any]:
    normalized_event = {
        "owner_kind": "workspace-improvement-pressure/v1",
        "source": str(event.get("source") or "unknown"),
        **event,
    }
    fingerprint = hashlib.sha256(json.dumps(normalized_event, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
    record = {
        "kind": "workspace-improvement-pressure-consequence-event/v1",
        "fingerprint": fingerprint,
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        **normalized_event,
    }
    if target_root is not None:
        lock_path = _lock_path(target_root)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise ConsequenceStoreUnavailable(
                "consequence store write is already in progress; retry after the active writer exits."
            ) from exc
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(json.dumps({"pid": os.getpid(), "recorded_at": record["recorded_at"]}, sort_keys=True))
            existing = {str(item.get("fingerprint") or "") for item in read_consequence_history(target_root=target_root, allow_locked=True)}
            if fingerprint not in existing:
                append_consequence_record(target_root=target_root, record=record)
        finally:
            try:
                lock_path.unlink()
            except OSError:
                pass
    return record


def consequence_summary(*, target_root: Path | None, active_finding_ids: set[str]) -> dict[str, Any]:
    try:
        records = read_consequence_history(target_root=target_root)
    except ConsequenceStoreUnavailable as exc:
        return {
            "kind": "workspace-improvement-pressure-consequence-store/v1",
            "status": "blocked-store-unavailable",
            "owner_kind": "workspace-improvement-pressure/v1",
            "source": "shared-improvement-consequence-owner",
            "path": IMPROVEMENT_CONSEQUENCE_HISTORY_RELATIVE_PATH.as_posix(),
            "record_count": 0,
            "open_finding_ids": ["consequence-store-unavailable"],
            "open_finding_count": 1,
            "disposed_finding_ids": [],
            "fail_closed": True,
            "reason": str(exc),
            "rule": "Unreadable, corrupt, or concurrently locked consequence state is a blocking lifecycle condition, not a quiet empty store.",
        }
    open_ids: set[str] = set()
    disposed_ids: set[str] = set()
    for record in records:
        finding_id = str(record.get("finding_id") or "")
        if not finding_id:
            continue
        event = str(record.get("event") or "")
        if event in {"disposed", "retired"}:
            disposed_ids.add(finding_id)
            open_ids.discard(finding_id)
        elif event == "observed":
            disposed_ids.discard(finding_id)
            open_ids.add(finding_id)
    open_ids.update(active_finding_ids - disposed_ids)
    return {
        "kind": "workspace-improvement-pressure-consequence-store/v1",
        "status": "attention" if open_ids else "quiet",
        "owner_kind": "workspace-improvement-pressure/v1",
        "source": "shared-improvement-consequence-owner",
        "path": IMPROVEMENT_CONSEQUENCE_HISTORY_RELATIVE_PATH.as_posix(),
        "record_count": len(records),
        "open_finding_ids": sorted(open_ids),
        "open_finding_count": len(open_ids),
        "disposed_finding_ids": sorted(disposed_ids - open_ids),
        "rule": "Consequence observations and dispositions are persisted through the shared improvement-pressure owner and rehydrated by all consumers.",
    }
