"""Package-local bridge to the generated Python CLI projection.

The durable generated source lives under generated/python/workspace-cli.
Installed wheels may bundle that projection under a private package-local
implementation module so runtime imports do not depend on repository layout.
"""

from __future__ import annotations

import importlib.util
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any


def _load_generated_source() -> ModuleType:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "generated" / "python" / "workspace-cli" / "generated_cli_package" / "__init__.py"
        if candidate.is_file():
            spec = importlib.util.spec_from_file_location("_agentic_workspace_generated_cli_package", candidate)
            if spec is None or spec.loader is None:
                break
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ModuleNotFoundError("generated/python/workspace-cli/generated_cli_package is unavailable")


try:
    _generated = import_module("agentic_workspace._generated_cli_package_impl")
except (ImportError, ModuleNotFoundError):
    _generated = _load_generated_source()


GENERATED_COMMAND_PACKAGE: dict[str, Any] = _generated.GENERATED_COMMAND_PACKAGE
build_generated_parser = _generated.build_generated_parser
generated_command_names = _generated.generated_command_names
generated_operation_contract = _generated.generated_operation_contract
generated_operation_ids = _generated.generated_operation_ids
generated_maturity = _generated.generated_maturity
generated_weak_agent_routing = _generated.generated_weak_agent_routing
run_generated_command = _generated.run_generated_command
supports_generated_command = _generated.supports_generated_command

__all__ = [
    "GENERATED_COMMAND_PACKAGE",
    "build_generated_parser",
    "generated_command_names",
    "generated_operation_contract",
    "generated_operation_ids",
    "generated_maturity",
    "generated_weak_agent_routing",
    "run_generated_command",
    "supports_generated_command",
]
