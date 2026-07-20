from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from agentic_workspace.config import WorkspaceUsageError
from agentic_workspace.evaluation import (
    append_observation_from_values,
    evaluation_summary,
    register_evaluation_from_values,
    transition_evaluation,
)
from agentic_workspace.session_logging import run_with_session_logging

_EVALUATION_COMMANDS = {"register", "observe", "status", "transition"}
_OBSERVATION_RESULTS = {"supports", "contradicts", "mixed", "not-applicable", "unknown"}
_CONFIDENCE_VALUES = {"low", "medium", "high"}
_BURDEN_VALUES = {"low", "medium", "high"}
_EVALUATION_LIFECYCLES = {
    "collecting",
    "enough-signal",
    "satisfied",
    "contradicted",
    "inconclusive",
    "paused",
    "superseded",
    "archived",
}


def _load_main():
    try:
        return importlib.import_module("agentic_workspace._generated_cli_package_impl.cli").main
    except ModuleNotFoundError as exc:
        if exc.name != "agentic_workspace._generated_cli_package_impl":
            raise
        repo_root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(repo_root))
        return importlib.import_module("generated.workspace.python.cli").main


def _evaluation_error(message: str, *, output_format: str = "text") -> int:
    if output_format == "json":
        print(json.dumps({"kind": "agentic-workspace/evaluation-error/v1", "status": "failed", "reason": message}, indent=2))
    else:
        print(f"agentic-workspace evaluation: {message}", file=sys.stderr)
    return 2


def _consume_option_value(tokens: list[str], index: int, flag: str) -> tuple[str | None, int, str | None]:
    token = tokens[index]
    if token.startswith(f"{flag}="):
        return token.split("=", 1)[1], index + 1, None
    if index + 1 >= len(tokens):
        return None, index + 1, f"{flag} requires a value"
    return tokens[index + 1], index + 2, None


def _parse_evaluation_options(
    tokens: list[str],
    *,
    value_options: dict[str, str],
    defaults: dict[str, object],
    choices: dict[str, set[str]] | None = None,
) -> tuple[dict[str, object], str | None]:
    values = dict(defaults)
    choices = choices or {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        matching_equals = next((flag for flag in value_options if token.startswith(f"{flag}=")), None)
        if token in value_options or matching_equals:
            flag = matching_equals or token
            value, index, error = _consume_option_value(tokens, index, flag)
            if error is not None:
                return values, error
            name = value_options[flag]
            if name in choices and value not in choices[name]:
                return values, f"{flag} must be one of: {', '.join(sorted(choices[name]))}"
            values[name] = value
            continue
        return values, f"unexpected argument: {token}"
    return values, None


def _split_evaluation_command(tokens: list[str]) -> tuple[dict[str, object], str, list[str], str | None]:
    values: dict[str, object] = {"target": ".", "format": "text"}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _EVALUATION_COMMANDS:
            return values, token, tokens[index + 1 :], None
        if token in {"--target", "--format"} or token.startswith("--target=") or token.startswith("--format="):
            flag = "--target" if token == "--target" or token.startswith("--target=") else "--format"
            value, index, error = _consume_option_value(tokens, index, flag)
            if error is not None:
                return values, "", [], error
            if flag == "--format" and value not in {"text", "json"}:
                return values, "", [], "--format must be one of: json, text"
            values["target" if flag == "--target" else "format"] = value
            continue
        return values, "", [], f"expected one of: {', '.join(sorted(_EVALUATION_COMMANDS))}"
    return values, "", [], f"expected one of: {', '.join(sorted(_EVALUATION_COMMANDS))}"


def _require_evaluation_options(values: dict[str, object], required: list[str]) -> str | None:
    for name in required:
        if not str(values.get(name) or "").strip():
            return f"--{name.replace('_', '-')} is required"
    return None


def _emit_evaluation_result(payload: dict[str, object], output_format: str) -> int:
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
    summaries = payload.get("summaries")
    if isinstance(summaries, list):
        for item in summaries:
            if not isinstance(item, dict):
                continue
            coverage = item.get("coverage", {})
            observation_count = coverage.get("observation_count", 0) if isinstance(coverage, dict) else 0
            print(
                f"- {item.get('evaluation_id', '')}: {item.get('lifecycle', '')}; "
                f"observations={observation_count}; next={item.get('next_collection_action', '')}"
            )
    return 0


def _evaluation_command_values(parent: dict[str, object], command: str, rest: list[str]) -> tuple[dict[str, object], str | None]:
    common = {"target": parent["target"], "format": parent["format"]}
    if command == "register":
        values, error = _parse_evaluation_options(
            rest,
            value_options={
                "--evaluation-id": "evaluation_id",
                "--question": "question",
                "--subject": "subject",
                "--criteria": "criteria",
                "--decision-owner": "decision_owner",
                "--evidence-sources": "evidence_sources",
                "--report-sinks": "report_sinks",
                "--selectors": "selectors",
                "--collection-policy": "collection_policy",
                "--conclusion-policy": "conclusion_policy",
                "--action-policy": "action_policy",
            },
            defaults={
                **common,
                "subject": '{"type":"workspace-task"}',
                "selectors": "{}",
                "collection_policy": "{}",
                "conclusion_policy": "{}",
                "action_policy": "{}",
            },
        )
        return values, error or _require_evaluation_options(
            values, ["evaluation_id", "question", "criteria", "decision_owner", "evidence_sources", "report_sinks"]
        )
    if command == "observe":
        values, error = _parse_evaluation_options(
            rest,
            value_options={
                "--evaluation-id": "evaluation_id",
                "--criterion": "criterion",
                "--result": "result",
                "--evidence-refs": "evidence_refs",
                "--confidence": "confidence",
                "--burden": "burden",
                "--context": "context",
                "--finding": "finding",
                "--recommended-action": "recommended_action",
            },
            defaults={
                **common,
                "evidence_refs": "",
                "confidence": "medium",
                "burden": "medium",
                "context": "{}",
                "finding": "",
                "recommended_action": "",
            },
            choices={"result": _OBSERVATION_RESULTS, "confidence": _CONFIDENCE_VALUES, "burden": _BURDEN_VALUES},
        )
        return values, error or _require_evaluation_options(values, ["evaluation_id", "criterion", "result"])
    if command == "status":
        return _parse_evaluation_options(
            rest,
            value_options={"--evaluation-id": "evaluation_id"},
            defaults={**common, "evaluation_id": None},
        )
    return _parse_evaluation_options(
        rest,
        value_options={"--evaluation-id": "evaluation_id", "--lifecycle": "lifecycle", "--reason": "reason"},
        defaults={**common, "reason": ""},
        choices={"lifecycle": _EVALUATION_LIFECYCLES},
    )


def _evaluation_payload(command: str, values: dict[str, object]) -> dict[str, object]:
    target_root = Path(str(values.get("target") or ".")).resolve()
    if command == "register":
        return register_evaluation_from_values(target_root=target_root, values=values)
    if command == "observe":
        return append_observation_from_values(target_root=target_root, values=values)
    if command == "status":
        evaluation_id = values.get("evaluation_id")
        return evaluation_summary(target_root=target_root, evaluation_id=str(evaluation_id) if evaluation_id else None)
    return transition_evaluation(
        target_root=target_root,
        evaluation_id=str(values.get("evaluation_id") or ""),
        lifecycle=str(values.get("lifecycle") or ""),
        reason=str(values.get("reason") or ""),
    )


def _run_evaluation_cli(argv: list[str]) -> int:
    parent, command, rest, split_error = _split_evaluation_command(argv)
    output_format = str(parent.get("format") or "text")
    if split_error is not None:
        return _evaluation_error(split_error, output_format=output_format)
    values, parse_error = _evaluation_command_values(parent, command, rest)
    output_format = str(values.get("format") or output_format)
    if parse_error is not None:
        return _evaluation_error(parse_error, output_format=output_format)
    try:
        payload = _evaluation_payload(command, values)
    except WorkspaceUsageError as exc:
        return _evaluation_error(str(exc), output_format=output_format)
    return _emit_evaluation_result(payload, output_format)


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
