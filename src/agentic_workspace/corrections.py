from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .builtin_modules import MEMORY_STATE, PLANNING_STATE, _json, _state_revision
from .generated_semantics import operation_contract, semantic_digest
from .modules import Module
from .operations import Operation


@dataclass(frozen=True)
class TrustedCorrection:
    """A correction admitted by a host capability, never by caller JSON."""

    correction_id: str
    statement: str
    subject: Mapping[str, Any]
    applicability: Mapping[str, Any]
    provenance: Mapping[str, Any]
    future_usefulness: str
    existing_owner: Mapping[str, Any] | None = None
    deterministic_owner_failure: Mapping[str, Any] | None = None

    @property
    def revision(self) -> str:
        return semantic_digest(
            {
                "correction_id": self.correction_id,
                "statement": self.statement,
                "subject": dict(self.subject),
                "applicability": dict(self.applicability),
                "provenance": dict(self.provenance),
                "future_usefulness": self.future_usefulness,
                "existing_owner": dict(self.existing_owner or {}),
                "deterministic_owner_failure": dict(self.deterministic_owner_failure or {}),
            }
        )


class TrustedCorrectionIngress:
    """Host-held custody for explicit human corrections.

    The capability is the Python object itself. Ordinary intent JSON and CLI
    arguments cannot mint entries in it or assert human provenance.
    """

    def __init__(self, *, transport: str, principal: str) -> None:
        if not transport or not principal:
            raise ValueError("trusted correction ingress requires transport and principal")
        self._transport = transport
        self._principal = principal
        self._pending: dict[str, TrustedCorrection] = {}
        self._completed: set[str] = set()

    def observe(
        self,
        *,
        correction_id: str,
        statement: str,
        subject: Mapping[str, Any],
        applicability: Mapping[str, Any] | None = None,
        future_usefulness: str = "unspecified",
        existing_owner: Mapping[str, Any] | None = None,
        deterministic_owner_failure: Mapping[str, Any] | None = None,
    ) -> TrustedCorrection:
        if not correction_id or not statement or not subject:
            raise ValueError("a correction requires stable identity, statement, and subject")
        if future_usefulness not in {"retain", "do-not-retain", "unspecified"}:
            raise ValueError("future_usefulness must be retain, do-not-retain, or unspecified")
        correction = TrustedCorrection(
            correction_id=correction_id,
            statement=statement,
            subject=dict(subject),
            applicability=dict(applicability or {}),
            provenance={"authority": "human", "transport": self._transport, "principal": self._principal},
            future_usefulness=future_usefulness,
            existing_owner=dict(existing_owner) if existing_owner else None,
            deterministic_owner_failure=dict(deterministic_owner_failure) if deterministic_owner_failure else None,
        )
        previous = self._pending.get(correction_id)
        if previous is not None and previous != correction:
            raise ValueError("correction identity was already admitted with different content")
        if correction_id not in self._completed:
            self._pending[correction_id] = correction
        return correction

    def module(self) -> Module:
        contract = operation_contract("correction.disposition")
        return Module(
            name="correction",
            owns=("correction-custody",),
            required_capabilities=("operation/durable-commit", "operation/owner-handoff"),
            contribute=self._contribute,
            operations=(
                Operation(
                    "correction.disposition",
                    contract["input"],
                    tuple(contract["effects"]),
                    self._disposition,
                ),
            ),
            currentness=self._currentness,
            handoff_complete=self._handoff_complete,
        )

    def _currentness(self, context: Mapping[str, Any]) -> str:
        root = Path(str(context["target"])).resolve()
        return semantic_digest(
            {
                "pending": {key: value.revision for key, value in sorted(self._pending.items())},
                "completed": sorted(self._completed),
                "memory": _state_revision(root, MEMORY_STATE),
                "planning": _state_revision(root, PLANNING_STATE),
            }
        )

    @staticmethod
    def _payload(correction: TrustedCorrection) -> dict[str, Any]:
        return {
            "correction_id": correction.correction_id,
            "statement": correction.statement,
            "subject": dict(correction.subject),
            "applicability": dict(correction.applicability),
            "provenance": dict(correction.provenance),
            "future_usefulness": correction.future_usefulness,
            "existing_owner": dict(correction.existing_owner or {}),
            "deterministic_owner_failure": dict(correction.deterministic_owner_failure or {}),
        }

    @staticmethod
    def _memory_key(correction: TrustedCorrection) -> str:
        return f"human-correction:{correction.correction_id}"

    def _effect_applied(self, root: Path, correction: TrustedCorrection, disposition: str) -> bool:
        if disposition == "memory":
            records = _json(root / MEMORY_STATE).get("records", [])
            return any(
                isinstance(item, Mapping)
                and item.get("key") == self._memory_key(correction)
                and item.get("value") == correction.statement
                and item.get("correction_revision") == correction.revision
                and item.get("provenance") == "trusted-human-correction:" + correction.revision
                for item in records
            )
        if disposition == "owner-repair":
            subjects = _json(root / PLANNING_STATE).get("subjects", {})
            subject = (
                subjects.get(f"correction-repair:{correction.correction_id}")
                if isinstance(subjects, Mapping)
                else None
            )
            return isinstance(subject, Mapping) and f"correction_revision={correction.revision}" in subject.get(
                "constraints", []
            )
        return False

    def _contribute(self, context: Mapping[str, Any]) -> dict[str, Any] | None:
        if not self._pending:
            return None
        correction_id = sorted(self._pending)[0]
        correction = self._pending[correction_id]
        root = Path(str(context["target"])).resolve()
        if correction.existing_owner:
            disposition, owner = "already-owned", "repository"
        elif correction.deterministic_owner_failure:
            disposition, owner = "owner-repair", "planning"
        elif correction.future_usefulness == "do-not-retain":
            disposition, owner = "no-new-durable-record", "correction"
        else:
            disposition, owner = "memory", "memory"
        evidence = correction.existing_owner or correction.deterministic_owner_failure or {}
        owner_revision = str(evidence.get("revision") or "")
        if self._effect_applied(root, correction, disposition):
            self._pending.pop(correction.correction_id, None)
            self._completed.add(correction.correction_id)
            return None
        if disposition == "memory":
            operation_id = "memory.accept-correction"
            effects = ["memory-state"]
            arguments = {
                "target": str(root),
                "correction": self._payload(correction),
                "correction_revision": correction.revision,
                "expected_state_revision": _state_revision(root, MEMORY_STATE),
            }
        elif disposition == "owner-repair":
            operation_id = "planning.accept-correction-failure"
            effects = ["planning-state"]
            arguments = {
                "target": str(root),
                "correction": self._payload(correction),
                "correction_revision": correction.revision,
                "owner_ref": str(evidence.get("ref") or ""),
                "owner_revision": owner_revision,
                "expected_state_revision": _state_revision(root, PLANNING_STATE),
            }
        elif disposition == "already-owned":
            operation_id = "repository.accept-correction"
            effects = []
            arguments = {
                "target": str(root),
                "correction": self._payload(correction),
                "correction_revision": correction.revision,
                "owner_ref": str(evidence.get("ref") or ""),
                "owner_revision": owner_revision,
            }
        else:
            operation_id = "correction.disposition"
            effects = ["correction-disposition"]
            arguments = {
                "target": str(root),
                "correction_id": correction.correction_id,
                "correction_revision": correction.revision,
                "disposition": disposition,
                "owner": owner,
                "owner_revision": owner_revision,
            }
        return {
            "revision": correction.revision,
            "facts": {
                "id": correction.correction_id,
                "subject": dict(correction.subject),
                "applicability": dict(correction.applicability),
                "provenance": dict(correction.provenance),
                "future_usefulness": correction.future_usefulness,
                "disposition": disposition,
                "owner": owner,
                "owner_revision": owner_revision,
            },
            "actions": [
                {
                    "operation_id": operation_id,
                    "arguments": arguments,
                    "effects": effects,
                    "priority": 100,
                }
            ],
        }

    def _disposition(self, arguments: dict[str, Any]) -> dict[str, Any]:
        correction = self._pending.get(arguments["correction_id"])
        if correction is None or correction.revision != arguments["correction_revision"]:
            return {"status": "rejected", "effects": [], "value": {"reason": "stale-correction"}}
        disposition, owner, owner_revision = "no-new-durable-record", "correction", ""
        if correction.future_usefulness != "do-not-retain":
            return {"status": "rejected", "effects": [], "value": {"reason": "owner-operation-required"}}
        if (arguments["disposition"], arguments["owner"], arguments["owner_revision"]) != (
            disposition,
            owner,
            owner_revision,
        ):
            return {"status": "rejected", "effects": [], "value": {"reason": "correction-route-mismatch"}}

        value: dict[str, Any] = {
            "id": correction.correction_id,
            "revision": correction.revision,
            "subject": dict(correction.subject),
            "applicability": dict(correction.applicability),
            "provenance": dict(correction.provenance),
            "future_usefulness": correction.future_usefulness,
            "disposition": disposition,
            "owner": owner,
            "owner_revision": owner_revision,
        }
        value["justification"] = "the human marked the correction as having no future decision value"
        self._pending.pop(correction.correction_id, None)
        self._completed.add(correction.correction_id)
        return {"status": "applied", "effects": ["correction-disposition"], "value": value}

    def _handoff_complete(
        self, operation_id: str, arguments: Mapping[str, Any], outcome: Mapping[str, Any]
    ) -> None:
        correction = arguments.get("correction")
        if operation_id not in {
            "memory.accept-correction",
            "planning.accept-correction-failure",
            "repository.accept-correction",
        } or not isinstance(correction, Mapping):
            return
        correction_id = str(correction.get("correction_id") or "")
        pending = self._pending.get(correction_id)
        if pending is None or arguments.get("correction_revision") != pending.revision:
            return
        value = outcome.get("value")
        if not isinstance(value, Mapping) or value.get("correction_revision") != pending.revision:
            return
        self._pending.pop(correction_id, None)
        self._completed.add(correction_id)


__all__ = ["TrustedCorrection", "TrustedCorrectionIngress"]
