"""Resolve durable configuration into current decision effects, not ambient posture."""

from __future__ import annotations

import hashlib
import json
from typing import Any

CONTROL_DIMENSIONS = {"action", "constraint", "proof", "claim", "procedure", "capability-selection"}
SOURCE_PRECEDENCE = {"repo-shared": 0, "module": 1, "task-derived": 2, "local-runtime": 3, "diagnostic": 4}


def compile_control_inputs(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return only applicable material effects with authority provenance."""

    admitted: list[dict[str, Any]] = []
    dispositions: list[dict[str, str]] = []
    for raw in records:
        record = dict(raw)
        record_id = str(record.get("id") or "unnamed")
        source_class = str(record.get("source_class") or "diagnostic")
        dimension = str(record.get("decision_dimension") or "")
        effects = record.get("effects") if isinstance(record.get("effects"), list) else []
        if record.get("applies") is not True:
            dispositions.append({"id": record_id, "disposition": "derived-or-unmatched", "reason": "not applicable to current decision"})
            continue
        if not effects or dimension not in CONTROL_DIMENSIONS:
            dispositions.append({"id": record_id, "disposition": "demoted", "reason": "no supported material decision effect"})
            continue
        if source_class == "module" and dimension not in {"action", "procedure", "capability-selection"}:
            dispositions.append(
                {
                    "id": record_id,
                    "disposition": "module-local",
                    "reason": "module cannot create a global authority, proof, or claim dimension",
                }
            )
            continue
        admitted.append(
            {
                "id": record_id,
                "source_class": source_class,
                "authority_class": str(record.get("authority_class") or "advisory"),
                "owner": str(record.get("owner") or source_class),
                "decision_dimension": dimension,
                "effects": effects,
                "source_ref": str(record.get("source_ref") or ""),
            }
        )
        dispositions.append({"id": record_id, "disposition": "retained", "reason": f"material {dimension} effect"})

    admitted.sort(key=lambda item: (SOURCE_PRECEDENCE.get(item["source_class"], 99), item["id"]))
    conflicts: list[dict[str, Any]] = []
    by_dimension: dict[str, list[dict[str, Any]]] = {}
    for item in admitted:
        by_dimension.setdefault(item["decision_dimension"], []).append(item)
    for dimension, items in by_dimension.items():
        authoritative = [item for item in items if item["authority_class"] not in {"advisory", "preference"}]
        if len({json.dumps(item["effects"], sort_keys=True) for item in authoritative}) > 1:
            conflicts.append(
                {
                    "decision_dimension": dimension,
                    "owners": [item["owner"] for item in authoritative],
                    "resolution_owner": "repository",
                }
            )
    identity = {"admitted": admitted, "conflicts": conflicts}
    revision = "sha256:" + hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "kind": "agentic-workspace/control-input-resolution/v1",
        "status": "blocked" if conflicts else "resolved",
        "input_revision": revision,
        "effects": admitted,
        "conflicts": conflicts,
        "dispositions": dispositions,
        "provenance_classes": ["repo-shared", "local-runtime", "module", "task-derived", "diagnostic"],
        "rule": "Only applicable inputs with a material supported effect enter the current contract; unmatched knobs and broad posture vocabulary remain diagnostic or owner-local.",
    }
