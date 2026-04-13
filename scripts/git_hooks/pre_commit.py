from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAT_EXTENSIONS = {".py", ".pyi", ".ipynb"}
FORMAT_ROOTS = {"src", "tests", "packages"}
HOOK_COMMANDS = (
    ["make", "lint"],
    [sys.executable, "scripts/check/check_master_tests.py"],
    [sys.executable, "scripts/check/check_no_absolute_paths.py"],
)


def _git_paths(*args: str) -> list[Path]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line]


def _format_candidates() -> list[Path]:
    staged_paths = _git_paths("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [
        path
        for path in staged_paths
        if path.suffix in FORMAT_EXTENSIONS and path.parts and path.parts[0] in FORMAT_ROOTS
    ]


def _partial_stage_conflicts(format_candidates: list[Path]) -> list[Path]:
    unstaged_paths = set(_git_paths("diff", "--name-only"))
    return sorted(path for path in format_candidates if path in unstaged_paths)


def _run(command: list[str]) -> int:
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


def _run_checked(command: list[str]) -> int:
    return subprocess.run(command, cwd=REPO_ROOT, check=False).returncode


def main() -> int:
    format_candidates = _format_candidates()
    conflicts = _partial_stage_conflicts(format_candidates)
    if conflicts:
        print(
            "pre-commit auto-format aborted: some staged Ruff-managed files also have unstaged changes.",
            file=sys.stderr,
        )
        for path in conflicts:
            print(f"- {path.as_posix()}", file=sys.stderr)
        print(
            "Stage or stash those files fully, then retry the commit.",
            file=sys.stderr,
        )
        return 1

    if format_candidates:
        format_command = [sys.executable, "-m", "ruff", "format", *[path.as_posix() for path in format_candidates]]
        if _run_checked(format_command) != 0:
            return 1
        if _run(["git", "add", "--", *[path.as_posix() for path in format_candidates]]) != 0:
            return 1

    for command in HOOK_COMMANDS:
        if _run(command) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())