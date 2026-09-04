from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .builtin_modules import _memory_record
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
            required_capabilities=("operation/durable-commit",),
            contribute=self._contribute,
            operations=(
                Operation(
                    "correction.disposition",
                    contract["input"],
                    tuple(contract["effects"]),
                    self._disposition,
                ),
            ),
            currentness=lambda _context: semantic_digest(
                {
                    "pending": {key: value.revision for key, value in sorted(self._pending.items())},
                    "completed": sorted(self._completed),
                }
            ),
        )

    @staticmethod
    def _route(correction: TrustedCorrection) -> tuple[str, str, str]:
        if correction.existing_owner:
            return (
                "already-owned",
                str(correction.existing_owner.get("owner") or "repository"),
                str(correction.existing_owner.get("revision") or ""),
            )
        if correction.deterministic_owner_failure:
            return (
                "owner-repair",
                str(correction.deterministic_owner_failure.get("owner") or "adaptation"),
                str(correction.deterministic_owner_failure.get("revision") or ""),
            )
        if correction.future_usefulness == "do-not-retain":
            return ("no-new-durable-record", "correction", "")
        return ("memory", "memory", "")

    def _contribute(self, context: Mapping[str, Any]) -> dict[str, Any] | None:
        if not self._pending:
            return None
        correction_id = sorted(self._pending)[0]
        correction = self._pending[correction_id]
        disposition, owner, owner_revision = self._route(correction)
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
                    "operation_id": "correction.disposition",
                    "arguments": {
                        "target": str(Path(str(context["target"])).resolve()),
                        "correction_id": correction.correction_id,
                        "correction_revision": correction.revision,
                        "disposition": disposition,
                        "owner": owner,
                        "owner_revision": owner_revision,
                    },
                    "effects": ["correction-disposition", "memory-state"],
                    "priority": 100,
                }
            ],
        }

    def _disposition(self, arguments: dict[str, Any]) -> dict[str, Any]:
        correction = self._pending.get(arguments["correction_id"])
        if correction is None or correction.revision != arguments["correction_revision"]:
            return {"status": "rejected", "effects": [], "value": {"reason": "stale-correction"}}
        disposition, owner, owner_revision = self._route(correction)
        if (arguments["disposition"], arguments["owner"], arguments["owner_revision"]) != (
            disposition,
            owner,
            owner_revision,
        ):
            return {"status": "rejected", "effects": [], "value": {"reason": "correction-route-mismatch"}}

        effects = ["correction-disposition"]
        if disposition == "memory":
            outcome = _memory_record(
                {
                    "target": arguments["target"],
                    "key": f"human-correction:{correction.correction_id}",
                    "value": correction.statement,
                    "summary": correction.statement,
                    "provenance": "trusted-human-correction:" + correction.revision,
                    "task_terms": list(correction.applicability.get("task_terms", [])),
                    "paths": list(correction.applicability.get("paths", [])),
                    "dependency_revision": str(correction.applicability.get("dependency_revision") or ""),
                    "kind": "advisory",
                }
            )
            if outcome["status"] == "rejected":
                return outcome
            effects.append("memory-state")

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
        if disposition == "already-owned":
            value["justification"] = "the correction is already enforced by the named canonical owner"
        elif disposition == "no-new-durable-record":
            value["justification"] = "the human marked the correction as having no future decision value"
        elif disposition == "owner-repair":
            value["adaptation_evidence"] = {
                "failed_owner": owner,
                "failed_revision": owner_revision,
                "correction_revision": correction.revision,
            }
        self._pending.pop(correction.correction_id, None)
        self._completed.add(correction.correction_id)
        return {"status": "applied", "effects": effects, "value": value}


__all__ = ["TrustedCorrection", "TrustedCorrectionIngress"]
