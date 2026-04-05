from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import tomllib


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
def _ownership_data() -> dict[str, object]:
    with ownership_manifest_path().open("rb") as handle:
        return tomllib.load(handle)


def module_root(module: str) -> Path:
    for entry in _ownership_data().get("module_roots", []):
        if entry.get("module") == module:
            return Path(entry["path"])
    raise KeyError(f"Module {module!r} is not defined in the ownership ledger.")