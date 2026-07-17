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
_CACHE_CONTRACT_VERSION = 3
_MAX_CACHE_RECORDS = 32
_GIT_TIMEOUT_SECONDS = 10
_IGNORED_DEPENDENCY_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
_LOCAL_DECISION_DEPENDENCIES = (
    ".agentic-workspace/local/cache/dogfooding-signal-status.json",
    ".agentic-workspace/local/cache/external-intent-evidence.json",
    ".agentic-workspace/local/cache/pr-comment-delta.json",
    ".agentic-workspace/local/cache/pr-comment-stack.json",
    ".agentic-workspace/local/cache/proof-reuse.json",
)
_OPERATION_DEPENDENCY_ROOTS = {
    "doctor": ("src/agentic_workspace", "generated/workspace", "scripts", "packages"),
    "report": ("src/agentic_workspace", "generated/workspace", "scripts", "packages", "docs"),
    "summary": ("src/agentic_workspace", "generated/workspace", "generated/planning", "scripts", "packages/planning", "docs"),
}


def _files_under(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    files: list[Path] = []
    for current, directories, filenames in os.walk(path):
        directories[:] = sorted(name for name in directories if name not in _IGNORED_DEPENDENCY_DIRS)
        current_path = Path(current)
        files.extend(current_path / filename for filename in sorted(filenames))
    return files


def _dependency_files(root: Path, operation: str) -> list[Path]:
    candidates = [root / "AGENTS.md", root / "pyproject.toml", root / "uv.lock", root / "Makefile"]
    candidates.extend(root.glob("*/AGENTS.md"))
    aw_root = root / ".agentic-workspace"
    if aw_root.is_dir():
        for child in aw_root.iterdir():
            if child.name in {"local", "logs", "projection-cache", "session-logging"}:
                continue
            if child.is_file():
                candidates.append(child)
            else:
                candidates.extend(_files_under(child))
        candidates.extend(root / relative for relative in _LOCAL_DECISION_DEPENDENCIES)
    for relative_root in _OPERATION_DEPENDENCY_ROOTS.get(operation, ()):
        candidates.extend(_files_under(root / relative_root))
    return sorted({path for path in candidates if path.is_file()}, key=lambda path: path.as_posix())


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
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
    dependencies: list[str] = []
    relevant_files = _dependency_files(root, operation)
    relevant_relatives = {path.relative_to(root).as_posix() for path in relevant_files}
    pathspecs = [
        "AGENTS.md",
        "pyproject.toml",
        "uv.lock",
        "Makefile",
        ".agentic-workspace",
        *_OPERATION_DEPENDENCY_ROOTS.get(operation, ()),
    ]
    worktree_lines = [
        line
        for line in _git(root, "status", "--porcelain=v1", "--untracked-files=all", "--", *pathspecs).splitlines()
        if line[3:].replace("\\", "/") in relevant_relatives
    ]
    worktree_state = "\n".join(worktree_lines)
    dirty_relatives = {line[3:].replace("\\", "/") for line in worktree_lines}
    digest.update(worktree_state.encode())
    for path in relevant_files:
        try:
            relative = path.relative_to(root).as_posix()
            stat = path.stat()
        except OSError:
            continue
        dependencies.append(relative)
        digest.update(relative.encode())
        if relative in dirty_relatives:
            try:
                digest.update(hashlib.sha256(path.read_bytes()).digest())
                continue
            except OSError:
                pass
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
    if context.get("volatile") or not (root / ".agentic-workspace").is_dir():
        return
    path = context["path"]
    actionability = payload.get("actionability", {}) if isinstance(payload.get("actionability"), dict) else {}
    next_action = payload.get("next_action", {}) if isinstance(payload.get("next_action"), dict) else {}
    decision_packet = payload.get("decision_packet", {}) if isinstance(payload.get("decision_packet"), dict) else {}
    planning_health = payload.get("planning_surface_health", {}) if isinstance(payload.get("planning_surface_health"), dict) else {}
    execution_readiness = payload.get("execution_readiness", {}) if isinstance(payload.get("execution_readiness"), dict) else {}
    current_pressure = payload.get("current_execution_pressure", {}) if isinstance(payload.get("current_execution_pressure"), dict) else {}
    continuation_view = payload.get("continuation_view", {}) if isinstance(payload.get("continuation_view"), dict) else {}
    proof_state = continuation_view.get("proof_state", {}) if isinstance(continuation_view.get("proof_state"), dict) else {}
    residue_governance = payload.get("residue_governance", {}) if isinstance(payload.get("residue_governance"), dict) else {}
    record = {
        "kind": _CACHE_KIND,
        "contract_version": _CACHE_CONTRACT_VERSION,
        "operation": operation,
        "query": query,
        "dependency_digest": context["digest"],
        "dependencies": context["dependencies"],
        "output_digest": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:20],
        "decision_snapshot": {
            "health": payload.get("health", payload.get("status", planning_health.get("status", ""))),
            "action_required": actionability.get("action_required", payload.get("action_required", bool(payload.get("warning_count", 0)))),
            "actionability_status": actionability.get("status", execution_readiness.get("status", "")),
            "decision": decision_packet.get("next_action", ""),
            "next_action": next_action.get(
                "action",
                next_action.get(
                    "summary",
                    current_pressure.get("recommended_next_action", planning_health.get("recommended_next_action", "")),
                ),
            ),
            "proof": proof_state.get("summary", proof_state.get("status", "")),
            "residue": residue_governance.get("status", ""),
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
