from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from agentic_command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, run_operation_steps

from repo_planning_bootstrap.installer import InstallResult, collect_status, format_actions, format_result_json


class OperationIrExecutionError(RuntimeError):
    pass


def run_operation_ir(operation: dict[str, Any], args: argparse.Namespace) -> int:
    if operation.get("id") not in {"planning.status.report"}:
        raise OperationIrExecutionError(f"unsupported operation IR contract: {operation.get('id')!r}")
    if operation.get("migration_status") != "runtime-consumed":
        raise OperationIrExecutionError(f"operation is not marked runtime-consumed: {operation.get('id')!r}")

    try:
        run_operation_steps(
            operation,
            initial_values={"target": getattr(args, "target", None), "format": getattr(args, "format", "text")},
            context=PrimitiveContext(cwd=Path.cwd(), roots={}),
            handlers={
                "planning.bootstrap.status.load": _load_planning_bootstrap_status,
                "output.emit": _emit_planning_operation_output,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc
    return 0


def _load_planning_bootstrap_status(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> InstallResult:
    return collect_status(target=values.get("target"))


def _emit_planning_operation_output(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> None:
    _emit_operation_output(values["result"], output_format=str(values.get("format") or "text"))


def _emit_operation_output(result: InstallResult, *, output_format: str) -> None:
    if output_format == "json":
        print(format_result_json(result))
        return

    print(f"Target: {result.target_root}")
    print(result.message)
    for line in format_actions(result.actions, result.target_root):
        print(f"- {line}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- [{warning['warning_class']}] {warning['path']}: {warning['message']}")
