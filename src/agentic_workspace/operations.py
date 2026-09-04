from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from .generated_semantics import IR, KINDS


class OperationError(RuntimeError):
    """Base error for typed operation transport failures."""


class StaleInvocationError(OperationError):
    """The invocation was compiled from an older source state."""


class OperationContractError(OperationError):
    """An operation or result violated its declared contract."""


class InterruptedOperationError(OperationError):
    """An interrupted effect requires its owner-specific recovery route."""


@dataclass(frozen=True)
class Operation:
    operation_id: str
    input_schema: Mapping[str, Any]
    effects: tuple[str, ...]
    handler: Callable[[dict[str, Any]], Mapping[str, Any]]
    recover: Callable[[dict[str, Any]], Mapping[str, Any] | None] | None = None
    accepted_handoffs: tuple[str, ...] = ()


class OperationDispatcher:
    """Dispatch one operation ID with only that operation's typed values."""

    def __init__(
        self,
        *,
        receipt_loader: Callable[[str], tuple[dict[str, Any], dict[str, Any]] | None] | None = None,
        receipt_writer: Callable[[str, dict[str, Any], dict[str, Any]], None] | None = None,
        journal_loader: Callable[[str], dict[str, Any] | None] | None = None,
        journal_writer: Callable[[str, dict[str, Any]], None] | None = None,
        journal_clearer: Callable[[str], None] | None = None,
        handoff_notifier: Callable[[str, str, Mapping[str, Any], Mapping[str, Any]], None] | None = None,
    ) -> None:
        self._operations: dict[str, Operation] = {}
        self._receipts: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
        self._receipt_loader = receipt_loader
        self._receipt_writer = receipt_writer
        self._journal_loader = journal_loader
        self._journal_writer = journal_writer
        self._journal_clearer = journal_clearer
        self._handoff_notifier = handoff_notifier

    def register(self, operation: Operation) -> None:
        if not operation.operation_id:
            raise OperationContractError("operation_id is required")
        if operation.operation_id in self._operations:
            raise OperationContractError(f"duplicate operation: {operation.operation_id}")
        self._operations[operation.operation_id] = operation

    @property
    def operation_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._operations))

    def operation(self, operation_id: str) -> Operation:
        """Return the registered contract used for admission and synchronization."""
        operation = self._operations.get(operation_id)
        if operation is None:
            raise OperationContractError(f"unknown operation: {operation_id}")
        return operation

    def invoke(
        self,
        invocation: Mapping[str, Any],
        *,
        resolve_decision: Callable[[], Mapping[str, Any]],
    ) -> dict[str, Any]:
        if invocation.get("kind") != KINDS["invocation"]:
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
        request_identity = {
            "operation_id": operation_id,
            "arguments": dict(arguments),
            "revision": expected_revision,
            "source_owner": invocation.get("source_owner"),
            "decision_response": dict(invocation["decision_response"])
            if isinstance(invocation.get("decision_response"), Mapping)
            else None,
        }
        if invocation.get("handoff_source") is not None:
            request_identity["handoff_source"] = invocation.get("handoff_source")
        previous = self._receipts.get(key)
        if previous is None and self._receipt_loader is not None:
            previous = self._receipt_loader(key)
        if previous is not None:
            previous_identity, previous_result = previous
            if previous_identity != request_identity:
                raise OperationContractError("idempotency key was already used for another invocation")
            return dict(previous_result)

        interrupted = self._journal_loader(key) if self._journal_loader is not None else None
        if interrupted is not None:
            if interrupted.get("request") != request_identity:
                raise OperationContractError("idempotency key has an interrupted different invocation")
            raw = interrupted.get("outcome")
            if not isinstance(raw, Mapping) and operation.recover is not None:
                raw = operation.recover(dict(arguments))
            if not isinstance(raw, Mapping):
                owner = invocation.get("source_owner") or operation_id
                raise InterruptedOperationError(
                    f"interrupted {operation_id} has uncertain effects; recover through owner {owner} before retry"
                )
            return self._finish(
                key,
                request_identity,
                operation,
                raw,
                expected_revision,
                resolve_decision,
            )

        current = dict(resolve_decision())
        if not expected_revision or expected_revision != current.get("input_revision"):
            raise StaleInvocationError("source state changed; resolve a fresh operating decision")
        current_action = current.get("primary_action")
        current_decision = current.get("decision_request")
        action_matches = isinstance(current_action, Mapping) and current_action.get("operation_id") == operation_id
        decision_matches = (
            isinstance(current_decision, Mapping) and current_decision.get("response_operation_id") == operation_id
        )
        if not action_matches and not decision_matches:
            raise StaleInvocationError("operation is no longer the current source-owned action")
        if action_matches and isinstance(current_action, Mapping):
            authoritative_owner = current_action.get("source_owner")
        elif isinstance(current_decision, Mapping):
            authoritative_owner = current_decision.get("owner")
        else:  # pragma: no cover - guarded by action_matches/decision_matches above
            raise StaleInvocationError("operation is no longer the current source-owned action")
        if invocation.get("source_owner") != authoritative_owner:
            raise OperationContractError("invocation source_owner does not match the current source owner")
        authoritative_handoff = current_action.get("handoff_source") if action_matches else None
        if invocation.get("handoff_source") != authoritative_handoff:
            raise OperationContractError("invocation handoff_source does not match the current handoff source")
        if decision_matches:
            response = invocation.get("decision_response")
            if not isinstance(response, Mapping):
                raise OperationContractError("bounded decision invocation requires decision_response")
            expected_response = {
                "id": current_decision.get("id"),
                "owner": current_decision.get("owner"),
                "revision": current_decision.get("revision"),
                "authority": current_decision.get("authority"),
            }
            if any(response.get(field) != value for field, value in expected_response.items()):
                raise StaleInvocationError("bounded decision response owner, revision, or authority is stale")
            answer = response.get("answer")
            if "answer" in arguments and arguments.get("answer") != answer:
                raise OperationContractError("typed decision answer differs from decision_response")
            choices = current_decision.get("choices", [])
            choice_ids = {choice.get("id") for choice in choices if isinstance(choice, Mapping)}
            if choices and answer not in choice_ids and current_decision.get("allow_open") is not True:
                raise OperationContractError("bounded decision answer is not one of the current choices")
            if not choices and (
                current_decision.get("allow_open") is not True or not isinstance(answer, str) or not answer
            ):
                raise OperationContractError("bounded open judgment requires a non-empty answer")

        if self._journal_writer is not None:
            self._journal_writer(key, {"phase": "prepared", "request": request_identity})
        raw_outcome = operation.handler(dict(arguments))
        if not isinstance(raw_outcome, Mapping):
            raise OperationContractError("operation handler must return an object")
        if self._journal_writer is not None:
            self._journal_writer(
                key,
                {"phase": "effect-applied", "request": request_identity, "outcome": dict(raw_outcome)},
            )
        return self._finish(
            key,
            request_identity,
            operation,
            raw_outcome,
            expected_revision,
            resolve_decision,
        )

    def _finish(
        self,
        key: str,
        request_identity: dict[str, Any],
        operation: Operation,
        raw_outcome: Mapping[str, Any],
        expected_revision: str,
        resolve_decision: Callable[[], Mapping[str, Any]],
    ) -> dict[str, Any]:
        if not isinstance(raw_outcome, Mapping):
            raise OperationContractError("operation handler must return an object")
        reported_effects = raw_outcome.get("effects", [])
        if not isinstance(reported_effects, list) or any(
            effect not in operation.effects for effect in reported_effects
        ):
            raise OperationContractError("operation result widened its declared effects")
        status = str(raw_outcome.get("status") or "")
        if status not in set(IR["operation"]["result_statuses"]):
            raise OperationContractError("operation result status must be applied, unchanged, or rejected")

        handoff_source = request_identity.get("handoff_source")
        if status in {"applied", "unchanged"} and handoff_source and self._handoff_notifier is not None:
            self._handoff_notifier(
                str(handoff_source), operation.operation_id, request_identity["arguments"], raw_outcome
            )
        next_decision = dict(resolve_decision())
        result = {
            "kind": KINDS["result"],
            "operation_id": operation.operation_id,
            "status": status,
            "effects": list(reported_effects),
            "value": raw_outcome.get("value"),
            "input_revision": expected_revision,
            "next_decision": next_decision,
        }
        self._receipts[key] = (request_identity, result)
        if self._receipt_writer is not None:
            self._receipt_writer(key, request_identity, result)
        if self._journal_clearer is not None:
            self._journal_clearer(key)
        return dict(result)
