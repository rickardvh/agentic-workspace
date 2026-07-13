"""Authoritative advisory binding for the actor's current repository work."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tomllib
from collections.abc import Iterable
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


def _selected_thread_id(root: Path) -> str:
    path = root / ".agentic-workspace" / "local" / "work-threads" / "index.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return ""
    return str(payload.get("selected_thread_id") or "").strip() if isinstance(payload, dict) else ""


def _ordered_refs(values: Iterable[Any]) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        match = re.search(r"#?(\d+)\b", text)
        ref = f"#{match.group(1)}" if match else text
        if ref in seen:
            continue
        seen.add(ref)
        refs.append(ref)
    return refs


def _task_pr_refs(task: str) -> list[str]:
    return _ordered_refs(match.group(1) for match in re.finditer(r"\b(?:PR|pull request)\s*#?(\d+)", task, flags=re.IGNORECASE))


def _task_issue_refs(task: str) -> list[str]:
    task_without_pr_refs = re.sub(r"\b(?:PR|pull request)\s*#?\d+", "", task, flags=re.IGNORECASE)
    return _ordered_refs(match.group(1) for match in re.finditer(r"#(\d+)", task_without_pr_refs))


def resolve_current_work_context(*, root: Path, task: str = "", argv: Sequence[str] = (), explicit_pr: str = "") -> dict[str, Any]:
    """Resolve one binding; prefer unknown over carrying metadata across transitions."""

    root = root.resolve()
    branch = _git(root, "branch", "--show-current")
    head = _git(root, "rev-parse", "HEAD")
    plan_id, plan_source = _active_plan(root)
    threads = _thread_candidates(root, branch)
    selected_thread_id = _selected_thread_id(root)
    selected_threads = [candidate for candidate in threads if str(candidate.get("id") or "").strip() == selected_thread_id]
    thread = selected_threads[0] if selected_threads else threads[0] if len(threads) == 1 else {}
    refs = thread.get("refs", {}) if isinstance(thread, dict) else {}
    issue_refs = _ordered_refs(refs.get("issues", [])) if isinstance(refs, dict) else []
    pr_refs = _ordered_refs(refs.get("prs", [])) if isinstance(refs, dict) else []
    task_pr_refs = _task_pr_refs(task)
    task_refs = _task_issue_refs(task)
    plan_refs = sorted({f"#{value}" for value in re.findall(r"(?:^|\D)(\d{3,})(?:\D|$)", plan_id)})
    conflicts: list[str] = []
    thread_status = str(thread.get("status") or "").strip().lower() if thread else ""
    stale_thread = bool(thread) and thread_status in {"stale", "closed", "completed", "superseded"}
    if stale_thread:
        conflicts.append("thread-stale")
    if task_refs and issue_refs and set(task_refs).isdisjoint(issue_refs):
        conflicts.append("task-thread-issue-conflict")
    if task_refs and plan_refs and set(task_refs).isdisjoint(plan_refs):
        conflicts.append("task-plan-conflict")
    if plan_refs and issue_refs and set(plan_refs).isdisjoint(issue_refs):
        conflicts.append("plan-thread-conflict")
    thread_compatible = bool(thread) and not conflicts
    if task_refs:
        issue_refs = task_refs
    elif not thread_compatible:
        issue_refs = []
    explicit_pr_refs = _ordered_refs([explicit_pr]) if explicit_pr else []
    if explicit_pr_refs:
        effective_pr_refs = explicit_pr_refs
        pr_ref_provenance = "explicit-environment"
    elif task_pr_refs:
        effective_pr_refs = task_pr_refs
        pr_ref_provenance = "explicit-task"
    elif thread_compatible:
        effective_pr_refs = pr_refs
        pr_ref_provenance = "branch-matched-local-thread" if pr_refs else "unknown"
    else:
        effective_pr_refs = []
        pr_ref_provenance = "unknown"
    pr_ref = effective_pr_refs[0] if effective_pr_refs else ""
    ambiguous = (len(threads) > 1 and not selected_threads) or bool(conflicts)
    identity = {
        "root": root.as_posix(),
        "branch": branch,
        "task": task,
        "plan_id": plan_id,
        "issue_refs": issue_refs,
        "pr_refs": effective_pr_refs,
        "thread_id": str(thread.get("id") or "") if thread_compatible else "",
    }
    return {
        "kind": "agentic-workspace/current-work-context/v1",
        "id": hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16],
        "status": "ambiguous" if ambiguous else "bound" if branch or plan_id or task else "unknown",
        "actor_scope": "current-process-session-worktree",
        "worktree": ".",
        "branch": branch,
        "head": head,
        "revision": {
            "head": head,
            "source": "live-git",
            "rule": "Revision changes do not by themselves create a new conceptual current-work identity.",
        },
        "task": task,
        "plan_id": plan_id,
        "issue_refs": issue_refs,
        "pr_refs": [] if ambiguous and not effective_pr_refs else effective_pr_refs,
        "pr_ref": "" if ambiguous and not effective_pr_refs else pr_ref,
        "thread_id": str(thread.get("id") or "") if thread_compatible else "",
        "selected_thread_id": selected_thread_id,
        "conflicts": conflicts,
        "provenance": {
            "worktree_branch_head": "live-git",
            "task": "explicit-command" if task else "unknown",
            "plan_id": plan_source or "unknown",
            "issue_refs": "explicit-task" if task_refs else "branch-matched-local-thread" if issue_refs else "unknown",
            "pr_ref": pr_ref_provenance,
            "pr_refs": pr_ref_provenance,
        },
        "freshness": {
            "resolved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "binding_conditions": ["worktree", "branch", "task", "active-plan", "selected-thread"],
            "invalidate_when": [
                "worktree changes",
                "branch changes",
                "task changes",
                "active Planning changes",
                "thread selection changes",
            ],
            "revision_changes": ["HEAD changes"],
        },
        "authority": "local-advisory-binding",
        "durable_authority": ["Planning", "issues and PRs", "proof receipts", "Memory and repository docs"],
        "safe_probe": "agentic-workspace start --target . --select work_threads --format json" if ambiguous else "",
        "rule": "Consumers must resolve this binding at use time and must not carry confident issue, PR, task, or plan metadata across invalidating transitions.",
    }
