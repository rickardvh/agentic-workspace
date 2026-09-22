"""Thin build-time binding to the Rust ownership read-profile producer."""

from __future__ import annotations

from pathlib import Path

from aw_maintainer.native_conformance import _request

LEDGER = ".agentic-workspace/OWNERSHIP.toml"
PROFILE = ".agentic-workspace/READING.json"


def render(ledger_text: str, *, target: Path) -> str:
    """Project proposed ledger bytes using the target repository's Git semantics."""
    return _request({"ownership_read_profile": {"target": str(target), "ledger": ledger_text}})["text"]
