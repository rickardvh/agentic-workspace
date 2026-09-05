"""Thin Python transport to the shared Agentic Workspace semantic core."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


class DecisionContractError(ValueError):
    """Raised when the shared core rejects a source-decision request."""


def _core_binary() -> Path:
    configured = os.environ.get("AGENTIC_WORKSPACE_CORE_BINARY")
    if configured:
        path = Path(configured)
    else:
        name = "agentic-workspace-core.exe" if os.name == "nt" else "agentic-workspace-core"
        path = Path(__file__).with_name("_native") / name
    if not path.is_file():
        raise DecisionContractError(
            "shared Agentic Workspace core is unavailable; install a supported native package "
            "or set AGENTIC_WORKSPACE_CORE_BINARY to the admitted core binary"
        )
    return path


def _request(payload: Mapping[str, Any]) -> dict[str, Any]:
    completed = subprocess.run(
        [str(_core_binary())],
        input=json.dumps(payload, separators=(",", ":")),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        try:
            message = json.loads(completed.stderr)["error"]["message"]
        except (KeyError, TypeError, json.JSONDecodeError):
            message = completed.stderr.strip() or f"shared core exited with status {completed.returncode}"
        raise DecisionContractError(str(message))
    return dict(json.loads(completed.stdout))


def compile_source_decision(
    contributions: Iterable[Mapping[str, Any]],
    *,
    intent: Mapping[str, Any] | None = None,
    capability_contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"contributions": list(contributions), "intent": dict(intent or {})}
    if capability_contract is not None:
        payload["capability_contract"] = dict(capability_contract)
    return _request(payload)


def select_decision_detail(decision: Mapping[str, Any], fields: Iterable[str]) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/decision-view/v1",
        "decision_id": decision.get("decision_id"),
        "input_revision": decision.get("input_revision"),
        "authoritative": False,
        "values": {field: decision[field] for field in fields if field in decision},
    }


__all__ = ["DecisionContractError", "compile_source_decision", "select_decision_detail"]
