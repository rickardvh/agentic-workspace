from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from . import __version__
from .operations import OperationError
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
    args = _parser().parse_args(list(argv) if argv is not None else None)
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
        print(
            json.dumps(
                {"kind": "agentic-workspace/error/v1", "status": "rejected", "message": str(exc)}, sort_keys=True
            )
        )
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") != "rejected" else 2


if __name__ == "__main__":
    raise SystemExit(main())
