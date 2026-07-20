from __future__ import annotations

import importlib
import json
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
    try:
        return run_with_session_logging(args, generated_main)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - the root CLI owns the last-resort recovery envelope
        command = " ".join(args)
        json_mode = any(token == "--format=json" for token in args) or any(
            token == "--format" and index + 1 < len(args) and args[index + 1] == "json" for index, token in enumerate(args)
        )
        if json_mode:
            payload = {
                "kind": "agentic-workspace/runtime-error/v1",
                "status": "failed",
                "command": command,
                "exit_status": 1,
                "exception_class": type(exc).__name__,
                "failure_class": "unexpected-runtime-exception",
                "safe_to_retry": False,
                "safe_recovery": "Report the exception class and command; rerun only after correcting the package failure or with an explicit debug route.",
                "completion_boundary": "command-did-not-complete",
            }
            print(json.dumps(payload, indent=2))
        else:
            print(
                f"agentic-workspace failed ({type(exc).__name__}): {exc}\n"
                "The command did not complete. Fix or report the package failure before retrying.",
                file=sys.stderr,
            )
        return 1


main = _run_cli

__all__ = ["main"]
