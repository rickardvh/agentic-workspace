from __future__ import annotations

import sys

from agentic_command_generation.generated_package_loader import load_generated_cli_package_module

_runtime = load_generated_cli_package_module(
    bundled_module="repo_memory_bootstrap._generated_cli_package_impl.memory_operation_ir_executor",
    generated_root="generated/python/memory-cli",
    file_name="memory_operation_ir_executor.py",
    module_name="_repo_memory_bootstrap_generated_operation_ir_executor",
)

globals().update(
    {
        name: getattr(_runtime, name)
        for name in dir(_runtime)
        if name == "__version__" or not (name.startswith("__") and name.endswith("__"))
    }
)
sys.modules[__name__] = _runtime
