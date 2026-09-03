from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "review_stack_ops.py"
_SPEC = importlib.util.spec_from_file_location("review_stack_ops", _SCRIPT)
assert _SPEC and _SPEC.loader
stack = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = stack
_SPEC.loader.exec_module(stack)


def git(cwd: Path, *args: str, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if check:
        assert completed.returncode == 0, completed.stderr or completed.stdout
    return completed.stdout.strip()


class IntegrationRunner(stack.CommandRunner):
    def __init__(self, *, fail_push: bool = False) -> None:
        self.fail_push = fail_push
        self.commands: list[list[str]] = []
        self.pr_bodies: dict[int, str] = {}

    def run(self, command, *, cwd, input_text=None):
        command = list(command)
        self.commands.append(command)
        if command[:2] == ["git", "push"] and self.fail_push:
            return subprocess.CompletedProcess(command, 1, "", "stale info")
        if command[:3] == ["gh", "pr", "view"]:
            pr = int(command[3])
            branch = "descendant"
            head = git(cwd, "ls-remote", "--heads", "origin", f"refs/heads/{branch}").split()[0]
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"body": self.pr_bodies.get(pr, "Stack PR"), "headRefOid": head}),
                "",
            )
        if command[:3] == ["gh", "pr", "edit"]:
            self.pr_bodies[int(command[3])] = command[command.index("--body") + 1]
            return subprocess.CompletedProcess(command, 0, "", "")
        return super().run(command, cwd=cwd, input_text=input_text)


class MergeRunner(stack.CommandRunner):
    def __init__(
        self,
        *,
        head: str,
        stacked: bool,
        ordinary_refusal: bool = False,
        async_results: list[dict] | None = None,
        review_success: bool = True,
    ) -> None:
        self.head = head
        self.stacked = stacked
        self.ordinary_refusal = ordinary_refusal
        self.async_results = list(async_results or [{"status": "merged", "details": {"sha": "a" * 40}}])
        self.review_success = review_success
        self.merged = False
        self.commands: list[list[str]] = []
        self.inputs: list[str | None] = []

    def run(self, command, *, cwd, input_text=None):
        command = list(command)
        self.commands.append(command)
        self.inputs.append(input_text)
        if command[:3] == ["gh", "repo", "view"]:
            return subprocess.CompletedProcess(command, 0, "owner/repo\n", "")
        if command[:3] == ["gh", "pr", "view"]:
            payload = {
                "headRefOid": self.head,
                "state": "MERGED" if self.merged else "OPEN",
                "isDraft": False,
                "mergeable": "MERGEABLE",
                "statusCheckRollup": [
                    {
                        "name": "Review approval",
                        "status": "COMPLETED",
                        "conclusion": "SUCCESS" if self.review_success else "FAILURE",
                    },
                    {"name": "tests", "status": "COMPLETED", "conclusion": "SUCCESS"},
                ],
                "mergedAt": "2026-09-02T12:00:00Z" if self.merged else None,
                "mergeCommit": {"oid": "a" * 40} if self.merged else None,
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if command[:2] == ["gh", "api"] and command[-2:] == ["--jq", ".stack // empty"]:
            return subprocess.CompletedProcess(command, 0, '{"number": 7}\n' if self.stacked else "", "")
        if command[:3] == ["gh", "pr", "merge"]:
            if self.ordinary_refusal:
                return subprocess.CompletedProcess(command, 1, "", "stack requires asynchronous merge API")
            self.merged = True
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[:4] == ["gh", "api", "--method", "PUT"]:
            return subprocess.CompletedProcess(command, 0, json.dumps({"status": "pending", "uuid": "request-1"}), "")
        if command[:2] == ["gh", "api"] and "merge-async/request-1" in command[-1]:
            payload = self.async_results.pop(0)
            if payload.get("status") == "merged":
                self.merged = True
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        raise AssertionError(f"unexpected command: {command}")


def commit(repo: Path, name: str, text: str, message: str) -> str:
    (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def stack_fixture(tmp_path: Path) -> tuple[Path, Path, dict]:
    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    git(tmp_path, "init", "--bare", origin.as_posix())
    git(tmp_path, "init", repo.as_posix())
    git(repo, "config", "user.email", "test@example.test")
    git(repo, "config", "user.name", "Test User")
    old_base = commit(repo, "README.md", "base\n", "base")
    git(repo, "branch", "-M", "master")
    git(repo, "remote", "add", "origin", origin.as_posix())
    git(repo, "push", "-u", "origin", "master")

    git(repo, "switch", "-c", "base-change")
    new_base = commit(repo, "base.txt", "new base\n", "base change")
    git(repo, "push", "-u", "origin", "base-change")

    git(repo, "switch", "--detach", old_base)
    git(repo, "switch", "-c", "descendant")
    old_remote_head = commit(repo, "feature.txt", "feature\n", "feature")
    git(repo, "push", "-u", "origin", "descendant")
    git(repo, "switch", "base-change")

    declaration = {
        "kind": stack.DECLARATION_KIND,
        "base": {"pr_number": 100, "branch": "base-change", "head": new_base},
        "descendants": [
            {
                "pr_number": 101,
                "branch": "descendant",
                "old_base": old_base,
                "new_base": new_base,
                "old_remote_head": old_remote_head,
            }
        ],
    }
    declaration_path = repo / "stack.json"
    declaration_path.write_text(json.dumps(declaration), encoding="utf-8")
    return repo, declaration_path, declaration


def test_declared_stack_dry_run_preserves_remote_and_records_patch_and_ancestry(tmp_path: Path) -> None:
    repo, declaration_path, declaration = stack_fixture(tmp_path)
    receipt_path = repo / "receipt.json"
    runner = IntegrationRunner()

    receipt = stack.restack(
        repo,
        declaration_path=declaration_path,
        receipt_path=receipt_path,
        runner=runner,
        publish=False,
        update_pr_bodies=False,
    )

    rewrite = receipt["rewrites"][0]
    assert receipt["status"] == "planned"
    assert rewrite["ancestry_preserved"] is True
    assert rewrite["patch_preserved"] is True
    assert rewrite["new_head"] != rewrite["old_remote_head"]
    assert (
        git(repo, "ls-remote", "--heads", "origin", "refs/heads/descendant").split()[0] == declaration["descendants"][0]["old_remote_head"]
    )
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["status"] == "planned"


def test_declared_stack_publishes_with_exact_lease_and_updates_pr_metadata(tmp_path: Path) -> None:
    repo, declaration_path, _ = stack_fixture(tmp_path)
    runner = IntegrationRunner()

    receipt = stack.restack(
        repo,
        declaration_path=declaration_path,
        receipt_path=repo / "published.json",
        runner=runner,
        publish=True,
        update_pr_bodies=True,
    )

    rewrite = receipt["rewrites"][0]
    assert receipt["status"] == "published"
    assert receipt["remote_updates"][0]["observed_new_head"] == rewrite["new_head"]
    assert f"<!-- aw-exact-head {rewrite['new_head']} -->" in runner.pr_bodies[101]
    push = next(command for command in runner.commands if command[:2] == ["git", "push"])
    assert f"--force-with-lease=refs/heads/descendant:{rewrite['old_remote_head']}" in push


def test_failed_force_with_lease_records_no_successful_remote_or_metadata_write(tmp_path: Path) -> None:
    repo, declaration_path, declaration = stack_fixture(tmp_path)
    runner = IntegrationRunner(fail_push=True)

    receipt = stack.restack(
        repo,
        declaration_path=declaration_path,
        receipt_path=repo / "failed.json",
        runner=runner,
        publish=True,
        update_pr_bodies=True,
    )

    assert receipt["status"] == "publication-failed"
    assert receipt["remote_updates"] == [
        {
            "branch": "descendant",
            "expected_old_head": declaration["descendants"][0]["old_remote_head"],
            "requested_new_head": receipt["rewrites"][0]["new_head"],
            "exit_code": 1,
            "status": "lease-or-push-failed",
            "diagnostic": "stale info",
        }
    ]
    assert receipt["pr_metadata_updates"] == []
    assert (
        git(repo, "ls-remote", "--heads", "origin", "refs/heads/descendant").split()[0] == declaration["descendants"][0]["old_remote_head"]
    )


def test_preflight_rejects_changed_remote_before_any_publication(tmp_path: Path) -> None:
    repo, declaration_path, declaration = stack_fixture(tmp_path)
    declaration["descendants"][0]["old_remote_head"] = "f" * 40
    declaration_path.write_text(json.dumps(declaration), encoding="utf-8")
    runner = IntegrationRunner()

    receipt = stack.restack(
        repo,
        declaration_path=declaration_path,
        receipt_path=repo / "preflight-failed.json",
        runner=runner,
        publish=True,
        update_pr_bodies=True,
    )

    assert receipt["status"] == "preflight-failed"
    assert receipt["error"]["code"] == "lease-preflight-failed"
    assert receipt["remote_updates"] == []
    assert not any(command[:2] == ["git", "push"] for command in runner.commands)


def test_stacked_merge_uses_exact_head_async_transport_and_observes_terminal_state(tmp_path: Path) -> None:
    head = "b" * 40
    runner = MergeRunner(head=head, stacked=True, async_results=[{"status": "pending"}, {"status": "merged"}])

    receipt = stack.merge_ready_pr(
        tmp_path,
        pr=93,
        reviewed_head=head,
        merge_method="merge",
        receipt_path=tmp_path / "merge.json",
        runner=runner,
        max_polls=3,
        poll_interval_seconds=0,
    )

    assert receipt["status"] == "merged"
    assert receipt["transport"] == "github-merge-async"
    assert receipt["terminal_observation"]["headRefOid"] == head
    assert not any(command[:3] == ["gh", "pr", "merge"] for command in runner.commands)
    request_index = next(index for index, command in enumerate(runner.commands) if command[:4] == ["gh", "api", "--method", "PUT"])
    assert json.loads(runner.inputs[request_index] or "{}") == {
        "sha": head,
        "merge_method": "merge",
        "merge_action": "default",
    }


def test_nonstacked_merge_keeps_simple_transport(tmp_path: Path) -> None:
    head = "c" * 40
    runner = MergeRunner(head=head, stacked=False)

    receipt = stack.merge_ready_pr(
        tmp_path,
        pr=94,
        reviewed_head=head,
        merge_method="squash",
        receipt_path=tmp_path / "merge.json",
        runner=runner,
        poll_interval_seconds=0,
    )

    assert receipt["status"] == "merged"
    assert receipt["transport"] == "gh-pr-merge"
    assert ["gh", "pr", "merge", "94", "--squash", "--match-head-commit", head] in runner.commands
    assert not any("merge-async" in " ".join(command) for command in runner.commands)


def test_async_transport_refusal_is_constructible_but_review_and_head_stay_fail_closed(tmp_path: Path) -> None:
    head = "d" * 40
    fallback = MergeRunner(head=head, stacked=False, ordinary_refusal=True)
    receipt = stack.merge_ready_pr(
        tmp_path,
        pr=95,
        reviewed_head=head,
        merge_method="rebase",
        receipt_path=tmp_path / "fallback.json",
        runner=fallback,
        poll_interval_seconds=0,
    )
    assert receipt["status"] == "merged"
    assert receipt["transport"] == "github-merge-async"
    assert "asynchronous merge" in receipt["ordinary_transport_refusal"]

    stale = MergeRunner(head="e" * 40, stacked=True)
    rejected = stack.merge_ready_pr(
        tmp_path,
        pr=96,
        reviewed_head=head,
        merge_method="merge",
        receipt_path=tmp_path / "stale.json",
        runner=stale,
        poll_interval_seconds=0,
    )
    assert rejected["status"] == "failed"
    assert rejected["error"]["code"] == "pr-head-mismatch"
    assert not any(command[:4] == ["gh", "api", "--method", "PUT"] for command in stale.commands)


def test_pending_async_merge_times_out_without_descendant_mutation(tmp_path: Path) -> None:
    head = "f" * 40
    runner = MergeRunner(head=head, stacked=True, async_results=[{"status": "pending"}, {"status": "pending"}])
    receipt = stack.merge_ready_pr(
        tmp_path,
        pr=97,
        reviewed_head=head,
        merge_method="merge",
        receipt_path=tmp_path / "timeout.json",
        runner=runner,
        max_polls=2,
        poll_interval_seconds=0,
    )

    assert receipt["status"] == "failed"
    assert receipt["error"]["code"] == "async-merge-timeout"
    assert not any(command[:2] == ["git", "push"] for command in runner.commands)
