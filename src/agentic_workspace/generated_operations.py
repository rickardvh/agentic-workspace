# Generated from the external consumer profile. Do not edit.
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from .client import invoke_operation


def config_report(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("config.report", values, target=target, invocation=invocation, allow_runtime_backed=True)


def delegation_outcome_append(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("delegation-outcome.append", values, target=target, invocation=invocation, allow_runtime_backed=True)
