from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from agentic_workspace.decision import DecisionContractError, admit_invocation, operation_result


class OperationError(RuntimeError):
    """Base error for typed operation transport failures."""


class StaleInvocationError(OperationError):
    """The invocation was compiled from an older source state."""


class OperationContractError(OperationError):
    """An operation or result violated its declared contract."""


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
        self._receipts: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}

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
        previous = self._receipts.get(key)
        try:
            current = dict(resolve_decision())
        except Exception:
            if previous is None:
                raise
            current = None
        try:
            admission = admit_invocation(current or {}, invocation, previous[0] if previous else None)
        except DecisionContractError as error:
            if previous:
                raise OperationContractError("idempotency key was already used; " + str(error)) from error
            raise StaleInvocationError(str(error)) from error
        if admission["disposition"] == "replay" and previous is not None:
            return operation_result(previous[0], previous[1], current)

        raw_outcome = operation.handler(dict(arguments))
        if not isinstance(raw_outcome, Mapping):
            raise OperationContractError("operation handler must return an object")
        outcome = deepcopy(dict(raw_outcome))
        try:
            # Validate before retaining committed evidence. Never retain a view.
            operation_result(request_identity, outcome, None)
        except DecisionContractError as error:
            raise OperationContractError(str(error)) from error
        self._receipts[key] = (request_identity, outcome)
        try:
            next_decision = dict(resolve_decision())
        except Exception:
            # The effect remains committed even when current sources cannot resolve.
            next_decision = None
        return operation_result(request_identity, outcome, next_decision)
