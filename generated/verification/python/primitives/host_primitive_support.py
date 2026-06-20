"""Generated target-local host primitive support module.

Source: src/agentic_workspace/contracts/command_package_ir.json
Host primitive support: src/agentic_workspace/contracts/python_primitive_support.py
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

# DO NOT EDIT DIRECTLY.
# Domain-runtime primitive behavior belongs in the configured host support source.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

from __future__ import annotations

from typing import Any

from .primitive_executor import (
    PrimitiveContext,
    PrimitiveExecutionError,
    _emit_output,
    _payload_current_memory,
    _payload_lifecycle_plan,
    _payload_status,
    _verify_payload,
)


def execute_host_primitive(
    primitive: str,
    *,
    values: dict[str, Any],
    arguments: dict[str, Any],
    context: PrimitiveContext,
) -> Any:
    if primitive == "memory.payload.status":
        return _payload_status(values=values, arguments=arguments, context=context)
    if primitive == "memory.payload.lifecycle-plan":
        return _payload_lifecycle_plan(values=values, arguments=arguments, context=context)
    if primitive == "memory.payload.current-memory":
        return _payload_current_memory(values=values, arguments=arguments, context=context)
    if primitive == "memory.payload.verify":
        return _verify_payload(values=values, arguments=arguments, context=context)
    if primitive == "memory.output.emit.install-result":
        return _emit_output(values=values, arguments={"text_style": "install-result"})
    if primitive == "memory.output.emit.current-memory":
        return _emit_output(values=values, arguments={"text_style": "current-memory"})
    if primitive == "workspace.output.emit":
        from .workspace_runtime import _emit_workspace_operation_output

        return _emit_workspace_operation_output(values, arguments, context)
    raise PrimitiveExecutionError(f"unsupported AW host primitive: {primitive!r}")
