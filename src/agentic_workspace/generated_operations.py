# Generated from the external consumer profile. Do not edit.
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from .client import invoke_operation


def assignment_admit(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("assignment.admit", values, target=target, invocation=invocation, allow_runtime_backed=True)


def assignment_cleanup(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("assignment.cleanup", values, target=target, invocation=invocation, allow_runtime_backed=True)


def assignment_close(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("assignment.close", values, target=target, invocation=invocation, allow_runtime_backed=True)


def assignment_export(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("assignment.export", values, target=target, invocation=invocation, allow_runtime_backed=True)


def assignment_import(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("assignment.import", values, target=target, invocation=invocation, allow_runtime_backed=True)


def assignment_integrate(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("assignment.integrate", values, target=target, invocation=invocation, allow_runtime_backed=True)


def assignment_override(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("assignment.override", values, target=target, invocation=invocation, allow_runtime_backed=True)


def assignment_reassign(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("assignment.reassign", values, target=target, invocation=invocation, allow_runtime_backed=True)


def assignment_reject(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("assignment.reject", values, target=target, invocation=invocation, allow_runtime_backed=True)


def assignment_repair(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("assignment.repair", values, target=target, invocation=invocation, allow_runtime_backed=True)


def config_report(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("config.report", values, target=target, invocation=invocation, allow_runtime_backed=True)


def delegation_outcome_append(values: Mapping[str, Any], *, target: str | Path, invocation: Sequence[str] | None = None) -> dict[str, Any]:
    return invoke_operation("delegation-outcome.append", values, target=target, invocation=invocation, allow_runtime_backed=True)
