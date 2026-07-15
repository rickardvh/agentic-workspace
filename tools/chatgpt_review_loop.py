from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence, TextIO

OPT_IN_MARKER = "<!-- aw-chatgpt-review:enabled -->"
REVIEW_POLICY = "pr-review-recheck-v1"
HEAD_SYNC_ATTEMPTS = 3
STATE_KIND = "agentic-workspace/chatgpt-review-loop-state/v1"
STATE_RELATIVE = Path(".agentic-workspace/local/chatgpt-review-loop")
OWNER_ROOT_ENV = "AW_CHATGPT_REVIEW_OWNER_ROOT"
OWNER_BRANCH_ENV = "AW_CHATGPT_REVIEW_OWNER_BRANCH"
DISPATCH_STATE = "dispatch.json"
REVIEW_MARKER_RE = re.compile(
    r"<!-- aw-chatgpt-review pr=(?P<pr>[1-9][0-9]*) "
    r"head=(?P<head>[0-9a-f]{40}) policy=pr-review-recheck-v1 "
    r"decision=(?P<decision>blocked|merge-ready) -->"
)
_LOG_STREAM: TextIO | None = None


class LoopError(RuntimeError):
    def __init__(self, code: str, message: str, *, recovery: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.recovery = recovery


@dataclass(frozen=True)
class Review:
    comment_id: str
    pr: int
    head: str
    decision: str
    findings: str
    url: str

    @property
    def key(self) -> str:
        return f"{self.pr}:{self.head}:{self.comment_id}"


class CommandRunner:
    def run(self, command: Sequence[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            _resolved_command(command),
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )

    def json(self, command: Sequence[str], *, cwd: Path) -> Any:
        completed = self.run(command, cwd=cwd)
        if completed.returncode:
            detail = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
            raise LoopError("command-failed", f"{' '.join(command)} failed: {detail}")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise LoopError("invalid-command-json", f"{' '.join(command)} returned invalid JSON") from exc


def _emit(payload: dict[str, Any], *, error: bool = False) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered, file=sys.stderr if error else sys.stdout, flush=True)
    if _LOG_STREAM is not None:
        print(rendered, file=_LOG_STREAM, flush=True)


def _configure_log(path: Path | None) -> None:
    global _LOG_STREAM
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _LOG_STREAM = path.open("a", encoding="utf-8")


def _resolved_command(command: Sequence[str], *, windows: bool | None = None) -> list[str]:
    resolved = list(command)
    is_windows = os.name == "nt" if windows is None else windows
    if not resolved or not is_windows or any(separator in resolved[0] for separator in ("/", "\\")):
        return resolved
    executable = shutil.which(resolved[0])
    if executable:
        resolved[0] = executable
    return resolved


def _repo_root(cwd: Path, runner: CommandRunner) -> Path:
    completed = runner.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    if completed.returncode:
        raise LoopError("not-a-git-repository", "handoff must run inside a Git worktree")
    return Path(completed.stdout.strip()).resolve()


def _git_value(root: Path, runner: CommandRunner, *args: str) -> str:
    completed = runner.run(["git", *args], cwd=root)
    if completed.returncode:
        raise LoopError("git-state-unavailable", completed.stderr.strip() or "could not read Git state")
    return completed.stdout.strip()


def _repo_slug(root: Path, runner: CommandRunner) -> str:
    payload = runner.json(["gh", "repo", "view", "--json", "nameWithOwner"], cwd=root)
    slug = str(payload.get("nameWithOwner", "")).strip()
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", slug):
        raise LoopError("repository-ambiguous", "gh did not identify one owner/repository")
    return slug


def _pr_view(root: Path, runner: CommandRunner, *, pr: int | None = None, repo: str | None = None) -> dict[str, Any]:
    command = [
        "gh",
        "pr",
        "view",
        *([str(pr)] if pr else []),
        *(["--repo", repo] if repo else []),
        "--json",
        "number,state,headRefName,headRefOid,body,comments,url",
    ]
    payload = runner.json(command, cwd=root)
    if not isinstance(payload, dict):
        raise LoopError("pr-state-invalid", "gh returned a non-object PR payload")
    return payload


def _state_path(root: Path, pr: int) -> Path:
    return root / STATE_RELATIVE / f"pr-{pr}.json"


def _save_state(root: Path, state: dict[str, Any]) -> None:
    path = _state_path(root, int(state["pr_number"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_state(root: Path, pr: int) -> dict[str, Any]:
    path = _state_path(root, pr)
    if not path.is_file():
        raise LoopError("state-missing", f"no local loop state exists for PR #{pr}", recovery="run handoff from the exact Codex session")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LoopError("state-invalid", f"local state for PR #{pr} is unreadable", recovery=f"inspect or remove {path}") from exc
    if payload.get("kind") != STATE_KIND or int(payload.get("pr_number", 0)) != pr:
        raise LoopError("state-invalid", f"local state for PR #{pr} has the wrong contract")
    return payload


def _all_states(root: Path) -> list[dict[str, Any]]:
    directory = root / STATE_RELATIVE
    if not directory.is_dir():
        return []
    states: list[dict[str, Any]] = []
    for path in sorted(directory.glob("pr-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            states.append({"kind": STATE_KIND, "status": "invalid-local-state", "path": path.as_posix()})
            continue
        states.append(payload)
    return states


def _dispatch_path(root: Path) -> Path:
    return root / STATE_RELATIVE / DISPATCH_STATE


def _load_dispatch(root: Path) -> dict[str, Any]:
    path = _dispatch_path(root)
    if not path.is_file():
        return {"kind": STATE_KIND, "prs": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LoopError("dispatch-state-invalid", f"global dispatcher state is unreadable: {path}") from exc
    if payload.get("kind") != STATE_KIND or not isinstance(payload.get("prs"), dict):
        raise LoopError("dispatch-state-invalid", "global dispatcher state has the wrong contract")
    return payload


def _save_dispatch(root: Path, payload: dict[str, Any]) -> None:
    path = _dispatch_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _comments_from_pr(payload: dict[str, Any]) -> list[dict[str, Any]]:
    comments = payload.get("comments", [])
    return [item for item in comments if isinstance(item, dict)] if isinstance(comments, list) else []


def _open_prs(root: Path, runner: CommandRunner) -> list[dict[str, Any]]:
    payload = runner.json(
        ["gh", "pr", "list", "--state", "open", "--limit", "100", "--json", "number,state,headRefName,headRefOid,body,comments,url"],
        cwd=root,
    )
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise LoopError("pr-list-invalid", "gh returned an invalid open PR list")
    return sorted(payload, key=lambda item: int(item.get("number", 0)))


def _ensure_opt_in(root: Path, runner: CommandRunner, payload: dict[str, Any]) -> bool:
    bodies = [str(payload.get("body", "")), *(str(item.get("body", "")) for item in _comments_from_pr(payload))]
    if any(OPT_IN_MARKER in body for body in bodies):
        return False
    pr = int(payload["number"])
    completed = runner.run(["gh", "pr", "comment", str(pr), "--body", OPT_IN_MARKER], cwd=root)
    if completed.returncode:
        raise LoopError("opt-in-failed", completed.stderr.strip() or f"could not opt PR #{pr} into external review")
    return True


def handoff(
    *,
    cwd: Path,
    session_id: str,
    pr: int | None,
    max_cycles: int,
    max_repeated_blockers: int,
    replace_session: bool,
    existing_only: bool,
    runner: CommandRunner,
) -> dict[str, Any]:
    session_id = session_id.strip()
    if not session_id:
        raise LoopError(
            "session-missing", "Codex session identity is required", recovery="run from a Stop hook or pass --session-id explicitly"
        )
    root = _repo_root(cwd, runner)
    owner_root = Path(os.environ.get(OWNER_ROOT_ENV, root.as_posix())).resolve()
    branch = os.environ.get(OWNER_BRANCH_ENV, "") or _git_value(root, runner, "branch", "--show-current")
    head = _git_value(root, runner, "rev-parse", "HEAD")
    if existing_only and os.environ.get(OWNER_ROOT_ENV) and not _git_value(root, runner, "branch", "--show-current"):
        candidates = [item for item in _all_states(owner_root) if item.get("branch") == branch and item.get("session_id") == session_id]
        if not candidates:
            return {"kind": STATE_KIND, "status": "handoff-not-enabled", "pr_number": 0, "head": head, "session_bound": False, "opt_in_added": False, "state_path": ""}
    if not branch:
        raise LoopError("detached-head", "handoff does not guess a PR from a detached HEAD")
    if existing_only:
        candidates = [
            item
            for item in _all_states(owner_root)
            if item.get("branch") == branch and item.get("session_id") == session_id
        ]
        if not candidates:
            candidates = [
                item
                for item in _all_states(owner_root)
                if item.get("branch") == branch and item.get("status") == "fresh-session-in-progress"
            ]
        if not candidates:
            return {
                "kind": STATE_KIND,
                "status": "handoff-not-enabled",
                "pr_number": 0,
                "head": head,
                "session_bound": False,
                "opt_in_added": False,
                "state_path": "",
            }
        if len(candidates) != 1:
            raise LoopError(
                "session-ambiguous",
                "multiple local review loops match this branch and exact Codex session",
                recovery="inspect status and stop or clean up stale loop state",
            )
        pr = int(candidates[0]["pr_number"])
    repo = _repo_slug(root, runner)
    payload = _pr_view(root, runner, pr=pr, repo=repo if pr else None)
    number = int(payload.get("number", 0))
    if payload.get("state") != "OPEN":
        raise LoopError("pr-not-open", f"PR #{number} is not open")
    if payload.get("headRefName") != branch:
        raise LoopError("branch-changed", f"current branch {branch!r} does not match PR head branch {payload.get('headRefName')!r}")
    for _ in range(HEAD_SYNC_ATTEMPTS - 1):
        if payload.get("headRefOid") == head:
            break
        time.sleep(1)
        payload = _pr_view(root, runner, pr=number, repo=repo)
    if payload.get("headRefOid") != head:
        raise LoopError("head-not-pushed", "current HEAD does not match the PR head; push before handoff")

    path = _state_path(owner_root, number)
    existing = _load_state(owner_root, number) if path.is_file() else None
    if existing and existing.get("session_id") not in {"", session_id} and not replace_session:
        raise LoopError(
            "session-ambiguous",
            f"PR #{number} is already bound to a different exact Codex session",
            recovery="inspect status, then rerun handoff with --replace-session only if the previous owner is intentionally superseded",
        )
    opted_in = _ensure_opt_in(root, runner, payload)
    state = existing or {
        "kind": STATE_KIND,
        "pr_number": number,
        "repository": repo,
        "handled_reviews": [],
        "blocker_fingerprints": {},
        "cycles": 0,
    }
    configured_max_cycles = int(state.get("max_cycles", max_cycles)) if existing_only else max_cycles
    configured_max_repeated_blockers = (
        int(state.get("max_repeated_blockers", max_repeated_blockers)) if existing_only else max_repeated_blockers
    )
    same_handoff = state.get("handoff_head") == head and state.get("session_id") == session_id
    if existing_only and same_handoff and state.get("status") in {"stopped", "merge-ready"}:
        return {
            "kind": STATE_KIND,
            "status": "handoff-not-enabled",
            "pr_number": number,
            "head": head,
            "session_bound": True,
            "opt_in_added": False,
            "state_path": path.relative_to(owner_root).as_posix(),
        }
    state.update(
        {
            "repo_root": owner_root.as_posix(),
            "repository": repo,
            "pr_number": number,
            "pr_url": str(payload.get("url", "")),
            "branch": branch,
            "handoff_head": head,
            "session_id": session_id,
            "max_cycles": configured_max_cycles,
            "max_repeated_blockers": configured_max_repeated_blockers,
            "status": "awaiting-review",
            "last_event": "handoff-noop" if same_handoff else "handoff-recorded",
            "recovery": "",
        }
    )
    if not same_handoff:
        state["handoff_at"] = datetime.now(timezone.utc).isoformat()
    state.pop("resume_exit_code", None)
    state.pop("resume_diagnostic", None)
    _save_state(owner_root, state)
    return {
        "kind": STATE_KIND,
        "status": state["last_event"],
        "pr_number": number,
        "head": head,
        "session_bound": True,
        "opt_in_added": opted_in,
        "state_path": path.relative_to(owner_root).as_posix(),
    }


def parse_reviews(comments: list[dict[str, Any]], *, expected_pr: int, expected_head: str) -> tuple[list[Review], list[dict[str, Any]]]:
    matches: list[Review] = []
    rejected: list[dict[str, Any]] = []
    for comment in comments:
        body = str(comment.get("body", ""))
        if "aw-chatgpt-review" not in body or body.strip() == OPT_IN_MARKER:
            continue
        markers = list(REVIEW_MARKER_RE.finditer(body))
        comment_id = str(comment.get("databaseId") or comment.get("id") or "").strip()
        if not comment_id:
            rejected.append({"comment_id": "", "reason": "missing-comment-id"})
            continue
        if len(markers) != 1:
            rejected.append({"comment_id": comment_id, "reason": "malformed-or-multiple-markers"})
            continue
        marker = markers[0]
        marker_pr = int(marker.group("pr"))
        marker_head = marker.group("head")
        if marker_pr != expected_pr:
            rejected.append({"comment_id": comment_id, "reason": "pr-mismatch"})
            continue
        if marker_head != expected_head:
            rejected.append({"comment_id": comment_id, "reason": "stale-head", "reviewed_head": marker_head})
            continue
        findings = (body[: marker.start()] + body[marker.end() :]).strip()
        matches.append(
            Review(
                comment_id=comment_id,
                pr=marker_pr,
                head=marker_head,
                decision=marker.group("decision"),
                findings=findings,
                url=str(comment.get("url", "")),
            )
        )
    return matches, rejected


AUTO_RECOVERY_EVENTS = frozenset({"resume-failed", "resume-ended-without-new-handoff"})


def _queue_automatic_recovery(state: dict[str, Any], root: Path, *, review_key: str = "") -> bool:
    """Re-arm one recoverable failed resume for the global serial dispatcher.

    A recovery job resumes the same durable Codex session once.  It may retry the
    review it had claimed, but never repeatedly: that review key is recorded
    before re-arming, and all other recovery-required states remain human-only.
    """
    if state.get("status") != "recovery-required" or state.get("last_event") not in AUTO_RECOVERY_EVENTS:
        return False
    key = review_key or str(state.get("recovery_review_key", ""))
    if not key:
        return False
    recovered = state.setdefault("automatic_recovery_reviews", [])
    if key in recovered:
        return False
    handled = state.setdefault("handled_reviews", [])
    state["handled_reviews"] = [item for item in handled if item != key]
    recovered.append(key)
    state.update(
        status="awaiting-review",
        last_event="automatic-recovery-queued",
        recovery="",
        recovery_review_key=key,
    )
    _save_state(root, state)
    return True


def _recover(state: dict[str, Any], root: Path, *, event: str, recovery: str) -> dict[str, Any]:
    state.update(status="recovery-required", last_event=event, recovery=recovery)
    _save_state(root, state)
    return {"pr_number": state["pr_number"], "status": "recovery-required", "event": event, "recovery": recovery}


def _review_prompt(review: Review, *, branch: str = "") -> str:
    return (
        f"External ChatGPT review found blockers for PR #{review.pr} at exact head {review.head}.\n\n"
        f"Review comment: {review.url or review.comment_id}\n\n"
        f"Actionable findings (transported verbatim; not reinterpreted):\n{review.findings}\n\n"
        f"{'You are detached: push with git push origin HEAD:' + branch + '. ' if branch else ''}Address these findings, run the appropriate proof, push a new head, and let the repo Stop hook record the next handoff. "
        "Do not merge from this continuation."
    )


def _should_keep_watching(results: list[dict[str, Any]]) -> bool:
    waiting_reasons = {
        "review-pending",
        "stale-review-rejected",
        "state-is-resume-in-progress",
        "no-eligible-blocked-review",
        "dispatcher-job-in-progress",
    }
    return any(
        item.get("status") in {"resumed", "dispatched", "recovery-required"}
        or (item.get("status") == "no-op" and item.get("reason") in waiting_reasons)
        for item in results
    )


def _resume_worktree_path(root: Path, state: dict[str, Any]) -> Path:
    return root / STATE_RELATIVE / "resume-worktrees" / f"pr-{state['pr_number']}-cycle-{state['cycles']}-{str(state['handoff_head'])[:8]}"


def _create_resume_worktree(root: Path, state: dict[str, Any], runner: CommandRunner) -> Path:
    worktree = _resume_worktree_path(root, state)
    worktree.parent.mkdir(parents=True, exist_ok=True)
    created = runner.run(["git", "worktree", "add", "--detach", worktree.as_posix(), str(state["handoff_head"])], cwd=root)
    if created.returncode:
        raise LoopError("worktree-create-failed", created.stderr.strip() or "could not create resume worktree")
    return worktree


def _remove_worktree(root: Path, worktree: Path, runner: CommandRunner) -> str:
    removed = runner.run(["git", "worktree", "remove", "--force", worktree.as_posix()], cwd=root)
    return removed.stderr.strip() or removed.stdout.strip() if removed.returncode else ""


def poll_one(
    root: Path,
    state: dict[str, Any],
    *,
    runner: CommandRunner,
    codex_command: str,
    bypass_hook_trust: bool = False,
    state_root: Path | None = None,
    isolated_worktree: bool = False,
) -> dict[str, Any]:
    owner_root = state_root or root
    pr = int(state["pr_number"])
    if state.get("status") != "awaiting-review":
        return {"pr_number": pr, "status": "no-op", "reason": f"state-is-{state.get('status', 'unknown')}"}
    state["hook_trust_mode"] = "automation-bypass" if bypass_hook_trust else "persisted-trust-required"
    _save_state(owner_root, state)
    current_branch = _git_value(root, runner, "branch", "--show-current")
    if not isolated_worktree and current_branch != state.get("branch"):
        return _recover(state, owner_root, event="branch-changed", recovery="return to the recorded branch or stop and clean up this loop")
    payload = _pr_view(root, runner, pr=pr, repo=str(state["repository"]))
    if payload.get("state") != "OPEN":
        return _recover(state, owner_root, event="pr-closed", recovery="inspect the closed PR, then stop or clean up the local loop")
    if payload.get("headRefName") != state.get("branch"):
        return _recover(state, owner_root, event="remote-branch-changed", recovery="inspect PR head ownership; do not guess a replacement branch")
    if payload.get("headRefOid") != state.get("handoff_head"):
        return _recover(
            state, owner_root, event="unrecorded-head", recovery="run handoff from the exact owning Codex session at the new pushed head"
        )

    matches, rejected = parse_reviews(_comments_from_pr(payload), expected_pr=pr, expected_head=str(state["handoff_head"]))
    malformed = [item for item in rejected if item["reason"] != "stale-head"]
    if malformed:
        return _recover(
            state,
            owner_root,
            event="malformed-review",
            recovery="repair or remove the malformed review comment, then use recover --action continue-waiting",
        )
    if len(matches) > 1:
        return _recover(
            state,
            owner_root,
            event="ambiguous-reviews",
            recovery="leave one authoritative matching review, then use recover --action continue-waiting",
        )
    if not matches:
        event = "stale-review-rejected" if rejected else "review-pending"
        state.update(last_event=event, recovery="")
        _save_state(owner_root, state)
        return {"pr_number": pr, "status": "no-op", "reason": event, "rejected": rejected}

    review = matches[0]
    handled = state.setdefault("handled_reviews", [])
    if review.key in handled:
        state.update(last_event="review-already-handled", recovery="")
        _save_state(owner_root, state)
        return {"pr_number": pr, "status": "no-op", "reason": "review-already-handled", "review_key": review.key}
    if review.decision == "merge-ready":
        handled.append(review.key)
        state.update(status="merge-ready", last_event="merge-ready-recorded", recovery="Human retains merge authority.")
        _save_state(owner_root, state)
        return {"pr_number": pr, "status": "merge-ready", "merged": False, "review_key": review.key}
    if not review.findings:
        return _recover(state, owner_root, event="missing-findings", recovery="the reviewer must post actionable findings with a blocked marker")
    if int(state.get("cycles", 0)) >= int(state.get("max_cycles", 3)):
        return _recover(state, owner_root, event="max-cycles-exceeded", recovery="human review is required before another continuation")

    fingerprint = hashlib.sha256(review.findings.encode("utf-8")).hexdigest()
    fingerprints = state.setdefault("blocker_fingerprints", {})
    repeated = int(fingerprints.get(fingerprint, 0)) + 1
    if repeated > int(state.get("max_repeated_blockers", 2)):
        return _recover(
            state, owner_root, event="repeated-blocker-threshold", recovery="the same blocker recurred; human intervention is required"
        )

    # Persist the attempt before launching Codex. A Stop hook or process crash cannot
    # make this exact review eligible for a second automatic resume.
    handled.append(review.key)
    fingerprints[fingerprint] = repeated
    state["cycles"] = int(state.get("cycles", 0)) + 1
    state.update(status="resume-in-progress", last_event="resume-attempt-recorded", recovery="")
    _save_state(owner_root, state)

    env = os.environ.copy()
    env["AW_CHATGPT_REVIEW_RESUME_ACTIVE"] = "1"
    worktree = root
    if isolated_worktree:
        try:
            worktree = _create_resume_worktree(owner_root, state, runner)
        except LoopError as exc:
            return _recover(state, owner_root, event=exc.code, recovery="inspect Git worktree state before retrying")
        env[OWNER_ROOT_ENV] = owner_root.as_posix()
        env[OWNER_BRANCH_ENV] = str(state["branch"])
    command = [
        *shlex.split(codex_command),
        "-C",
        worktree.as_posix(),
        "exec",
        "resume",
        *(["--dangerously-bypass-hook-trust"] if bypass_hook_trust else []),
        str(state["session_id"]),
        _review_prompt(review),
    ]
    try:
        completed = runner.run(command, cwd=worktree, env=env)
    finally:
        cleanup = _remove_worktree(owner_root, worktree, runner) if isolated_worktree else ""
    latest = _load_state(owner_root, pr)
    if cleanup:
        return _recover(latest, owner_root, event="worktree-cleanup-failed", recovery=cleanup[-2000:])
    if completed.returncode:
        diagnostic = (completed.stderr or completed.stdout).strip()[-2000:]
        latest.update(
            status="recovery-required",
            last_event="resume-failed",
            recovery="the watcher will launch one recovery resume for this exact review; inspect it if that recovery also fails",
            recovery_review_key=review.key,
            resume_exit_code=completed.returncode,
            resume_diagnostic=diagnostic,
        )
        _save_state(owner_root, latest)
        return {
            "pr_number": pr,
            "status": "recovery-required",
            "event": "resume-failed",
            "exit_code": completed.returncode,
            "diagnostic": diagnostic,
        }
    if latest.get("handoff_head") == review.head:
        latest.update(
            status="recovery-required",
            last_event="resume-ended-without-new-handoff",
            recovery="the watcher will launch one recovery resume for this exact review; inspect it if that recovery also ends without a handoff",
            recovery_review_key=review.key,
        )
        _save_state(owner_root, latest)
        return {"pr_number": pr, "status": "recovery-required", "event": "resume-ended-without-new-handoff"}
    return {"pr_number": pr, "status": "resumed", "new_head": latest.get("handoff_head"), "review_key": review.key}


def _session_id_from_jsonl(output: str) -> str:
    """Extract the one durable Codex session identity from `codex exec --json` output."""
    candidates: set[str] = set()
    for line in output.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        stack: list[Any] = [item]
        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {"session_id", "thread_id", "threadId"} and isinstance(child, str) and child.strip():
                        candidates.add(child.strip())
                    else:
                        stack.append(child)
            elif isinstance(value, list):
                stack.extend(value)
    if len(candidates) != 1:
        raise LoopError("session-unavailable", "fresh Codex job did not report one session identity")
    return candidates.pop()


def _worktree_for(root: Path, pr: int, *, worktree_root: Path) -> Path:
    return (worktree_root / f"pr-{pr}").resolve()


def _cleanup_closed_dispatches(root: Path, registry: dict[str, Any], *, runner: CommandRunner, worktree_root: Path) -> list[int]:
    entries = registry["prs"]
    removed: list[int] = []
    for key, entry in list(entries.items()):
        if not isinstance(entry, dict) or not key.isdigit():
            continue
        pr = int(key)
        payload = _pr_view(root, runner, pr=pr, repo=str(entry.get("repository", "")) or None)
        if payload.get("state") == "OPEN":
            continue
        worktree = Path(str(entry.get("worktree", ""))).resolve()
        if worktree.is_relative_to(worktree_root.resolve()) and worktree.exists():
            completed = runner.run(["git", "worktree", "remove", "--force", worktree.as_posix()], cwd=root)
            if completed.returncode:
                raise LoopError("worktree-cleanup-failed", completed.stderr.strip() or f"could not remove worktree for closed PR #{pr}")
        _state_path(root, pr).unlink(missing_ok=True)
        entries.pop(key)
        removed.append(pr)
    if removed:
        _save_dispatch(root, registry)
    return removed


def _dispatch_all_unlocked(
    root: Path,
    *,
    runner: CommandRunner,
    codex_command: str,
    worktree_root: Path,
    max_cycles: int,
    max_repeated_blockers: int,
    bypass_hook_trust: bool = False,
) -> dict[str, Any]:
    """Run at most one eligible blocked review across every open PR.

    The registry is deliberately local and records the owning session/worktree per
    PR.  Existing PRs are resumed; a first review creates one worktree and starts
    one fresh Codex session there.  A later poll never creates a second job while
    that PR has a recorded in-progress session.
    """
    registry = _load_dispatch(root)
    entries = registry["prs"]
    retired = _cleanup_closed_dispatches(root, registry, runner=runner, worktree_root=worktree_root)
    candidates: list[tuple[dict[str, Any], Review]] = []
    for payload in _open_prs(root, runner):
        pr = int(payload.get("number", 0))
        head = str(payload.get("headRefOid", ""))
        if pr < 1 or not re.fullmatch(r"[0-9a-f]{40}", head):
            continue
        matches, rejected = parse_reviews(_comments_from_pr(payload), expected_pr=pr, expected_head=head)
        if any(item["reason"] != "stale-head" for item in rejected) or len(matches) != 1:
            continue
        review = matches[0]
        if review.decision != "blocked" or not review.findings:
            continue
        entry = entries.get(str(pr))
        if isinstance(entry, dict) and _state_path(root, pr).is_file():
            # A completed or exhausted session must release the global serial
            # slot. A recoverable failed resume gets exactly one automatic
            # recovery job; other recovery states remain explicitly human-owned.
            existing = _load_state(root, pr)
            if existing.get("status") == "recovery-required":
                if not _queue_automatic_recovery(existing, root, review_key=review.key):
                    continue
            elif existing.get("status") != "awaiting-review":
                continue
        candidates.append((payload, review))
    if not candidates:
        return {"status": "no-op", "reason": "no-eligible-blocked-review", "retired": retired}

    payload, review = candidates[0]
    pr = int(payload["number"])
    entry = entries.get(str(pr))
    if isinstance(entry, dict):
        worktree = Path(str(entry.get("worktree", "")))
        state_path = _state_path(root, pr)
        if state_path.is_file():
            state = _load_state(root, pr)
            _emit({"kind": STATE_KIND, "status": "job-started", "pr_number": pr, "mode": "resume"})
            result = poll_one(
                root,
                state,
                runner=runner,
                codex_command=codex_command,
                bypass_hook_trust=bypass_hook_trust,
                isolated_worktree=True,
            )
            return {"status": "dispatched", "pr_number": pr, "mode": "resume", "result": result}
        # Old failed fresh sessions had no durable state/session binding.  Their
        # detached worktree cannot be resumed safely, so retire it and start one
        # new, recorded session below.
        if worktree.is_dir():
            runner.run(["git", "worktree", "remove", "--force", worktree.as_posix()], cwd=root)
        entries.pop(str(pr), None)
        _save_dispatch(root, registry)

    worktree = _worktree_for(root, pr, worktree_root=worktree_root)
    if worktree.exists():
        if not worktree.is_relative_to(worktree_root.resolve()):
            return {"status": "recovery-required", "pr_number": pr, "event": "unowned-worktree-exists"}
        removed = runner.run(["git", "worktree", "remove", "--force", worktree.as_posix()], cwd=root)
        if removed.returncode:
            try:
                shutil.rmtree(worktree)
            except OSError:
                return {"status": "recovery-required", "pr_number": pr, "event": "orphan-worktree-cleanup-failed"}
    branch = str(payload.get("headRefName", ""))
    if not branch:
        return {"status": "recovery-required", "pr_number": pr, "event": "missing-head-branch"}
    fetched = runner.run(["git", "fetch", "--no-tags", "origin", branch], cwd=root)
    if fetched.returncode:
        raise LoopError("reviewed-head-fetch-failed", fetched.stderr.strip() or f"could not fetch PR #{pr} head branch")
    fetched_head = _git_value(root, runner, "rev-parse", "FETCH_HEAD")
    if fetched_head != str(payload["headRefOid"]):
        raise LoopError("reviewed-head-mismatch", f"fetched branch for PR #{pr} does not equal the reviewed head")
    created = runner.run(["git", "worktree", "add", "--detach", worktree.as_posix(), fetched_head], cwd=root)
    if created.returncode:
        raise LoopError("worktree-create-failed", created.stderr.strip() or f"could not create worktree for PR #{pr}")
    prompt = _review_prompt(review, branch=branch)
    # Bind owner-local state before the detached fresh session starts. Its Stop
    # hook is the first point at which Codex exposes the session identity.
    _save_state(
        root,
        {
            "kind": STATE_KIND, "repo_root": root.as_posix(), "repository": _repo_slug(root, runner),
            "pr_number": pr, "pr_url": str(payload.get("url", "")), "branch": branch,
            "handoff_head": review.head, "session_id": "", "max_cycles": max_cycles,
            "max_repeated_blockers": max_repeated_blockers, "handled_reviews": [],
            "blocker_fingerprints": {}, "cycles": 0, "status": "fresh-session-in-progress",
            "last_event": "fresh-session-bound", "recovery": "",
        },
    )
    entries[str(pr)] = {"worktree": worktree.as_posix(), "branch": branch, "repository": _repo_slug(root, runner)}
    _save_dispatch(root, registry)
    _emit({"kind": STATE_KIND, "status": "job-started", "pr_number": pr, "mode": "fresh"})
    command = [*shlex.split(codex_command), "-C", worktree.as_posix(), "exec", "--json", *(["--dangerously-bypass-hook-trust"] if bypass_hook_trust else []), prompt]
    env = os.environ.copy()
    env["AW_CHATGPT_REVIEW_RESUME_ACTIVE"] = "1"
    env[OWNER_ROOT_ENV] = root.as_posix()
    env[OWNER_BRANCH_ENV] = branch
    completed = runner.run(command, cwd=worktree, env=env)
    cleanup = _remove_worktree(root, worktree, runner)
    if cleanup:
        return {"status": "recovery-required", "pr_number": pr, "event": "worktree-cleanup-failed", "diagnostic": cleanup[-2000:]}
    if completed.returncode:
        _state_path(root, pr).unlink(missing_ok=True)
        entries.pop(str(pr), None)
        _save_dispatch(root, registry)
        return {"status": "recovery-required", "pr_number": pr, "event": "fresh-session-failed"}
    session_id = _session_id_from_jsonl(completed.stdout)
    updated = _pr_view(root, runner, pr=pr)
    new_head = str(updated.get("headRefOid", ""))
    if new_head == review.head:
        # A fresh Codex session may finish before it pushes.  Preserve that exact
        # session and the reviewed head so the next serial dispatch resumes it
        # instead of suppressing this PR forever.
        state = {
            "kind": STATE_KIND,
            "repo_root": root.as_posix(),
            "repository": _repo_slug(root, runner),
            "pr_number": pr,
            "pr_url": str(updated.get("url", "")),
            "branch": branch,
            "handoff_head": review.head,
            "session_id": session_id,
            "max_cycles": max_cycles,
            "max_repeated_blockers": max_repeated_blockers,
            "handled_reviews": [],
            "blocker_fingerprints": {},
            "cycles": 0,
            "status": "awaiting-review",
            "last_event": "fresh-session-awaiting-resume",
            "recovery": "",
        }
        _save_state(root, state)
        entries[str(pr)] = {
            "worktree": worktree.as_posix(),
            "session_id": session_id,
            "branch": branch,
            "repository": str(payload.get("repository", "")),
            "reviewed_head": review.head,
        }
        _save_dispatch(root, registry)
        return {"status": "dispatched", "pr_number": pr, "mode": "fresh", "session_id": session_id, "awaiting_resume": True}
    state = {
        "kind": STATE_KIND,
        "repo_root": root.as_posix(),
        "repository": _repo_slug(root, runner),
        "pr_number": pr,
        "pr_url": str(updated.get("url", "")),
        "branch": branch,
        "handoff_head": new_head,
        "session_id": session_id,
        "max_cycles": max_cycles,
        "max_repeated_blockers": max_repeated_blockers,
        "handled_reviews": [review.key],
        "blocker_fingerprints": {},
        "cycles": 1,
        "status": "awaiting-review",
        "last_event": "fresh-handoff-recorded",
        "recovery": "",
    }
    _save_state(root, state)
    entries[str(pr)] = {
        "worktree": worktree.as_posix(),
        "session_id": session_id,
        "branch": branch,
        "repository": str(payload.get("repository", "")),
        "reviewed_head": str(payload["headRefOid"]),
    }
    _save_dispatch(root, registry)
    return {"status": "dispatched", "pr_number": pr, "mode": "fresh", "session_id": session_id}


def _process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _acquire_dispatch_lock(lock: Path) -> bool:
    """Acquire the global dispatch lock, reclaiming only a dead owner's lock."""
    try:
        with lock.open("x", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        return True
    except FileExistsError:
        try:
            owner = int(lock.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return False
        if _process_is_running(owner):
            return False
        try:
            lock.unlink()
        except OSError:
            return False
        try:
            with lock.open("x", encoding="utf-8") as handle:
                handle.write(str(os.getpid()))
            return True
        except FileExistsError:
            return False


def dispatch_all(
    root: Path,
    *,
    runner: CommandRunner,
    codex_command: str,
    worktree_root: Path,
    max_cycles: int,
    max_repeated_blockers: int,
    bypass_hook_trust: bool = False,
) -> dict[str, Any]:
    """Serialize all global scans, including the foreground Codex job they launch."""
    lock = root / STATE_RELATIVE / "dispatch.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    if not _acquire_dispatch_lock(lock):
        return {"status": "no-op", "reason": "dispatcher-job-in-progress"}
    try:
        return _dispatch_all_unlocked(
            root,
            runner=runner,
            codex_command=codex_command,
            worktree_root=worktree_root,
            max_cycles=max_cycles,
            max_repeated_blockers=max_repeated_blockers,
            bypass_hook_trust=bypass_hook_trust,
        )
    finally:
        lock.unlink(missing_ok=True)


def _hook_input() -> tuple[Path, str]:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise LoopError("hook-input-invalid", "Stop hook stdin was not valid JSON") from exc
    if payload.get("hook_event_name") != "Stop":
        raise LoopError("hook-event-invalid", "this hook command accepts only a Stop event")
    return Path(str(payload.get("cwd", "."))).resolve(), str(payload.get("session_id", ""))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Repo-local deterministic ChatGPT-review-to-Codex continuation transport.")
    sub = parser.add_subparsers(dest="command", required=True)
    handoff_parser = sub.add_parser("handoff", help="Record one pushed PR head and exact Codex session without waiting.")
    handoff_parser.add_argument(
        "--hook", action="store_true", help="Read Stop hook JSON and update only an explicitly enabled loop."
    )
    handoff_parser.add_argument("--session-id", default=os.environ.get("CODEX_THREAD_ID", ""))
    handoff_parser.add_argument("--target", type=Path, default=Path.cwd())
    handoff_parser.add_argument("--pr", type=int)
    handoff_parser.add_argument("--max-cycles", type=int, default=3)
    handoff_parser.add_argument("--max-repeated-blockers", type=int, default=2)
    handoff_parser.add_argument("--replace-session", action="store_true")

    poll_parser = sub.add_parser("poll", help="Poll with gh and resume only exact blocked handoffs.")
    poll_parser.add_argument("--target", type=Path, default=Path.cwd())
    poll_parser.add_argument("--pr", type=int)
    poll_parser.add_argument("--watch", action="store_true")
    poll_parser.add_argument("--interval", type=int, default=60)
    poll_parser.add_argument("--max-polls", type=int, default=60)
    poll_parser.add_argument(
        "--all-open",
        action="store_true",
        help="Scan every open PR and dispatch at most one exact-head blocked review per poll.",
    )
    poll_parser.add_argument(
        "--worktree-root",
        type=Path,
        default=Path(".agentic-workspace/local/chatgpt-review-worktrees"),
        help="Local root that owns one isolated worktree for each globally dispatched PR.",
    )
    poll_parser.add_argument("--max-cycles", type=int, default=3)
    poll_parser.add_argument("--max-repeated-blockers", type=int, default=2)
    poll_parser.add_argument("--log-file", type=Path, help="Append watcher events to this file while also printing them.")
    poll_parser.add_argument("--codex-command", default=os.environ.get("AW_CHATGPT_REVIEW_CODEX", "codex"))
    poll_parser.add_argument(
        "--bypass-hook-trust",
        action="store_true",
        help="Activate reviewed hooks for resumed Codex automation without persisted /hooks trust.",
    )

    for name in ("status", "stop", "cleanup"):
        item = sub.add_parser(name)
        item.add_argument("--target", type=Path, default=Path.cwd())
        item.add_argument("--pr", type=int)
    recover_parser = sub.add_parser("recover", help="Explicitly re-arm polling after a human resolves bounded recovery state.")
    recover_parser.add_argument("--target", type=Path, default=Path.cwd())
    recover_parser.add_argument("--pr", type=int, required=True)
    recover_parser.add_argument("--action", choices=["continue-waiting"], required=True)
    return parser


def main(argv: Sequence[str] | None = None, *, runner: CommandRunner | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    runner = runner or CommandRunner()
    try:
        if args.command == "poll":
            _configure_log(args.log_file)
        if args.command == "handoff":
            cwd, session_id = _hook_input() if args.hook else (args.target.resolve(), args.session_id)
            if args.max_cycles < 1 or args.max_repeated_blockers < 1:
                raise LoopError("invalid-limit", "cycle and repeated-blocker limits must be positive")
            result = handoff(
                cwd=cwd,
                session_id=session_id,
                pr=args.pr,
                max_cycles=args.max_cycles,
                max_repeated_blockers=args.max_repeated_blockers,
                replace_session=args.replace_session,
                existing_only=args.hook,
                runner=runner,
            )
            if args.hook:
                hook_result: dict[str, Any] = {"continue": True}
                if result["status"] != "handoff-not-enabled":
                    hook_result["systemMessage"] = (
                        f"ChatGPT review handoff {result['status']} for PR #{result['pr_number']} at {result['head']}."
                    )
                _emit(hook_result)
            else:
                _emit(result)
            return 0

        root = _repo_root(args.target.resolve(), runner)
        if args.command == "status":
            states = [_load_state(root, args.pr)] if args.pr else _all_states(root)
            _emit({"kind": STATE_KIND, "status": "inspected", "states": states})
            return 0
        if args.command == "cleanup":
            states = [_load_state(root, args.pr)] if args.pr else _all_states(root)
            removed: list[str] = []
            for state in states:
                if "pr_number" not in state:
                    continue
                path = _state_path(root, int(state["pr_number"]))
                path.unlink(missing_ok=True)
                removed.append(path.relative_to(root).as_posix())
            _emit({"kind": STATE_KIND, "status": "cleaned", "removed": removed})
            return 0
        if args.command == "stop":
            states = [_load_state(root, args.pr)] if args.pr else _all_states(root)
            stopped: list[int] = []
            for state in states:
                if "pr_number" not in state:
                    continue
                state.update(status="stopped", last_event="stopped-by-human", recovery="run handoff to start a new cycle")
                _save_state(root, state)
                stopped.append(int(state["pr_number"]))
            _emit({"kind": STATE_KIND, "status": "stopped", "prs": stopped})
            return 0
        if args.command == "recover":
            state = _load_state(root, args.pr)
            if state.get("status") != "recovery-required":
                raise LoopError("recovery-not-required", f"PR #{args.pr} is not in recovery-required state")
            state.update(status="awaiting-review", last_event="human-recovery-confirmed", recovery="")
            _save_state(root, state)
            _emit({"kind": STATE_KIND, "status": "awaiting-review", "pr_number": args.pr})
            return 0

        polls = args.max_polls if args.watch else 1
        if polls < 1 or args.interval < 1 or args.max_cycles < 1 or args.max_repeated_blockers < 1:
            raise LoopError("invalid-limit", "poll limits and interval must be positive")
        last_results: list[dict[str, Any]] = []
        for index in range(polls):
            if args.all_open:
                if args.pr:
                    raise LoopError("invalid-selection", "--all-open and --pr cannot be used together")
                worktree_root = args.worktree_root if args.worktree_root.is_absolute() else root / args.worktree_root
                try:
                    result = dispatch_all(
                        root,
                        runner=runner,
                        codex_command=args.codex_command,
                        worktree_root=worktree_root,
                        max_cycles=args.max_cycles,
                        max_repeated_blockers=args.max_repeated_blockers,
                        bypass_hook_trust=args.bypass_hook_trust,
                    )
                except LoopError as exc:
                    result = {"status": "recovery-required", "event": exc.code, "recovery": str(exc)}
                last_results = [result]
            else:
                states = [_load_state(root, args.pr)] if args.pr else _all_states(root)
                last_results = [
                    poll_one(
                        root,
                        state,
                        runner=runner,
                        codex_command=args.codex_command,
                        bypass_hook_trust=args.bypass_hook_trust,
                    )
                    for state in states
                    if "pr_number" in state
                ]
            _emit({"kind": STATE_KIND, "status": "poll-complete", "poll": index + 1, "results": last_results})
            if not args.watch or not _should_keep_watching(last_results):
                break
            if index + 1 < polls:
                # A foreground Codex job has already ended. Immediately release
                # the serial slot to the next eligible PR; only idle scans wait.
                if args.all_open and result.get("status") == "dispatched":
                    continue
                time.sleep(args.interval)
        else:
            _emit(
                {
                    "kind": STATE_KIND,
                    "status": "max-polls-reached",
                    "recovery": "restart polling explicitly if continued waiting is intended",
                }
            )
        return 0
    except LoopError as exc:
        _emit({"kind": STATE_KIND, "status": "error", "code": exc.code, "message": str(exc), "recovery": exc.recovery}, error=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
