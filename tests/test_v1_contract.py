from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aw_maintainer.native_conformance import compile_source_decision, select_decision_detail

ROOT = Path(__file__).resolve().parents[1]
CAPABILITY_CONTRACT = json.loads((ROOT / "tests/vectors/capability_contract.json").read_text(encoding="utf-8"))
for owner in CAPABILITY_CONTRACT["owners"]:
    for operation in owner.get("operations", []):
        if operation["id"] in {"planning.complete", "example.finish"}:
            operation["input_schema"].setdefault("properties", {})["target"] = {"type": "string"}


def _planning(state: dict[str, Any]) -> dict[str, Any]:
    actions = []
    if state["status"] == "open":
        actions.append(
            {
                "dependency_revision": state["revision"],
                "operation_id": "planning.complete",
                "arguments": {"item": "ship-v1", **({"target": state["target"]} if "target" in state else {})},
                "effects": ["planning-state"],
            }
        )
    return {
        "owner": "planning",
        "revision": state["revision"],
        "facts": {"status": state["status"]},
        "actions": actions,
        "claims": {
            "allowed": ["planning-progress", "complete"] if state["status"] == "complete" else ["planning-progress"],
            "blocked": [] if state["status"] == "complete" else ["complete"],
        },
        "settled": state["status"] == "complete",
        "outcome": (
            {"id": "ship", "status": "complete", "claim": "complete", "evidence_revision": state["revision"]}
            if state["status"] == "complete"
            else None
        ),
    }


def _ship_intent() -> dict[str, Any]:
    return {"outcome": {"id": "ship", "owner": "planning", "claim": "complete"}}


def test_same_source_state_has_one_answer_across_views(shared_core_binary: object) -> None:
    decision = compile_source_decision(
        [_planning({"status": "open", "revision": "p1"})], intent=_ship_intent(), capability_contract=CAPABILITY_CONTRACT
    )
    cli = select_decision_detail(decision, ["status", "primary_action", "claim_boundary"])
    python = select_decision_detail(decision, ["primary_action", "status"])

    assert cli["decision_id"] == python["decision_id"] == decision["decision_id"]
    assert cli["input_revision"] == python["input_revision"] == decision["input_revision"]
    assert cli["values"]["status"] == python["values"]["status"] == "actionable"
