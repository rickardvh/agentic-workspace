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
