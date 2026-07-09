from __future__ import annotations

import importlib
import sys
from pathlib import Path

from agentic_workspace.session_logging import run_with_session_logging


def _load_main():
    try:
        return importlib.import_module("agentic_workspace._generated_cli_package_impl.cli").main
    except ModuleNotFoundError as exc:
        if exc.name != "agentic_workspace._generated_cli_package_impl":
            raise
        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root))
        return importlib.import_module("generated.workspace.python.cli").main


def _run_cli(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    generated_main = _load_main()
    return run_with_session_logging(args, generated_main)


main = _run_cli

__all__ = ["main"]
