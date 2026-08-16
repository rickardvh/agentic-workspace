"""Small pre-state runtime/repository compatibility admission boundary."""

from __future__ import annotations

import copy
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

from agentic_workspace import __version__

READER_CONTRACT_EPOCH = 1
READER_CAPABILITIES = ("pre-state-runtime-compatibility-v1",)
_LAST_ADMISSION: dict[str, Any] = {}


def _read_table(path: Path) -> dict[str, Any]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _configured_invocation(target_root: Path, repo_config: dict[str, Any]) -> str:
    local_config = _read_table(target_root / ".agentic-workspace" / "config.local.toml")
    for payload in (local_config, repo_config):
        workspace = payload.get("workspace")
        if isinstance(workspace, dict):
            invocation = workspace.get("cli_invoke")
            if isinstance(invocation, str) and invocation.strip():
                return invocation.strip()
    return "agentic-workspace"


def _positive_int(value: Any, *, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else default


def admit_runtime_compatibility(target_root: Path) -> dict[str, Any]:
    """Read only the compatibility/config boundary; never inspect managed state."""

    global _LAST_ADMISSION
    root = target_root.resolve()
    config_path = root / ".agentic-workspace" / "config.toml"
    config = _read_table(config_path)
    raw_expectation = config.get("cli_compatibility")
    expectation = raw_expectation if isinstance(raw_expectation, dict) else {}
    raw_minimum_epoch = expectation.get("minimum_reader_epoch")
    minimum_epoch = _positive_int(raw_minimum_epoch, default=0)
    contract_errors: list[str] = []
    if raw_minimum_epoch is not None and minimum_epoch == 0:
        contract_errors.append("minimum_reader_epoch must be a positive integer")
    raw_capabilities = expectation.get("required_reader_capabilities", [])
    if not isinstance(raw_capabilities, list):
        contract_errors.append("required_reader_capabilities must be a list")
        raw_capabilities = []
    required_capabilities = tuple(sorted({item.strip() for item in raw_capabilities if isinstance(item, str) and item.strip()}))
    configured_invocation = _configured_invocation(root, config)
    missing_capabilities = sorted(set(required_capabilities) - set(READER_CAPABILITIES))
    epoch_supported = minimum_epoch <= READER_CONTRACT_EPOCH
    admitted = epoch_supported and not missing_capabilities and not contract_errors
    expected_identity = {
        "contract_schema": str(expectation.get("contract_schema") or "agentic-workspace/installed-state-compatibility/v1"),
        "minimum_reader_epoch": minimum_epoch,
        "required_reader_capabilities": list(required_capabilities),
        "source": ".agentic-workspace/config.toml [cli_compatibility]" if config_path.is_file() else "repository-default",
    }
    observed_identity = {
        "package": "agentic-workspace",
        "version": __version__,
        "reader_epoch": READER_CONTRACT_EPOCH,
        "reader_capabilities": list(READER_CAPABILITIES),
    }
    identity_material = {"expected": expected_identity, "observed": observed_identity, "target": str(root)}
    identity_digest = "sha256:" + hashlib.sha256(json.dumps(identity_material, sort_keys=True).encode("utf-8")).hexdigest()
    if admitted:
        result = {
            "kind": "agentic-workspace/runtime-compatibility-admission/v1",
            "status": "admitted",
            "identity_digest": identity_digest,
            "target": str(root),
            "observed_runtime": observed_identity,
            "expected_repository": expected_identity,
            "configured_invocation": configured_invocation,
            "managed_state_interpreted": False,
            "rule": "Compatibility is admitted before generated handlers, session logging, Planning, or Workspace state are loaded.",
        }
    else:
        failed_checks: list[str] = []
        if not epoch_supported:
            failed_checks.append("minimum_reader_epoch")
        if missing_capabilities:
            failed_checks.append("required_reader_capabilities")
        if contract_errors:
            failed_checks.append("compatibility_contract_shape")
        result = {
            "kind": "agentic-workspace/runtime-compatibility-incompatibility/v1",
            "status": "blocked",
            "failure_class": "runtime-repository-contract-incompatible",
            "identity_digest": identity_digest,
            "target": str(root),
            "observed_runtime": observed_identity,
            "expected_repository": expected_identity,
            "failed_checks": failed_checks,
            "missing_reader_capabilities": missing_capabilities,
            "contract_errors": contract_errors,
            "configured_invocation": configured_invocation,
            "recovery_command": configured_invocation,
            "managed_state_interpreted": False,
            "unavailable_effects": [
                "owner-selection",
                "implementation-permission",
                "mutation-guidance",
                "proof-and-closeout-authority",
                "completion-claims",
            ],
            "completion_boundary": "repository-managed-state-not-admitted",
            "rule": "An incompatible reader fails before any decision-shaped repository state is interpreted.",
        }
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
