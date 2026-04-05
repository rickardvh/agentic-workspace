from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any


def _packaged_manifest_path() -> Path:
    return Path(__file__).resolve().with_name("_ownership.toml")


def _workspace_manifest_path() -> Path | None:
    for candidate in Path(__file__).resolve().parents:
        manifest = candidate / ".agentic-workspace" / "OWNERSHIP.toml"
        if manifest.exists():
            return manifest
    return None


def ownership_manifest_path() -> Path:
    workspace_manifest = _workspace_manifest_path()
    if workspace_manifest is not None:
        return workspace_manifest

    packaged_manifest = _packaged_manifest_path()
    if packaged_manifest.exists():
        return packaged_manifest

    raise FileNotFoundError("Could not locate .agentic-workspace/OWNERSHIP.toml or packaged ownership mirror.")


@lru_cache(maxsize=1)
def _ownership_data() -> dict[str, Any]:
    with ownership_manifest_path().open("rb") as handle:
        return tomllib.load(handle)


def module_root(module: str) -> Path:
    module_roots = _ownership_data().get("module_roots", [])
    if not isinstance(module_roots, list):
        raise KeyError("Ownership ledger is missing a valid module_roots list.")

    for entry in module_roots:
        if not isinstance(entry, dict):
            continue
        if entry.get("module") == module:
            return Path(entry["path"])
    raise KeyError(f"Module {module!r} is not defined in the ownership ledger.")
