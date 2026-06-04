"""Generated runtime binding facade.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning
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

def adopt_bootstrap(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import adopt_bootstrap as source_function

    return source_function(*args, **kwargs)


def close_planning_item(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import close_planning_item as source_function

    return source_function(*args, **kwargs)


def collect_status(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import collect_status as source_function

    return source_function(*args, **kwargs)


def create_review_record(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import create_review_record as source_function

    return source_function(*args, **kwargs)


def doctor_bootstrap(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import doctor_bootstrap as source_function

    return source_function(*args, **kwargs)


def install_bootstrap(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import install_bootstrap as source_function

    return source_function(*args, **kwargs)


def planning_handoff(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import planning_handoff as source_function

    return source_function(*args, **kwargs)


def planning_report(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import planning_report as source_function

    return source_function(*args, **kwargs)


def planning_report_tiny(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import planning_report_tiny as source_function

    return source_function(*args, **kwargs)


def uninstall_bootstrap(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import uninstall_bootstrap as source_function

    return source_function(*args, **kwargs)


def upgrade_bootstrap(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import upgrade_bootstrap as source_function

    return source_function(*args, **kwargs)


def verify_payload(*args: Any, **kwargs: Any) -> Any:
    from repo_planning_bootstrap.installer import verify_payload as source_function

    return source_function(*args, **kwargs)


__all__ = [
    'adopt_bootstrap',
    'close_planning_item',
    'collect_status',
    'create_review_record',
    'doctor_bootstrap',
    'install_bootstrap',
    'planning_handoff',
    'planning_report',
    'planning_report_tiny',
    'uninstall_bootstrap',
    'upgrade_bootstrap',
    'verify_payload',
]
