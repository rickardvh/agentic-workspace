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
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence, TextIO

REVIEW_POLICY = "pr-review-recheck-v1"
HEAD_SYNC_ATTEMPTS = 3
STATE_KIND = "agentic-workspace/chatgpt-review-loop-state/v1"
STATE_RELATIVE = Path(".agentic-workspace/local/chatgpt-review-loop")
OWNER_ROOT_ENV = "AW_CHATGPT_REVIEW_OWNER_ROOT"
OWNER_BRANCH_ENV = "AW_CHATGPT_REVIEW_OWNER_BRANCH"
DISPATCH_STATE = "dispatch.json"
PROMPT_TRANSPORT = "stdin-v1"
DEFAULT_CODEX_COMMAND = 'codex -m gpt-5.5 -c model_reasoning_effort="high"'
FORBIDDEN_CODEX_MODEL_MARKERS = ("5.6", "gpt-5.6", "terra")
REVIEW_MARKER_RE = re.compile(
    r"<!-- aw-chatgpt-review pr=(?P<pr>[1-9][0-9]*) "
    r"head=(?P<head>[0-9a-f]{40}) policy=pr-review-recheck-v1 "
    r"decision=(?P<decision>blocked|merge-ready) -->"
)
_LOG_STREAM: TextIO | None = None
_COMPACT_CONSOLE = False
_CODEX_MESSAGE_ROLES = {"codex", "user"}
_CODEX_TOOL_ROLES = {"exec", "analysis", "commentary", "tool"}


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

    def run_interactive(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: dict[str, str] | None = None,
        input_text: str = "",
    ) -> subprocess.CompletedProcess[str]:
        """Run a Codex job in its own live console instead of capturing its output."""
        _validate_codex_launch_command(command)
        kwargs: dict[str, Any] = {
            "cwd": cwd,
            "env": env,
            "check": False,
            "input": input_text,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = getattr(subprocess, "SW_SHOWMINNOACTIVE", 7)
            kwargs["startupinfo"] = startupinfo
            kwargs["close_fds"] = True
        resolved = _resolved_command(command)
        if os.name == "nt":
            # A relay in the new console prevents .CMD shims from retaining the
            # watcher's handles and restores Windows newline translation that
            # direct CONOUT$ redirection bypasses.
            resolved = [sys.executable, str(Path(__file__).resolve()), "_console-run", *resolved]
        completed = subprocess.run(resolved, **kwargs)
        return subprocess.CompletedProcess(command, completed.returncode, "", "")


def _console_job_output(lines: Sequence[str]) -> list[str]:
    """Keep Codex conversation readable while collapsing noisy tool transcripts."""
    rendered: list[str] = []
    mode = "tool"
    tool_announced = False
    for raw in lines:
        line = raw.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
        marker = line.strip().lower()
        if marker in _CODEX_MESSAGE_ROLES:
            mode = "message"
            tool_announced = False
            rendered.append(marker)
            continue
        if marker in _CODEX_TOOL_ROLES:
            mode = "tool"
            tool_announced = False
            continue
        if mode == "message":
            rendered.append(line)
            continue
        if line.strip() and not tool_announced:
            summary = " ".join(line.split())
            rendered.append(f"[tool] {summary[:240]}")
            tool_announced = True
    return rendered


def _model_values_from_command(command: Sequence[str]) -> list[str]:
    values: list[str] = []
    index = 0
    while index < len(command):
        token = command[index]
        if token in {"-m", "--model"}:
            if index + 1 >= len(command):
                raise LoopError(
                    "codex-model-missing",
                    f"{token} must be followed by an explicit model for review watcher jobs",
                    recovery="Set AW_CHATGPT_REVIEW_CODEX to the pinned 5.5 command or pass --codex-command explicitly.",
                )
            values.append(command[index + 1])
            index += 2
            continue
        if token.startswith("--model="):
            values.append(token.split("=", 1)[1])
        elif token.startswith("-m") and token != "-m":
            values.append(token[2:])
        elif token in {"-c", "--config"}:
            if index + 1 >= len(command):
                raise LoopError(
                    "codex-config-missing",
                    f"{token} must be followed by a config assignment",
                    recovery="Set AW_CHATGPT_REVIEW_CODEX to the pinned 5.5 command or pass --codex-command explicitly.",
                )
            config_value = command[index + 1]
            if config_value.startswith("model="):
                values.append(config_value.split("=", 1)[1])
            index += 2
            continue
        elif token.startswith("--config="):
            config_value = token.split("=", 1)[1]
            if config_value.startswith("model="):
                values.append(config_value.split("=", 1)[1])
        index += 1
    return values


def _validate_codex_launch_command(command: Sequence[str]) -> None:
    command_text = " ".join(command).lower()
    forbidden = next((marker for marker in FORBIDDEN_CODEX_MODEL_MARKERS if marker in command_text), "")
    if forbidden:
        raise LoopError(
            "forbidden-codex-model",
            f"refusing to launch review watcher Codex job because the command mentions forbidden model marker {forbidden!r}",
            recovery="Set AW_CHATGPT_REVIEW_CODEX to the pinned 5.5 command or pass --codex-command explicitly.",
        )
    model_values = _model_values_from_command(command)
    if not model_values:
        raise LoopError(
            "codex-model-unpinned",
            "refusing to launch review watcher Codex job without an explicit model pin",
            recovery="Use codex -m gpt-5.5 -c model_reasoning_effort=\"high\" for review watcher jobs.",
        )


def _console_run(command: Sequence[str]) -> int:
    """Stream concise Codex conversation through this process's console."""
    if not command:
        return 2
    _validate_codex_launch_command(command)
    prompt = sys.stdin.read()
    console = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)  # noqa: PTH123
    try:
        process = subprocess.Popen(
            list(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(prompt)
        process.stdin.close()
        mode = "tool"
        tool_announced = False
        for raw in process.stdout:
            line = raw.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
            marker = line.strip().lower()
            if marker in _CODEX_MESSAGE_ROLES:
                mode, tool_announced = "message", False
                console.write(marker + "\n")
            elif marker in _CODEX_TOOL_ROLES:
                mode, tool_announced = "tool", False
            elif mode == "message":
                console.write(line + "\n")
            elif line.strip() and not tool_announced:
                console.write("[tool] " + " ".join(line.split())[:240] + "\n")
                tool_announced = True
            console.flush()
        return process.wait()
    finally:
        console.close()


def _emit(payload: dict[str, Any], *, error: bool = False) -> None:
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    console_output = _compact_console_event(payload) if _COMPACT_CONSOLE else rendered
    if console_output:
        print(console_output, file=sys.stderr if error else sys.stdout, flush=True)
    if _LOG_STREAM is not None:
        print(rendered, file=_LOG_STREAM, flush=True)


def _compact_console_event(payload: dict[str, Any]) -> str:
    timestamp = datetime.now().astimezone().strftime("%H:%M:%S")
    status = str(payload.get("status", "event"))
    pr = payload.get("pr_number")
    prefix = f"[{timestamp}]" + (f" PR #{pr}" if pr else "")
    if status == "job-started":
        return f"{prefix} {payload.get('mode', 'review')} job started"
    if status == "poll-complete":
        lines: list[str] = []
        for result in payload.get("results", []):
            if not isinstance(result, dict) or result.get("status") == "no-op":
                continue
            result_pr = result.get("pr_number")
            result_prefix = f"[{timestamp}]" + (f" PR #{result_pr}" if result_pr else "")
            if result.get("status") == "dispatched":
                nested = result.get("result", {})
                if isinstance(nested, dict) and nested.get("status") == "recovery-required":
                    lines.append(f"{result_prefix} job ended: {nested.get('event', 'recovery required')}")
                elif isinstance(nested, dict) and nested.get("status") == "resumed":
                    lines.append(f"{result_prefix} job completed with handoff {str(nested.get('new_head', ''))[:8]}")
                elif result.get("awaiting_resume"):
                    lines.append(f"{result_prefix} fresh session saved; resume pending")
                else:
                    lines.append(f"{result_prefix} {result.get('mode', 'review')} job completed")
            elif result.get("status") == "recovery-required":
                lines.append(f"{result_prefix} recovery required: {result.get('event', 'unknown')}")
            else:
                lines.append(f"{result_prefix} {result.get('status')}")
        if not lines:
            return f"{prefix} poll #{payload.get('poll', '?')} idle"
        return "\n".join(lines)
    if status == "error":
        return f"{prefix} ERROR {payload.get('code', '')}: {payload.get('message', '')}"
    if status == "max-polls-reached":
        return f"{prefix} watcher stopped after reaching its poll limit"
    return f"{prefix} {status}"


def _configure_log(path: Path | None) -> None:
    global _LOG_STREAM
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _LOG_STREAM = path.open("a", encoding="utf-8")


def _configure_console_output(*, windows: bool | None = None) -> None:
    """Bind watcher output to its newly allocated Windows console."""
    global _COMPACT_CONSOLE
    if not (os.name == "nt" if windows is None else windows):
        return
    console = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)  # noqa: PTH123
    sys.stdout = console
    sys.stderr = console
    _COMPACT_CONSOLE = True


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
        "number,state,headRefName,headRefOid,body,comments,url,mergeable,mergeStateStatus,statusCheckRollup",
    ]
    payload = runner.json(command, cwd=root)
    if not isinstance(payload, dict):
        raise LoopError("pr-state-invalid", "gh returned a non-object PR payload")
    return payload


def _converged_pr_view(root: Path, runner: CommandRunner, *, pr: int, previous_head: str) -> dict[str, Any]:
    """Boundedly wait for a post-job remote head to differ from its reviewed head."""
    payload = _pr_view(root, runner, pr=pr)
    for _ in range(HEAD_SYNC_ATTEMPTS - 1):
        if payload.get("headRefOid") != previous_head:
            break
        time.sleep(1)
        payload = _pr_view(root, runner, pr=pr)
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


def _record_job_terminal(
    state: dict[str, Any],
    *,
    mode: str,
    worktree: Path,
    start_head: str,
    exit_code: int,
    disposition: str,
    event: str,
    proof_status: str = "unreported",
    diagnostic: str = "",
) -> None:
    """Persist the one machine-readable disposition for a launched job.

    A Codex exit code is transport evidence, not proof that the agent validated
    or pushed its change.  Keeping that distinction in the state file makes a
    later recovery deterministic and prevents callers from treating a remote
    head change as the normal success signal.
    """
    attempt = state.get("job_attempt") if isinstance(state.get("job_attempt"), dict) else {}
    terminal = state.get("terminal_result") if isinstance(state.get("terminal_result"), dict) else {}
    # A terminal disposition may annotate only the result created for this launch.
    # Never inherit declared proof or push evidence from an earlier attempt.
    if terminal.get("attempt_id") != attempt.get("id"):
        terminal = {}
    state["terminal_result"] = {
        **terminal,
        "kind": "agentic-workspace/chatgpt-review-job-result/v1",
        "pr_number": int(state["pr_number"]),
        "session_id": str(state.get("session_id", "")),
        "worktree": worktree.as_posix(),
        "starting_head": start_head,
        "ending_head": str(terminal.get("ending_head") or state.get("handoff_head", "")),
        "attempt_id": str(attempt.get("id", "")),
        "mode": mode,
        "exit_code": exit_code,
        "proof_status": terminal.get("proof_status", proof_status),
        "proof_commands": terminal.get("proof_commands", []),
        "proof_exit_code": terminal.get("proof_exit_code"),
        "push_status": terminal.get("push_status", "unreported"),
        "disposition": disposition,
        "event": event,
        "diagnostic": diagnostic[-2000:],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def _begin_job_attempt(state: dict[str, Any], *, mode: str, worktree: Path, start_head: str) -> dict[str, Any]:
    """Create the evidence boundary for one process launch before it starts."""
    attempt = {
        "id": uuid.uuid4().hex,
        "pr_number": int(state["pr_number"]),
        "mode": mode,
        "worktree": worktree.as_posix(),
        "starting_head": start_head,
        "session_id": str(state.get("session_id", "")),
        "launch_identity": uuid.uuid4().hex,
        "result_recorded": False,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    state["job_attempt"] = attempt
    state.pop("terminal_result", None)
    return attempt


def _validated_attempt_result(state: dict[str, Any], *, worktree: Path, start_head: str) -> bool:
    attempt = state.get("job_attempt")
    result = state.get("terminal_result")
    if not isinstance(attempt, dict) or not isinstance(result, dict) or not attempt.get("result_recorded"):
        return False
    return bool(
        result.get("kind") == "agentic-workspace/chatgpt-review-job-result/v1"
        and result.get("attempt_id") == attempt.get("id")
        and result.get("pr_number") == int(state["pr_number"])
        and result.get("session_id") == state.get("session_id") == attempt.get("session_id")
        and result.get("worktree") == attempt.get("worktree") == worktree.as_posix()
        and result.get("starting_head") == attempt.get("starting_head") == start_head
        and result.get("ending_head") == state.get("handoff_head")
        and result.get("proof_status") == "passed"
        and result.get("proof_exit_code") == 0
        and bool(result.get("proof_commands"))
        and result.get("push_status") == "passed"
    )


def report_job_result(*, cwd: Path, session_id: str, proof_status: str, proof_command: str, proof_exit_code: int, push_status: str, runner: CommandRunner) -> dict[str, Any]:
    """Record agent-supplied proof/push evidence for the exact owning session."""
    root = _repo_root(cwd, runner)
    # The command is invoked from the launched worktree.  Keep that path as the
    # binding fact even when a test or wrapper resolves the Git top-level via an
    # owner checkout.
    worktree = cwd.resolve()
    owner_root = Path(os.environ.get(OWNER_ROOT_ENV, root.as_posix())).resolve()
    def matching_states(state_root: Path) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for item in _all_states(state_root):
            attempt = item.get("job_attempt")
            if not isinstance(attempt, dict) or attempt.get("worktree") != worktree.as_posix():
                continue
            if item.get("session_id") == session_id or attempt.get("session_id") == session_id:
                matches.append(item)
            elif item.get("status") in {"fresh-session-in-progress", "resume-in-progress"} and not item.get("session_id") and not attempt.get("session_id"):
                # This is the first authoritative identity boundary for a launched job.
                matches.append(item)
        return matches

    candidates = matching_states(owner_root)
    # A direct invocation has no detached-owner transport.  Do not let an
    # inherited owner-root variable hide its local exact attempt.
    if not candidates and owner_root != root:
        owner_root = root
        candidates = matching_states(owner_root)
    if len(candidates) != 1:
        raise LoopError("job-result-session-ambiguous", "job result requires exactly one bound owning session")
    state = candidates[0]
    attempt = state["job_attempt"]
    if attempt.get("result_recorded"):
        raise LoopError("job-result-duplicate", "job result was already recorded for this exact launch")
    if state.get("session_id") not in {"", session_id} or attempt.get("session_id") not in {"", session_id}:
        raise LoopError("job-result-session-mismatch", "job result session does not match the launched job")
    state["session_id"] = session_id
    attempt["session_id"] = session_id
    state["terminal_result"] = {
        "kind": "agentic-workspace/chatgpt-review-job-result/v1",
        "pr_number": int(state["pr_number"]), "session_id": session_id,
        "attempt_id": attempt["id"], "mode": attempt["mode"],
        "worktree": worktree.as_posix(), "starting_head": attempt["starting_head"],
        "ending_head": _git_value(worktree, runner, "rev-parse", "HEAD"),
        "launch_identity": attempt["launch_identity"],
        "proof_status": proof_status, "proof_commands": [proof_command] if proof_command else [],
        "proof_exit_code": proof_exit_code, "push_status": push_status,
        "reported_at": datetime.now(timezone.utc).isoformat(),
    }
    attempt["result_recorded"] = True
    _save_state(owner_root, state)
    return state["terminal_result"]


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
        ["gh", "pr", "list", "--state", "open", "--limit", "100", "--json", "number,state,headRefName,headRefOid,body,comments,url,mergeable,mergeStateStatus,statusCheckRollup"],
        cwd=root,
    )
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise LoopError("pr-list-invalid", "gh returned an invalid open PR list")
    return sorted(payload, key=lambda item: int(item.get("number", 0)))


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
    checkout_branch = _git_value(root, runner, "branch", "--show-current")
    detached_owner_handoff = existing_only and bool(os.environ.get(OWNER_ROOT_ENV)) and not checkout_branch
    owner_root = Path(os.environ.get(OWNER_ROOT_ENV, root.as_posix()) if detached_owner_handoff else root).resolve()
    branch = os.environ.get(OWNER_BRANCH_ENV, "") if detached_owner_handoff else checkout_branch
    head = _git_value(root, runner, "rev-parse", "HEAD")
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
    # Opt-in is the local, exact-session state written below. Posting a remote
    # marker comment made routine watcher setup visible and noisy on PRs.
    opted_in = False
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
    attempt = state.get("job_attempt")
    if isinstance(attempt, dict) and not attempt.get("session_id"):
        # A Stop hook gives the fresh job's identity before any later completion
        # transition can observe its handoff.
        attempt["session_id"] = session_id
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
        if "aw-chatgpt-review" not in body:
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


def _system_trigger(payload: dict[str, Any], *, pr: int, head: str) -> Review | None:
    """Return one deterministic actionable CI/conflict trigger for this head."""
    findings: list[str] = []
    if str(payload.get("mergeable", "")).upper() == "CONFLICTING" or str(payload.get("mergeStateStatus", "")).upper() == "DIRTY":
        findings.append("The PR has merge conflicts. Rebase or merge the base branch, resolve the conflicts, run the relevant proof, and push the result.")
    failed = {"FAILURE", "FAILED", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"}
    for check in payload.get("statusCheckRollup", []):
        if not isinstance(check, dict) or str(check.get("conclusion", "")).upper() not in failed:
            continue
        name = str(check.get("name") or check.get("context") or "unnamed check")
        conclusion = str(check.get("conclusion")).lower()
        details = str(check.get("detailsUrl") or check.get("url") or "")
        findings.append(f"CI check `{name}` concluded `{conclusion}`.{(' Inspect ' + details + '.') if details else ''}")
    if not findings:
        return None
    text = "\n".join(findings)
    fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return Review(comment_id=f"system:{fingerprint}", pr=pr, head=head, decision="blocked", findings=text, url="")


AUTO_RECOVERY_EVENTS = frozenset(
    {
        "resume-failed",
        "resume-ended-without-new-handoff",
        "orphaned-resume",
        "orphaned-fresh-session",
        "fresh-session-unbound",
        "worktree-create-failed",
        "orphan-worktree-cleanup-failed",
    }
)


def _queue_automatic_recovery(state: dict[str, Any], root: Path, *, review_key: str = "") -> bool:
    """Re-arm one recoverable failed job for the global serial dispatcher.

    A bound job resumes the exact durable Codex session; an unbound fresh job
    receives one replacement session after its owned worktree is retired. Either
    may retry the claimed review only once: the review key is recorded before
    re-arming, and all other recovery-required states remain human-only.
    """
    key = review_key or str(state.get("recovery_review_key", ""))
    if not _automatic_recovery_available(state, review_key=key):
        return False
    recovered = state.setdefault("automatic_recovery_reviews", [])
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


def _automatic_recovery_available(state: dict[str, Any], *, review_key: str = "") -> bool:
    key = review_key or str(state.get("recovery_review_key", ""))
    return bool(
        state.get("status") == "recovery-required"
        and state.get("last_event") in AUTO_RECOVERY_EVENTS
        and key
        and key not in state.get("automatic_recovery_reviews", [])
    )


def _select_serial_candidate(
    recovery_candidates: list[tuple[dict[str, Any], Review]], candidates: list[tuple[dict[str, Any], Review]]
) -> tuple[dict[str, Any], Review] | None:
    """Keep a bounded recovery at the head of the one-job serial lane."""
    queue = recovery_candidates or candidates
    return queue[0] if queue else None


def _recover(state: dict[str, Any], root: Path, *, event: str, recovery: str) -> dict[str, Any]:
    state.update(status="recovery-required", last_event=event, recovery=recovery)
    _save_state(root, state)
    return {"pr_number": state["pr_number"], "status": "recovery-required", "event": event, "recovery": recovery}


def _review_prompt(review: Review, *, branch: str = "") -> str:
    source = "external review" if not review.comment_id.startswith("system:") else "PR CI or mergeability"
    return (
        f"{source} found actionable blockers for PR #{review.pr} at exact head {review.head}.\n\n"
        f"Source: {review.url or review.comment_id}\n\n"
        f"Required work:\n{review.findings}\n\n"
        f"{'You are detached: push with git push origin HEAD:' + branch + '. ' if branch else ''}Address these findings, run the appropriate proof, push a new head, and let the repo Stop hook record the next handoff. "
        "After proof and push, record their exact outcomes with `python tools/chatgpt_review_loop.py job-result --session-id $CODEX_THREAD_ID --proof-status passed|failed --proof-command \"<command>\" --proof-exit-code <exit> --push-status passed|failed`. Do not merge from this continuation."
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


def _prepare_owned_worktree(worktree: Path, state: dict[str, Any], runner: CommandRunner) -> None:
    """Reuse the PR-owned checkout at the exact handoff head.

    The dispatcher owns this worktree for the full lifetime of the open PR.  In
    particular, a resume must not create a throwaway checkout or inspect the
    owner's branch checkout to find its commit.
    """
    if not worktree.is_dir():
        raise LoopError("owned-worktree-missing", f"recorded worktree is missing: {worktree}")
    expected_head = str(state["handoff_head"])
    if _git_value(worktree, runner, "rev-parse", "HEAD") == expected_head:
        return
    updated = runner.run(["git", "checkout", "--detach", expected_head], cwd=worktree)
    if updated.returncode:
        raise LoopError(
            "owned-worktree-update-failed",
            updated.stderr.strip() or f"could not update owned worktree to recorded handoff {expected_head}",
        )


def poll_one(
    root: Path,
    state: dict[str, Any],
    *,
    runner: CommandRunner,
    codex_command: str,
    bypass_hook_trust: bool = False,
    state_root: Path | None = None,
    isolated_worktree: bool = False,
    owned_worktree: Path | None = None,
) -> dict[str, Any]:
    owner_root = state_root or root
    pr = int(state["pr_number"])
    if state.get("status") != "awaiting-review":
        return {"pr_number": pr, "status": "no-op", "reason": f"state-is-{state.get('status', 'unknown')}"}
    state["hook_trust_mode"] = "automation-bypass" if bypass_hook_trust else "persisted-trust-required"
    _save_state(owner_root, state)
    current_branch = _git_value(root, runner, "branch", "--show-current") if not isolated_worktree else ""
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
    system_review = _system_trigger(payload, pr=pr, head=str(state["handoff_head"]))
    if system_review is not None:
        review = system_review
    elif len(matches) == 1:
        review = matches[0]
    else:
        review = None
        if review is None:
            event = "stale-review-rejected" if rejected else "review-pending"
            state.update(last_event=event, recovery="")
            _save_state(owner_root, state)
            return {"pr_number": pr, "status": "no-op", "reason": event, "rejected": rejected}
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
    state.update(status="resume-in-progress", last_event="resume-attempt-recorded", recovery="", prompt_transport=PROMPT_TRANSPORT)
    _begin_job_attempt(state, mode="resume", worktree=owned_worktree if isolated_worktree and owned_worktree else root, start_head=review.head)
    _save_state(owner_root, state)

    env = os.environ.copy()
    env["AW_CHATGPT_REVIEW_RESUME_ACTIVE"] = "1"
    worktree = root
    if isolated_worktree:
        if owned_worktree is None:
            return _recover(state, owner_root, event="owned-worktree-unavailable", recovery="restore or explicitly replace the recorded PR worktree")
        try:
            worktree = owned_worktree
            _prepare_owned_worktree(worktree, state, runner)
        except LoopError as exc:
            return _recover(state, owner_root, event=exc.code, recovery="inspect or explicitly replace the recorded PR worktree before retrying")
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
        "-",
    ]
    completed = runner.run_interactive(command, cwd=worktree, env=env, input_text=_review_prompt(review))
    latest = _load_state(owner_root, pr)
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
        _record_job_terminal(
            latest, mode="resume", worktree=worktree, start_head=review.head,
            exit_code=completed.returncode, disposition="failed", event="resume-failed", diagnostic=diagnostic,
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
        _record_job_terminal(
            latest, mode="resume", worktree=worktree, start_head=review.head,
            exit_code=0, disposition="unreported", event="resume-ended-without-new-handoff",
        )
        _save_state(owner_root, latest)
        return {"pr_number": pr, "status": "recovery-required", "event": "resume-ended-without-new-handoff"}
    if not _validated_attempt_result(latest, worktree=worktree, start_head=review.head):
        latest.update(
            status="recovery-required", last_event="handoff-proof-unreported",
            recovery="the job pushed a handoff without a passed proof-and-push result; resume the exact session and report it",
        )
        _record_job_terminal(
            latest, mode="resume", worktree=worktree, start_head=review.head,
            exit_code=0, disposition="proof-unreported", event="handoff-proof-unreported",
        )
        _save_state(owner_root, latest)
        return {"pr_number": pr, "status": "recovery-required", "event": "handoff-proof-unreported"}
    _record_job_terminal(
        latest, mode="resume", worktree=worktree, start_head=review.head,
        exit_code=0, disposition="handoff-recorded", event="resume-completed",
    )
    _save_state(owner_root, latest)
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
    recovery_candidates: list[tuple[dict[str, Any], Review]] = []
    for payload in _open_prs(root, runner):
        pr = int(payload.get("number", 0))
        head = str(payload.get("headRefOid", ""))
        if pr < 1 or not re.fullmatch(r"[0-9a-f]{40}", head):
            continue
        entry = entries.get(str(pr))
        if isinstance(entry, dict) and _state_path(root, pr).is_file():
            existing = _load_state(root, pr)
            prior_head = str(existing.get("handoff_head", ""))
            if prior_head and prior_head != head and existing.get("branch") == payload.get("headRefName"):
                if existing.get("last_event") == "fresh-session-unbound":
                    # The completed fresh process pushed without recording a
                    # session/result. Its old review is stale, so do not replay
                    # it; retire only the owned checkout and let a new-head
                    # review create a normal fresh session later.
                    worktree = Path(str(entry.get("worktree", "")))
                    if worktree.is_dir():
                        removed = runner.run(["git", "worktree", "remove", "--force", worktree.as_posix()], cwd=root)
                        if removed.returncode:
                            existing.update(
                                status="recovery-required",
                                last_event="orphan-fresh-worktree-cleanup-failed",
                                recovery="inspect or explicitly remove the orphaned fresh worktree before retrying",
                            )
                            _save_state(root, existing)
                            continue
                    retired_attempts = registry.setdefault("retired_attempts", [])
                    if isinstance(retired_attempts, list):
                        retired_attempts.append(
                            {"pr_number": pr, "old_head": prior_head, "new_head": head, "terminal_result": existing.get("terminal_result", {})}
                        )
                    _state_path(root, pr).unlink(missing_ok=True)
                    entries.pop(str(pr), None)
                    _save_dispatch(root, registry)
                    entry = None
                    continue
                # A remote movement is diagnostic evidence only.  It cannot
                # advance a handoff without the exact launch's validated result.
                existing.update(
                    status="recovery-required",
                    last_event="remote-head-observed-without-result",
                    recovery="remote head changed without a validated exact-attempt result; inspect the recorded job and explicitly recover",
                )
                _save_state(root, existing)
        matches, rejected = parse_reviews(_comments_from_pr(payload), expected_pr=pr, expected_head=head)
        if any(item["reason"] != "stale-head" for item in rejected) or len(matches) > 1:
            continue
        review = _system_trigger(payload, pr=pr, head=head) or (matches[0] if matches else None)
        if review is None or review.decision != "blocked" or not review.findings:
            continue
        if isinstance(entry, dict) and _state_path(root, pr).is_file():
            # A completed or exhausted session must release the global serial
            # slot. A recoverable failed resume gets exactly one automatic
            # recovery job; other recovery states remain explicitly human-owned.
            existing = _load_state(root, pr)
            if existing.get("status") == "recovery-required" and existing.get("prompt_transport") != PROMPT_TRANSPORT:
                # Every argv-based multiline prompt on Windows was truncated.
                # Rearm that invalid history once under the durable stdin
                # transport without charging the PR's cycle/repetition budget.
                existing.update(
                    status="awaiting-review",
                    last_event="legacy-prompt-transport-rearmed",
                    recovery="",
                    prompt_transport=PROMPT_TRANSPORT,
                    cycles=0,
                    blocker_fingerprints={},
                    handled_reviews=[item for item in existing.get("handled_reviews", []) if item != review.key],
                    automatic_recovery_reviews=[
                        item for item in existing.get("automatic_recovery_reviews", []) if item != review.key
                    ],
                )
                _save_state(root, existing)
            if existing.get("status") == "resume-in-progress":
                # Acquiring the dispatcher lock proves no review job is still
                # running. Recover an attempt orphaned by watcher termination.
                existing.update(
                    status="recovery-required",
                    last_event="orphaned-resume",
                    recovery="the watcher will launch one recovery resume for the interrupted job",
                    recovery_review_key=review.key,
                )
                attempt = existing.get("job_attempt") if isinstance(existing.get("job_attempt"), dict) else {}
                _record_job_terminal(
                    existing, mode="resume", worktree=Path(str(attempt.get("worktree") or entry.get("worktree"))),
                    start_head=str(attempt.get("starting_head") or existing.get("handoff_head", "")),
                    exit_code=-1, disposition="interrupted", event="orphaned-resume",
                    diagnostic="dispatcher lock reclaimed after an interrupted resume",
                )
                _save_state(root, existing)
            if existing.get("status") == "fresh-session-in-progress":
                # A fresh job has no session identity until its Stop hook binds
                # one.  Once the dispatcher lock has been reclaimed, that job
                # is orphaned: retire its owned worktree and permit exactly one
                # replacement fresh job for the same review.
                if review.key in existing.get("automatic_recovery_reviews", []):
                    existing.update(
                        status="recovery-required",
                        last_event="orphaned-fresh-session-recovery-exhausted",
                        recovery="the replacement fresh job was also interrupted; inspect or explicitly recover the recorded worktree",
                        recovery_review_key=review.key,
                    )
                else:
                    existing.update(
                        status="recovery-required",
                        last_event="orphaned-fresh-session",
                        recovery="the watcher will retire the orphaned fresh worktree and launch one replacement fresh job",
                        recovery_review_key=review.key,
                        recovery_mode="fresh",
                    )
                attempt = existing.get("job_attempt") if isinstance(existing.get("job_attempt"), dict) else {}
                _record_job_terminal(
                    existing, mode="fresh", worktree=Path(str(attempt.get("worktree") or entry.get("worktree"))),
                    start_head=str(attempt.get("starting_head") or existing.get("handoff_head", "")),
                    exit_code=-1, disposition="interrupted", event=str(existing["last_event"]),
                    diagnostic="dispatcher lock reclaimed after an interrupted fresh launch",
                )
                _save_state(root, existing)
            if existing.get("status") == "recovery-required":
                if not _automatic_recovery_available(existing, review_key=review.key):
                    continue
                # Preserve the serial lane for a bounded recovery.  Stacked PRs
                # may have lower-numbered sibling reviews, but they must not
                # delay the exact session that just ended without a handoff.
                recovery_candidates.append((payload, review))
                continue
            elif existing.get("status") != "awaiting-review":
                continue
        candidates.append((payload, review))
    selected = _select_serial_candidate(recovery_candidates, candidates)
    if selected is None:
        return {"status": "no-op", "reason": "no-eligible-blocked-review", "retired": retired}

    payload, review = selected
    pr = int(payload["number"])
    entry = entries.get(str(pr))
    fresh_recovery_reviews: list[str] = []
    if isinstance(entry, dict):
        worktree = Path(str(entry.get("worktree", "")))
        state_path = _state_path(root, pr)
        if state_path.is_file():
            state = _load_state(root, pr)
            if state.get("status") == "recovery-required" and not _queue_automatic_recovery(
                state, root, review_key=review.key
            ):
                return {"status": "no-op", "reason": "automatic-recovery-unavailable", "pr_number": pr}
            state = _load_state(root, pr)
            if state.get("recovery_mode") == "fresh":
                # No exact session exists to resume.  Remove this dispatcher-
                # owned checkout before creating the single bounded replacement
                # below; retain the recovery budget on the new durable state.
                if worktree.is_dir():
                    removed = runner.run(["git", "worktree", "remove", "--force", worktree.as_posix()], cwd=root)
                    if removed.returncode:
                        return _recover(
                            state,
                            root,
                            event="orphan-fresh-worktree-cleanup-failed",
                            recovery="inspect or explicitly remove the orphaned fresh worktree before retrying",
                        )
                fresh_recovery_reviews = list(state.get("automatic_recovery_reviews", []))
                state_path.unlink(missing_ok=True)
                entries.pop(str(pr), None)
                _save_dispatch(root, registry)
                entry = None
            else:
                _emit({"kind": STATE_KIND, "status": "job-started", "pr_number": pr, "mode": "resume"})
                result = poll_one(
                    root,
                    state,
                    runner=runner,
                    codex_command=codex_command,
                    bypass_hook_trust=bypass_hook_trust,
                    isolated_worktree=True,
                    owned_worktree=worktree,
                )
                return {"status": "dispatched", "pr_number": pr, "mode": "resume", "result": result}
        if entry is not None:
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
    fresh_state = {
        "kind": STATE_KIND, "repo_root": root.as_posix(), "repository": _repo_slug(root, runner),
        "pr_number": pr, "pr_url": str(payload.get("url", "")), "branch": branch,
        "handoff_head": review.head, "session_id": "", "max_cycles": max_cycles,
        "max_repeated_blockers": max_repeated_blockers, "handled_reviews": [],
        "blocker_fingerprints": {}, "cycles": 0, "status": "fresh-session-in-progress",
        "last_event": "fresh-session-bound", "recovery": "", "prompt_transport": PROMPT_TRANSPORT,
        "automatic_recovery_reviews": fresh_recovery_reviews,
    }
    _begin_job_attempt(fresh_state, mode="fresh", worktree=worktree, start_head=review.head)
    _save_state(root, fresh_state)
    entries[str(pr)] = {"worktree": worktree.as_posix(), "branch": branch, "repository": _repo_slug(root, runner)}
    _save_dispatch(root, registry)
    _emit({"kind": STATE_KIND, "status": "job-started", "pr_number": pr, "mode": "fresh"})
    command = [
        *shlex.split(codex_command),
        "-C",
        worktree.as_posix(),
        "exec",
        *(["--dangerously-bypass-hook-trust"] if bypass_hook_trust else []),
        "-",
    ]
    env = os.environ.copy()
    env["AW_CHATGPT_REVIEW_RESUME_ACTIVE"] = "1"
    env[OWNER_ROOT_ENV] = root.as_posix()
    env[OWNER_BRANCH_ENV] = branch
    completed = runner.run_interactive(command, cwd=worktree, env=env, input_text=prompt)
    if completed.returncode:
        bound = _load_state(root, pr)
        diagnostic = (completed.stderr or completed.stdout).strip()[-2000:]
        bound.update(
            status="recovery-required",
            last_event="fresh-session-failed",
            recovery="fresh Codex session failed; inspect the exact job and explicitly recover or clean up before redispatching this review",
            fresh_exit_code=completed.returncode,
            fresh_diagnostic=diagnostic,
        )
        _record_job_terminal(
            bound, mode="fresh", worktree=worktree, start_head=review.head,
            exit_code=completed.returncode, disposition="failed", event="fresh-session-failed", diagnostic=diagnostic,
        )
        _save_state(root, bound)
        _save_dispatch(root, registry)
        return {"status": "recovery-required", "pr_number": pr, "event": "fresh-session-failed"}
    bound = _load_state(root, pr)
    session_id = str(bound.get("session_id", "")).strip()
    if not session_id:
        bound.update(
            status="recovery-required",
            last_event="fresh-session-unbound",
            recovery="the watcher will retire the completed unbound fresh worktree and launch one replacement session for this exact review",
            recovery_review_key=review.key,
            recovery_mode="fresh",
        )
        _record_job_terminal(
            bound, mode="fresh", worktree=worktree, start_head=review.head,
            exit_code=0, disposition="unbound", event="fresh-session-unbound",
        )
        _save_state(root, bound)
        _save_dispatch(root, registry)
        return {"status": "recovery-required", "pr_number": pr, "event": "fresh-session-unbound"}
    updated = _converged_pr_view(root, runner, pr=pr, previous_head=review.head)
    new_head = str(updated.get("headRefOid", ""))
    if new_head == review.head:
        # A fresh Codex session may finish before it pushes.  Preserve that exact
        # session and the reviewed head so the next serial dispatch resumes it
        # instead of suppressing this PR forever.
        state = bound
        state.update(handoff_head=review.head, session_id=session_id, status="awaiting-review", last_event="fresh-session-awaiting-resume", recovery="")
        _record_job_terminal(
            state, mode="fresh", worktree=worktree, start_head=review.head,
            exit_code=0, disposition="awaiting-resume", event="fresh-session-awaiting-resume",
        )
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
    state = bound
    if state.get("handoff_head") != new_head or not _validated_attempt_result(state, worktree=worktree, start_head=review.head):
        state.update(status="recovery-required", last_event="fresh-handoff-proof-unreported", recovery="the fresh job must record one passed proof-and-push result before its handoff can advance")
        _record_job_terminal(state, mode="fresh", worktree=worktree, start_head=review.head, exit_code=0, disposition="proof-unreported", event="fresh-handoff-proof-unreported")
        _save_state(root, state)
        _save_dispatch(root, registry)
        return {"status": "recovery-required", "pr_number": pr, "event": "fresh-handoff-proof-unreported"}
    state.update(handoff_head=new_head, session_id=session_id, handled_reviews=[review.key], cycles=1, status="awaiting-review", last_event="fresh-handoff-recorded", recovery="")
    _record_job_terminal(
        state, mode="fresh", worktree=worktree, start_head=review.head,
        exit_code=0, disposition="handoff-recorded", event="fresh-handoff-recorded",
    )
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


def reset_open_pr_cycles(root: Path, runner: CommandRunner) -> list[int]:
    """Reset per-PR attempt and repetition budgets without changing job ownership."""
    open_prs = {int(item["number"]) for item in _open_prs(root, runner) if int(item.get("number", 0)) > 0}
    reset: list[int] = []
    for pr in sorted(open_prs):
        if not _state_path(root, pr).is_file():
            continue
        state = _load_state(root, pr)
        state.update(
            cycles=0,
            blocker_fingerprints={},
            automatic_recovery_reviews=[],
            last_budget_reset_at=datetime.now(timezone.utc).isoformat(),
        )
        _save_state(root, state)
        reset.append(pr)
    return reset


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

    result_parser = sub.add_parser("job-result", help="Record proof and push evidence for one bound review job.")
    result_parser.add_argument("--target", type=Path, default=Path.cwd())
    result_parser.add_argument("--session-id", default=os.environ.get("CODEX_THREAD_ID", ""))
    result_parser.add_argument("--proof-status", choices=["passed", "failed"], required=True)
    result_parser.add_argument("--proof-command", default="")
    result_parser.add_argument("--proof-exit-code", type=int, required=True)
    result_parser.add_argument("--push-status", choices=["passed", "failed"], required=True)

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
    poll_parser.add_argument("--console-output", action="store_true", help="Bind watcher events to the allocated Windows console.")
    poll_parser.add_argument("--codex-command", default=os.environ.get("AW_CHATGPT_REVIEW_CODEX", DEFAULT_CODEX_COMMAND))
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
    recover_parser.add_argument(
        "--action",
        choices=["continue-waiting", "replace-worktree"],
        required=True,
        help="Rearm the session, or retire its owned checkout so the next dispatch starts a replacement session.",
    )
    reset_parser = sub.add_parser("reset-cycles", help="Reset attempt and repetition budgets for every open PR.")
    reset_parser.add_argument("--target", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None, *, runner: CommandRunner | None = None) -> int:
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    if effective_argv[:1] == ["_console-run"]:
        return _console_run(effective_argv[1:])
    args = _parser().parse_args(effective_argv)
    runner = runner or CommandRunner()
    try:
        if args.command == "poll":
            if args.console_output:
                _configure_console_output()
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
        if args.command == "job-result":
            result = report_job_result(
                cwd=args.target.resolve(), session_id=args.session_id.strip(), proof_status=args.proof_status,
                proof_command=args.proof_command, proof_exit_code=args.proof_exit_code,
                push_status=args.push_status, runner=runner,
            )
            _emit(result)
            return 0

        root = _repo_root(args.target.resolve(), runner)
        if args.command == "reset-cycles":
            reset = reset_open_pr_cycles(root, runner)
            _emit({"kind": STATE_KIND, "status": "cycles-reset", "prs": reset})
            return 0
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
            if args.action == "replace-worktree":
                registry = _load_dispatch(root)
                entry = registry["prs"].get(str(args.pr))
                worktree = Path(str(entry.get("worktree", ""))).resolve() if isinstance(entry, dict) else None
                if worktree is not None and worktree.exists():
                    if worktree.name != f"pr-{args.pr}":
                        raise LoopError("unowned-worktree", f"refusing to replace unexpected worktree {worktree}")
                    removed = runner.run(["git", "worktree", "remove", "--force", worktree.as_posix()], cwd=root)
                    if removed.returncode:
                        raise LoopError(
                            "worktree-replacement-failed",
                            removed.stderr.strip() or f"could not remove worktree for PR #{args.pr}",
                        )
                registry["prs"].pop(str(args.pr), None)
                _save_dispatch(root, registry)
                _state_path(root, args.pr).unlink(missing_ok=True)
                _emit({"kind": STATE_KIND, "status": "worktree-replacement-ready", "pr_number": args.pr})
                return 0
            state.update(status="awaiting-review", last_event="human-recovery-confirmed", recovery="")
            _save_state(root, state)
            _emit({"kind": STATE_KIND, "status": "awaiting-review", "pr_number": args.pr})
            return 0

        polls = args.max_polls if args.watch else 1
        if polls < 1 or args.interval < 1 or args.max_cycles < 1 or args.max_repeated_blockers < 1:
            raise LoopError("invalid-limit", "poll limits and interval must be positive")
        try:
            _validate_codex_launch_command(shlex.split(args.codex_command))
        except ValueError as exc:
            raise LoopError(
                "codex-command-invalid",
                f"--codex-command is not valid shell syntax: {exc}",
                recovery="Set AW_CHATGPT_REVIEW_CODEX to the pinned 5.5 command or pass --codex-command explicitly.",
            ) from exc
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
