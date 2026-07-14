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


class FakeRunner(loop.CommandRunner):
    def __init__(self, root: Path, *, comments: list[dict] | None = None) -> None:
        self.root = root
        self.branch = "codex/issue-2290"
        self.head = HEAD_A
        self.pr_head = HEAD_A
        self.pr_branch = self.branch
        self.pr_state = "OPEN"
        self.comments = comments or []
        self.commands: list[list[str]] = []
        self.codex_exit = 0
        self.next_handoff_head = ""

    def run(self, command, *, cwd, env=None):
        command = list(command)
        self.commands.append(command)
        if command[:3] == ["git", "rev-parse", "--show-toplevel"]:
            return subprocess.CompletedProcess(command, 0, str(self.root), "")
        if command[:3] == ["git", "branch", "--show-current"]:
            return subprocess.CompletedProcess(command, 0, self.branch, "")
        if command[:3] == ["git", "rev-parse", "HEAD"]:
            return subprocess.CompletedProcess(command, 0, self.head, "")
        if command[:3] == ["gh", "repo", "view"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"nameWithOwner": "owner/repo"}), "")
        if command[:3] == ["gh", "pr", "view"]:
            payload = {
                "number": 12,
                "state": self.pr_state,
                "headRefName": self.pr_branch,
                "headRefOid": self.pr_head,
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
            return subprocess.CompletedProcess(command, self.codex_exit, "", "failed" if self.codex_exit else "")
        raise AssertionError(f"unexpected command: {command}")


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


def test_blocked_review_resumes_exact_session_once_and_requires_new_handoff(tmp_path: Path) -> None:
    review = {"id": "IC_blocked_91", "body": f"- fix the race\n{marker()}", "url": "https://example.test/c/91"}
    runner = FakeRunner(tmp_path, comments=[review])
    runner.next_handoff_head = HEAD_B
    initial = state(tmp_path)

    result = loop.poll_one(tmp_path, initial, runner=runner, codex_command="codex")

    assert result == {
        "pr_number": 12,
        "status": "resumed",
        "new_head": HEAD_B,
        "review_key": f"12:{HEAD_A}:IC_blocked_91",
    }
    resume = next(command for command in runner.commands if "resume" in command)
    assert resume[:4] == ["codex", "resume", "--cd", tmp_path.as_posix()]
    assert resume[4] == SESSION
    assert "fix the race" in resume[5]
    assert loop._load_state(tmp_path, 12)["handled_reviews"] == [f"12:{HEAD_A}:IC_blocked_91"]


def test_resume_failure_is_not_retried_for_same_comment(tmp_path: Path) -> None:
    review = {"databaseId": 92, "body": f"Fix it\n{marker()}", "url": "u"}
    runner = FakeRunner(tmp_path, comments=[review])
    runner.codex_exit = 9
    initial = state(tmp_path)

    first = loop.poll_one(tmp_path, initial, runner=runner, codex_command="codex")
    second = loop.poll_one(tmp_path, loop._load_state(tmp_path, 12), runner=runner, codex_command="codex")

    assert first["event"] == "resume-failed"
    assert second == {"pr_number": 12, "status": "no-op", "reason": "state-is-recovery-required"}
    assert sum("resume" in command for command in runner.commands) == 1


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


def test_project_stop_hook_uses_repo_runtime_and_has_no_machine_local_path() -> None:
    hooks = json.loads((_SCRIPT.parents[1] / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    handler = hooks["hooks"]["Stop"][0]["hooks"][0]

    assert handler["timeout"] == 30
    assert "uv run python" in handler["command"]
    assert "git rev-parse --show-toplevel" in handler["command"]
    assert "uv run python" in handler["commandWindows"]
    assert "ricka" not in json.dumps(handler)
