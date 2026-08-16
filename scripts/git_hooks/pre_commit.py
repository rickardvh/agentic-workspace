from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _repo_root(cwd: Path | None = None) -> Path:
    current = cwd or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=current,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return Path(__file__).resolve().parents[2]
    root = result.stdout.strip()
    return Path(root).resolve() if root else Path(__file__).resolve().parents[2]


REPO_ROOT = _repo_root()
FORMAT_EXTENSIONS = {".py", ".pyi", ".ipynb"}
FORMAT_ROOTS = {"src", "tests", "packages"}
POST_FORMAT_COMMANDS = (
    ["make", "lint-nosync"],
    ["make", "typecheck-nosync"],
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
    return [path for path in staged_paths if path.suffix in FORMAT_EXTENSIONS and path.parts and path.parts[0] in FORMAT_ROOTS]


def _partial_stage_conflicts(format_candidates: list[Path]) -> list[Path]:
    unstaged_paths = set(_git_paths("diff", "--name-only"))
    return sorted(path for path in format_candidates if path in unstaged_paths)


def _validation_environment() -> dict[str, str]:
    environment = os.environ.copy()
    run_id = environment.get("VALIDATION_RUN_ID", "")
    if run_id and environment.get("VALIDATION_JOIN_TOKEN") == f"join:{run_id}":
        environment["VALIDATION_RUN_PROVENANCE"] = "transported-child"
        return environment
    result = subprocess.run(
        [sys.executable, "scripts/check/allocate_validation_run_id.py"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    environment["VALIDATION_RUN_ID"] = result.stdout.strip()
    environment["VALIDATION_JOIN_TOKEN"] = f"join:{environment['VALIDATION_RUN_ID']}"
    environment["VALIDATION_RUN_PROVENANCE"] = "allocated-here"
    return environment


def _run(command: list[str], *, environment: dict[str, str]) -> int:
    return subprocess.run(command, cwd=REPO_ROOT, env=environment, check=False).returncode


def main() -> int:
    environment = _validation_environment()
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

    if _run(["make", "sync-all"], environment=environment) != 0:
        return 1

    if format_candidates:
        format_command = [
            sys.executable,
            "scripts/check/run_compact_command.py",
            "--label",
            "pre-commit format",
            "--id",
            "format.pre-commit",
            "--depends-on",
            "sync.all",
            "--proof-purpose",
            "format staged Ruff-managed files before commit",
            "--",
            sys.executable,
            "-m",
            "ruff",
            "format",
            *[path.as_posix() for path in format_candidates],
        ]
        if _run(format_command, environment=environment) != 0:
            return 1
        if _run(
            ["git", "add", "--", *[path.as_posix() for path in format_candidates]], environment=environment
        ) != 0:
            return 1

    for command in POST_FORMAT_COMMANDS:
        if _run(command, environment=environment) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
