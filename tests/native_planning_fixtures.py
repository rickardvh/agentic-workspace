"""Stable former-owner inputs, independent of mutable dogfood Planning history."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fixture_source(reference: str | Path) -> Path:
    path = Path(reference)
    if path.as_posix().startswith(".agentic-workspace/planning/execplans/"):
        return ROOT / "tests/fixtures/native_planning" / path.name
    return ROOT / path
