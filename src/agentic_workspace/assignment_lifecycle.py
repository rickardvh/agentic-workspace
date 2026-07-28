"""Assignment-result owner admission used by composed-operation checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentic_workspace.operation_owner_packet_contract import owner_decision_packet


def composed_delegated_return_packet(*, target: Path) -> dict[str, Any]:
    returned = _read_json_if_present(target / ".agentic-workspace" / "local" / "delegation" / "returned-result.json")
    current = returned.get("status") == "admitted"
    return owner_decision_packet(
        kind="agentic-workspace/delegated-return-admission/v1",
        producer_module=__name__,
        owner="delegation",
        status="admitted" if current else "rejected",
        admitted=current,
        source=".agentic-workspace/local/delegation/returned-result.json",
        typed_action="admit-result",
        effect_scope="returned-result-admission",
        stable_reason="return-receipt-current",
        proof_claim_boundary="admitted-result-before-claim",
        next_transition="admit-or-repair-return",
        terminal_state="continue",
        operation_id="assignment.admit",
        producer_observation={
            "kind": "agentic-workspace/delegated-return-receipt/v1",
            "returned_result": returned,
            "current": current,
        },
    )


def admit_delegated_return_result(*, target: Path) -> dict[str, Any]:
    path = target / ".agentic-workspace" / "local" / "delegation" / "returned-result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"status": "admitted", "revision": "repair"}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "kind": "agentic-workspace/delegated-return-repair/v1",
        "status": "applied",
        "operation": "admit-or-repair-return",
        "source": ".agentic-workspace/local/delegation/returned-result.json",
    }


def _read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "invalid-json"}
    return payload if isinstance(payload, dict) else {"status": "not-object"}
