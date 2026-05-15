"""Generated Python runtime operation handler module.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-memory
Regenerate with: uv run python scripts/generate/generate_command_packages.py
"""

from __future__ import annotations

import argparse
import importlib
import sys
from typing import Any

# DO NOT EDIT DIRECTLY.
# Runtime handler changes belong in src/agentic_workspace/contracts/command_package_ir.json.
# Regenerate with: uv run python scripts/generate/generate_command_packages.py
from . import build_generated_parser as build_generated_cli_package_parser
from . import generated_command_names as generated_cli_package_command_names
from . import generated_operation_contract as generated_cli_package_operation_contract
from . import run_generated_command as run_generated_cli_package_command
from . import supports_generated_command as supports_generated_cli_package_command
from .memory_operation_ir_executor import run_operation_ir


from repo_memory_bootstrap.runtime_primitives import _build_agent_prompt as _build_agent_prompt


from repo_memory_bootstrap.runtime_primitives import _emit_result as _emit_result


from repo_memory_bootstrap.runtime_primitives import _print_install_summary as _print_install_summary


_RUNTIME_EXPORT_SOURCES = (
    ('repo_memory_bootstrap.runtime_primitives', '_build_agent_prompt', '_build_agent_prompt'),
    ('repo_memory_bootstrap.runtime_primitives', '_emit_result', '_emit_result'),
    ('repo_memory_bootstrap.runtime_primitives', '_print_install_summary', '_print_install_summary'),
)


def _sync_runtime_export_patches() -> None:
    for module_name, source_name, exported_name in _RUNTIME_EXPORT_SOURCES:
        value = globals().get(exported_name)
        module = importlib.import_module(module_name)
        if getattr(module, source_name, None) is not value:
            setattr(module, source_name, value)


def _program_name() -> str:
    invoked = sys.argv[0].replace("\\", "/").rsplit("/", 1)[-1]
    if invoked == 'agentic-memory':
        return invoked
    return 'agentic-memory'


def build_parser() -> argparse.ArgumentParser:
    return build_generated_cli_package_parser()


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    try:
        return run_generated_cli_package_command(argv_list, _run_generated_cli_operation)
    except Exception as exc:
        if exc.__class__.__name__.endswith('UsageError') or exc.__class__.__name__ == 'RepoDetectionError':
            build_generated_cli_package_parser().error(str(exc))
        raise


def _run_generated_cli_operation(operation_id: str, args: argparse.Namespace) -> int:
    handler = _GENERATED_RUNTIME_HANDLERS.get(operation_id)
    if handler is None:
        build_generated_cli_package_parser().error(
            f"Generated adapter for {getattr(args, 'command', operation_id)} references unsupported operation {operation_id}."
        )
        raise SystemExit(2)
    _sync_runtime_export_patches()
    return handler(args)


def _run_memory_adopt_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.adopt.lifecycle'), args)


def _run_memory_bootstrap_cleanup_apply_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.bootstrap-cleanup.apply'), args)


def _run_memory_capture_note_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.capture-note.report'), args)


def _run_memory_create_note_apply_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.create-note.apply'), args)


def _run_memory_current_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.current.report'), args)


def _run_memory_doctor_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.doctor.report'), args)


def _run_memory_init_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.init.lifecycle'), args)


def _run_memory_install_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.install.lifecycle'), args)


def _run_memory_list_files_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.list-files.report'), args)


def _run_memory_list_skills_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.list-skills.report'), args)


def _run_memory_migrate_layout_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.migrate-layout.lifecycle'), args)


def _run_memory_promotion_report_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.promotion-report.report'), args)


def _run_memory_prompt_render_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.prompt.render'), args)


def _run_memory_report_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.report.report'), args)


def _run_memory_route_report_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.route-report.report'), args)


def _run_memory_route_review_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.route-review.report'), args)


def _run_memory_route_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.route.report'), args)


def _run_memory_search_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.search.report'), args)


def _run_memory_status_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.status.report'), args)


def _run_memory_sync_memory_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.sync-memory.report'), args)


def _run_memory_uninstall_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.uninstall.lifecycle'), args)


def _run_memory_upgrade_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.upgrade.lifecycle'), args)


def _run_memory_verify_payload_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('memory.verify-payload.report'), args)



_GENERATED_RUNTIME_HANDLERS = {
    'memory.adopt.lifecycle': _run_memory_adopt_lifecycle_adapter,
    'memory.bootstrap-cleanup.apply': _run_memory_bootstrap_cleanup_apply_adapter,
    'memory.capture-note.report': _run_memory_capture_note_report_adapter,
    'memory.create-note.apply': _run_memory_create_note_apply_adapter,
    'memory.current.report': _run_memory_current_report_adapter,
    'memory.doctor.report': _run_memory_doctor_report_adapter,
    'memory.init.lifecycle': _run_memory_init_lifecycle_adapter,
    'memory.install.lifecycle': _run_memory_install_lifecycle_adapter,
    'memory.list-files.report': _run_memory_list_files_report_adapter,
    'memory.list-skills.report': _run_memory_list_skills_report_adapter,
    'memory.migrate-layout.lifecycle': _run_memory_migrate_layout_lifecycle_adapter,
    'memory.promotion-report.report': _run_memory_promotion_report_report_adapter,
    'memory.prompt.render': _run_memory_prompt_render_adapter,
    'memory.report.report': _run_memory_report_report_adapter,
    'memory.route-report.report': _run_memory_route_report_report_adapter,
    'memory.route-review.report': _run_memory_route_review_report_adapter,
    'memory.route.report': _run_memory_route_report_adapter,
    'memory.search.report': _run_memory_search_report_adapter,
    'memory.status.report': _run_memory_status_report_adapter,
    'memory.sync-memory.report': _run_memory_sync_memory_report_adapter,
    'memory.uninstall.lifecycle': _run_memory_uninstall_lifecycle_adapter,
    'memory.upgrade.lifecycle': _run_memory_upgrade_lifecycle_adapter,
    'memory.verify-payload.report': _run_memory_verify_payload_report_adapter,
}
