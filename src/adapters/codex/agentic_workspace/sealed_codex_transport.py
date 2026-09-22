"""Thin Codex app-server bridge for the native owner's sealed worker protocol.

Core owns packet validation, return identity, attempts and integration. This
adapter owns only provider discovery and one fresh read-only host turn.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from agentic_workspace import codex_provider as native_transport
from agentic_workspace.native_core import core_binary


def assignment_packet(context: dict[str, Any]) -> dict[str, Any]:
    """Forward packet admission to the paired core; never interpret it in Python."""
    result = subprocess.run(
        [str(core_binary())],
        input=json.dumps({"assignment_packet": context}),
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(result.stderr.strip())
    return json.loads(result.stdout)


def capability(root: Path, parameters: dict[str, Any]) -> dict[str, Any]:
    """Fresh adapter facts only: no worker turn, session or retained observation."""
    facts: dict[str, Any] = {
        "kind": "agentic-workspace/host-transport-capability/v1",
        "parameters": parameters,
        "adapter_revision": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    try:
        snapshot = native_transport.discover(root, refresh=True, persist=False)
        facts["provider_revision"] = snapshot["revision"]
        native_transport.validate_selection(
            snapshot, {"mode": "fresh", "parameters": parameters, "capability_revision": snapshot["revision"]}
        )
        facts.update(status="available", reason="current-protocol-and-model", result_classes=["read-only", "unapplied-patch"])
    except native_transport.ProviderError as error:
        reason = str(error)
        # Only settled adapter facts establish unavailability. Discovery errors,
        # quota, timeouts and unknown protocol remain unresolved, never local fit.
        unavailable = reason in {
            "native-adapter-executable-unavailable",
            "native-model-unavailable",
            "native-continuity-unavailable",
            "native-parameter-unsupported",
            "native-ephemeral-continuity-unavailable",
        }
        facts.update(status="unavailable" if unavailable else "unknown", reason=reason, result_classes=[])
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        facts.update(status="unknown", reason="host-capability-discovery-failed", result_classes=[])
    facts["revision"] = native_transport.digest(facts)
    return facts


def dispatch(root: Path, packet: dict[str, Any]) -> dict[str, Any]:
    entry = assignment_packet({"action": "entry", "packet": packet})
    configuration = packet["assignment_identity"]["current_assignment"]["selected"]["configuration"]
    adapter = configuration["execution"]["adapter"]
    if adapter.get("adapter") != "codex-app-server/v1":
        raise ValueError("unsupported sealed host adapter")
    parameters = adapter["parameters"]
    if configuration["execution"].get("host_capability") != capability(root, parameters):
        raise ValueError("host capability changed; resolve current Assignment before dispatch")
    snapshot = native_transport.discover(root, refresh=True)
    if snapshot["revision"] != configuration["execution"]["host_capability"]["provider_revision"]:
        raise ValueError("host capability changed; resolve current Assignment before dispatch")
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
            "result_delivery": {"type": "string", "const": "unapplied-patch"},
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
    if sys.argv[1:] == ["--aw-capability"]:
        print(json.dumps(capability(Path.cwd(), json.load(sys.stdin))))
        return
    packet = json.load(sys.stdin)
    print(json.dumps(dispatch(Path.cwd(), packet)))


if __name__ == "__main__":
    main()
