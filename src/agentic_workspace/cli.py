from __future__ import annotations

import subprocess
import sys

from agentic_workspace.native_core import cli_binary


def _run_cli(argv: list[str] | None = None) -> int:
    """Optional Python entry point; the paired Rust executable owns the command."""
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        return subprocess.call([str(cli_binary()), *args])
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


main = _run_cli

__all__ = ["main"]
