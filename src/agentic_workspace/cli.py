from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Sequence
from datetime import UTC, datetime

from . import __version__
from .operations import OperationError
from .session_logging import append_session_event
from .workspace import Workspace


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentic-workspace")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="Resolve the one current operating decision.")
    start.add_argument("--target", default=".")
    start.add_argument("--task", default="")
    start.add_argument("--intent", help="Structured JSON intent interpreted by relevant source owners.")
    start.add_argument("--changed", action="append", default=[])
    start.add_argument("--claim", action="append", default=[])

    invoke = commands.add_parser("invoke", help="Execute an exact typed operation invocation.")
    invoke.add_argument("--target", default=".")
    invoke.add_argument("--invocation", required=True, help="JSON operation invocation returned by start.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    effective_argv = list(argv) if argv is not None else sys.argv[1:]
    args = _parser().parse_args(effective_argv)
    started_at = datetime.now(UTC).isoformat()
    started = time.perf_counter()
    try:
        workspace = Workspace(args.target)
        if args.command == "start":
            intent = json.loads(args.intent) if args.intent else None
            if intent is not None and not isinstance(intent, dict):
                raise ValueError("--intent must contain a JSON object")
            payload = workspace.start(intent=intent, task=args.task, changed_paths=args.changed, claims=args.claim)
        else:
            invocation = json.loads(args.invocation)
            if not isinstance(invocation, dict):
                raise ValueError("--invocation must contain a JSON object")
            payload = workspace.invoke(invocation)
    except (TypeError, ValueError, OperationError, json.JSONDecodeError) as exc:
        payload = {"kind": "agentic-workspace/error/v1", "status": "rejected", "message": str(exc)}
        exit_code = 2
    else:
        exit_code = 0 if payload.get("status") != "rejected" else 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    try:
        append_session_event(
            target=args.target,
            argv=effective_argv,
            command=args.command,
            payload=payload,
            exit_code=exit_code,
            started_at=started_at,
            duration_seconds=time.perf_counter() - started,
        )
    except (OSError, ValueError) as exc:
        print(f"agentic-workspace: session logging failed: {exc}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
