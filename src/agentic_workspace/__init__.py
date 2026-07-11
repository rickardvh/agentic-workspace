from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentic-workspace")
except PackageNotFoundError:
    __version__ = "0.0.0"

from .client import (
    AWClientError,
    detect_workspace,
    external_consumer_profile,
    external_contract_bundle,
    invoke_operation,
    negotiate_requirements,
    operation_compatibility_fingerprint,
    require_operations,
    resolve_invocation,
)

__all__ = [
    "AWClientError",
    "detect_workspace",
    "external_consumer_profile",
    "external_contract_bundle",
    "invoke_operation",
    "negotiate_requirements",
    "operation_compatibility_fingerprint",
    "require_operations",
    "resolve_invocation",
]
