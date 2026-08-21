from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from agentic_workspace.runtime_compatibility import admit_runtime_compatibility, target_root_from_argv
from agentic_workspace.session_logging import run_with_session_logging


def _run_instructions_cli(argv: list[str]) -> int:
    from agentic_workspace.scoped_instructions import (
        _migration_advice,
        _render_text,
        _write_scaffold,
        inspect_instructions,
    )

    parser = argparse.ArgumentParser(
        prog="agentic-workspace instructions", description="Create, check, and explain scoped Markdown instructions."
    )
    parser.add_argument("--target", default=".")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    commands = parser.add_subparsers(dest="instruction_command")
    new = commands.add_parser("new", help="Scaffold one global or path-scoped Markdown instruction.")
    new.add_argument("name")
    new.add_argument("--paths", action="append", default=[])
    new.add_argument("--target", default=".")
    new.add_argument("--format", choices=("text", "json"), default="text")
    check = commands.add_parser("check", help="Validate instruction syntax and references without executing checks.")
    check.add_argument("--target", default=".")
    check.add_argument("--format", choices=("text", "json"), default="text")
    explain = commands.add_parser("explain", help="Explain task-specific applicability in repository vocabulary.")
    explain.add_argument("--task", default="")
    explain.add_argument("--changed", action="append", default=[])
    explain.add_argument("--verbose", action="store_true")
    explain.add_argument("--target", default=".")
    explain.add_argument("--format", choices=("text", "json"), default="text")
    migrate = commands.add_parser("migrate", help="Give non-destructive incremental migration guidance.")
    migrate.add_argument("--from", dest="source", required=True)
    migrate.add_argument("--target", default=".")
    migrate.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    root = Path(args.target).resolve()
    try:
        if args.instruction_command == "new":
            payload = _write_scaffold(root, name=args.name, paths=args.paths)
        elif args.instruction_command == "migrate":
            payload = _migration_advice(root, args.source)
        else:
            payload = inspect_instructions(
                root,
                task=getattr(args, "task", ""),
                changed_paths=getattr(args, "changed", []),
                include_ir=bool(getattr(args, "verbose", False)),
            )
    except (OSError, ValueError) as exc:
        payload = {"kind": "agentic-workspace/scoped-instruction-error/v1", "status": "failed", "message": str(exc)}
        print(json.dumps(payload, indent=2) if args.format == "json" else payload["message"])
        return 2
    print(json.dumps(payload, indent=2) if args.format == "json" else _render_text(payload))
    return 2 if args.instruction_command == "check" and payload["status"] == "invalid" else 0


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
    compatibility = admit_runtime_compatibility(target_root_from_argv(args))
    if compatibility["status"] != "admitted":
        json_mode = any(token == "--format=json" for token in args) or any(
            token == "--format" and index + 1 < len(args) and args[index + 1] == "json" for index, token in enumerate(args)
        )
        if json_mode:
            print(json.dumps(compatibility, indent=2))
        else:
            print(
                "agentic-workspace cannot interpret this repository with the active runtime.\n"
                f"Recovery: {compatibility['recovery_command']}",
                file=sys.stderr,
            )
        return 2
    if args[:1] == ["instructions"]:
        return _run_instructions_cli(args[1:])
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
                "message": str(exc),
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
