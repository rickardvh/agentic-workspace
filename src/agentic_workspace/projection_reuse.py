"""Dependency-aware reuse for unchanged AW command projections."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

_CACHE_KIND = "agentic-workspace/projection-reuse-record/v1"
_CACHE_CONTRACT_VERSION = 2
_MAX_CACHE_RECORDS = 32
_OPERATION_DEPENDENCY_ROOTS = {
    "doctor": ("src/agentic_workspace", "generated/workspace", "scripts", "packages"),
    "report": ("src/agentic_workspace", "generated/workspace", "scripts", "packages", "docs"),
}


def _dependency_files(root: Path, operation: str) -> list[Path]:
    candidates = [root / "AGENTS.md", root / "pyproject.toml", root / "uv.lock", root / "Makefile"]
    candidates.extend(root.glob("*/AGENTS.md"))
    aw_root = root / ".agentic-workspace"
    if aw_root.is_dir():
        candidates.extend(
            path
            for path in aw_root.rglob("*")
            if path.is_file() and not {"projection-cache", "logs", "session-logging"}.intersection(path.relative_to(aw_root).parts)
        )
    for relative_root in _OPERATION_DEPENDENCY_ROOTS.get(operation, ()):
        folder = root / relative_root
        if folder.is_dir():
            candidates.extend(path for path in folder.rglob("*") if path.is_file())
    return sorted({path for path in candidates if path.is_file()}, key=lambda path: path.as_posix())


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def dependency_digest(*, root: Path, operation: str, query: dict[str, Any]) -> tuple[str, list[str]]:
    root = root.resolve()
    digest = hashlib.sha256()
    digest.update(operation.encode())
    digest.update(json.dumps(query, sort_keys=True, ensure_ascii=True).encode())
    digest.update(str(_CACHE_CONTRACT_VERSION).encode())
    try:
        package_version = version("agentic-workspace")
    except PackageNotFoundError:
        package_version = "source-checkout"
    digest.update(package_version.encode())
    resolved_head = _git(root, "rev-parse", "HEAD")
    digest.update(resolved_head.encode())
    dependencies: list[str] = []
    relevant_files = _dependency_files(root, operation)
    relevant_relatives = {path.relative_to(root).as_posix() for path in relevant_files}
    worktree_state = "\n".join(
        line
        for line in _git(root, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
        if line[3:].replace("\\", "/") in relevant_relatives
    )
    digest.update(worktree_state.encode())
    for path in relevant_files:
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
    volatile = (
        operation not in _OPERATION_DEPENDENCY_ROOTS
        or bool(query.get("volatile") or query.get("external_freshness_required"))
        or os.environ.get("AW_PROJECTION_VOLATILE", "").lower() in {"1", "true", "yes"}
    )
    context = {
        "digest": digest,
        "dependencies": dependencies,
        "path": path,
        "forced": forced,
        "volatile": volatile,
        "dependency_contract": operation,
    }
    if forced or volatile or not path.is_file():
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
    if context.get("volatile"):
        return
    path = context["path"]
    actionability = payload.get("actionability", {}) if isinstance(payload.get("actionability"), dict) else {}
    next_action = payload.get("next_action", {}) if isinstance(payload.get("next_action"), dict) else {}
    record = {
        "kind": _CACHE_KIND,
        "contract_version": _CACHE_CONTRACT_VERSION,
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
        records = sorted(path.parent.glob("*.json"), key=lambda item: item.stat().st_mtime_ns, reverse=True)
        for stale in records[_MAX_CACHE_RECORDS:]:
            stale.unlink(missing_ok=True)
    except OSError:
        return
