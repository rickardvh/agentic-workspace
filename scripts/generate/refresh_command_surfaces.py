from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SEQUENCE = (
    ("uv", "run", "python", "scripts/generate/generate_command_packages.py"),
    ("uv", "run", "python", "scripts/generate/generate_command_adapters.py"),
    ("uv", "run", "python", "scripts/generate/generate_command_packages.py"),
)


def main() -> int:
    for command in SEQUENCE:
        print("[refresh]", " ".join(command), flush=True)
        completed = subprocess.run(command, cwd=REPO_ROOT)
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
