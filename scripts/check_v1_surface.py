from __future__ import annotations

import subprocess
from pathlib import Path

FORBIDDEN_TRACKED_PREFIXES = (
    ".agentic-workspace/fallback/",
    "generated/",
    "packages/",
)
FORBIDDEN_SOURCE_NAMES = {
    "operating_decision.py",
    "runtime_compatibility.py",
    "workspace_runtime_core.py",
}


def main() -> int:
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
    violations = [path for path in tracked if path.startswith(FORBIDDEN_TRACKED_PREFIXES)]
    violations.extend(
        path
        for path in tracked
        if Path(path).parent == Path("src/agentic_workspace") and Path(path).name in FORBIDDEN_SOURCE_NAMES
    )
    if violations:
        for path in sorted(set(violations)):
            print(f"pre-v1 surface is not allowed: {path}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
