from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentic-workspace")
except PackageNotFoundError:
    __version__ = "0.0.0"

from .client import (
    AWClientError,
    detect_workspace,
    external_conformance_profile,
    external_consumer_profile,
    external_contract_bundle,
    external_operation_conformance_receipts,
    external_readiness_report,
    invoke_operation,
    negotiate_requirements,
    operation_compatibility_fingerprint,
    require_operations,
    resolve_invocation,
)
from .decision import DecisionContractError, compile_source_decision, select_decision_detail
from .modules import Module, discover_modules, module_contributions, register_module_operations
from .operations import Operation, OperationContractError, OperationDispatcher, OperationError, StaleInvocationError

__all__ = [
    "AWClientError",
    "detect_workspace",
    "external_conformance_profile",
    "external_consumer_profile",
    "external_contract_bundle",
    "external_operation_conformance_receipts",
    "external_readiness_report",
    "invoke_operation",
    "negotiate_requirements",
    "operation_compatibility_fingerprint",
    "require_operations",
    "resolve_invocation",
    "DecisionContractError",
    "compile_source_decision",
    "select_decision_detail",
    "Module",
    "discover_modules",
    "module_contributions",
    "register_module_operations",
    "Operation",
    "OperationContractError",
    "OperationDispatcher",
    "OperationError",
    "StaleInvocationError",
]
