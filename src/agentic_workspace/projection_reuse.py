"""Dependency-aware reuse for unchanged AW command projections."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

_CACHE_KIND = "agentic-workspace/projection-reuse-record/v1"


def _dependency_files(root: Path) -> list[Path]:
    candidates = [root / "AGENTS.md", root / "pyproject.toml", root / "Makefile", root / ".git" / "HEAD"]
    aw_root = root / ".agentic-workspace"
    if aw_root.is_dir():
        candidates.extend(
            path
            for path in aw_root.rglob("*")
            if path.is_file() and not {"projection-cache", "logs", "session-logging"}.intersection(path.relative_to(aw_root).parts)
        )
    return sorted({path for path in candidates if path.is_file()}, key=lambda path: path.as_posix())


def dependency_digest(*, root: Path, operation: str, query: dict[str, Any]) -> tuple[str, list[str]]:
    root = root.resolve()
    digest = hashlib.sha256()
    digest.update(operation.encode())
    digest.update(json.dumps(query, sort_keys=True, ensure_ascii=True).encode())
    dependencies: list[str] = []
    for path in _dependency_files(root):
        try:
            relative = path.relative_to(root).as_posix()
            stat = path.stat()
        except OSError:
            continue
        dependencies.append(relative)
        digest.update(relative.encode())
        try:
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        except OSError:
            digest.update(str(stat.st_size).encode())
            digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()[:20], dependencies


def _cache_path(root: Path, operation: str, query: dict[str, Any]) -> Path:
    key = hashlib.sha256(json.dumps({"operation": operation, "query": query}, sort_keys=True).encode()).hexdigest()[:16]
    return root / ".agentic-workspace" / "local" / "projection-cache" / f"{operation}-{key}.json"


def lookup_projection_reuse(
    *, root: Path, operation: str, query: dict[str, Any], full_detail_command: str, force_refresh: bool = False
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    digest, dependencies = dependency_digest(root=root, operation=operation, query=query)
    path = _cache_path(root, operation, query)
    forced = force_refresh or os.environ.get("AW_PROJECTION_FORCE_REFRESH", "").lower() in {"1", "true", "yes"}
    context = {"digest": digest, "dependencies": dependencies, "path": path, "forced": forced}
    if forced or not path.is_file():
        return None, context
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, context
    if record.get("kind") != _CACHE_KIND or record.get("dependency_digest") != digest:
        return None, context
    prior = record.get("decision_snapshot", {}) if isinstance(record.get("decision_snapshot"), dict) else {}
    return {
        "kind": "agentic-workspace/unchanged-projection/v1",
        "status": "unchanged",
        "operation": operation,
        "dependency_digest": digest,
        "query": query,
        "actionability_delta": "unchanged",
        "decision_delta": "unchanged",
        "proof_delta": "unchanged",
        "residue_delta": "unchanged",
        "next_action_delta": "unchanged",
        "prior_decision": prior,
        "work_avoided": {
            "full_projection_builder_skipped": True,
            "serialization_of_full_projection_skipped": True,
            "dependency_count": len(dependencies),
        },
        "full_detail": {"command": full_detail_command, "force_recompute": True},
        "refresh": {
            "command": full_detail_command,
            "environment_override": "AW_PROJECTION_FORCE_REFRESH=1",
            "rule": "Verbose detail or the explicit environment override forces recomputation when external freshness is required.",
        },
        "rule": "Reuse is valid only while declared dependencies and the normalized query are unchanged.",
    }, context


def record_projection_reuse(*, root: Path, operation: str, query: dict[str, Any], context: dict[str, Any], payload: dict[str, Any]) -> None:
    path = context["path"]
    actionability = payload.get("actionability", {}) if isinstance(payload.get("actionability"), dict) else {}
    next_action = payload.get("next_action", {}) if isinstance(payload.get("next_action"), dict) else {}
    record = {
        "kind": _CACHE_KIND,
        "operation": operation,
        "query": query,
        "dependency_digest": context["digest"],
        "dependencies": context["dependencies"],
        "output_digest": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:20],
        "decision_snapshot": {
            "health": payload.get("health", payload.get("status", "")),
            "action_required": actionability.get("action_required", payload.get("action_required", False)),
            "actionability_status": actionability.get("status", ""),
            "next_action": next_action.get("action", next_action.get("summary", "")),
        },
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    except OSError:
        return
