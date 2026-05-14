from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from repo_planning_bootstrap.installer import (
    InstallResult,
    collect_status,
    doctor_bootstrap,
    format_actions,
    format_result_json,
    planning_report,
    planning_report_tiny,
)

from agentic_command_generation.primitive_executor import PrimitiveContext, PrimitiveExecutionError, run_operation_steps


class OperationIrExecutionError(RuntimeError):
    pass


def run_operation_ir(operation: dict[str, Any], args: argparse.Namespace) -> int:
    if operation.get("id") not in {"planning.doctor.report", "planning.report.report", "planning.status.report"}:
        raise OperationIrExecutionError(f"unsupported operation IR contract: {operation.get('id')!r}")
    if operation.get("migration_status") != "runtime-consumed":
        raise OperationIrExecutionError(f"operation is not marked runtime-consumed: {operation.get('id')!r}")

    try:
        run_operation_steps(
            operation,
            initial_values={
                "target": getattr(args, "target", None),
                "format": getattr(args, "format", "text"),
                "verbose": getattr(args, "verbose", False),
            },
            context=PrimitiveContext(cwd=Path.cwd(), roots={}),
            handlers={
                "planning.bootstrap.doctor.load": _load_planning_bootstrap_doctor,
                "planning.report.load": _load_planning_report,
                "planning.bootstrap.status.load": _load_planning_bootstrap_status,
                "output.emit": _emit_planning_operation_output,
            },
        )
    except PrimitiveExecutionError as exc:
        raise OperationIrExecutionError(str(exc)) from exc
    return 0


def _load_planning_bootstrap_doctor(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> InstallResult:
    return doctor_bootstrap(target=values.get("target"))


def _load_planning_report(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> dict[str, Any]:
    if values.get("verbose"):
        return planning_report(target=values.get("target"))
    return planning_report_tiny(target=values.get("target"))


def _load_planning_bootstrap_status(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> InstallResult:
    return collect_status(target=values.get("target"))


def _emit_planning_operation_output(values: dict[str, Any], _arguments: dict[str, Any], _context: PrimitiveContext) -> None:
    _emit_operation_output(values["result"], output_format=str(values.get("format") or "text"))


def _emit_operation_output(result: Any, *, output_format: str) -> None:
    if isinstance(result, dict):
        if output_format == "json":
            print(json.dumps(result, indent=2))
            return
        _print_report(result)
        return

    if output_format == "json":
        print(format_result_json(result))
        return

    print(f"Target: {result.target_root}")
    print(result.message)
    for line in format_actions(result.actions, result.target_root):
        print(f"- {line}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- [{warning['warning_class']}] {warning['path']}: {warning['message']}")


def _print_report(report: dict[str, Any]) -> None:
    print(f"Target: {report['target_root']}")
    print("Command: report")
    print(f"Health: {report['health']}")
    status = report.get("status", {})
    if isinstance(status, dict):
        print(
            "Status: "
            f"{status.get('active_todo_count', 0)} active TODO / "
            f"{status.get('queued_todo_count', 0)} queued TODO / "
            f"{status.get('active_execplan_count', 0)} active execplans / "
            f"{status.get('completed_execplan_count', 0)} completed execplans / "
            f"{status.get('roadmap_lane_count', 0)} roadmap lanes / "
            f"{status.get('roadmap_candidate_count', 0)} roadmap candidates"
        )
    next_action = report.get("next_action", {})
    if isinstance(next_action, dict) and next_action.get("summary"):
        print(f"Next action: {next_action['summary']}")
    ownership_review = report.get("ownership_review", {})
    if isinstance(ownership_review, dict) and ownership_review.get("status") == "present":
        print(
            "Ownership review: "
            f"{len(ownership_review.get('repo_owned_surfaces', []))} repo-owned / "
            f"{len(ownership_review.get('package_owned_roots', []))} package-owned roots"
        )
    active = report.get("active", {})
    if isinstance(active, dict):
        _print_report_active_section(active)
    intent_validation = report.get("intent_validation", {})
    if isinstance(intent_validation, dict) and intent_validation.get("status") == "present":
        _print_report_intent_validation(intent_validation)
    finished_work_inspection = report.get("finished_work_inspection", {})
    if isinstance(finished_work_inspection, dict) and finished_work_inspection.get("status") == "present":
        _print_report_finished_work_inspection(finished_work_inspection)
    completed_execplans = report.get("completed_execplans", [])
    if completed_execplans:
        print(f"Completed execplans awaiting archive: {len(completed_execplans)}")
        for item in completed_execplans:
            print(f"- {item.get('path', '')}: {item.get('status', '')}")
            proof_report = item.get("proof_report", {})
            if proof_report:
                print(f"  Proof report: {proof_report.get('proof achieved now', '')}")
            intent_satisfaction = item.get("intent_satisfaction", {})
            if intent_satisfaction:
                print(f"  Intent satisfaction: {intent_satisfaction.get('was original intent fully satisfied?', '')}")
            closure_check = item.get("closure_check", {})
            if closure_check:
                print(f"  Closure decision: {closure_check.get('closure decision', '')}")
    findings = report.get("findings", [])
    if findings:
        print("Findings:")
        for finding in findings:
            path = f"{finding['path']}: " if finding.get("path") else ""
            print(f"- {path}{finding.get('message', '')}")


def _print_report_active_section(active: dict[str, Any]) -> None:
    hierarchy_contract = active.get("hierarchy_contract", {})
    if isinstance(hierarchy_contract, dict) and hierarchy_contract.get("status") == "present":
        parent_lane = hierarchy_contract.get("parent_lane", {})
        active_chunk = hierarchy_contract.get("active_chunk", {})
        lane_label = parent_lane.get("id") or parent_lane.get("title") or "unspecified"
        print(f"Hierarchy: {lane_label} -> {active_chunk.get('milestone_id', '') or active_chunk.get('todo_id', '')}")
    context_budget_contract = active.get("context_budget_contract", {})
    if isinstance(context_budget_contract, dict) and context_budget_contract.get("status") == "present":
        print(f"Live working set: {context_budget_contract.get('live_working_set', '')}")
        print(f"Pre-work config pull: {context_budget_contract.get('pre_work_config_pull', '')}")
        print(f"Pre-work memory pull: {context_budget_contract.get('pre_work_memory_pull', '')}")
    planning_record = active.get("planning_record", {})
    if isinstance(planning_record, dict) and planning_record.get("status") == "present":
        proof_report = planning_record.get("proof_report", {})
        intent_satisfaction = planning_record.get("intent_satisfaction", {})
        closure_check = planning_record.get("closure_check", {})
        if proof_report:
            print(f"Proof report: {proof_report.get('proof achieved now', '')}")
        if intent_satisfaction:
            print(f"Intent satisfaction: {intent_satisfaction.get('was original intent fully satisfied?', '')}")
        if closure_check:
            print(f"Closure decision: {closure_check.get('closure decision', '')}")
    intent_interpretation_contract = active.get("intent_interpretation_contract", {})
    if isinstance(intent_interpretation_contract, dict) and intent_interpretation_contract.get("status") == "present":
        print(f"Intent interpretation: {intent_interpretation_contract.get('interpretation_distance', '')}")
    execution_run_contract = active.get("execution_run_contract", {})
    if isinstance(execution_run_contract, dict) and execution_run_contract.get("status") == "present":
        print(f"Execution run: {execution_run_contract.get('run_status', '')}")
        print(f"Changed surfaces: {execution_run_contract.get('changed_surfaces', '')}")
    finished_run_review_contract = active.get("finished_run_review_contract", {})
    if isinstance(finished_run_review_contract, dict) and finished_run_review_contract.get("status") == "present":
        print(f"Finished-run review: {finished_run_review_contract.get('review_status', '')}")


def _print_report_intent_validation(intent_validation: dict[str, Any]) -> None:
    counts = intent_validation.get("counts", {})
    external = intent_validation.get("external_evidence", {})
    current_external = intent_validation.get("current_external_work", {})
    historical_audit = intent_validation.get("historical_audit_references", {})
    print(
        "Intent validation: "
        f"{counts.get('attention_count', 0)} attention / "
        f"{counts.get('untracked_external_open_count', 0)} untracked external open / "
        f"{counts.get('lower_trust_closeout_count', 0)} lower-trust closeouts"
    )
    print(f"External intent evidence: {external.get('status', 'absent')}")
    print(
        "Current external work: "
        f"{current_external.get('status', 'absent')} "
        f"({current_external.get('open_count', 0)} open / {current_external.get('closed_count', 0)} closed)"
    )
    print(
        "Historical audit references: "
        f"{historical_audit.get('status', 'absent')} "
        f"({historical_audit.get('follow_up_open_count', 0)} follow-up open)"
    )


def _print_report_finished_work_inspection(finished_work_inspection: dict[str, Any]) -> None:
    counts = finished_work_inspection.get("counts", {})
    evidence = finished_work_inspection.get("evidence", {})
    print(
        "Finished-work inspection: "
        f"{counts.get('attention_count', 0)} attention / "
        f"{counts.get('likely_premature_closeout_count', 0)} likely premature / "
        f"{counts.get('partial_count', 0)} partial archived lanes"
    )
    print(f"Finished-work evidence: {evidence.get('status', 'absent')}")
