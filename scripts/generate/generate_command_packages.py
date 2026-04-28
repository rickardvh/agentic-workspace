from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = REPO_ROOT / "scripts" / "generate"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from workspace_command_generation import generate_workspace_command_packages, render_workspace_command_package_outputs  # noqa: E402


def _render_outputs(manifest: dict[str, object]) -> list[tuple[Path, str]]:
    return [(output.path, output.content) for output in render_workspace_command_package_outputs(manifest, repo_root=REPO_ROOT)]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate command package metadata from the command-package IR.")
    parser.add_argument("--check", action="store_true", help="Fail if generated command package files are stale.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    stale_outputs = generate_workspace_command_packages(repo_root=REPO_ROOT, check=bool(args.check))
    if args.check:
        if stale_outputs:
            for output in stale_outputs:
                print(f"{output} is stale; regenerate command packages.")
            return 1
        print("[ok] generated command packages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
