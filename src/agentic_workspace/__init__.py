from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agentic-workspace")
except PackageNotFoundError:
    __version__ = "0.0.0"

from .corrections import TrustedCorrection, TrustedCorrectionIngress
from .decision import DecisionContractError, compile_source_decision, select_decision_detail
from .generated_semantics import (
    BUNDLED_SKILLS,
    IR,
    bundled_skill,
    canonical_serialize,
    operation_contract,
    owner_conclusion_identity,
    semantic_digest,
)
from .modules import Module, discover_modules, module_contributions, register_module_operations
from .operations import Operation, OperationContractError, OperationDispatcher, OperationError, StaleInvocationError
from .workspace import Workspace

__all__ = [
    "DecisionContractError",
    "BUNDLED_SKILLS",
    "IR",
    "Module",
    "Operation",
    "OperationContractError",
    "OperationDispatcher",
    "OperationError",
    "StaleInvocationError",
    "TrustedCorrection",
    "TrustedCorrectionIngress",
    "Workspace",
    "compile_source_decision",
    "canonical_serialize",
    "bundled_skill",
    "discover_modules",
    "module_contributions",
    "operation_contract",
    "owner_conclusion_identity",
    "register_module_operations",
    "select_decision_detail",
    "semantic_digest",
]
