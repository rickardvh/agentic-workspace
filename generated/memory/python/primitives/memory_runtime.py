"""Generated runtime binding facade.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

from typing import Any

# DO NOT EDIT DIRECTLY.
# This generated-local seam makes remaining source-runtime delegates explicit per function.
# Export semantics: generated wrappers perform live source-module lookup at call time.
# Monkeypatching this facade is local to the facade; it is not forwarded back into source modules.
# Replace individual bindings here with generated/codegen-owned primitives as those operations migrate.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py

def _load_memory_bootstrap_doctor(*args: Any, **kwargs: Any) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_bootstrap_doctor as source_function

    return source_function(*args, **kwargs)


def _load_memory_current(*args: Any, **kwargs: Any) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_current as source_function

    return source_function(*args, **kwargs)


def _load_memory_promotion_report(*args: Any, **kwargs: Any) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_promotion_report as source_function

    return source_function(*args, **kwargs)


def _load_memory_prompt(*args: Any, **kwargs: Any) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_prompt as source_function

    return source_function(*args, **kwargs)


def _load_memory_report(*args: Any, **kwargs: Any) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_report as source_function

    return source_function(*args, **kwargs)


def _load_memory_route_report(*args: Any, **kwargs: Any) -> Any:
    from repo_memory_bootstrap.runtime_primitives import _load_memory_route_report as source_function

    return source_function(*args, **kwargs)


__all__ = [
    '_load_memory_bootstrap_doctor',
    '_load_memory_current',
    '_load_memory_promotion_report',
    '_load_memory_prompt',
    '_load_memory_report',
    '_load_memory_route_report',
]
