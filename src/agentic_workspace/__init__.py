from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentic-workspace")
except PackageNotFoundError:
    __version__ = "0.0.0"

from .decision import DecisionContractError, compile_source_decision, select_decision_detail
from .modules import Module, discover_modules, module_contributions, register_module_operations
from .operations import Operation, OperationContractError, OperationDispatcher, OperationError, StaleInvocationError
from .workspace import Workspace

__all__ = [
    "DecisionContractError",
    "Module",
    "Operation",
    "OperationContractError",
    "OperationDispatcher",
    "OperationError",
    "StaleInvocationError",
    "Workspace",
    "compile_source_decision",
    "discover_modules",
    "module_contributions",
    "register_module_operations",
    "select_decision_detail",
]
