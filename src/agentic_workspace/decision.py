"""Stable Python imports for generated source-decision semantics."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _load_generated():
    try:
        return importlib.import_module("agentic_workspace._generated_cli_package_impl.semantic_decision")
    except ModuleNotFoundError as exc:
        if exc.name != "agentic_workspace._generated_cli_package_impl":
            raise
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        return importlib.import_module("generated.workspace.python.semantic_decision")


_generated = _load_generated()
DecisionContractError = _generated.DecisionContractError
compile_source_decision = _generated.compile_source_decision
normalize_contribution = _generated.normalize_contribution
select_decision_detail = _generated.select_decision_detail

__all__ = ["DecisionContractError", "compile_source_decision", "normalize_contribution", "select_decision_detail"]
