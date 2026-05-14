from __future__ import annotations

import sys

from agentic_command_generation.generated_package_loader import load_generated_cli_package_module

_runtime = load_generated_cli_package_module(
    bundled_module="agentic_workspace._generated_cli_package_impl.workspace_runtime_cli",
    generated_root="generated/python/workspace-cli",
    file_name="workspace_runtime_cli.py",
    module_name="_agentic_workspace_generated_runtime_cli",
)

globals().update(
    {
        name: getattr(_runtime, name)
        for name in dir(_runtime)
        if name == "__version__" or not (name.startswith("__") and name.endswith("__"))
    }
)
sys.modules[__name__] = _runtime
