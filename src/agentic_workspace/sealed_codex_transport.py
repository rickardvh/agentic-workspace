"""Thin Codex app-server bridge for the native owner's sealed worker protocol.

Core owns packet validation, return identity, attempts and integration. This
adapter owns only provider discovery and one fresh read-only host turn.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from agentic_workspace import native_transport
from agentic_workspace.decision import assignment_packet


def dispatch(root: Path, packet: dict[str, Any]) -> dict[str, Any]:
    entry = assignment_packet({"action": "entry", "packet": packet})
    configuration = packet["assignment_identity"]["current_assignment"]["selected"]["configuration"]
    adapter = configuration["execution"]["adapter"]
    if adapter.get("adapter") != "codex-app-server/v1":
        raise ValueError("unsupported sealed host adapter")
    parameters = adapter["parameters"]
    snapshot = native_transport.discover(root, refresh=True)
    selection = {"mode": "fresh", "parameters": parameters, "capability_revision": snapshot["revision"]}
    native_transport.validate_selection(snapshot, selection)
    # Expand the bounded captured capsule mechanically, never from the filesystem.
    prompt = json.dumps({"worker": entry, "captured_inputs": packet["assignment_identity"]["input_capsule"]})
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "changed_paths": {"type": "array", "items": {"type": "string"}},
            "patch": {"type": "string"},
            "stop_conditions_hit": {"type": "array", "items": {"type": "string"}},
            "result_delivery": {"const": "unapplied-patch"},
        },
        "required": ["summary", "changed_paths", "patch", "stop_conditions_hit", "result_delivery"],
    }
    result = native_transport.execute(root, snapshot, selection, prompt, schema, timeout=adapter["timeout_seconds"])
    returned = assignment_packet({"action": "return", "packet": packet, "material": result["returned_work"]})
    return next(
        request["arguments"]["returned"]
        for request in returned["reentry"]["request"]
        if request["request_kind"] in {"assignment/observe-readonly-return/v1", "assignment/observe-patch-return/v1"}
    )


def main() -> None:
    packet = json.load(sys.stdin)
    print(json.dumps(dispatch(Path.cwd(), packet)))


if __name__ == "__main__":
    main()
