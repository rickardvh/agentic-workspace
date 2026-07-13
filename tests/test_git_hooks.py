from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


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
