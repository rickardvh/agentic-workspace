"""External-observation owner admission used by composed-operation checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentic_workspace.operation_owner_packet_contract import owner_decision_packet


def composed_external_observation_packet(*, target: Path, observation_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(observation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return owner_decision_packet(
            kind="agentic-workspace/external-observation-admission/v1",
            producer_module=__name__,
            owner="workspace",
            status="rejected",
            admitted=False,
            source=observation_path.relative_to(target).as_posix(),
            typed_action="recover",
            effect_scope="external-observation-only",
            stable_reason="malformed-observation-rejected",
            proof_claim_boundary="no-completion-claim",
            next_transition="request-valid-observation",
            terminal_state="blocked",
            operation_id="external-observation.admit",
            producer_observation={"kind": "agentic-workspace/external-observation-parse/v1", "error": exc.__class__.__name__},
        )
    admitted = isinstance(payload, dict)
    return owner_decision_packet(
        kind="agentic-workspace/external-observation-admission/v1",
        producer_module=__name__,
        owner="workspace",
        status="admitted" if admitted else "rejected",
        admitted=admitted,
        source=observation_path.relative_to(target).as_posix(),
        typed_action="recover",
        effect_scope="external-observation-only",
        stable_reason="valid-observation" if admitted else "malformed-observation-rejected",
        proof_claim_boundary="proof-before-completion-claim" if admitted else "no-completion-claim",
        next_transition="continue-safe-route" if admitted else "request-valid-observation",
        terminal_state="continue" if admitted else "blocked",
        operation_id="external-observation.admit",
        producer_observation={"kind": "agentic-workspace/external-observation-parse/v1", "payload": payload},
    )


def replace_external_observation(*, target: Path, source: str) -> dict[str, Any]:
    path = target / source
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"status": "current", "observation": "valid"}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "kind": "agentic-workspace/external-observation-repair/v1",
        "status": "applied",
        "operation": "request-valid-observation",
        "source": source,
    }
