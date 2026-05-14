from __future__ import annotations

from typing import Any

from agentic_command_generation.generated_package_loader import load_generated_cli_package

_generated = load_generated_cli_package(
    bundled_module="agentic_workspace._generated_cli_package_impl",
    generated_root="generated/python/workspace-cli",
    module_name="_agentic_workspace_generated_cli_package",
)

GENERATED_COMMAND_PACKAGE: dict[str, Any] = _generated.GENERATED_COMMAND_PACKAGE
build_generated_parser = _generated.build_generated_parser
generated_command_names = _generated.generated_command_names
generated_operation_contract = _generated.generated_operation_contract
generated_operation_ids = _generated.generated_operation_ids
generated_maturity = _generated.generated_maturity
generated_weak_agent_routing = _generated.generated_weak_agent_routing
run_generated_command = _generated.run_generated_command
supports_generated_command = _generated.supports_generated_command
main = _generated.main

__all__ = [
    "GENERATED_COMMAND_PACKAGE",
    "build_generated_parser",
    "generated_command_names",
    "generated_operation_contract",
    "generated_operation_ids",
    "generated_maturity",
    "generated_weak_agent_routing",
    "main",
    "run_generated_command",
    "supports_generated_command",
]
