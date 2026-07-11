"""Authoritative advisory binding for the actor's current repository work."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=2, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _active_plan(root: Path) -> tuple[str, str]:
    path = root / ".agentic-workspace" / "planning" / "state.toml"
    try:
        state = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, tomllib.TOMLDecodeError):
        return "", ""
    items = state.get("todo", {}).get("active_items", []) if isinstance(state.get("todo"), dict) else []
    if not items or not isinstance(items[0], dict):
        return "", ""
    return str(items[0].get("id") or ""), path.relative_to(root).as_posix()


def _thread_candidates(root: Path, branch: str) -> list[dict[str, Any]]:
    folder = root / ".agentic-workspace" / "local" / "work-threads"
    candidates: list[dict[str, Any]] = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        if path.name == "index.json":
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        observations = record.get("observations", {}) if isinstance(record, dict) else {}
        observed_branch = observations.get("branch", {}) if isinstance(observations, dict) else {}
        observed_branch = observed_branch.get("value", "") if isinstance(observed_branch, dict) else observed_branch
        if str(observed_branch or "") == branch:
            candidates.append(record)
    return candidates


def resolve_current_work_context(*, root: Path, task: str = "", argv: Sequence[str] = (), explicit_pr: str = "") -> dict[str, Any]:
    """Resolve one binding; prefer unknown over carrying metadata across transitions."""

    root = root.resolve()
    branch = _git(root, "branch", "--show-current")
    head = _git(root, "rev-parse", "HEAD")
    plan_id, plan_source = _active_plan(root)
    threads = _thread_candidates(root, branch)
    thread = threads[0] if len(threads) == 1 else {}
    refs = thread.get("refs", {}) if isinstance(thread, dict) else {}
    issue_refs = [str(value) for value in refs.get("issues", [])] if isinstance(refs, dict) else []
    pr_refs = [str(value) for value in refs.get("prs", [])] if isinstance(refs, dict) else []
    task_refs = sorted({f"#{value}" for value in re.findall(r"#(\d+)", task)})
    if task_refs:
        issue_refs = task_refs
    declared_pr = str(explicit_pr or "").strip().lstrip("#")
    pr_ref = f"#{declared_pr}" if declared_pr else pr_refs[0] if len(pr_refs) == 1 else ""
    ambiguous = len(threads) > 1
    identity = {"root": root.as_posix(), "branch": branch, "head": head, "task": task, "plan_id": plan_id, "pr_ref": pr_ref}
    return {
        "kind": "agentic-workspace/current-work-context/v1",
        "id": hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16],
        "status": "ambiguous" if ambiguous else "bound" if branch or plan_id or task else "unknown",
        "actor_scope": "current-process-session-worktree",
        "worktree": ".",
        "branch": branch,
        "head": head,
        "task": task,
        "plan_id": plan_id,
        "issue_refs": issue_refs,
        "pr_ref": "" if ambiguous else pr_ref,
        "thread_id": str(thread.get("id") or "") if not ambiguous else "",
        "provenance": {
            "worktree_branch_head": "live-git",
            "task": "explicit-command" if task else "unknown",
            "plan_id": plan_source or "unknown",
            "issue_refs": "explicit-task" if task_refs else "branch-matched-local-thread" if issue_refs else "unknown",
            "pr_ref": "explicit-environment" if declared_pr else "branch-matched-local-thread" if pr_ref else "unknown",
        },
        "freshness": {
            "resolved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "binding_conditions": ["worktree", "branch", "head", "task", "active-plan", "selected-thread"],
            "invalidate_when": [
                "worktree changes",
                "branch changes",
                "HEAD changes",
                "task changes",
                "active Planning changes",
                "thread selection changes",
            ],
        },
        "authority": "local-advisory-binding",
        "durable_authority": ["Planning", "issues and PRs", "proof receipts", "Memory and repository docs"],
        "safe_probe": "agentic-workspace start --target . --select work_threads --format json" if ambiguous else "",
        "rule": "Consumers must resolve this binding at use time and must not carry confident issue, PR, task, or plan metadata across invalidating transitions.",
    }
