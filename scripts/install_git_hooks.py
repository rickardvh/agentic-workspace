from __future__ import annotations

import stat
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _hook_script(python_executable: Path, hook_runner: Path) -> str:
    python_path = python_executable.resolve().as_posix()
    runner_path = hook_runner.resolve().as_posix()
    return (
        "#!/bin/sh\n"
        f'"{python_path}" "{runner_path}" "$@"\n'
    )


def main() -> int:
    repo_root = _repo_root()
    hooks_dir = repo_root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        raise SystemExit("Git hooks directory not found; run this inside the repository root clone.")

    hook_path = hooks_dir / "pre-commit"
    hook_runner = repo_root / "scripts" / "git_hooks" / "pre_commit.py"
    hook_path.write_text(_hook_script(Path(sys.executable), hook_runner), encoding="utf-8", newline="\n")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Installed repo-managed pre-commit hook at {hook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())