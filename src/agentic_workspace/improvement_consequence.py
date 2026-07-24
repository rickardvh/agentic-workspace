"""Shared improvement-pressure consequence lifecycle helpers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

IMPROVEMENT_CONSEQUENCE_HISTORY_RELATIVE_PATH = Path(".agentic-workspace") / "local" / "improvement-pressure" / "consequence-history.jsonl"


def read_consequence_history(*, target_root: Path | None) -> list[dict[str, Any]]:
    if target_root is None:
        return []
    path = target_root / IMPROVEMENT_CONSEQUENCE_HISTORY_RELATIVE_PATH
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                records.append(value)
    except (OSError, json.JSONDecodeError):
        return records
    return records


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
        existing = {str(item.get("fingerprint") or "") for item in read_consequence_history(target_root=target_root)}
        if fingerprint not in existing:
            append_consequence_record(target_root=target_root, record=record)
    return record


def consequence_summary(*, target_root: Path | None, active_finding_ids: set[str]) -> dict[str, Any]:
    records = read_consequence_history(target_root=target_root)
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
