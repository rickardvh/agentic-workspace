"""Generated Python runtime operation handler module.

Source: src/agentic_workspace/contracts/command_package_ir.json
Program: agentic-planning
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
from .planning_operation_ir_executor import run_operation_ir


from repo_planning_bootstrap.runtime_projection import _print_summary as _print_summary


from repo_planning_bootstrap.runtime_projection import _print_report as _print_report


from repo_planning_bootstrap.runtime_projection import _print_reconcile as _print_reconcile


from repo_planning_bootstrap.runtime_projection import _print_handoff as _print_handoff


_RUNTIME_EXPORT_SOURCES = (
    ('repo_planning_bootstrap.runtime_projection', '_print_summary', '_print_summary'),
    ('repo_planning_bootstrap.runtime_projection', '_print_report', '_print_report'),
    ('repo_planning_bootstrap.runtime_projection', '_print_reconcile', '_print_reconcile'),
    ('repo_planning_bootstrap.runtime_projection', '_print_handoff', '_print_handoff'),
)


def _sync_runtime_export_patches() -> None:
    for module_name, source_name, exported_name in _RUNTIME_EXPORT_SOURCES:
        value = globals().get(exported_name)
        module = importlib.import_module(module_name)
        if getattr(module, source_name, None) is not value:
            setattr(module, source_name, value)


def _program_name() -> str:
    invoked = sys.argv[0].replace("\\", "/").rsplit("/", 1)[-1]
    if invoked == 'agentic-planning':
        return invoked
    return 'agentic-planning'


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


def _run_planning_adopt_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.adopt.lifecycle'), args)


def _run_planning_archive_plan_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.archive-plan.lifecycle'), args)


def _run_planning_close_item_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.close-item.lifecycle'), args)


def _run_planning_create_review_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.create-review.lifecycle'), args)


def _run_planning_delegation_decision_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.delegation-decision.lifecycle'), args)


def _run_planning_doctor_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.doctor.report'), args)


def _run_planning_handoff_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.handoff.report'), args)


def _run_planning_init_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.init.lifecycle'), args)


def _run_planning_install_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.install.lifecycle'), args)


def _run_planning_list_files_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.list-files.report'), args)


def _run_planning_new_plan_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.new-plan.lifecycle'), args)


def _run_planning_promote_to_plan_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.promote-to-plan.lifecycle'), args)


def _run_planning_prompt_render_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.prompt.render'), args)


def _run_planning_reconcile_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.reconcile.report'), args)


def _run_planning_record_recovery_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.record-recovery.lifecycle'), args)


def _run_planning_report_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.report.report'), args)


def _run_planning_status_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.status.report'), args)


def _run_planning_summary_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.summary.report'), args)


def _run_planning_uninstall_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.uninstall.lifecycle'), args)


def _run_planning_upgrade_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.upgrade.lifecycle'), args)


def _run_planning_verify_payload_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract('planning.verify-payload.report'), args)



_GENERATED_RUNTIME_HANDLERS = {
    'planning.adopt.lifecycle': _run_planning_adopt_lifecycle_adapter,
    'planning.archive-plan.lifecycle': _run_planning_archive_plan_lifecycle_adapter,
    'planning.close-item.lifecycle': _run_planning_close_item_lifecycle_adapter,
    'planning.create-review.lifecycle': _run_planning_create_review_lifecycle_adapter,
    'planning.delegation-decision.lifecycle': _run_planning_delegation_decision_lifecycle_adapter,
    'planning.doctor.report': _run_planning_doctor_report_adapter,
    'planning.handoff.report': _run_planning_handoff_report_adapter,
    'planning.init.lifecycle': _run_planning_init_lifecycle_adapter,
    'planning.install.lifecycle': _run_planning_install_lifecycle_adapter,
    'planning.list-files.report': _run_planning_list_files_report_adapter,
    'planning.new-plan.lifecycle': _run_planning_new_plan_lifecycle_adapter,
    'planning.promote-to-plan.lifecycle': _run_planning_promote_to_plan_lifecycle_adapter,
    'planning.prompt.render': _run_planning_prompt_render_adapter,
    'planning.reconcile.report': _run_planning_reconcile_report_adapter,
    'planning.record-recovery.lifecycle': _run_planning_record_recovery_lifecycle_adapter,
    'planning.report.report': _run_planning_report_report_adapter,
    'planning.status.report': _run_planning_status_report_adapter,
    'planning.summary.report': _run_planning_summary_report_adapter,
    'planning.uninstall.lifecycle': _run_planning_uninstall_lifecycle_adapter,
    'planning.upgrade.lifecycle': _run_planning_upgrade_lifecycle_adapter,
    'planning.verify-payload.report': _run_planning_verify_payload_report_adapter,
}
