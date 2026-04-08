from __future__ import annotations

import subprocess


def current_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def main() -> int:
    branch = current_branch()
    if branch != "master":
        print(f"pre-commit master test gate: skipped on {branch or 'detached HEAD'}")
        return 0

    print("pre-commit master test gate: running tests on master")
    return subprocess.run(["make", "test"], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
