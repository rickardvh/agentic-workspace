"""agentic-memory-bootstrap package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("agentic-memory-bootstrap")
except PackageNotFoundError:  # pragma: no cover - fallback for direct source execution
    __version__ = "0+unknown"
