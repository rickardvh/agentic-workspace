from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

OPT_IN_MARKER = "<!-- aw-chatgpt-review:enabled -->"
REVIEW_POLICY = "pr-review-recheck-v1"
STATE_KIND = "agentic-workspace/chatgpt-review-loop-state/v1"
STATE_RELATIVE = Path(".agentic-workspace/local/chatgpt-review-loop")
REVIEW_MARKER_RE = re.compile(
    r"<!-- aw-chatgpt-review pr=(?P<pr>[1-9][0-9]*) "
    r"head=(?P<head>[0-9a-f]{40}) policy=pr-review-recheck-v1 "
    r"decision=(?P<decision>blocked|merge-ready) -->"
)


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
        return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)

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
    print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr if error else sys.stdout)


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


def _comments_from_pr(payload: dict[str, Any]) -> list[dict[str, Any]]:
    comments = payload.get("comments", [])
    return [item for item in comments if isinstance(item, dict)] if isinstance(comments, list) else []


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
    branch = _git_value(root, runner, "branch", "--show-current")
    head = _git_value(root, runner, "rev-parse", "HEAD")
    if not branch:
        raise LoopError("detached-head", "handoff does not guess a PR from a detached HEAD")
    if existing_only:
        candidates = [
            item
            for item in _all_states(root)
            if item.get("branch") == branch and item.get("session_id") == session_id
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
    if payload.get("headRefOid") != head:
        raise LoopError("head-not-pushed", "current HEAD does not match the PR head; push before handoff")

    path = _state_path(root, number)
    existing = _load_state(root, number) if path.is_file() else None
    if existing and existing.get("session_id") != session_id and not replace_session:
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
    same_handoff = state.get("handoff_head") == head and state.get("session_id") == session_id
    if existing_only and same_handoff and state.get("status") in {"stopped", "merge-ready"}:
        return {
            "kind": STATE_KIND,
            "status": "handoff-not-enabled",
            "pr_number": number,
            "head": head,
            "session_bound": True,
            "opt_in_added": False,
            "state_path": path.relative_to(root).as_posix(),
        }
    state.update(
        {
            "repo_root": root.as_posix(),
            "repository": repo,
            "pr_number": number,
            "pr_url": str(payload.get("url", "")),
            "branch": branch,
            "handoff_head": head,
            "session_id": session_id,
            "max_cycles": max_cycles,
            "max_repeated_blockers": max_repeated_blockers,
            "status": "awaiting-review",
            "last_event": "handoff-noop" if same_handoff else "handoff-recorded",
            "recovery": "",
        }
    )
    _save_state(root, state)
    return {
        "kind": STATE_KIND,
        "status": state["last_event"],
        "pr_number": number,
        "head": head,
        "session_bound": True,
        "opt_in_added": opted_in,
        "state_path": path.relative_to(root).as_posix(),
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


def _recover(state: dict[str, Any], root: Path, *, event: str, recovery: str) -> dict[str, Any]:
    state.update(status="recovery-required", last_event=event, recovery=recovery)
    _save_state(root, state)
    return {"pr_number": state["pr_number"], "status": "recovery-required", "event": event, "recovery": recovery}


def _review_prompt(review: Review) -> str:
    return (
        f"External ChatGPT review found blockers for PR #{review.pr} at exact head {review.head}.\n\n"
        f"Review comment: {review.url or review.comment_id}\n\n"
        f"Actionable findings (transported verbatim; not reinterpreted):\n{review.findings}\n\n"
        "Address these findings, run the appropriate proof, push a new head, and let the repo Stop hook record the next handoff. "
        "Do not merge from this continuation."
    )


def poll_one(root: Path, state: dict[str, Any], *, runner: CommandRunner, codex_command: str) -> dict[str, Any]:
    pr = int(state["pr_number"])
    if state.get("status") != "awaiting-review":
        return {"pr_number": pr, "status": "no-op", "reason": f"state-is-{state.get('status', 'unknown')}"}
    current_branch = _git_value(root, runner, "branch", "--show-current")
    if current_branch != state.get("branch"):
        return _recover(state, root, event="branch-changed", recovery="return to the recorded branch or stop and clean up this loop")
    payload = _pr_view(root, runner, pr=pr, repo=str(state["repository"]))
    if payload.get("state") != "OPEN":
        return _recover(state, root, event="pr-closed", recovery="inspect the closed PR, then stop or clean up the local loop")
    if payload.get("headRefName") != state.get("branch"):
        return _recover(state, root, event="remote-branch-changed", recovery="inspect PR head ownership; do not guess a replacement branch")
    if payload.get("headRefOid") != state.get("handoff_head"):
        return _recover(
            state, root, event="unrecorded-head", recovery="run handoff from the exact owning Codex session at the new pushed head"
        )

    matches, rejected = parse_reviews(_comments_from_pr(payload), expected_pr=pr, expected_head=str(state["handoff_head"]))
    malformed = [item for item in rejected if item["reason"] != "stale-head"]
    if malformed:
        return _recover(
            state,
            root,
            event="malformed-review",
            recovery="repair or remove the malformed review comment, then use recover --action continue-waiting",
        )
    if len(matches) > 1:
        return _recover(
            state,
            root,
            event="ambiguous-reviews",
            recovery="leave one authoritative matching review, then use recover --action continue-waiting",
        )
    if not matches:
        event = "stale-review-rejected" if rejected else "review-pending"
        state.update(last_event=event, recovery="")
        _save_state(root, state)
        return {"pr_number": pr, "status": "no-op", "reason": event, "rejected": rejected}

    review = matches[0]
    handled = state.setdefault("handled_reviews", [])
    if review.key in handled:
        state.update(last_event="review-already-handled", recovery="")
        _save_state(root, state)
        return {"pr_number": pr, "status": "no-op", "reason": "review-already-handled", "review_key": review.key}
    if review.decision == "merge-ready":
        handled.append(review.key)
        state.update(status="merge-ready", last_event="merge-ready-recorded", recovery="Human retains merge authority.")
        _save_state(root, state)
        return {"pr_number": pr, "status": "merge-ready", "merged": False, "review_key": review.key}
    if not review.findings:
        return _recover(state, root, event="missing-findings", recovery="the reviewer must post actionable findings with a blocked marker")
    if int(state.get("cycles", 0)) >= int(state.get("max_cycles", 3)):
        return _recover(state, root, event="max-cycles-exceeded", recovery="human review is required before another continuation")

    fingerprint = hashlib.sha256(review.findings.encode("utf-8")).hexdigest()
    fingerprints = state.setdefault("blocker_fingerprints", {})
    repeated = int(fingerprints.get(fingerprint, 0)) + 1
    if repeated > int(state.get("max_repeated_blockers", 2)):
        return _recover(
            state, root, event="repeated-blocker-threshold", recovery="the same blocker recurred; human intervention is required"
        )

    # Persist the attempt before launching Codex. A Stop hook or process crash cannot
    # make this exact review eligible for a second automatic resume.
    handled.append(review.key)
    fingerprints[fingerprint] = repeated
    state["cycles"] = int(state.get("cycles", 0)) + 1
    state.update(status="resume-in-progress", last_event="resume-attempt-recorded", recovery="")
    _save_state(root, state)

    env = os.environ.copy()
    env["AW_CHATGPT_REVIEW_RESUME_ACTIVE"] = "1"
    command = [*shlex.split(codex_command), "resume", "--cd", root.as_posix(), str(state["session_id"]), _review_prompt(review)]
    completed = runner.run(command, cwd=root, env=env)
    latest = _load_state(root, pr)
    if completed.returncode:
        latest.update(
            status="recovery-required",
            last_event="resume-failed",
            recovery="inspect the Codex failure; this exact review will not be retried automatically",
            resume_exit_code=completed.returncode,
        )
        _save_state(root, latest)
        return {"pr_number": pr, "status": "recovery-required", "event": "resume-failed", "exit_code": completed.returncode}
    if latest.get("handoff_head") == review.head:
        latest.update(
            status="recovery-required",
            last_event="resume-ended-without-new-handoff",
            recovery="inspect the exact Codex session; push a corrective head and run handoff before continuing",
        )
        _save_state(root, latest)
        return {"pr_number": pr, "status": "recovery-required", "event": "resume-ended-without-new-handoff"}
    return {"pr_number": pr, "status": "resumed", "new_head": latest.get("handoff_head"), "review_key": review.key}


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
    poll_parser.add_argument("--codex-command", default=os.environ.get("AW_CHATGPT_REVIEW_CODEX", "codex"))

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
        if polls < 1 or args.interval < 1:
            raise LoopError("invalid-limit", "poll limits and interval must be positive")
        last_results: list[dict[str, Any]] = []
        for index in range(polls):
            states = [_load_state(root, args.pr)] if args.pr else _all_states(root)
            last_results = [
                poll_one(root, state, runner=runner, codex_command=args.codex_command) for state in states if "pr_number" in state
            ]
            _emit({"kind": STATE_KIND, "status": "poll-complete", "poll": index + 1, "results": last_results})
            if not args.watch or not any(item.get("status") == "no-op" for item in last_results):
                break
            if index + 1 < polls:
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
