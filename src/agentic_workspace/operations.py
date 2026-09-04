from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator


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

    def __init__(
        self,
        *,
        receipt_loader: Callable[[str], tuple[dict[str, Any], dict[str, Any]] | None] | None = None,
        receipt_writer: Callable[[str, dict[str, Any], dict[str, Any]], None] | None = None,
    ) -> None:
        self._operations: dict[str, Operation] = {}
        self._receipts: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
        self._receipt_loader = receipt_loader
        self._receipt_writer = receipt_writer

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

        expected_revision = str(invocation.get("expected_input_revision") or "")
        arguments = invocation.get("arguments", {})
        if not isinstance(arguments, Mapping):
            raise OperationContractError("arguments must be an object")
        errors = sorted(
            Draft202012Validator(operation.input_schema).iter_errors(dict(arguments)),
            key=lambda error: list(error.path),
        )
        if errors:
            raise OperationContractError(errors[0].message)

        invocation_effects = invocation.get("effects", [])
        if not isinstance(invocation_effects, list) or tuple(invocation_effects) != operation.effects:
            raise OperationContractError("invocation effects do not match the operation contract")
        key = str(invocation.get("idempotency_key") or "")
        if not key:
            raise OperationContractError("idempotency_key is required")
        request_identity = {"operation_id": operation_id, "arguments": dict(arguments), "revision": expected_revision}
        previous = self._receipts.get(key)
        if previous is None and self._receipt_loader is not None:
            previous = self._receipt_loader(key)
        if previous is not None:
            previous_identity, previous_result = previous
            if previous_identity != request_identity:
                raise OperationContractError("idempotency key was already used for another invocation")
            return dict(previous_result)

        current = dict(resolve_decision())
        if not expected_revision or expected_revision != current.get("input_revision"):
            raise StaleInvocationError("source state changed; resolve a fresh operating decision")
        current_action = current.get("primary_action")
        if not isinstance(current_action, Mapping) or current_action.get("operation_id") != operation_id:
            raise StaleInvocationError("operation is no longer the current source-owned action")

        raw_outcome = operation.handler(dict(arguments))
        if not isinstance(raw_outcome, Mapping):
            raise OperationContractError("operation handler must return an object")
        reported_effects = raw_outcome.get("effects", [])
        if not isinstance(reported_effects, list) or any(
            effect not in operation.effects for effect in reported_effects
        ):
            raise OperationContractError("operation result widened its declared effects")
        status = str(raw_outcome.get("status") or "")
        if status not in {"applied", "unchanged", "rejected"}:
            raise OperationContractError("operation result status must be applied, unchanged, or rejected")

        next_decision = dict(resolve_decision())
        result = {
            "kind": "agentic-workspace/operation-result/v1",
            "operation_id": operation_id,
            "status": status,
            "effects": list(reported_effects),
            "value": raw_outcome.get("value"),
            "input_revision": expected_revision,
            "next_decision": next_decision,
        }
        self._receipts[key] = (request_identity, result)
        if self._receipt_writer is not None:
            self._receipt_writer(key, request_identity, result)
        return dict(result)
