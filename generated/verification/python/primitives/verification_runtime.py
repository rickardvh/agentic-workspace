"""Generated runtime binding facade.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-verification
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

def verification_report_payload(*args: Any, **kwargs: Any) -> Any:
    from repo_verification_bootstrap.runtime_primitives import verification_report_payload as source_function

    return source_function(*args, **kwargs)


__all__ = [
    'verification_report_payload',
]
