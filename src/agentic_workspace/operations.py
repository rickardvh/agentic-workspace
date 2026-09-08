from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from threading import Lock
from typing import Any

from jsonschema import Draft202012Validator

from agentic_workspace.decision import (
    DecisionContractError,
    admit_attempt,
    admit_stored_attempt,
    commit_attempt,
    commit_stored_attempt,
    operation_result,
)


class OperationError(RuntimeError):
    """Base error for typed operation transport failures."""


class StaleInvocationError(OperationError):
    """The invocation was compiled from an older source state."""


class OperationContractError(OperationError):
    """An operation or result violated its declared contract."""


class UncertainOperationError(OperationError):
    """The exact attempt may have effected; owner recovery is required."""

    def __init__(self, admission: dict[str, Any]) -> None:
        self.admission = admission
        super().__init__(f"operation attempt {admission['attempt_id']} is uncertain; owner recovery required")


@dataclass(frozen=True)
class Operation:
    operation_id: str
    input_schema: Mapping[str, Any]
    effects: tuple[str, ...]
    handler: Callable[[dict[str, Any]], Mapping[str, Any]]


class OperationDispatcher:
    """Dispatch one operation ID with only that operation's typed values."""

    def __init__(self) -> None:
        self._operations: dict[str, Operation] = {}
        self._attempts: dict[str, dict[str, Any]] = {}
        self._custody: dict[str, dict[str, Any]] = {}
        self._admission_lock = Lock()

    def register(self, operation: Operation) -> None:
        if not operation.operation_id:
            raise OperationContractError("operation_id is required")
        if operation.operation_id in self._operations:
            raise OperationContractError(f"duplicate operation: {operation.operation_id}")
        self._operations[operation.operation_id] = operation

    @property
    def operation_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._operations))

    def invoke(
        self,
        invocation: Mapping[str, Any],
        *,
        resolve_decision: Callable[[], Mapping[str, Any]],
        custody: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if invocation.get("kind") != "agentic-workspace/operation-invocation/v1":
            raise OperationContractError("unsupported invocation kind")
        operation_id = str(invocation.get("operation_id") or "")
        operation = self._operations.get(operation_id)
        if operation is None:
            raise OperationContractError(f"unknown operation: {operation_id}")

        arguments = invocation.get("arguments", {})
        if not isinstance(arguments, Mapping):
            raise OperationContractError("arguments must be an object")
        errors = sorted(Draft202012Validator(operation.input_schema).iter_errors(dict(arguments)), key=lambda error: list(error.path))
        if errors:
            raise OperationContractError(errors[0].message)

        invocation_effects = invocation.get("effects", [])
        if not isinstance(invocation_effects, list) or tuple(invocation_effects) != operation.effects:
            raise OperationContractError("invocation effects do not match the operation contract")
        key = str(invocation.get("idempotency_key") or "")
        if not key:
            raise OperationContractError("idempotency_key is required")
        request_identity = deepcopy(dict(invocation))
        # Serialize only process-local admission, never the handler or resolution.
        try:
            current = dict(resolve_decision())
        except Exception:
            current = None
        with self._admission_lock:
            previous = self._attempts.get(key)
            retained = deepcopy(dict(custody)) if custody is not None else self._custody.get(key)
            try:
                admission = (
                    admit_stored_attempt(str(arguments.get("target") or ""), current or {}, request_identity, retained)
                    if operation.effects
                    else admit_attempt(current or {}, request_identity, previous)
                )
            except DecisionContractError as error:
                if previous:
                    raise OperationContractError("idempotency key was already used; " + str(error)) from error
                raise StaleInvocationError(str(error)) from error
            record = admission["record"]
            self._attempts[key] = record
            if operation.effects:
                self._custody[key] = deepcopy(admission["custody"])
        if admission["disposition"] == "uncertain":
            raise UncertainOperationError(admission)
        if admission["disposition"] == "replay":
            result = operation_result(record["invocation"], record["outcome"], current)
            if operation.effects:
                result["custody"] = deepcopy(admission["custody"])
            return result

        try:
            raw_outcome = operation.handler(dict(arguments))
            if not isinstance(raw_outcome, Mapping):
                raise OperationContractError("operation handler must return an object")
            if operation.effects:
                stored = commit_stored_attempt(str(arguments["target"]), admission["custody"], deepcopy(dict(raw_outcome)))
                committed = stored["record"]
            else:
                committed = commit_attempt(record, deepcopy(dict(raw_outcome)))
        except Exception as error:
            uncertain = admit_attempt(current or {}, request_identity, record)
            if operation.effects:
                uncertain["custody"] = deepcopy(admission["custody"])
            raise UncertainOperationError(uncertain) from error
        with self._admission_lock:
            self._attempts[key] = committed
            if operation.effects:
                self._custody[key] = deepcopy(stored["custody"])
        try:
            next_decision = dict(resolve_decision())
        except Exception:
            next_decision = None
        result = operation_result(committed["invocation"], committed["outcome"], next_decision)
        if operation.effects:
            result["custody"] = deepcopy(stored["custody"])
        return result
