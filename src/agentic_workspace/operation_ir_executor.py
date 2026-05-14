from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agentic_command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, run_operation_steps


class OperationIrExecutionError(RuntimeError):
    pass


def run_operation_ir(operation: dict[str, Any], args: argparse.Namespace) -> int:
    if operation.get("id") != "defaults.report":
        raise OperationIrExecutionError(f"unsupported operation IR contract: {operation.get('id')!r}")
    if operation.get("migration_status") != "runtime-consumed":
        raise OperationIrExecutionError(f"operation is not marked runtime-consumed: {operation.get('id')!r}")

    context = PrimitiveContext(cwd=Path.cwd())
    try:
        run_operation_steps(
            operation,
            initial_values={
                "format": getattr(args, "format", "text"),
                "profile": _diagnostic_profile(args, default="tiny"),
                "section": getattr(args, "section", None),
                "select": getattr(args, "select", None),
            },
            context=context,
            handlers={
                "workspace.defaults.load": _load_defaults,
                "workspace.defaults.select": _select_defaults,
                "output.emit": _emit_workspace_output,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc
    return 0


def _load_defaults(_values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    from agentic_workspace._runtime_cli import _defaults_payload

    return _defaults_payload()


def _select_defaults(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    from agentic_workspace._runtime_cli import _select_defaults_section, _select_payload_fields, _tiny_defaults_payload, serialise_value

    payload = values["defaults_payload"]
    section = values.get("section")
    if section is not None:
        payload = _select_defaults_section(payload, section=str(section))
    elif values.get("profile") == "tiny":
        payload = _tiny_defaults_payload(payload)
    select = values.get("select")
    if select is not None:
        payload = _select_payload_fields(payload, select=str(select), source_command="defaults")
    return serialise_value(payload)


def _emit_workspace_output(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> None:
    from agentic_workspace._runtime_cli import _emit_compact_answer_text, _emit_defaults

    payload = values["result"]
    output_format = str(values.get("format") or "text")
    if output_format == "json":
        print(json.dumps(payload, indent=2))
        return
    if values.get("section") is not None and isinstance(payload, dict):
        _emit_compact_answer_text(payload)
        return
    _emit_defaults(
        format_name=output_format,
        section=None,
        profile=str(values.get("profile") or "tiny"),
        select=str(values["select"]) if values.get("select") is not None else None,
    )


def _diagnostic_profile(args: argparse.Namespace, *, default: str) -> str:
    from agentic_workspace._runtime_cli import _diagnostic_profile as runtime_diagnostic_profile

    return runtime_diagnostic_profile(args, default=default)
