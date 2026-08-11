from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest


def _run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def _load_pre_commit_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "git_hooks" / "pre_commit.py"
    spec = importlib.util.spec_from_file_location("pre_commit_hook_under_test", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_pre_commit_repo_root_uses_current_linked_worktree(tmp_path: Path) -> None:
    main = tmp_path / "main"
    linked = tmp_path / "linked"
    main.mkdir()
    _run(["git", "init"], cwd=main)
    _run(["git", "config", "user.email", "test@example.com"], cwd=main)
    _run(["git", "config", "user.name", "Test User"], cwd=main)
    (main / "README.md").write_text("# Test\n", encoding="utf-8")
    _run(["git", "add", "README.md"], cwd=main)
    _run(["git", "commit", "-m", "init"], cwd=main)
    _run(["git", "worktree", "add", str(linked), "-b", "linked-branch"], cwd=main)

    pre_commit = _load_pre_commit_module()

    assert pre_commit._repo_root(cwd=linked) == linked.resolve()


def test_installed_hook_enters_the_invoking_worktree() -> None:
    installer_path = Path(__file__).resolve().parents[1] / "scripts" / "install_git_hooks.py"
    spec = importlib.util.spec_from_file_location("install_git_hooks_under_test", installer_path)
    assert spec is not None and spec.loader is not None
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)

    hook = installer._hook_script(Path("python"), Path("scripts/git_hooks/pre_commit.py"))

    assert "git rev-parse --show-toplevel" in hook
    assert 'cd "$repo_root"' in hook


def test_pre_commit_uses_one_run_for_setup_lint_and_typecheck(monkeypatch: pytest.MonkeyPatch) -> None:
    pre_commit = _load_pre_commit_module()
    environment = {"VALIDATION_RUN_ID": "explicit-run"}
    commands: list[tuple[list[str], dict[str, str]]] = []

    monkeypatch.setattr(pre_commit, "_validation_environment", lambda: environment)
    monkeypatch.setattr(pre_commit, "_format_candidates", lambda: [])
    monkeypatch.setattr(pre_commit, "_partial_stage_conflicts", lambda _: [])
    monkeypatch.setattr(
        pre_commit,
        "_run",
        lambda command, *, environment: commands.append((command, environment)) or 0,
    )

    assert pre_commit.main() == 0
    assert [command for command, _ in commands] == [
        ["make", "sync-all"],
        ["make", "lint-nosync"],
        ["make", "typecheck-nosync"],
        [pre_commit.sys.executable, "scripts/check/check_no_absolute_paths.py"],
    ]
    assert all(command_environment is environment for _, command_environment in commands)


def test_pre_commit_records_and_stages_format_before_other_phases(monkeypatch: pytest.MonkeyPatch) -> None:
    pre_commit = _load_pre_commit_module()
    candidate = Path("tests/test_example.py")
    commands: list[list[str]] = []

    monkeypatch.setattr(pre_commit, "_validation_environment", lambda: {"VALIDATION_RUN_ID": "run-1"})
    monkeypatch.setattr(pre_commit, "_format_candidates", lambda: [candidate])
    monkeypatch.setattr(pre_commit, "_partial_stage_conflicts", lambda _: [])
    monkeypatch.setattr(
        pre_commit,
        "_run",
        lambda command, *, environment: commands.append(command) or 0,
    )

    assert pre_commit.main() == 0
    assert commands[0] == ["make", "sync-all"]
    assert commands[1][1:7] == [
        "scripts/check/run_compact_command.py",
        "--label",
        "pre-commit format",
        "--id",
        "format.pre-commit",
        "--depends-on",
    ]
    assert commands[2] == ["git", "add", "--", candidate.as_posix()]
    assert commands[3:5] == [["make", "lint-nosync"], ["make", "typecheck-nosync"]]
