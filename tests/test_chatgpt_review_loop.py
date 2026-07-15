from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "chatgpt_review_loop.py"
_SPEC = importlib.util.spec_from_file_location("chatgpt_review_loop", _SCRIPT)
assert _SPEC and _SPEC.loader
loop = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = loop
_SPEC.loader.exec_module(loop)


HEAD_A = "a" * 40
HEAD_B = "b" * 40
SESSION = "11111111-1111-1111-1111-111111111111"


def marker(*, pr: int = 12, head: str = HEAD_A, decision: str = "blocked") -> str:
    return f"<!-- aw-chatgpt-review pr={pr} head={head} policy=pr-review-recheck-v1 decision={decision} -->"


def test_windows_command_resolution_uses_pathed_shell_shim(monkeypatch) -> None:
    monkeypatch.setattr(loop.shutil, "which", lambda command: "tools/codex.CMD" if command == "codex" else None)

    assert loop._resolved_command(["codex", "exec", "resume"], windows=True) == [
        "tools/codex.CMD",
        "exec",
        "resume",
    ]
    assert loop._resolved_command(["tools/codex.exe", "exec"], windows=True)[0] == "tools/codex.exe"


def test_command_runner_decodes_output_as_utf8(tmp_path: Path, monkeypatch) -> None:
    observed = {}

    def fake_run(command, **kwargs):
        observed.update(kwargs)
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(loop.subprocess, "run", fake_run)

    completed = loop.CommandRunner().run(["gh", "version"], cwd=tmp_path)

    assert completed.stdout == "ok"
    assert observed["encoding"] == "utf-8"
    assert observed["errors"] == "replace"


def test_interactive_codex_job_uses_a_background_console_on_windows(tmp_path: Path, monkeypatch) -> None:
    observed = {}

    def fake_run(command, **kwargs):
        observed["command"] = command
        observed.update(kwargs)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(loop.subprocess, "run", fake_run)

    completed = loop.CommandRunner().run_interactive(["codex", "exec", "-"], cwd=tmp_path, input_text="line one\nline two")

    assert completed.returncode == 0
    assert observed["input"] == "line one\nline two"
    if loop.os.name == "nt":
        assert observed["command"][:3] == [loop.sys.executable, str(loop.Path(loop.__file__).resolve()), "_console-run"]
        assert loop.Path(observed["command"][-3]).stem.lower() == "codex"
        assert observed["command"][-2:] == ["exec", "-"]
        assert observed["creationflags"] & loop.subprocess.CREATE_NEW_CONSOLE
        assert observed["startupinfo"].wShowWindow == getattr(loop.subprocess, "SW_SHOWMINNOACTIVE", 7)
        assert observed["close_fds"] is True


def test_watcher_console_output_rebinds_stdout_and_stderr(monkeypatch) -> None:
    stream = io.StringIO()
    monkeypatch.setattr(loop, "open", lambda *args, **kwargs: stream, raising=False)
    old_stdout, old_stderr, old_compact = loop.sys.stdout, loop.sys.stderr, loop._COMPACT_CONSOLE
    try:
        loop._configure_console_output(windows=True)
        assert loop.sys.stdout is stream
        assert loop.sys.stderr is stream
    finally:
        loop.sys.stdout, loop.sys.stderr = old_stdout, old_stderr
        loop._COMPACT_CONSOLE = old_compact


def test_compact_console_suppresses_noop_poll_and_summarizes_jobs() -> None:
    assert loop._compact_console_event(
        {"status": "poll-complete", "poll": 7, "results": [{"status": "no-op", "reason": "no-eligible-blocked-review"}]}
    ).endswith(" poll #7 idle")
    message = loop._compact_console_event(
        {
            "status": "poll-complete",
            "results": [
                {
                    "status": "dispatched",
                    "pr_number": 12,
                    "mode": "resume",
                    "result": {"status": "recovery-required", "event": "resume-ended-without-new-handoff"},
                }
            ],
        }
    )
    assert "PR #12 job ended: resume-ended-without-new-handoff" in message


def test_console_job_output_keeps_agent_messages_and_collapses_tool_transcripts() -> None:
    assert loop._console_job_output(
        [
            "codex\n",
            "I will inspect the watcher.\n",
            "exec\n",
            '"pwsh" -Command "Get-Content tools/chatgpt_review_loop.py"\n',
            "very large command output that must not be printed\n",
            "codex\n",
            "The command succeeded.\n",
        ]
    ) == [
        "codex",
        "I will inspect the watcher.",
        '[tool] "pwsh" -Command "Get-Content tools/chatgpt_review_loop.py"',
        "codex",
        "The command succeeded.",
    ]


class FakeRunner(loop.CommandRunner):
    def __init__(self, root: Path, *, comments: list[dict] | None = None) -> None:
        self.root = root
        self.branch = "codex/issue-2290"
        self.head = HEAD_A
        self.pr_head = HEAD_A
        self.pr_heads: list[str] = []
        self.pr_branch = self.branch
        self.pr_state = "OPEN"
        self.comments = comments or []
        self.commands: list[list[str]] = []
        self.codex_exit = 0
        self.next_handoff_head = ""
        self.next_job_result: dict[str, object] | None = None
        self.next_review_decision = ""
        self.interactive_inputs: list[str] = []

    def run(self, command, *, cwd, env=None):
        command = list(command)
        self.commands.append(command)
        if command[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(command, 0, str(self.root), "")
        if command[:3] == ["git", "branch", "--show-current"]:
            return subprocess.CompletedProcess(command, 0, self.branch, "")
        if command[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(command, 0, self.head, "")
        if command[:3] == ["git", "worktree", "remove"]:
            path = Path(command[-1])
            if path.exists():
                path.rmdir()
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[:3] == ["gh", "repo", "view"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"nameWithOwner": "owner/repo"}), "")
        if command[:3] == ["gh", "pr", "view"]:
            pr_head = self.pr_heads.pop(0) if self.pr_heads else self.pr_head
            payload = {
                "number": 12,
                "state": self.pr_state,
                "headRefName": self.pr_branch,
                "headRefOid": pr_head,
                "body": "",
                "comments": self.comments,
                "url": "https://example.test/pr/12",
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if command[:3] == ["gh", "pr", "comment"]:
            self.comments.append({"databaseId": 1, "body": loop.OPT_IN_MARKER, "url": "https://example.test/c/1"})
            return subprocess.CompletedProcess(command, 0, "", "")
        if "resume" in command:
            assert env and env["AW_CHATGPT_REVIEW_RESUME_ACTIVE"] == "1"
            if self.next_handoff_head:
                state = loop._load_state(self.root, 12)
                state.update(handoff_head=self.next_handoff_head, status="awaiting-review", last_event="handoff-recorded")
                loop._save_state(self.root, state)
                self.pr_head = self.next_handoff_head
                self.head = self.next_handoff_head
                if self.next_job_result:
                    loop.report_job_result(
                        cwd=self.root,
                        session_id=SESSION,
                        proof_status=str(self.next_job_result["proof_status"]),
                        proof_command=str(self.next_job_result["proof_command"]),
                        proof_exit_code=int(self.next_job_result["proof_exit_code"]),
                        push_status=str(self.next_job_result["push_status"]),
                        runner=self,
                    )
                if self.next_review_decision:
                    self.comments = [
                        {
                            "id": "IC_next_head",
                            "body": marker(head=self.next_handoff_head, decision=self.next_review_decision),
                            "url": "https://example.test/c/next",
                        }
                    ]
            return subprocess.CompletedProcess(command, self.codex_exit, "", "failed" if self.codex_exit else "")
        raise AssertionError(f"unexpected command: {command}")

    def run_interactive(self, command, *, cwd, env=None, input_text=""):
        self.interactive_inputs.append(input_text)
        if "resume" in command:
            return self.run(command, cwd=cwd, env=env)
        command = list(command)
        self.commands.append(command)
        existing = loop._load_state(self.root, 12)
        existing.update(session_id="fresh-session", status="awaiting-review", last_event="handoff-noop")
        loop._save_state(self.root, existing)
        return subprocess.CompletedProcess(command, self.codex_exit, "", "failed" if self.codex_exit else "")


def state(root: Path, **updates) -> dict:
    payload = {
        "kind": loop.STATE_KIND,
        "repo_root": root.as_posix(),
        "repository": "owner/repo",
        "pr_number": 12,
        "pr_url": "https://example.test/pr/12",
        "branch": "codex/issue-2290",
        "handoff_head": HEAD_A,
        "session_id": SESSION,
        "status": "awaiting-review",
        "handled_reviews": [],
        "blocker_fingerprints": {},
        "cycles": 0,
        "max_cycles": 3,
        "max_repeated_blockers": 2,
        "last_event": "handoff-recorded",
        "recovery": "",
    }
    payload.update(updates)
    loop._save_state(root, payload)
    return payload


def passed_result(runner: FakeRunner) -> None:
    runner.next_job_result = {"proof_status": "passed", "proof_command": "pytest -q", "proof_exit_code": 0, "push_status": "passed"}


def test_marker_parser_accepts_only_exact_pr_and_full_sha() -> None:
    comments = [
        {"id": "IC_exact", "body": f"Fix A\n{marker()}", "url": "u1"},
        {"databaseId": 2, "body": f"Old\n{marker(head=HEAD_B)}", "url": "u2"},
        {"databaseId": 3, "body": "<!-- aw-chatgpt-review pr=12 head=abc decision=blocked -->", "url": "u3"},
        {"databaseId": 4, "body": f"Wrong PR\n{marker(pr=13)}", "url": "u4"},
    ]

    matches, rejected = loop.parse_reviews(comments, expected_pr=12, expected_head=HEAD_A)

    assert [(item.comment_id, item.findings) for item in matches] == [("IC_exact", "Fix A")]
    assert {item["reason"] for item in rejected} == {"stale-head", "malformed-or-multiple-markers", "pr-mismatch"}


def test_fresh_session_json_requires_one_durable_identity() -> None:
    assert loop._session_id_from_jsonl('{"type":"thread.started","thread_id":"fresh-12"}\n') == "fresh-12"
    with pytest.raises(loop.LoopError, match="did not report one session"):
        loop._session_id_from_jsonl('{"session_id":"one"}\n{"thread_id":"two"}\n')


def test_resume_reuses_owned_worktree_and_updates_it_to_recorded_handoff(tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path)
    existing = state(tmp_path, handoff_head=HEAD_A, cycles=1)
    worktree = tmp_path / "worktrees" / "pr-12"
    worktree.mkdir(parents=True)
    runner.head = HEAD_B
    original_run = runner.run

    def run(command, *, cwd, env=None):
        command = list(command)
        if command[:3] == ["git", "checkout", "--detach"]:
            runner.commands.append(command)
            assert cwd == worktree
            assert command[-1] == HEAD_A
            return subprocess.CompletedProcess(command, 0, "", "")
        return original_run(command, cwd=cwd, env=env)

    runner.run = run

    loop._prepare_owned_worktree(worktree, existing, runner)

    assert runner.commands[-1] == ["git", "checkout", "--detach", HEAD_A]
    assert not any(command[:3] == ["git", "worktree", "add"] for command in runner.commands)


def test_explicit_worktree_replacement_retires_owned_checkout_and_state(tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path)
    state(tmp_path, status="recovery-required", last_event="owned-worktree-missing")
    worktree = tmp_path / "worktrees" / "pr-12"
    worktree.mkdir(parents=True)
    loop._save_dispatch(tmp_path, {"kind": loop.STATE_KIND, "prs": {"12": {"worktree": worktree.as_posix()}}})

    assert loop.main(["recover", "--target", tmp_path.as_posix(), "--pr", "12", "--action", "replace-worktree"], runner=runner) == 0

    assert not worktree.exists()
    assert not loop._state_path(tmp_path, 12).exists()
    assert loop._load_dispatch(tmp_path)["prs"] == {}


def test_global_dispatch_does_not_start_when_no_exact_blocked_review(tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path, comments=[{"id": "old", "body": marker(head=HEAD_B), "url": "u"}])
    original_run = runner.run

    def run(command, *, cwd, env=None):
        if list(command)[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    [
                        {
                            "number": 12,
                            "state": "OPEN",
                            "headRefName": runner.branch,
                            "headRefOid": HEAD_A,
                            "body": "",
                            "comments": runner.comments,
                            "url": "https://example.test/pr/12",
                        }
                    ]
                ),
                "",
            )
        return original_run(command, cwd=cwd, env=env)

    runner.run = run
    result = loop.dispatch_all(
        tmp_path,
        runner=runner,
        codex_command="codex",
        worktree_root=tmp_path / "worktrees",
        max_cycles=3,
        max_repeated_blockers=2,
    )

    assert result == {"status": "no-op", "reason": "no-eligible-blocked-review", "retired": []}
    assert not any(command[:3] == ["git", "worktree", "add"] for command in runner.commands)


def test_global_dispatch_refuses_a_live_concurrent_job(tmp_path: Path, monkeypatch) -> None:
    lock = tmp_path / loop.STATE_RELATIVE / "dispatch.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("123", encoding="utf-8")
    monkeypatch.setattr(loop, "_process_is_running", lambda pid: pid == 123)

    result = loop.dispatch_all(
        tmp_path,
        runner=FakeRunner(tmp_path),
        codex_command="codex",
        worktree_root=tmp_path / "worktrees",
        max_cycles=3,
        max_repeated_blockers=2,
    )

    assert result == {"status": "no-op", "reason": "dispatcher-job-in-progress"}


def test_global_dispatch_reclaims_a_dead_dispatch_lock(tmp_path: Path, monkeypatch) -> None:
    lock = tmp_path / loop.STATE_RELATIVE / "dispatch.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("123", encoding="utf-8")
    monkeypatch.setattr(loop, "_process_is_running", lambda pid: False)
    runner = FakeRunner(tmp_path)
    original_run = runner.run

    def run(command, *, cwd, env=None):
        if list(command)[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(command, 0, "[]", "")
        return original_run(command, cwd=cwd, env=env)

    runner.run = run

    result = loop.dispatch_all(
        tmp_path,
        runner=runner,
        codex_command="codex",
        worktree_root=tmp_path / "worktrees",
        max_cycles=3,
        max_repeated_blockers=2,
    )

    assert result == {"status": "no-op", "reason": "no-eligible-blocked-review", "retired": []}
    assert not lock.exists()


def test_global_dispatch_skips_pr_with_human_only_recovery(tmp_path: Path) -> None:
    review = {"id": "blocked", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    worktree = tmp_path / "worktrees" / "pr-12"
    worktree.mkdir(parents=True)
    state(tmp_path, status="recovery-required", last_event="max-cycles-exceeded", prompt_transport=loop.PROMPT_TRANSPORT)
    loop._save_dispatch(tmp_path, {"kind": loop.STATE_KIND, "prs": {"12": {"worktree": worktree.as_posix()}}})
    original_run = runner.run

    def run(command, *, cwd, env=None):
        if list(command)[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps([{"number": 12, "headRefName": runner.branch, "headRefOid": HEAD_A, "comments": [review], "url": "u"}]),
                "",
            )
        return original_run(command, cwd=cwd, env=env)

    runner.run = run
    assert (
        loop.dispatch_all(
            tmp_path, runner=runner, codex_command="codex", worktree_root=tmp_path / "worktrees", max_cycles=10, max_repeated_blockers=2
        )["reason"]
        == "no-eligible-blocked-review"
    )


@pytest.mark.parametrize(
    ("initial_status", "last_event"),
    [("recovery-required", "resume-failed"), ("resume-in-progress", "resume-attempt-recorded")],
)
def test_global_dispatch_launches_one_recovery_resume(tmp_path: Path, monkeypatch, initial_status: str, last_event: str) -> None:
    review = {"id": "blocked", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    worktree = tmp_path / "worktrees" / "pr-12"
    worktree.mkdir(parents=True)
    state(
        tmp_path,
        status=initial_status,
        last_event=last_event,
        recovery_review_key=f"12:{HEAD_A}:blocked",
        handled_reviews=[f"12:{HEAD_A}:blocked"],
        prompt_transport=loop.PROMPT_TRANSPORT,
    )
    loop._save_dispatch(tmp_path, {"kind": loop.STATE_KIND, "prs": {"12": {"worktree": worktree.as_posix()}}})
    original_run = runner.run

    def run(command, *, cwd, env=None):
        if list(command)[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps([{"number": 12, "headRefName": runner.branch, "headRefOid": HEAD_A, "comments": [review], "url": "u"}]),
                "",
            )
        return original_run(command, cwd=cwd, env=env)

    runner.run = run
    seen = {}

    def resume(root, recovered_state, **kwargs):
        seen.update(recovered_state)
        return {"pr_number": 12, "status": "resumed"}

    monkeypatch.setattr(loop, "poll_one", resume)
    result = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=tmp_path / "worktrees", max_cycles=10, max_repeated_blockers=2
    )

    assert result == {"status": "dispatched", "pr_number": 12, "mode": "resume", "result": {"pr_number": 12, "status": "resumed"}}
    assert seen["status"] == "awaiting-review"
    assert seen["handled_reviews"] == []
    assert seen["automatic_recovery_reviews"] == [f"12:{HEAD_A}:blocked"]


def test_global_scan_consumes_recovery_only_for_selected_pr(tmp_path: Path, monkeypatch) -> None:
    review_12 = {"id": "blocked-12", "body": f"Fix 12\n{marker(pr=12)}", "url": "u12"}
    review_13 = {"id": "blocked-13", "body": f"Fix 13\n{marker(pr=13)}", "url": "u13"}
    runner = FakeRunner(tmp_path)
    first = state(
        tmp_path,
        status="recovery-required",
        last_event="resume-failed",
        recovery_review_key=f"12:{HEAD_A}:blocked-12",
        handled_reviews=[f"12:{HEAD_A}:blocked-12"],
        prompt_transport=loop.PROMPT_TRANSPORT,
    )
    second = dict(first)
    second.update(
        pr_number=13,
        pr_url="https://example.test/pr/13",
        recovery_review_key=f"13:{HEAD_A}:blocked-13",
        handled_reviews=[f"13:{HEAD_A}:blocked-13"],
    )
    loop._save_state(tmp_path, second)
    loop._save_dispatch(
        tmp_path,
        {"kind": loop.STATE_KIND, "prs": {"12": {"worktree": "unused-12"}, "13": {"worktree": "unused-13"}}},
    )
    original_run = runner.run

    def run(command, *, cwd, env=None):
        if list(command)[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    [
                        {"number": 12, "headRefName": runner.branch, "headRefOid": HEAD_A, "comments": [review_12], "url": "u12"},
                        {"number": 13, "headRefName": runner.branch, "headRefOid": HEAD_A, "comments": [review_13], "url": "u13"},
                    ]
                ),
                "",
            )
        return original_run(command, cwd=cwd, env=env)

    runner.run = run
    monkeypatch.setattr(loop, "poll_one", lambda *args, **kwargs: {"pr_number": 12, "status": "resumed"})

    result = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=tmp_path / "worktrees", max_cycles=10, max_repeated_blockers=2
    )

    assert result["pr_number"] == 12
    assert loop._load_state(tmp_path, 12)["automatic_recovery_reviews"] == [f"12:{HEAD_A}:blocked-12"]
    assert loop._load_state(tmp_path, 13).get("automatic_recovery_reviews", []) == []


def test_global_dispatch_rearms_legacy_truncated_prompt_without_charging_budget(tmp_path: Path, monkeypatch) -> None:
    review = {"id": "blocked", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    state(
        tmp_path,
        status="recovery-required",
        last_event="resume-failed",
        cycles=2,
        handled_reviews=[f"12:{HEAD_A}:blocked"],
        automatic_recovery_reviews=[f"12:{HEAD_A}:blocked"],
        blocker_fingerprints={"old": 2},
    )
    loop._save_dispatch(tmp_path, {"kind": loop.STATE_KIND, "prs": {"12": {"worktree": "unused"}}})
    original_run = runner.run

    def run(command, *, cwd, env=None):
        if list(command)[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps([{"number": 12, "headRefName": runner.branch, "headRefOid": HEAD_A, "comments": [review], "url": "u"}]),
                "",
            )
        return original_run(command, cwd=cwd, env=env)

    runner.run = run
    seen = {}
    monkeypatch.setattr(
        loop,
        "poll_one",
        lambda root, recovered_state, **kwargs: seen.update(recovered_state) or {"pr_number": 12, "status": "resumed"},
    )

    loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=tmp_path / "worktrees", max_cycles=10, max_repeated_blockers=2
    )

    assert seen["prompt_transport"] == loop.PROMPT_TRANSPORT
    assert seen["cycles"] == 0
    assert seen["handled_reviews"] == []
    assert seen["automatic_recovery_reviews"] == []
    assert seen["blocker_fingerprints"] == {}


def test_global_dispatch_treats_remote_head_without_result_as_recovery_evidence(tmp_path: Path) -> None:
    old_review = {"id": "blocked", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[old_review])
    runner.pr_head = HEAD_B
    state(tmp_path, status="recovery-required", last_event="resume-ended-without-new-handoff", handoff_head=HEAD_A)
    loop._save_dispatch(tmp_path, {"kind": loop.STATE_KIND, "prs": {"12": {"worktree": "unused"}}})
    original_run = runner.run

    def run(command, *, cwd, env=None):
        if list(command)[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    [
                        {
                            "number": 12,
                            "headRefName": runner.branch,
                            "headRefOid": HEAD_B,
                            "comments": [old_review],
                            "url": "u",
                        }
                    ]
                ),
                "",
            )
        return original_run(command, cwd=cwd, env=env)

    runner.run = run

    result = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=tmp_path / "worktrees", max_cycles=10, max_repeated_blockers=2
    )

    assert result["status"] == "no-op"
    reconciled = loop._load_state(tmp_path, 12)
    assert reconciled["handoff_head"] == HEAD_A
    assert reconciled["status"] == "recovery-required"
    assert reconciled["last_event"] == "remote-head-observed-without-result"


def test_fresh_global_dispatch_fetches_and_detaches_at_reviewed_head(tmp_path: Path, monkeypatch) -> None:
    review = {"id": "fresh", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    original_run = runner.run

    def run(command, *, cwd, env=None):
        command = list(command)
        if command[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps([{"number": 12, "headRefName": runner.branch, "headRefOid": HEAD_A, "comments": [review], "url": "u"}]),
                "",
            )
        if command[:3] == ["git", "fetch", "--no-tags"]:
            runner.commands.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")
        if command == ["git", "rev-parse", "FETCH_HEAD"]:
            runner.commands.append(command)
            return subprocess.CompletedProcess(command, 0, HEAD_A, "")
        if command[:3] == ["git", "worktree", "add"]:
            runner.commands.append(command)
            Path(command[-2]).mkdir(parents=True)
            return subprocess.CompletedProcess(command, 0, "", "")
        if "exec" in command and "--json" in command:
            runner.pr_head = HEAD_B
            return subprocess.CompletedProcess(command, 0, '{"thread_id":"fresh-session"}\n', "")
        return original_run(command, cwd=cwd, env=env)

    runner.run = run
    monkeypatch.setattr(loop, "handoff", lambda **kwargs: {})
    result = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=tmp_path / "worktrees", max_cycles=3, max_repeated_blockers=2
    )

    assert result["mode"] == "fresh"
    assert ["git", "worktree", "add", "--detach"] == next(
        command[:4] for command in runner.commands if command[:3] == ["git", "worktree", "add"]
    )


def test_fresh_global_dispatch_records_per_pr_resume_state_when_no_head_is_pushed(tmp_path: Path) -> None:
    review = {"id": "fresh", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    original_run = runner.run

    def run(command, *, cwd, env=None):
        command = list(command)
        if command[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps([{"number": 12, "headRefName": runner.branch, "headRefOid": HEAD_A, "comments": [review], "url": "u"}]),
                "",
            )
        if command[:3] == ["git", "fetch", "--no-tags"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        if command == ["git", "rev-parse", "FETCH_HEAD"]:
            return subprocess.CompletedProcess(command, 0, HEAD_A, "")
        if command[:3] == ["git", "worktree", "add"]:
            Path(command[-2]).mkdir(parents=True)
            return subprocess.CompletedProcess(command, 0, "", "")
        if "exec" in command and "--json" in command:
            return subprocess.CompletedProcess(command, 0, '{"thread_id":"fresh-session"}\n', "")
        return original_run(command, cwd=cwd, env=env)

    runner.run = run
    result = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=tmp_path / "worktrees", max_cycles=10, max_repeated_blockers=2
    )

    assert result["awaiting_resume"] is True
    saved = loop._load_state(tmp_path, 12)
    assert (saved["session_id"], saved["handoff_head"], saved["cycles"], saved["max_cycles"]) == ("fresh-session", HEAD_A, 0, 10)
    assert saved["status"] == "awaiting-review"


def test_detached_fresh_stop_hook_binds_precreated_owner_state(tmp_path: Path, monkeypatch) -> None:
    runner = FakeRunner(tmp_path)
    state(tmp_path, session_id="", status="fresh-session-in-progress")
    monkeypatch.setenv(loop.OWNER_ROOT_ENV, tmp_path.as_posix())
    monkeypatch.setenv(loop.OWNER_BRANCH_ENV, runner.branch)

    result = loop.handoff(
        cwd=tmp_path,
        session_id=SESSION,
        pr=None,
        max_cycles=10,
        max_repeated_blockers=2,
        replace_session=False,
        existing_only=True,
        runner=runner,
    )

    assert result["status"] == "handoff-recorded"
    assert loop._load_state(tmp_path, 12)["session_id"] == SESSION


def test_interrupted_fresh_dispatch_is_recovered_once_then_resumes_the_recorded_session(tmp_path: Path) -> None:
    review = {"id": "fresh", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    worktree_root = tmp_path / "worktrees"
    original_run = runner.run
    attempts: list[tuple[str, Path, str]] = []

    def run(command, *, cwd, env=None):
        command = list(command)
        if command[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    [{"number": 12, "headRefName": runner.branch, "headRefOid": runner.pr_head, "comments": runner.comments, "url": "u"}]
                ),
                "",
            )
        if command[:3] == ["git", "fetch", "--no-tags"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        if command == ["git", "rev-parse", "FETCH_HEAD"]:
            return subprocess.CompletedProcess(command, 0, runner.pr_head, "")
        if command[:3] == ["git", "worktree", "add"]:
            runner.commands.append(command)
            Path(command[-2]).mkdir(parents=True)
            return subprocess.CompletedProcess(command, 0, "", "")
        return original_run(command, cwd=cwd, env=env)

    def run_interactive(command, *, cwd, env=None, input_text=""):
        command = list(command)
        mode = "resume" if "resume" in command else "fresh"
        attempts.append((mode, cwd, command[-2] if mode == "resume" else ""))
        runner.commands.append(command)
        if len(attempts) == 1:
            raise KeyboardInterrupt("watcher terminated during fresh job")
        if mode == "fresh":
            saved = loop._load_state(tmp_path, 12)
            saved.update(session_id="replacement-session", status="awaiting-review", last_event="handoff-recorded")
            loop._save_state(tmp_path, saved)
            return subprocess.CompletedProcess(command, 0, "", "")
        return original_run(command, cwd=cwd, env=env)

    runner.run = run
    runner.run_interactive = run_interactive
    with pytest.raises(KeyboardInterrupt, match="terminated"):
        loop.dispatch_all(
            tmp_path, runner=runner, codex_command="codex", worktree_root=worktree_root, max_cycles=3, max_repeated_blockers=2
        )

    assert loop._load_state(tmp_path, 12)["status"] == "fresh-session-in-progress"
    recovered = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=worktree_root, max_cycles=3, max_repeated_blockers=2
    )
    assert recovered["mode"] == "fresh"
    saved = loop._load_state(tmp_path, 12)
    assert saved["session_id"] == "replacement-session"
    assert saved["automatic_recovery_reviews"] == [f"12:{HEAD_A}:fresh"]

    runner.next_handoff_head = HEAD_B
    resumed = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=worktree_root, max_cycles=3, max_repeated_blockers=2
    )
    assert resumed["mode"] == "resume"
    assert attempts == [
        ("fresh", worktree_root / "pr-12", ""),
        ("fresh", worktree_root / "pr-12", ""),
        ("resume", worktree_root / "pr-12", "replacement-session"),
    ]
    assert sum(command[:3] == ["git", "worktree", "add"] for command in runner.commands) == 2
    assert sum(command[:3] == ["git", "worktree", "remove"] for command in runner.commands) == 1


def test_global_dispatch_retains_one_owned_worktree_through_resume_then_retires_it_on_close(tmp_path: Path, monkeypatch) -> None:
    first_review = {"id": "fresh", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[first_review])
    worktree_root = tmp_path / "worktrees"
    original_run = runner.run
    seen: list[tuple[str, Path]] = []

    def run(command, *, cwd, env=None):
        command = list(command)
        if command[:3] == ["git", "branch", "--show-current"] and cwd != tmp_path:
            runner.commands.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    [{"number": 12, "headRefName": runner.branch, "headRefOid": runner.pr_head, "comments": runner.comments, "url": "u"}]
                ),
                "",
            )
        if command[:3] == ["git", "fetch", "--no-tags"]:
            runner.commands.append(command)
            return subprocess.CompletedProcess(command, 0, "", "")
        if command == ["git", "rev-parse", "FETCH_HEAD"]:
            runner.commands.append(command)
            return subprocess.CompletedProcess(command, 0, runner.pr_head, "")
        if command[:3] == ["git", "worktree", "add"]:
            runner.commands.append(command)
            Path(command[-2]).mkdir(parents=True)
            return subprocess.CompletedProcess(command, 0, "", "")
        return original_run(command, cwd=cwd, env=env)

    def stop_hook(worktree: Path, session_id: str) -> None:
        monkeypatch.setattr(
            sys,
            "stdin",
            io.StringIO(json.dumps({"hook_event_name": "Stop", "cwd": str(worktree), "session_id": session_id})),
        )
        assert loop.main(["handoff", "--hook"], runner=runner) == 0

    def run_interactive(command, *, cwd, env=None, input_text=""):
        command = list(command)
        runner.commands.append(command)
        seen.append(("resume" if "resume" in command else "fresh", cwd))
        assert env and env[loop.OWNER_ROOT_ENV] == tmp_path.as_posix()
        if "resume" in command:
            runner.head = HEAD_A.replace("a", "c")
            runner.pr_head = runner.head
            runner.pr_heads = [HEAD_B, runner.head]
            loop.report_job_result(
                cwd=cwd,
                session_id="fresh-session",
                proof_status="passed",
                proof_command="pytest -q",
                proof_exit_code=0,
                push_status="passed",
                runner=runner,
            )
            stop_hook(cwd, "fresh-session")
        else:
            runner.head = HEAD_B
            runner.pr_head = HEAD_B
            runner.pr_heads = [HEAD_A, HEAD_B]
            loop.report_job_result(
                cwd=cwd,
                session_id="fresh-session",
                proof_status="passed",
                proof_command="pytest -q",
                proof_exit_code=0,
                push_status="passed",
                runner=runner,
            )
            stop_hook(cwd, "fresh-session")
        return subprocess.CompletedProcess(command, 0, "", "")

    runner.run = run
    runner.run_interactive = run_interactive
    monkeypatch.setenv(loop.OWNER_ROOT_ENV, tmp_path.as_posix())

    first = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=worktree_root, max_cycles=3, max_repeated_blockers=2
    )
    assert first["session_id"] == "fresh-session"
    assert loop._load_state(tmp_path, 12)["handoff_head"] == HEAD_B
    assert loop._load_state(tmp_path, 12)["terminal_result"]["disposition"] == "handoff-recorded"
    assert worktree_root / "pr-12" == Path(loop._load_dispatch(tmp_path)["prs"]["12"]["worktree"])
    assert (worktree_root / "pr-12").is_dir()

    runner.comments = [{"id": "resume", "body": f"Fix the follow-up\n{marker(head=HEAD_B)}", "url": "u"}]
    resumed = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=worktree_root, max_cycles=3, max_repeated_blockers=2
    )
    assert resumed["mode"] == "resume"
    assert seen[0] == ("fresh", worktree_root / "pr-12")
    assert seen[1] == ("resume", worktree_root / "pr-12")
    assert loop._load_state(tmp_path, 12)["session_id"] == "fresh-session"
    assert (worktree_root / "pr-12").is_dir()
    assert len([command for command in runner.commands if command[:3] == ["git", "worktree", "add"]]) == 1
    assert not any(command[:3] == ["git", "worktree", "remove"] for command in runner.commands)

    runner.pr_state = "CLOSED"
    loop.dispatch_all(tmp_path, runner=runner, codex_command="codex", worktree_root=worktree_root, max_cycles=3, max_repeated_blockers=2)
    assert not loop._state_path(tmp_path, 12).exists()
    assert loop._load_dispatch(tmp_path)["prs"] == {}
    assert not (worktree_root / "pr-12").exists()


def test_completed_fresh_session_without_hook_binding_gets_one_safe_replacement(tmp_path: Path) -> None:
    review = {"id": "fresh", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    original_run = runner.run

    def run(command, *, cwd, env=None):
        command = list(command)
        if command[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps([{"number": 12, "headRefName": runner.branch, "headRefOid": HEAD_A, "comments": [review], "url": "u"}]),
                "",
            )
        if command[:3] == ["git", "fetch", "--no-tags"]:
            return subprocess.CompletedProcess(command, 0, "", "")
        if command == ["git", "rev-parse", "FETCH_HEAD"]:
            return subprocess.CompletedProcess(command, 0, HEAD_A, "")
        if command[:3] == ["git", "worktree", "add"]:
            Path(command[-2]).mkdir(parents=True)
            return subprocess.CompletedProcess(command, 0, "", "")
        return original_run(command, cwd=cwd, env=env)

    def run_interactive(command, *, cwd, env=None, input_text=""):
        runner.commands.append(list(command))
        return subprocess.CompletedProcess(command, 0, "", "")

    runner.run = run
    runner.run_interactive = run_interactive
    first = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=tmp_path / "worktrees", max_cycles=3, max_repeated_blockers=2
    )
    second = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=tmp_path / "worktrees", max_cycles=3, max_repeated_blockers=2
    )
    third = loop.dispatch_all(
        tmp_path, runner=runner, codex_command="codex", worktree_root=tmp_path / "worktrees", max_cycles=3, max_repeated_blockers=2
    )

    assert first["event"] == "fresh-session-unbound"
    assert second["event"] == "fresh-session-unbound"
    assert loop._load_state(tmp_path, 12)["status"] == "recovery-required"
    assert third["reason"] == "no-eligible-blocked-review"
    assert sum("exec" in command for command in runner.commands) == 2


def test_handoff_is_idempotent_adds_opt_in_and_rejects_session_guessing(tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path)

    first = loop.handoff(
        cwd=tmp_path,
        session_id=SESSION,
        pr=None,
        max_cycles=3,
        max_repeated_blockers=2,
        replace_session=False,
        existing_only=False,
        runner=runner,
    )
    second = loop.handoff(
        cwd=tmp_path,
        session_id=SESSION,
        pr=None,
        max_cycles=3,
        max_repeated_blockers=2,
        replace_session=False,
        existing_only=False,
        runner=runner,
    )

    assert first["status"] == "handoff-recorded"
    assert first["opt_in_added"] is True
    assert second["status"] == "handoff-noop"
    assert second["opt_in_added"] is False
    assert sum(command[:3] == ["gh", "pr", "comment"] for command in runner.commands) == 1
    saved = loop._load_state(tmp_path, 12)
    assert (saved["session_id"], saved["handoff_head"]) == (SESSION, HEAD_A)
    assert saved["handoff_at"]
    assert saved["updated_at"]

    with pytest.raises(loop.LoopError, match="different exact Codex session") as error:
        loop.handoff(
            cwd=tmp_path,
            session_id="22222222-2222-2222-2222-222222222222",
            pr=12,
            max_cycles=3,
            max_repeated_blockers=2,
            replace_session=False,
            existing_only=False,
            runner=runner,
        )
    assert error.value.code == "session-ambiguous"


def test_handoff_bounded_retry_absorbs_github_head_propagation(tmp_path: Path, monkeypatch) -> None:
    runner = FakeRunner(tmp_path)
    runner.pr_heads = [HEAD_B, HEAD_A]
    monkeypatch.setattr(loop.time, "sleep", lambda _seconds: None)

    result = loop.handoff(
        cwd=tmp_path,
        session_id=SESSION,
        pr=12,
        max_cycles=3,
        max_repeated_blockers=2,
        replace_session=False,
        existing_only=False,
        runner=runner,
    )

    assert result["status"] == "handoff-recorded"
    assert sum(command[:3] == ["gh", "pr", "view"] for command in runner.commands) == 2


def test_fresh_post_exit_head_convergence_waits_for_delayed_push(tmp_path: Path, monkeypatch) -> None:
    runner = FakeRunner(tmp_path)
    runner.pr_heads = [HEAD_A, HEAD_B]
    monkeypatch.setattr(loop.time, "sleep", lambda _seconds: None)

    payload = loop._converged_pr_view(tmp_path, runner, pr=12, previous_head=HEAD_A)

    assert payload["headRefOid"] == HEAD_B
    assert sum(command[:3] == ["gh", "pr", "view"] for command in runner.commands) == 2


def test_stop_handoff_preserves_explicitly_configured_limits(tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path)
    existing = state(
        tmp_path,
        status="resume-in-progress",
        cycles=7,
        max_cycles=10,
        max_repeated_blockers=4,
    )
    loop._save_state(tmp_path, existing)

    result = loop.handoff(
        cwd=tmp_path,
        session_id=SESSION,
        pr=None,
        max_cycles=3,
        max_repeated_blockers=2,
        replace_session=False,
        existing_only=True,
        runner=runner,
    )

    refreshed = loop._load_state(tmp_path, 12)
    assert result["status"] == "handoff-noop"
    assert refreshed["status"] == "awaiting-review"
    assert refreshed["cycles"] == 7
    assert refreshed["max_cycles"] == 10
    assert refreshed["max_repeated_blockers"] == 4


def test_blocked_review_resumes_exact_session_once_and_requires_new_handoff(tmp_path: Path) -> None:
    review = {"id": "IC_blocked_91", "body": f"- fix the race\n{marker()}", "url": "https://example.test/c/91"}
    runner = FakeRunner(tmp_path, comments=[review])
    runner.next_handoff_head = HEAD_B
    passed_result(runner)
    initial = state(tmp_path)

    result = loop.poll_one(tmp_path, initial, runner=runner, codex_command="codex", bypass_hook_trust=True)

    assert result == {
        "pr_number": 12,
        "status": "resumed",
        "new_head": HEAD_B,
        "review_key": f"12:{HEAD_A}:IC_blocked_91",
    }
    resume = next(command for command in runner.commands if "resume" in command)
    assert resume[:5] == [
        "codex",
        "-C",
        tmp_path.as_posix(),
        "exec",
        "resume",
    ]
    assert resume[5] == "--dangerously-bypass-hook-trust"
    assert resume[6] == SESSION
    assert resume[7] == "-"
    assert "fix the race" in runner.interactive_inputs[-1]
    assert loop._load_state(tmp_path, 12)["handled_reviews"] == [f"12:{HEAD_A}:IC_blocked_91"]
    assert loop._load_state(tmp_path, 12)["hook_trust_mode"] == "automation-bypass"


def test_resume_persists_a_machine_readable_terminal_result(tmp_path: Path) -> None:
    review = {"id": "IC_terminal", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    runner.next_handoff_head = HEAD_B
    passed_result(runner)

    loop.poll_one(tmp_path, state(tmp_path), runner=runner, codex_command="codex")

    terminal = loop._load_state(tmp_path, 12)["terminal_result"]
    assert terminal["kind"] == "agentic-workspace/chatgpt-review-job-result/v1"
    assert terminal["pr_number"] == 12
    assert terminal["session_id"] == SESSION
    assert terminal["starting_head"] == HEAD_A
    assert terminal["ending_head"] == HEAD_B
    assert terminal["disposition"] == "handoff-recorded"
    assert terminal["proof_status"] == "passed"


def test_resume_rejects_stale_result_even_when_a_new_head_was_handed_off(tmp_path: Path) -> None:
    review = {"id": "stale", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    runner.next_handoff_head = HEAD_B
    saved = state(tmp_path, terminal_result={"proof_status": "passed", "push_status": "passed"})

    result = loop.poll_one(tmp_path, saved, runner=runner, codex_command="codex")

    assert result["event"] == "handoff-proof-unreported"
    assert loop._load_state(tmp_path, 12)["terminal_result"]["attempt_id"] == loop._load_state(tmp_path, 12)["job_attempt"]["id"]
    assert loop._load_state(tmp_path, 12)["terminal_result"]["proof_status"] == "unreported"


def test_resume_rejects_failed_proof_result_after_push(tmp_path: Path) -> None:
    review = {"id": "failed-proof", "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    runner.next_handoff_head = HEAD_B
    runner.next_job_result = {"proof_status": "failed", "proof_command": "pytest -q", "proof_exit_code": 1, "push_status": "passed"}

    result = loop.poll_one(tmp_path, state(tmp_path), runner=runner, codex_command="codex")

    assert result["event"] == "handoff-proof-unreported"
    assert loop._load_state(tmp_path, 12)["terminal_result"]["proof_status"] == "failed"


def test_job_result_is_exactly_once_and_requires_a_complete_result(tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path)
    saved = state(tmp_path, status="resume-in-progress")
    loop._begin_job_attempt(saved, mode="resume", worktree=tmp_path, start_head=HEAD_A)
    loop._save_state(tmp_path, saved)

    loop.report_job_result(
        cwd=tmp_path,
        session_id=SESSION,
        proof_status="passed",
        proof_command="",
        proof_exit_code=0,
        push_status="passed",
        runner=runner,
    )
    recorded = loop._load_state(tmp_path, 12)
    assert not loop._validated_attempt_result(recorded, worktree=tmp_path, start_head=HEAD_A)
    with pytest.raises(loop.LoopError, match="already recorded") as error:
        loop.report_job_result(
            cwd=tmp_path,
            session_id=SESSION,
            proof_status="passed",
            proof_command="pytest -q",
            proof_exit_code=0,
            push_status="passed",
            runner=runner,
        )
    assert error.value.code == "job-result-duplicate"


def test_malformed_result_and_mismatched_ending_head_cannot_validate(tmp_path: Path) -> None:
    saved = state(tmp_path, status="resume-in-progress", handoff_head=HEAD_B)
    attempt = loop._begin_job_attempt(saved, mode="resume", worktree=tmp_path, start_head=HEAD_A)
    saved["terminal_result"] = {
        "kind": "wrong",
        "attempt_id": attempt["id"],
        "pr_number": 12,
        "session_id": SESSION,
        "worktree": tmp_path.as_posix(),
        "starting_head": HEAD_A,
        "ending_head": HEAD_A,
        "proof_status": "passed",
        "proof_commands": ["pytest -q"],
        "proof_exit_code": 0,
        "push_status": "passed",
    }
    attempt.update(session_id=SESSION, result_recorded=True)
    saved["session_id"] = SESSION
    assert not loop._validated_attempt_result(saved, worktree=tmp_path, start_head=HEAD_A)


def test_new_handoff_clears_stale_resume_failure_diagnostics(tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path)
    existing = state(tmp_path, status="recovery-required", resume_exit_code=2, resume_diagnostic="old failure")
    loop._save_state(tmp_path, existing)

    result = loop.handoff(
        cwd=tmp_path,
        session_id=SESSION,
        pr=12,
        max_cycles=3,
        max_repeated_blockers=2,
        replace_session=False,
        existing_only=False,
        runner=runner,
    )

    refreshed = loop._load_state(tmp_path, 12)
    assert result["status"] == "handoff-noop"
    assert refreshed["status"] == "awaiting-review"
    assert "resume_exit_code" not in refreshed
    assert "resume_diagnostic" not in refreshed


def test_resume_failure_gets_one_automatic_recovery_for_same_comment(tmp_path: Path) -> None:
    review = {"databaseId": 92, "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    runner.codex_exit = 9
    initial = state(tmp_path)

    first = loop.poll_one(tmp_path, initial, runner=runner, codex_command="codex")
    recovery_key = f"12:{HEAD_A}:92"
    assert loop._queue_automatic_recovery(loop._load_state(tmp_path, 12), tmp_path, review_key=recovery_key) is True
    second = loop.poll_one(tmp_path, loop._load_state(tmp_path, 12), runner=runner, codex_command="codex")

    assert first["event"] == "resume-failed"
    assert first["diagnostic"] == "failed"
    assert loop._load_state(tmp_path, 12)["resume_diagnostic"] == "failed"
    assert second["event"] == "resume-failed"
    assert loop._queue_automatic_recovery(loop._load_state(tmp_path, 12), tmp_path, review_key=recovery_key) is False
    assert sum("resume" in command for command in runner.commands) == 2


def test_orphaned_worktree_failure_gets_one_automatic_recovery(tmp_path: Path) -> None:
    recovery_key = f"12:{HEAD_A}:blocked"
    state(tmp_path, status="recovery-required", last_event="worktree-create-failed", recovery_review_key=recovery_key)

    assert loop._queue_automatic_recovery(loop._load_state(tmp_path, 12), tmp_path, review_key=recovery_key) is True
    recovered = loop._load_state(tmp_path, 12)
    assert recovered["status"] == "awaiting-review"
    assert recovered["automatic_recovery_reviews"] == [recovery_key]


def test_serial_dispatch_prioritizes_recovery_over_an_earlier_stack_pr() -> None:
    normal = ({"number": 12}, loop.Review("normal", 12, HEAD_A, "blocked", "fix", "u"))
    recovery = ({"number": 13}, loop.Review("recovery", 13, HEAD_A, "blocked", "fix", "u"))

    assert loop._select_serial_candidate([recovery], [normal]) == recovery
    assert loop._select_serial_candidate([], [normal]) == normal


def test_reset_open_pr_cycles_clears_attempt_and_repeat_budgets(tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path)
    existing = state(
        tmp_path,
        cycles=7,
        blocker_fingerprints={"same": 2},
        automatic_recovery_reviews=[f"12:{HEAD_A}:blocked"],
    )
    original_run = runner.run

    def run(command, *, cwd, env=None):
        if list(command)[:3] == ["gh", "pr", "list"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps([{"number": 12, "headRefName": runner.branch, "headRefOid": HEAD_A, "comments": [], "url": "u"}]),
                "",
            )
        return original_run(command, cwd=cwd, env=env)

    runner.run = run

    assert loop.reset_open_pr_cycles(tmp_path, runner) == [12]
    reset = loop._load_state(tmp_path, 12)
    assert reset["cycles"] == 0
    assert reset["blocker_fingerprints"] == {}
    assert reset["automatic_recovery_reviews"] == []
    assert reset["handled_reviews"] == existing["handled_reviews"]


def test_merge_ready_records_readiness_without_merging(tmp_path: Path) -> None:
    review = {"databaseId": 93, "body": marker(decision="merge-ready"), "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])

    result = loop.poll_one(tmp_path, state(tmp_path), runner=runner, codex_command="codex")

    assert result["status"] == "merge-ready"
    assert result["merged"] is False
    assert not any("merge" in command for command in runner.commands)
    assert loop._load_state(tmp_path, 12)["status"] == "merge-ready"


@pytest.mark.parametrize(
    ("mutation", "event"),
    [
        (lambda runner: setattr(runner, "branch", "other"), "branch-changed"),
        (lambda runner: setattr(runner, "pr_state", "CLOSED"), "pr-closed"),
        (lambda runner: setattr(runner, "pr_head", HEAD_B), "unrecorded-head"),
    ],
)
def test_unsafe_repository_states_require_explicit_recovery(tmp_path: Path, mutation, event: str) -> None:
    runner = FakeRunner(tmp_path)
    mutation(runner)

    result = loop.poll_one(tmp_path, state(tmp_path), runner=runner, codex_command="codex")

    assert result["status"] == "recovery-required"
    assert result["event"] == event
    assert loop._load_state(tmp_path, 12)["recovery"]


def test_stale_review_is_a_visible_noop(tmp_path: Path) -> None:
    runner = FakeRunner(
        tmp_path,
        comments=[{"databaseId": 94, "body": f"Old blocker\n{marker(head=HEAD_B)}", "url": "u"}],
    )

    result = loop.poll_one(tmp_path, state(tmp_path), runner=runner, codex_command="codex")

    assert result["reason"] == "stale-review-rejected"
    assert result["rejected"][0]["reviewed_head"] == HEAD_B
    assert not any("resume" in command for command in runner.commands)


def test_repeated_blocker_and_cycle_limits_escalate_without_resume(tmp_path: Path) -> None:
    body = "Same blocker"
    review = {"databaseId": 95, "body": f"{body}\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    fingerprint = loop.hashlib.sha256(body.encode()).hexdigest()
    repeated_state = state(tmp_path, blocker_fingerprints={fingerprint: 2}, max_repeated_blockers=2)

    repeated = loop.poll_one(tmp_path, repeated_state, runner=runner, codex_command="codex")
    assert repeated["event"] == "repeated-blocker-threshold"

    cycle_state = state(tmp_path, cycles=3, max_cycles=3)
    cycle = loop.poll_one(tmp_path, cycle_state, runner=runner, codex_command="codex")
    assert cycle["event"] == "max-cycles-exceeded"
    assert not any("resume" in command for command in runner.commands)


def test_hook_mode_is_quiet_until_an_exact_loop_is_explicitly_enabled(tmp_path: Path, monkeypatch, capsys) -> None:
    runner = FakeRunner(tmp_path)
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({"hook_event_name": "Stop", "cwd": str(tmp_path), "session_id": SESSION})),
    )

    assert loop.main(["handoff", "--hook"], runner=runner) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["continue"] is True
    assert "systemMessage" not in output
    assert not any(command[:2] == ["gh", "pr"] for command in runner.commands)


def test_runtime_state_root_is_covered_by_repo_gitignore() -> None:
    gitignore = (_SCRIPT.parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert ".agentic-workspace/local/" in gitignore


def test_watcher_continues_only_for_review_waiting_states() -> None:
    assert loop._should_keep_watching([{"status": "no-op", "reason": "review-pending"}]) is True
    assert loop._should_keep_watching([{"status": "no-op", "reason": "stale-review-rejected"}]) is True
    assert loop._should_keep_watching([{"status": "no-op", "reason": "state-is-resume-in-progress"}]) is True
    assert loop._should_keep_watching([{"status": "resumed", "new_head": HEAD_B}]) is True
    assert loop._should_keep_watching([{"status": "no-op", "reason": "no-eligible-blocked-review"}]) is True
    assert loop._should_keep_watching([{"status": "dispatched", "pr_number": 12}]) is True
    assert loop._should_keep_watching([{"status": "no-op", "reason": "state-is-stopped"}]) is False
    assert loop._should_keep_watching([{"status": "recovery-required", "event": "resume-failed"}]) is True


def test_global_watch_waits_after_empty_scan_then_dispatches(tmp_path: Path, monkeypatch, capsys) -> None:
    runner = FakeRunner(tmp_path)
    results = iter(
        [
            {"status": "no-op", "reason": "no-eligible-blocked-review"},
            {"status": "dispatched", "pr_number": 12, "mode": "fresh"},
        ]
    )
    monkeypatch.setattr(loop, "dispatch_all", lambda *args, **kwargs: next(results))
    monkeypatch.setattr(loop.time, "sleep", lambda _seconds: None)

    assert (
        loop.main(["poll", "--target", str(tmp_path), "--all-open", "--watch", "--interval", "1", "--max-polls", "2"], runner=runner) == 0
    )

    output = capsys.readouterr().out
    assert output.count('"poll-complete"') == 2


def test_watch_started_during_resume_waits_for_stop_handoff(tmp_path: Path, monkeypatch, capsys) -> None:
    runner = FakeRunner(tmp_path)
    state(tmp_path, status="resume-in-progress", last_event="resume-attempt-recorded")

    def record_stop_handoff(_seconds: int) -> None:
        current = loop._load_state(tmp_path, 12)
        current.update(status="awaiting-review", last_event="handoff-recorded")
        loop._save_state(tmp_path, current)

    monkeypatch.setattr(loop.time, "sleep", record_stop_handoff)

    assert (
        loop.main(
            ["poll", "--target", str(tmp_path), "--pr", "12", "--watch", "--interval", "1", "--max-polls", "2"],
            runner=runner,
        )
        == 0
    )

    output = capsys.readouterr().out
    assert '"reason": "state-is-resume-in-progress"' in output
    assert '"reason": "review-pending"' in output
    assert sum(command[:3] == ["gh", "pr", "view"] for command in runner.commands) == 1


def test_watch_loop_resumes_head_a_then_reviews_head_b_without_restart(tmp_path: Path, monkeypatch, capsys) -> None:
    first_review = {
        "id": "IC_head_a",
        "body": f"Fix head A\n{marker(head=HEAD_A)}",
        "url": "https://example.test/c/a",
    }
    runner = FakeRunner(tmp_path, comments=[first_review])
    runner.next_handoff_head = HEAD_B
    passed_result(runner)
    runner.next_review_decision = "merge-ready"
    state(tmp_path)
    monkeypatch.setattr(loop.time, "sleep", lambda _seconds: None)

    assert (
        loop.main(
            [
                "poll",
                "--target",
                str(tmp_path),
                "--pr",
                "12",
                "--watch",
                "--interval",
                "1",
                "--max-polls",
                "3",
                "--bypass-hook-trust",
            ],
            runner=runner,
        )
        == 0
    )

    assert loop._load_state(tmp_path, 12)["status"] == "merge-ready"
    assert sum("resume" in command for command in runner.commands) == 1
    output = capsys.readouterr().out
    assert '"status": "resumed"' in output
    assert '"status": "merge-ready"' in output


def test_project_stop_hook_uses_repo_runtime_and_has_no_machine_local_path() -> None:
    hooks = json.loads((_SCRIPT.parents[1] / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    handler = hooks["hooks"]["Stop"][0]["hooks"][0]

    assert handler["timeout"] == 30
    assert "uv run python" in handler["command"]
    assert "git rev-parse --show-toplevel" in handler["command"]
    assert "uv run python" in handler["commandWindows"]
    assert handler["commandWindows"] == "uv run python tools/chatgpt_review_loop.py handoff --hook"
    assert "powershell" not in handler["commandWindows"].lower()
    assert "ricka" not in json.dumps(handler)
