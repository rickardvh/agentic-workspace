from __future__ import annotations

import importlib
import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from agentic_workspace.config import WorkspaceUsageError
from agentic_workspace.evaluation import (
    append_observation_from_values,
    evaluation_summary,
    register_evaluation_from_values,
    transition_evaluation,
)
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


def _evaluation_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="agentic-workspace evaluation", description="Manage local-first workspace evaluations.")
    parser.add_argument("--target", default=".", help="Repository path.")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")
    subparsers = parser.add_subparsers(dest="evaluation_command", required=True)

    register = subparsers.add_parser("register", help="Register or update one evaluation definition.")
    register.add_argument("--evaluation-id", required=True)
    register.add_argument("--question", required=True)
    register.add_argument("--subject", default='{"type":"workspace-task"}')
    register.add_argument("--criteria", required=True, help="JSON object keyed by criterion id.")
    register.add_argument("--decision-owner", required=True, help="JSON object with id and class.")
    register.add_argument("--evidence-sources", required=True, help="Comma-separated evidence source ids.")
    register.add_argument("--report-sinks", required=True, help="Comma-separated report sink ids.")
    register.add_argument("--selectors", default="{}")
    register.add_argument("--collection-policy", default="{}")
    register.add_argument("--conclusion-policy", default="{}")
    register.add_argument("--action-policy", default="{}")

    observe = subparsers.add_parser("observe", help="Append one local observation.")
    observe.add_argument("--evaluation-id", required=True)
    observe.add_argument("--criterion", required=True)
    observe.add_argument("--result", required=True, choices=("supports", "contradicts", "mixed", "not-applicable", "unknown"))
    observe.add_argument("--evidence-refs", default="")
    observe.add_argument("--confidence", default="medium", choices=("low", "medium", "high"))
    observe.add_argument("--burden", default="medium", choices=("low", "medium", "high"))
    observe.add_argument("--context", default="{}")
    observe.add_argument("--finding", default="")
    observe.add_argument("--recommended-action", default="")

    status = subparsers.add_parser("status", help="Inspect derived evaluation status.")
    status.add_argument("--evaluation-id")

    transition = subparsers.add_parser("transition", help="Move an evaluation through a validated lifecycle transition.")
    transition.add_argument("--evaluation-id", required=True)
    transition.add_argument(
        "--lifecycle",
        required=True,
        choices=("collecting", "enough-signal", "satisfied", "contradicted", "inconclusive", "paused", "superseded", "archived"),
    )
    transition.add_argument("--reason", default="")
    return parser


def _emit_evaluation_result(payload: dict, output_format: str) -> int:
    if output_format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    print(f"Kind: {payload.get('kind', '')}")
    if "outcome" in payload:
        print(f"Outcome: {payload['outcome']}")
    if "evaluation_id" in payload:
        print(f"Evaluation: {payload['evaluation_id']}")
    if "path" in payload:
        print(f"Path: {payload['path']}")
    if payload.get("summaries"):
        for item in payload["summaries"]:
            print(
                f"- {item['evaluation_id']}: {item['lifecycle']}; "
                f"observations={item['coverage']['observation_count']}; "
                f"next={item['next_collection_action']}"
            )
    return 0


def _run_evaluation_cli(argv: list[str]) -> int:
    parser = _evaluation_parser()
    args = parser.parse_args(argv)
    target_root = Path(args.target).resolve()
    try:
        payload = _evaluation_payload(args, target_root=target_root)
    except WorkspaceUsageError as exc:
        if args.format == "json":
            print(json.dumps({"kind": "agentic-workspace/evaluation-error/v1", "status": "failed", "reason": str(exc)}, indent=2))
            return 2
        parser.error(str(exc))
    return _emit_evaluation_result(payload, args.format)


def _evaluation_payload(args: Namespace, *, target_root: Path) -> dict:
    values = vars(args)
    if args.evaluation_command == "register":
        return register_evaluation_from_values(target_root=target_root, values=values)
    if args.evaluation_command == "observe":
        return append_observation_from_values(target_root=target_root, values=values)
    if args.evaluation_command == "status":
        return evaluation_summary(target_root=target_root, evaluation_id=args.evaluation_id)
    if args.evaluation_command == "transition":
        return transition_evaluation(
            target_root=target_root,
            evaluation_id=args.evaluation_id,
            lifecycle=args.lifecycle,
            reason=args.reason,
        )
    raise WorkspaceUsageError(f"unsupported evaluation command: {args.evaluation_command}")


def _run_cli(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "evaluation":
        return _run_evaluation_cli(args[1:])
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
