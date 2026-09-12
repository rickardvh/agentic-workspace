"""Resolve packaged native artifacts or an explicitly configured development core."""

from __future__ import annotations

import hashlib
import json
import os
from importlib.metadata import version
from pathlib import Path


def _verify(path: Path, key: str) -> None:
    packaged = Path(__file__).with_name("_native")
    manifest_path = packaged / "artifact.json"
    if packaged.is_dir():
        if not manifest_path.is_file():
            raise RuntimeError("packaged native artifact manifest missing")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["package_version"] != version("agentic-workspace"):
            raise RuntimeError("packaged native artifact version mismatch")
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[key]:
            raise RuntimeError("packaged native artifact digest mismatch")


def core_binary() -> Path:
    name = "agentic-workspace-core.exe" if os.name == "nt" else "agentic-workspace-core"
    configured = os.environ.get("AGENTIC_WORKSPACE_CORE_BINARY")
    path = Path(configured) if configured else Path(__file__).with_name("_native") / name
    if not path.is_file():
        raise RuntimeError(
            "shared Agentic Workspace core is unavailable; install the native package or explicitly set AGENTIC_WORKSPACE_CORE_BINARY for development"
        )
    _verify(path, "sha256")
    return path


def cli_binary() -> Path:
    path = core_binary().with_name("agentic-workspace.exe" if os.name == "nt" else "agentic-workspace")
    if not path.is_file():
        raise RuntimeError("paired native Agentic Workspace CLI is unavailable")
    _verify(path, "cli_sha256")
    return path
