"""Private installed transport; ordinary meaning belongs to the paired Rust core."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from typing import Any

from .native_core import core_binary as native_core_binary


class DecisionContractError(ValueError):
    """Raised when the shared core rejects a source-decision request."""


def resources(context: Mapping[str, Any]) -> dict[str, Any]:
    """Bounded Rust-owned resource proposals and effects; no host policy reducer."""
    return _request({"resources": context})


def start(context: Mapping[str, Any]) -> dict[str, Any]:
    """Consume repository sources through the native public owner boundary."""
    return _request({"start": context})


def invoke(context: Mapping[str, Any]) -> dict[str, Any]:
    """Submit an exact public invocation to the same native owner boundary."""
    return _request({"invoke": context})


def select_reference(context: Mapping[str, Any], reference: str, **material: Any) -> dict[str, Any]:
    """Forward an exact reference and optional bounded answer to Rust.

    Context is copied, never retained as hidden session state. Rust alone
    validates the answer and current owner identity.
    """
    if set(material) - {"answer"}:
        raise TypeError("select_reference accepts only answer material")
    return start({**context, "reference": reference, **material})


def answer_carried(carriage: Mapping[str, Any], reference: str, answer: Any) -> dict[str, Any]:
    """Carry exact owner material; Rust binds only the returned bounded answer."""
    return _request({"start": {"request": carriage, "reference": reference, "answer": answer, "projection": "carried"}})


def invoke_carried(carriage: Mapping[str, Any], reference: str) -> dict[str, Any]:
    """Execute one exact carried action, with native execution-time admission."""
    return _request({"invoke": {"invocation": carriage, "reference": reference, "projection": "carried"}})


def _request(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        binary = native_core_binary()
    except (OSError, RuntimeError) as error:
        raise DecisionContractError(str(error)) from error
    completed = subprocess.run(
        [str(binary)],
        input=json.dumps(payload, separators=(",", ":")),
        text=True,
        encoding="utf-8",
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
