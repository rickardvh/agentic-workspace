from __future__ import annotations

import argparse
import sys

from repo_planning_bootstrap import runtime_projection as _runtime_projection

from . import (
    build_generated_parser as build_generated_cli_package_parser,
)
from . import (
    generated_operation_contract as generated_cli_package_operation_contract,
)
from . import (
    run_generated_command as run_generated_cli_package_command,
)
from .planning_operation_ir_executor import run_operation_ir


def _program_name() -> str:
    invoked = sys.argv[0].replace("\\", "/").rsplit("/", 1)[-1]
    if invoked == "agentic-planning":
        return invoked
    return "agentic-planning"


def build_parser() -> argparse.ArgumentParser:
    return build_generated_cli_package_parser()


def _print_summary(summary: dict) -> None:
    _runtime_projection._print_summary(summary)


def _print_report(report: dict) -> None:
    _runtime_projection._print_report(report)


def _print_reconcile(reconcile: dict) -> None:
    _runtime_projection._print_reconcile(reconcile)


def _print_handoff(handoff: dict) -> None:
    _runtime_projection._print_handoff(handoff)


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    return run_generated_cli_package_command(argv_list, _run_generated_cli_operation)


def _run_generated_cli_operation(operation_id: str, args: argparse.Namespace) -> int:
    handler = _GENERATED_RUNTIME_HANDLERS.get(operation_id)
    if handler is None:
        build_generated_cli_package_parser().error(
            f"Generated adapter for {getattr(args, 'command', operation_id)} references unsupported operation {operation_id}."
        )
        raise SystemExit(2)
    return handler(args)


def _run_adopt_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.adopt.lifecycle"), args)


def _run_archive_plan_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.archive-plan.lifecycle"), args)


def _run_close_item_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.close-item.lifecycle"), args)


def _run_create_review_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.create-review.lifecycle"), args)


def _run_delegation_decision_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.delegation-decision.lifecycle"), args)


def _run_doctor_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.doctor.report"), args)


def _run_handoff_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.handoff.report"), args)


def _run_init_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.init.lifecycle"), args)


def _run_install_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.install.lifecycle"), args)


def _run_list_files_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.list-files.report"), args)


def _run_new_plan_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.new-plan.lifecycle"), args)


def _run_promote_to_plan_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.promote-to-plan.lifecycle"), args)


def _run_prompt_render_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.prompt.render"), args)


def _run_reconcile_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.reconcile.report"), args)


def _run_record_recovery_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.record-recovery.lifecycle"), args)


def _run_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.report.report"), args)


def _run_status_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.status.report"), args)


def _run_summary_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.summary.report"), args)


def _run_uninstall_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.uninstall.lifecycle"), args)


def _run_upgrade_lifecycle_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.upgrade.lifecycle"), args)


def _run_verify_payload_report_adapter(args: argparse.Namespace) -> int:
    return run_operation_ir(generated_cli_package_operation_contract("planning.verify-payload.report"), args)


_GENERATED_RUNTIME_HANDLERS = {
    "planning.adopt.lifecycle": _run_adopt_lifecycle_adapter,
    "planning.archive-plan.lifecycle": _run_archive_plan_lifecycle_adapter,
    "planning.close-item.lifecycle": _run_close_item_lifecycle_adapter,
    "planning.create-review.lifecycle": _run_create_review_lifecycle_adapter,
    "planning.delegation-decision.lifecycle": _run_delegation_decision_lifecycle_adapter,
    "planning.doctor.report": _run_doctor_report_adapter,
    "planning.handoff.report": _run_handoff_report_adapter,
    "planning.init.lifecycle": _run_init_lifecycle_adapter,
    "planning.install.lifecycle": _run_install_lifecycle_adapter,
    "planning.list-files.report": _run_list_files_report_adapter,
    "planning.new-plan.lifecycle": _run_new_plan_lifecycle_adapter,
    "planning.promote-to-plan.lifecycle": _run_promote_to_plan_lifecycle_adapter,
    "planning.prompt.render": _run_prompt_render_adapter,
    "planning.reconcile.report": _run_reconcile_report_adapter,
    "planning.record-recovery.lifecycle": _run_record_recovery_lifecycle_adapter,
    "planning.report.report": _run_report_adapter,
    "planning.status.report": _run_status_report_adapter,
    "planning.summary.report": _run_summary_report_adapter,
    "planning.uninstall.lifecycle": _run_uninstall_lifecycle_adapter,
    "planning.upgrade.lifecycle": _run_upgrade_lifecycle_adapter,
    "planning.verify-payload.report": _run_verify_payload_report_adapter,
}
