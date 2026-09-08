"""Small pre-state runtime/repository compatibility admission boundary."""

from __future__ import annotations

import copy
import json
import tomllib
from pathlib import Path
from typing import Any

from agentic_workspace import __version__

_READER = json.loads((Path(__file__).parent / "contracts/schemas/runtime_compatibility.schema.json").read_text(encoding="utf-8"))[
    "x-runtime-reader"
]
READER_CONTRACT_EPOCH = _READER["reader_epoch"]
READER_CAPABILITIES = tuple(_READER["reader_capabilities"])
_LAST_ADMISSION: dict[str, Any] = {}


def _read_table(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, tomllib.TOMLDecodeError):
        errors.append(f"{path.name}: configuration source unreadable or invalid TOML")
        return {}
    return payload if isinstance(payload, dict) else {}


def admit_runtime_compatibility(target_root: Path) -> dict[str, Any]:
    """Observe only configuration and this reader; shared core admits compatibility."""
    from agentic_workspace.decision import runtime_compatibility

    global _LAST_ADMISSION
    root = target_root.resolve()
    config_path = root / ".agentic-workspace" / "config.toml"
    errors: list[str] = []
    repo = _read_table(config_path, errors)
    local = _read_table(root / ".agentic-workspace" / "config.local.toml", errors)
    result = runtime_compatibility(
        {
            "target": str(root),
            "config_present": config_path.is_file(),
            "repo_config": repo,
            "local_config": local,
            "source_errors": errors,
            "observed_runtime": {
                "package": "agentic-workspace",
                "version": __version__,
                "reader_epoch": READER_CONTRACT_EPOCH,
                "reader_capabilities": list(READER_CAPABILITIES),
            },
        }
    )
    _LAST_ADMISSION = copy.deepcopy(result)
    return result


def current_runtime_compatibility_admission() -> dict[str, Any]:
    """Return compact provenance for the current root-CLI invocation, if observed."""

    return copy.deepcopy(_LAST_ADMISSION)


def target_root_from_argv(argv: list[str], *, cwd: Path | None = None) -> Path:
    base = (cwd or Path.cwd()).resolve()
    for index, token in enumerate(argv):
        if token == "--target" and index + 1 < len(argv):
            return (base / argv[index + 1]).resolve() if not Path(argv[index + 1]).is_absolute() else Path(argv[index + 1]).resolve()
        if token.startswith("--target="):
            value = token.partition("=")[2]
            return (base / value).resolve() if not Path(value).is_absolute() else Path(value).resolve()
    return base
