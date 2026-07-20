from __future__ import annotations

import contextlib
import io
import json
import shutil
from collections.abc import Callable
from typing import Any

from repo_planning_bootstrap._source import UpgradeSource, resolve_upgrade_source
from repo_planning_bootstrap.installer import (
    activate_lane_record,
    apply_integration_proposal,
    archive_execplan,
    archive_lane_record,
    archive_parent_lane_closeout,
    close_lane_record,
    closeout_execplan,
    create_decomposition_record,
    create_execplan_scaffold,
    create_lane_record,
    format_actions,
    format_result_json,
    format_summary_json,
    intake_planning_artifact,
    list_bundled_skill_files,
    list_default_payload_files,
    list_optional_payload_files,
    list_payload_files,
    planning_reconcile,
    planning_report,
    planning_report_tiny,
    planning_summary,
    promote_decomposition_lane_to_lane_record,
    promote_todo_item_to_execplan,
    propose_integration_transition,
    record_delegation_decision,
    select_existing_owner,
    shape_issue_relation,
)


def load_planning_report_operation(values: dict, _arguments: dict, _context) -> dict | str:
    if values.get("verbose"):
        report = planning_report(
            target=values.get("target"),
            audit_cursor=str(values.get("audit_cursor") or ""),
            audit_page_size=int(values.get("audit_page_size") or 25),
        )
        if str(values.get("format") or "text") != "json":
            with contextlib.redirect_stdout(io.StringIO()) as output:
                _print_report(report)
            return output.getvalue().rstrip()
        return report
    return planning_report_tiny(target=values.get("target"))


def load_planning_summary_operation(values: dict, _arguments: dict, _context) -> dict:
    summary_profile = "full" if values.get("verbose") or values.get("format") != "json" else "tiny"
    return planning_summary(
        target=values.get("target"),
        profile=summary_profile,
        task_text=values.get("task"),
        changed_paths=list(values.get("changed") or []),
    )


def load_planning_reconcile_operation(values: dict, _arguments: dict, _context) -> dict:
    return planning_reconcile(
        target=values.get("target"),
        apply_safe_prune=bool(values.get("apply_safe_prune")),
        dry_run=bool(values.get("dry_run")),
        lane=str(values.get("lane") or ""),
        apply_lane_reconcile=bool(values.get("apply_lane_reconcile")),
        issue=str(values.get("issue") or ""),
        external_ref=str(values.get("external_ref") or ""),
        priority=str(values.get("priority") or ""),
        depends_on=str(values.get("depends_on") or ""),
        rationale=str(values.get("rationale") or ""),
        maturity=str(values.get("maturity") or ""),
        expected_relation_revision=str(values.get("expect_relation_revision") or ""),
        apply_issue_relation_reconcile=bool(values.get("apply_issue_relation_reconcile")),
        apply_issue_relation_migration=bool(values.get("apply_issue_relation_migration")),
        preview=bool(values.get("preview")),
        apply=bool(values.get("apply")),
        proposal=str(values.get("proposal") or ""),
        expected_planning_revision=str(values.get("expected_planning_revision") or ""),
    )


def load_planning_list_files_operation(_values: dict, _arguments: dict, _context) -> dict:
    return {
        "files": list_payload_files(),
        "default_files": list_default_payload_files(),
        "optional_files": list_optional_payload_files(),
        "bundled_skill_files": list_bundled_skill_files(),
        "optional_enable_commands": [
            "agentic-planning install --include-optional",
            "agentic-planning adopt --include-optional",
            "agentic-planning upgrade --include-optional",
        ],
    }


def render_planning_prompt_operation(values: dict, _arguments: dict, _context) -> str:
    return _build_prompt(str(values.get("prompt_command") or ""), values.get("target"))


def _planning_operation_value(values: dict, source: str, coerce: str = "raw", default: Any = None) -> Any:
    if coerce == "str":
        return str(values.get(source) or default or "")
    if coerce == "bool":
        return bool(values.get(source))
    if coerce == "not_bool":
        return not bool(values.get(source))
    if coerce == "false":
        return False
    value = values.get(source)
    if value is None and default is not None:
        return default
    return value


def _call_planning_operation(
    function: Callable[..., Any],
    values: dict,
    *,
    positional: tuple[tuple[str, str, Any], ...] = (),
    keywords: tuple[tuple[str, str, str, Any], ...] = (),
) -> Any:
    args = [_planning_operation_value(values, source, coerce, default) for source, coerce, default in positional]
    kwargs = {target: _planning_operation_value(values, source, coerce, default) for target, source, coerce, default in keywords}
    return function(*args, **kwargs)


def apply_planning_new_plan_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        create_execplan_scaffold,
        values,
        keywords=(
            ("plan_id", "id", "str", ""),
            ("title", "title", "str", ""),
            ("source", "source", "str", ""),
            ("target", "target", "raw", None),
            ("activate", "activate", "bool", None),
            ("queue", "queue", "bool", None),
            ("switch_active", "switch_active", "bool", None),
            ("lane", "lane", "str", ""),
            ("prep_only", "prep_only", "bool", None),
            ("overwrite", "overwrite", "bool", None),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_intake_artifact_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        intake_planning_artifact,
        values,
        keywords=(
            ("artifact", "artifact", "str", ""),
            ("target", "target", "raw", None),
            ("route", "route", "str", "auto"),
            ("artifact_id", "id", "str", ""),
            ("title", "title", "str", ""),
            ("activate", "activate", "bool", None),
            ("queue", "queue", "bool", None),
            ("switch_active", "switch_active", "bool", None),
            ("remove_source", "remove_source", "bool", None),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_promote_to_plan_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        promote_todo_item_to_execplan,
        values,
        positional=(("item_id", "str", ""),),
        keywords=(
            ("target", "target", "raw", None),
            ("plan_slug", "plan_slug", "raw", None),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_lane_create_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        create_lane_record,
        values,
        keywords=(
            ("lane_id", "id", "str", ""),
            ("title", "title", "str", ""),
            ("target", "target", "raw", None),
            ("parent_decomposition", "parent_decomposition", "str", ""),
            ("outcome", "outcome", "str", ""),
            ("purpose", "purpose", "str", ""),
            ("proof_strategy", "proof_strategy", "str", ""),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_decomposition_create_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        create_decomposition_record,
        values,
        keywords=(
            ("decomposition_id", "id", "str", ""),
            ("title", "title", "str", ""),
            ("outcome", "outcome", "str", ""),
            ("target", "target", "raw", None),
            (
                "promotion_rule",
                "promotion_rule",
                "str",
                "Promote a candidate lane only after its scope, owner surface, and proof are ready.",
            ),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_lane_promote_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        promote_decomposition_lane_to_lane_record,
        values,
        positional=(("lane", "str", ""),),
        keywords=(
            ("alternate_lane_id", "alternate_lane_id", "str", ""),
            ("target", "target", "raw", None),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_lane_activate_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        activate_lane_record,
        values,
        positional=(("lane", "str", ""),),
        keywords=(
            ("target", "target", "raw", None),
            ("current_slice", "current_slice", "str", ""),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_owner_select_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        select_existing_owner,
        values,
        positional=(("owner", "str", ""),),
        keywords=(
            ("owner_ref", "owner_ref", "str", ""),
            ("target", "target", "raw", None),
            ("mode", "mode", "str", "local"),
            ("reason", "reason", "str", ""),
            ("current_work_id", "current_work_id", "str", ""),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("expected_current_work_revision", "expect_current_work_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_issue_shape_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        shape_issue_relation,
        values,
        keywords=(
            ("issue", "issue", "str", ""),
            ("external_ref", "external_ref", "str", ""),
            ("lane", "lane", "str", ""),
            ("priority", "priority", "str", ""),
            ("depends_on", "depends_on", "str", ""),
            ("rationale", "rationale", "str", ""),
            ("maturity", "maturity", "str", ""),
            ("target", "target", "raw", None),
            ("expected_relation_revision", "expect_relation_revision", "str", ""),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_integration_propose_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        propose_integration_transition,
        values,
        keywords=(
            ("proposal_id", "proposal_id", "str", ""),
            ("owner", "owner", "str", ""),
            ("owner_ref", "owner_ref", "str", ""),
            ("issue", "issue", "str", ""),
            ("external_ref", "external_ref", "str", ""),
            ("requested_transition", "requested_transition", "str", ""),
            ("proof", "proof", "str", ""),
            ("parent_boundary", "parent_boundary", "str", ""),
            ("invariant", "invariant", "str", ""),
            ("expected_subject_revision", "expect_subject_revision", "str", ""),
            ("expected_target_revision", "expect_target_revision", "str", ""),
            ("target", "target", "raw", None),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_integration_apply_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        apply_integration_proposal,
        values,
        keywords=(
            ("proposal", "proposal", "str", ""),
            ("target", "target", "raw", None),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_lane_close_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        close_lane_record,
        values,
        positional=(("lane", "str", ""),),
        keywords=(
            ("target", "target", "raw", None),
            ("proof", "proof", "str", ""),
            ("residual_work", "residual_work", "str", ""),
            ("parent_contribution", "parent_contribution", "str", ""),
            ("parent_close_permission", "parent_close_permission", "str", "may-advance-parent"),
            ("next_owner", "next_owner", "str", ""),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_lane_archive_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        archive_lane_record,
        values,
        positional=(("lane", "str", ""),),
        keywords=(
            ("target", "target", "raw", None),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def apply_planning_archive_plan_operation(values: dict, _arguments: dict, _context):
    if values.get("parent_lane_closeout"):
        return _call_planning_operation(
            archive_parent_lane_closeout,
            values,
            positional=(("parent_lane_closeout", "str", ""),),
            keywords=(
                ("target", "target", "raw", None),
                ("dry_run", "dry_run", "bool", None),
                ("expected_planning_revision", "expect_planning_revision", "str", ""),
                ("intent_satisfied", "intent_satisfied", "raw", None),
                ("intent_evidence", "intent_evidence", "raw", None),
                ("closure_reason", "closure_reason", "raw", None),
                ("closure_evidence", "closure_evidence", "raw", None),
                ("reopen_trigger", "reopen_trigger", "raw", None),
                ("discard_summary", "discard_summary", "raw", None),
                ("continuation_summary", "continuation_summary", "raw", None),
            ),
        )
    return _call_planning_operation(
        archive_execplan,
        values,
        positional=(("plan", "str", ""),),
        keywords=(
            ("target", "target", "raw", None),
            ("dry_run", "dry_run", "bool", None),
            ("apply_cleanup", "apply_cleanup", "bool", None),
            ("prepare_closeout", "prepare_closeout", "bool", None),
            ("closure_decision", "closure_decision", "raw", None),
            ("intent_satisfied", "intent_satisfied", "raw", None),
            ("unsolved_intent", "unsolved_intent", "raw", None),
            ("intent_evidence", "intent_evidence", "raw", None),
            ("closure_reason", "closure_reason", "raw", None),
            ("closure_evidence", "closure_evidence", "raw", None),
            ("reopen_trigger", "reopen_trigger", "raw", None),
            ("discard_summary", "discard_summary", "raw", None),
            ("continuation_summary", "continuation_summary", "raw", None),
            ("retain_archive", "retain_archive", "bool", None),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("decision_point_carry_key", "decision_point_carry_key", "str", ""),
            ("prune_decision_point_carry_key", "prune_decision_point_carry_key", "str", ""),
        ),
    )


def apply_planning_closeout_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        closeout_execplan,
        values,
        positional=(("plan", "str", ""),),
        keywords=(
            ("target", "target", "raw", None),
            ("dry_run", "dry_run", "bool", None),
            ("claim_level", "claim_level", "str", "slice"),
            ("intent_status", "intent_status", "str", "satisfied"),
            ("residue", "residue", "str", "none"),
            ("proof_from", "proof_from", "str", "last"),
            ("proof_file", "proof_file", "raw", None),
            ("residue_owner", "residue_owner", "raw", None),
            ("retain_archive", "discard_archive", "false", None),
            ("what_happened", "what_happened", "raw", None),
            ("scope_touched", "scope_touched", "raw", None),
            ("changed_surfaces", "changed_surfaces", "raw", None),
            ("review_summary", "review_summary", "raw", None),
            ("outcome_summary", "outcome_summary", "raw", None),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
        ),
    )


def apply_planning_delegation_decision_operation(values: dict, _arguments: dict, _context):
    return _call_planning_operation(
        record_delegation_decision,
        values,
        keywords=(
            ("target", "target", "raw", None),
            ("plan", "plan", "raw", None),
            ("route", "route", "str", ""),
            ("skipped_reason", "skipped_reason", "str", ""),
            ("expected_savings", "expected_savings", "str", ""),
            ("actual_friction", "actual_friction", "str", ""),
            ("proof_result", "proof_result", "str", ""),
            ("quality_concern", "quality_concern", "str", ""),
            ("decomposition_adjustment", "decomposition_adjustment", "str", ""),
            ("expected_planning_revision", "expect_planning_revision", "str", ""),
            ("dry_run", "dry_run", "bool", None),
        ),
    )


def emit_planning_operation_output(values: dict, _arguments: dict, _context) -> None:
    result = values["result"]
    output_format = str(values.get("format") or "text")
    operation_id = str(values.get("operation_id") or "")
    if operation_id == "planning.list-files.report":
        if output_format == "json":
            print(json.dumps(result, indent=2))
        else:
            for path in result.get("files", []):
                print(path)
        return
    if operation_id == "planning.prompt.render":
        print(str(result))
        return
    if operation_id == "planning.summary.report":
        if output_format == "json":
            print(format_summary_json(result))
        else:
            _print_summary(result)
        return
    if operation_id == "planning.reconcile.report":
        if output_format == "json":
            print(json.dumps(result, indent=2))
        else:
            _print_reconcile(result)
        return
    if operation_id == "planning.handoff.report":
        if output_format == "json":
            print(json.dumps(result, indent=2))
        else:
            _print_handoff(result)
        return
    if output_format == "json":
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(format_result_json(result))
        return
    if isinstance(result, dict):
        _print_report(result)
        return
    _emit(result, output_format)


def _emit(result, output_format: str) -> int:
    if output_format == "json":
        print(format_result_json(result))
        return 0
    print(f"Target: {result.target_root}")
    print(result.message)
    mutation_outcome = result.to_dict() if result.mutation_expected else {}
    if mutation_outcome:
        print(f"Outcome: {mutation_outcome['outcome']} ({mutation_outcome['reason_code']})")
        print(f"Mutation applied: {'yes' if mutation_outcome['mutation_applied'] else 'no'}")
        if mutation_outcome.get("conflict_owner"):
            print(f"Conflict owner: {mutation_outcome['conflict_owner']}")
        if mutation_outcome.get("recovery_command"):
            print(f"Recovery: {mutation_outcome['recovery_command']}")
    for line in format_actions(result.actions, result.target_root):
        print(f"- {line}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"- [{warning['warning_class']}] {warning['path']}: {warning['message']}")
    return 0


def _print_summary(summary: dict) -> None:
    print(f"Target: {summary['target_root']}")
    print(f"Mode: {summary['adoption_mode']}")
    print(
        f"TODO: {summary['todo']['active_count']} active / "
        f"{summary['todo'].get('queued_count', 0)} queued / "
        f"{summary['todo']['item_count']} items / {summary['todo']['line_count']} lines"
    )
    print(
        f"Execplans: {summary['execplans']['active_count']} active / "
        f"{summary['execplans'].get('completed_count', 0)} completed / "
        f"{summary['execplans']['archived_count']} archived"
    )
    print(f"Roadmap: {summary['roadmap'].get('lane_count', 0)} candidate lanes / {summary['roadmap']['candidate_count']} candidate bullets")
    lanes = summary.get("lanes", {})
    if isinstance(lanes, dict) and lanes:
        print(
            f"Lane records: {lanes.get('active_count', 0)} active / "
            f"{lanes.get('open_count', 0)} open / {lanes.get('closed_count', 0)} closed"
        )
        for lane in lanes.get("records", [])[:3]:
            if not isinstance(lane, dict):
                continue
            proof = lane.get("proof_aggregation", {}) if isinstance(lane.get("proof_aggregation"), dict) else {}
            print(
                f"- {lane.get('id', '')}: {lane.get('status', '')}; "
                f"proof {proof.get('status', '')}; parent {lane.get('parent_close_permission', '')}"
            )
    planning_surface_health = summary.get("planning_surface_health", {})
    if isinstance(planning_surface_health, dict) and planning_surface_health:
        print("Planning-surface health:")
        print(f"- Status: {planning_surface_health.get('status', 'unknown')}")
        print(f"- Warning count: {planning_surface_health.get('warning_count', 0)}")
        print(f"- Recommended next action: {planning_surface_health.get('recommended_next_action', '')}")
        for warning in planning_surface_health.get("warnings", [])[:3]:
            print(f"- [{warning.get('warning_class', '')}] {warning.get('path', '')}: {warning.get('message', '')}")
    ownership_review = summary.get("ownership_review", {})
    if ownership_review.get("status") == "present":
        print("Ownership review:")
        print(f"- Package-owned roots: {', '.join(ownership_review.get('package_owned_roots', []))}")
        print(f"- Repo-owned surfaces: {', '.join(ownership_review.get('repo_owned_surfaces', []))}")
        print(f"- Minimal repo hook: {ownership_review.get('minimal_repo_hook', '')}")
    residue_governance = summary.get("residue_governance", {})
    if isinstance(residue_governance, dict) and residue_governance.get("status"):
        review_routing = residue_governance.get("review_routing", {})
        review_routing = review_routing if isinstance(review_routing, dict) else {}
        read_first = review_routing.get("read_first", [])
        read_first_text = ", ".join(str(path) for path in read_first[:3]) if isinstance(read_first, list) else ""
        print(
            "Residue governance: "
            f"{residue_governance.get('review_count', 0)} reviews / "
            f"{residue_governance.get('archived_execplan_count', 0)} archived execplans / "
            f"review routing {review_routing.get('status', 'unknown')}"
        )
        if read_first_text:
            print(f"- Review read-first: {read_first_text}")
    hierarchy_contract = summary.get("hierarchy_contract", {})
    if hierarchy_contract.get("status") == "present":
        parent_lane = hierarchy_contract.get("parent_lane", {})
        active_chunk = hierarchy_contract.get("active_chunk", {})
        proof_state = hierarchy_contract.get("proof_state", {})
        print("Planning hierarchy view:")
        if parent_lane.get("id") or parent_lane.get("title"):
            lane_label = parent_lane.get("title") or parent_lane.get("id", "")
            if parent_lane.get("id") and parent_lane.get("title"):
                lane_label = f"{parent_lane['id']}: {parent_lane['title']}"
            print(f"- Parent lane: {lane_label}")
        else:
            print("- Parent lane: unspecified")
        active_chunk_label = active_chunk.get("milestone_id", "") or active_chunk.get("todo_id", "")
        active_chunk_scope = active_chunk.get("milestone_scope", "")
        print(f"- Active chunk: {active_chunk_label}: {active_chunk_scope}")
        near_term_queue = hierarchy_contract.get("near_term_queue", [])
        if near_term_queue:
            next_queued = near_term_queue[0]
            print(f"- Near-term queue: {next_queued.get('id', '')}: {next_queued.get('surface', '')}")
        print(f"- Next likely chunk: {hierarchy_contract.get('next_likely_chunk', '')}")
        print(f"- Proof achieved now: {proof_state.get('proof_achieved_now', '')}")
        print(f"- Validation still needed: {proof_state.get('validation_still_needed', '')}")
    elif hierarchy_contract:
        print(
            "Planning hierarchy view: "
            f"{hierarchy_contract.get('status')} ({hierarchy_contract.get('reason', 'no hierarchy projection available')})"
        )
    planning_record = summary.get("planning_record", {})
    if planning_record.get("status") == "present":
        task = planning_record.get("task", {})
        print("Planning record:")
        print(f"- Task: {task.get('id', '')}: {task.get('surface', '')}")
        print(f"- Requested outcome: {planning_record['requested_outcome']}")
        print(f"- Next action: {planning_record['next_action']}")
        print(f"- Continuation owner: {planning_record['continuation_owner']}")
        print(f"- Proof expectations: {', '.join(planning_record['proof_expectations'])}")
        proof_report = planning_record.get("proof_report", {})
        if proof_report:
            proof_evidence = proof_report.get('evidence for "proof achieved" state', "")
            print(f"- Proof achieved now: {proof_report.get('proof achieved now', '')}")
            print(f'- Evidence for "Proof achieved" state: {proof_evidence}')
        intent_satisfaction = planning_record.get("intent_satisfaction", {})
        if intent_satisfaction:
            print(f"- Was original intent fully satisfied?: {intent_satisfaction.get('was original intent fully satisfied?', '')}")
            print(f"- Unsolved intent passed to: {intent_satisfaction.get('unsolved intent passed to', '')}")
        closure_check = planning_record.get("closure_check", {})
        if closure_check:
            print(f"- Closure decision: {closure_check.get('closure decision', '')}")
            print(f"- Larger-intent status: {closure_check.get('larger-intent status', '')}")
        intent_interpretation = planning_record.get("intent_interpretation", {})
        if intent_interpretation:
            print(f"- Literal request: {intent_interpretation.get('literal request', '')}")
            print(f"- Inferred intended outcome: {intent_interpretation.get('inferred intended outcome', '')}")
        execution_bounds = planning_record.get("execution_bounds", {})
        if execution_bounds:
            print(f"- Allowed paths: {execution_bounds.get('allowed paths', '')}")
            print(f"- Max changed files: {execution_bounds.get('max changed files', '')}")
        stop_conditions = planning_record.get("stop_conditions", {})
        if stop_conditions:
            print(f"- Stop when: {stop_conditions.get('stop when', '')}")
        execution_run = planning_record.get("execution_run", {})
        if execution_run:
            print(f"- Execution run status: {execution_run.get('run status', '')}")
            print(f"- Execution run next step: {execution_run.get('next step', '')}")
        finished_run_review = planning_record.get("finished_run_review", {})
        if finished_run_review:
            print(f"- Finished-run review: {finished_run_review.get('review status', '')}")
            print(f"- Intent served: {finished_run_review.get('intent served', '')}")
        tool_verification = planning_record.get("tool_verification", {})
        required_tools = tool_verification.get("required_tools", [])
        if required_tools:
            print(f"- Required tools: {', '.join(required_tools)}")
    elif planning_record:
        print(f"Planning record: {planning_record.get('status')} ({planning_record.get('reason', 'no compact record available')})")
    completed_execplans = summary.get("execplans", {}).get("completed_execplans", [])
    if completed_execplans:
        print("Completed execplans awaiting archive:")
        for item in completed_execplans:
            print(f"- {item.get('path', '')}: {item.get('status', '')}")
            proof_report = item.get("proof_report", {})
            if proof_report:
                print(f"  - Proof achieved now: {proof_report.get('proof achieved now', '')}")
            intent_satisfaction = item.get("intent_satisfaction", {})
            if intent_satisfaction:
                print(f"  - Intent satisfied: {intent_satisfaction.get('was original intent fully satisfied?', '')}")
            closure_check = item.get("closure_check", {})
            if closure_check:
                print(f"  - Closure decision: {closure_check.get('closure decision', '')}")
    active_contract = summary.get("active_contract", {})
    if active_contract.get("status") == "present":
        print("Active contract view:")
        print(f"- TODO item: {active_contract['todo_item']['id']}: {active_contract['todo_item']['surface']}")
    elif active_contract:
        print(f"Active contract view: {active_contract.get('status')} ({active_contract.get('reason', 'no compact contract available')})")
    resumable_contract = summary.get("resumable_contract", {})
    if resumable_contract.get("status") == "present":
        print("Resumable contract view:")
        print(f"- Next action: {resumable_contract['current_next_action']}")
    elif resumable_contract:
        print(
            "Resumable contract view: "
            f"{resumable_contract.get('status')} ({resumable_contract.get('reason', 'no resumable contract available')})"
        )
    follow_through_contract = summary.get("follow_through_contract", {})
    if follow_through_contract.get("status") == "present":
        print("Follow-through contract view:")
        print(f"- Enabled: {follow_through_contract['what_this_slice_enabled']}")
        print(f"- Next likely slice: {follow_through_contract['next_likely_slice']}")
    elif follow_through_contract:
        print(
            "Follow-through contract view: "
            f"{follow_through_contract.get('status')} ({follow_through_contract.get('reason', 'no follow-through contract available')})"
        )
    context_budget_contract = summary.get("context_budget_contract", {})
    if context_budget_contract.get("status") == "present":
        print("Context budget contract view:")
        print(f"- Live working set: {context_budget_contract.get('live_working_set', '')}")
        print(f"- Recoverable later: {context_budget_contract.get('recoverable_later', '')}")
        print(f"- Pre-work config pull: {context_budget_contract.get('pre_work_config_pull', '')}")
        print(f"- Pre-work memory pull: {context_budget_contract.get('pre_work_memory_pull', '')}")
        print(f"- Shift triggers: {context_budget_contract.get('context_shift_triggers', '')}")
    elif context_budget_contract:
        print(
            "Context budget contract view: "
            f"{context_budget_contract.get('status')} ({context_budget_contract.get('reason', 'no context-budget contract available')})"
        )
    intent_interpretation_contract = summary.get("intent_interpretation_contract", {})
    if intent_interpretation_contract.get("status") == "present":
        print("Intent-interpretation contract view:")
        print(f"- Literal request: {intent_interpretation_contract.get('literal_request', '')}")
        print(f"- Inferred intended outcome: {intent_interpretation_contract.get('inferred_intended_outcome', '')}")
    elif intent_interpretation_contract:
        print(
            "Intent-interpretation contract view: "
            f"{intent_interpretation_contract.get('status')} ({intent_interpretation_contract.get('reason', 'no intent-interpretation contract available')})"
        )
    execution_run_contract = summary.get("execution_run_contract", {})
    if execution_run_contract.get("status") == "present":
        print("Execution-run contract view:")
        print(f"- Run status: {execution_run_contract.get('run_status', '')}")
        print(f"- Executor: {execution_run_contract.get('executor', '')}")
        print(f"- Changed surfaces: {execution_run_contract.get('changed_surfaces', '')}")
        print(f"- Next step: {execution_run_contract.get('next_step', '')}")
    elif execution_run_contract:
        print(
            "Execution-run contract view: "
            f"{execution_run_contract.get('status')} ({execution_run_contract.get('reason', 'no execution-run contract available')})"
        )
    finished_run_review_contract = summary.get("finished_run_review_contract", {})
    if finished_run_review_contract.get("status") == "present":
        print("Finished-run review contract view:")
        print(f"- Review status: {finished_run_review_contract.get('review_status', '')}")
        print(f"- Scope respected: {finished_run_review_contract.get('scope_respected', '')}")
        print(f"- Intent served: {finished_run_review_contract.get('intent_served', '')}")
        print(f"- Config compliance: {finished_run_review_contract.get('config_compliance', '')}")
        print(f"- Config trust: {finished_run_review_contract.get('config_trust', '')}")
    elif finished_run_review_contract:
        print(
            "Finished-run review contract view: "
            f"{finished_run_review_contract.get('status')} ({finished_run_review_contract.get('reason', 'no finished-run review contract available')})"
        )
    intent_validation_contract = summary.get("intent_validation_contract", {})
    if intent_validation_contract.get("status") == "present":
        counts = intent_validation_contract.get("counts", {})
        external = intent_validation_contract.get("external_evidence", {})
        current_external = intent_validation_contract.get("current_external_work", {})
        historical_audit = intent_validation_contract.get("historical_audit_references", {})
        print("Intent-validation contract view:")
        print(f"- Attention count: {counts.get('attention_count', 0)}")
        print(f"- Untracked external open items: {counts.get('untracked_external_open_count', 0)}")
        print(f"- Lower-trust closeouts: {counts.get('lower_trust_closeout_count', 0)}")
        print(f"- External evidence: {external.get('status', 'absent')}")
        print(
            "- Current external work: "
            f"{current_external.get('status', 'absent')} "
            f"({current_external.get('open_count', 0)} open / {current_external.get('closed_count', 0)} closed)"
        )
        print(
            "- Historical audit references: "
            f"{historical_audit.get('status', 'absent')} "
            f"({historical_audit.get('follow_up_open_count', 0)} follow-up open)"
        )
        print(f"- Recommended next action: {intent_validation_contract.get('recommended_next_action', '')}")
    elif intent_validation_contract:
        print(
            "Intent-validation contract view: "
            f"{intent_validation_contract.get('status')} ({intent_validation_contract.get('reason', 'no intent-validation contract available')})"
        )
    finished_work_inspection_contract = summary.get("finished_work_inspection_contract", {})
    if finished_work_inspection_contract.get("status") == "present":
        counts = finished_work_inspection_contract.get("counts", {})
        evidence = finished_work_inspection_contract.get("evidence", {})
        print("Finished-work inspection contract view:")
        print(f"- Archived closeouts: {counts.get('archived_closeout_count', 0)}")
        print(f"- Likely premature closeouts: {counts.get('likely_premature_closeout_count', 0)}")
        print(f"- Partial archived lanes: {counts.get('partial_count', 0)}")
        print(f"- Optional evidence: {evidence.get('status', 'absent')}")
        print(f"- Recommended next action: {finished_work_inspection_contract.get('recommended_next_action', '')}")
    elif finished_work_inspection_contract:
        print(
            "Finished-work inspection contract view: "
            f"{finished_work_inspection_contract.get('status')} ({finished_work_inspection_contract.get('reason', 'no finished-work inspection contract available')})"
        )
    if summary["todo"]["active_items"]:
        print("Active items:")
        for item in summary["todo"]["active_items"]:
            print(f"- {item['id']}: {item['surface']}")
    if summary["warning_count"]:
        print(f"Warnings: {summary['warning_count']}")
        for warning in summary["warnings"]:
            print(f"- [{warning['warning_class']}] {warning['path']}: {warning['message']}")
    else:
        print("Warnings: none")


def _print_report(report: dict) -> None:
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
    residue_governance = report.get("residue_governance", {})
    if isinstance(residue_governance, dict) and residue_governance.get("status"):
        review_routing = residue_governance.get("review_routing", {})
        review_routing = review_routing if isinstance(review_routing, dict) else {}
        print(
            "Residue governance: "
            f"{residue_governance.get('review_count', 0)} reviews / "
            f"{residue_governance.get('archived_execplan_count', 0)} archived execplans / "
            f"review routing {review_routing.get('status', 'unknown')}"
        )
    active = report.get("active", {})
    if isinstance(active, dict):
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
    intent_validation = report.get("intent_validation", {})
    if isinstance(intent_validation, dict) and intent_validation.get("status") == "present":
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
    finished_work_inspection = report.get("finished_work_inspection", {})
    if isinstance(finished_work_inspection, dict) and finished_work_inspection.get("status") == "present":
        counts = finished_work_inspection.get("counts", {})
        evidence = finished_work_inspection.get("evidence", {})
        print(
            "Finished-work inspection: "
            f"{counts.get('attention_count', 0)} attention / "
            f"{counts.get('likely_premature_closeout_count', 0)} likely premature / "
            f"{counts.get('partial_count', 0)} partial archived lanes"
        )
        print(f"Finished-work evidence: {evidence.get('status', 'absent')}")
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


def _print_reconcile(reconcile: dict) -> None:
    print(f"Target: {reconcile['target_root']}")
    print("Command: reconcile")
    print(f"Status: {reconcile['status']}")
    external = reconcile.get("external_work_state", {})
    if isinstance(external, dict):
        print(
            "Current external work: "
            f"{external.get('status', 'absent')} / "
            f"{external.get('open_count', 0)} open / "
            f"{external.get('closed_count', 0)} closed / "
            f"{external.get('untracked_open_count', 0)} untracked open"
        )
    historical = reconcile.get("historical_audit_references", {})
    if isinstance(historical, dict):
        print(
            "Historical audit references: "
            f"{historical.get('status', 'absent')} / "
            f"{historical.get('follow_up_open_count', 0)} follow-up open / "
            f"{historical.get('needs_audit_count', 0)} need audit"
        )
    stale = reconcile.get("stale_forward_state", {})
    if isinstance(stale, dict):
        completed = stale.get("completed_live_execplans", [])
        closed_lanes = stale.get("closed_roadmap_lanes", [])
        print(f"Completed live execplans: {len(completed) if isinstance(completed, list) else 0}")
        print(f"Closed roadmap lanes: {len(closed_lanes) if isinstance(closed_lanes, list) else 0}")
    recommendations = reconcile.get("recommendations", [])
    if isinstance(recommendations, list) and recommendations:
        print("Recommendations:")
        for item in recommendations:
            print(f"- {item}")


def _print_handoff(handoff: dict) -> None:
    print(f"Target: {handoff['target_root']}")
    contract = handoff.get("handoff_contract", {})
    if contract.get("status") != "present":
        reason = contract.get("reason", "no delegated handoff is available")
        print(f"Handoff: unavailable ({reason})")
        return

    task = contract.get("task", {})
    print("Delegated handoff:")
    print(f"- Task: {task.get('id', '')}: {task.get('surface', '')}")
    parent_lane = contract.get("parent_lane", {})
    lane_label = parent_lane.get("id") or parent_lane.get("title")
    if lane_label:
        print(f"- Parent lane: {lane_label}")
    print(f"- Next action: {contract.get('next_action', '')}")
    print(f"- Read first: {', '.join(contract.get('read_first', []))}")
    print(f"- Write scope: {', '.join(contract.get('owned_write_scope', []))}")
    print(f"- Proof: {', '.join(contract.get('proof_expectations', []))}")
    references = contract.get("references", [])
    if references:
        rendered = []
        for reference in references:
            if not isinstance(reference, dict):
                continue
            target = str(reference.get("target", "")).strip()
            if not target:
                continue
            rendered.append(
                f"{reference.get('kind', 'artifact')}:{target}"
                + (f" ({reference.get('role', 'context')})" if reference.get("role") else "")
            )
        if rendered:
            print(f"- References: {', '.join(rendered)}")
    review_residue = contract.get("review_residue", [])
    if review_residue:
        rendered_reviews = []
        for review in review_residue:
            if not isinstance(review, dict):
                continue
            title = str(review.get("title", "")).strip()
            target = str(review.get("target", "")).strip()
            finding_count = review.get("finding_count", 0)
            if not title and not target:
                continue
            rendered_reviews.append(f"{title or target} ({finding_count} findings)")
        if rendered_reviews:
            print(f"- Review residue: {', '.join(rendered_reviews)}")
    capability_posture = contract.get("capability_posture", {})
    if isinstance(capability_posture, dict) and capability_posture:
        print(
            "- Capability posture: "
            f"{capability_posture.get('execution class', '')} / "
            f"{capability_posture.get('recommended strength', '')} / "
            f"{capability_posture.get('preferred location', '')}"
        )
        print(f"- Capability why: {capability_posture.get('why', '')}")
    intent_interpretation = contract.get("intent_interpretation", {})
    if isinstance(intent_interpretation, dict) and intent_interpretation.get("status") == "present":
        print(f"- Literal request: {intent_interpretation.get('literal_request', '')}")
        print(f"- Interpreted outcome: {intent_interpretation.get('inferred_intended_outcome', '')}")
    execution_bounds = contract.get("execution_bounds", {})
    if isinstance(execution_bounds, dict) and execution_bounds:
        print(f"- Allowed paths: {execution_bounds.get('allowed paths', '')}")
        print(f"- Max changed files: {execution_bounds.get('max changed files', '')}")
    stop_conditions = contract.get("stop_conditions", {})
    if isinstance(stop_conditions, dict) and stop_conditions:
        print(f"- Stop when: {stop_conditions.get('stop when', '')}")
    context_budget = contract.get("context_budget", {})
    if isinstance(context_budget, dict) and context_budget.get("status") == "present":
        print(f"- Live working set: {context_budget.get('live_working_set', '')}")
        print(f"- Pre-work config pull: {context_budget.get('pre_work_config_pull', '')}")
        print(f"- Pre-work memory pull: {context_budget.get('pre_work_memory_pull', '')}")
        print(f"- Shift triggers: {context_budget.get('context_shift_triggers', '')}")
    worker_contract = contract.get("worker_contract", {})
    print(f"- Allowed methods: {', '.join(worker_contract.get('allowed_execution_methods', []))}")
    print(f"- Worker owns by default: {', '.join(worker_contract.get('worker_owns_by_default', []))}")
    return_with = contract.get("return_with", {})
    if isinstance(return_with, dict):
        print(f"- Return with execution-run fields: {', '.join(return_with.get('execution_run_fields', []))}")
        print(f"- Return with execution-summary fields: {', '.join(return_with.get('execution_summary_fields', []))}")


def _build_prompt(command: str, target: str | None) -> str:
    source = resolve_upgrade_source(target)
    runner = _preferred_runner(source)
    target_args = f" --target {target}" if target else ""
    non_interactive_args = " --non-interactive"
    if command == "install":
        if runner is None:
            return (
                "No pinned remote runner is published for this bootstrap version yet. "
                "Use an installed `agentic-planning` command if it is already available locally, "
                "or publish a tagged release before relying on remote `prompt install` workflows."
            )
        return (
            f"Run `{runner} install{target_args}{non_interactive_args}`. "
            "Then customise `AGENTS.md`, prune starter placeholders, and run "
            "`agentic-workspace doctor --target ./repo --modules planning --format json` inside the target repo."
        )
    if command == "adopt":
        if runner is None:
            return (
                "No pinned remote runner is published for this bootstrap version yet. "
                "Use an installed `agentic-planning` command if it is already available locally, "
                "or publish a tagged release before relying on remote `prompt adopt` workflows."
            )
        return (
            f"Run `{runner} adopt{target_args}{non_interactive_args}` conservatively. "
            "Do not overwrite repo-owned planning files unless the user asks for it. "
            "Afterwards run `agentic-workspace doctor --target ./repo --modules planning --format json` inside the target repo."
        )
    if command == "upgrade":
        upgrade_guidance = (
            f"Use the checked-in `bootstrap-upgrade` skill under `{_managed_skills_path(target)}/`. "
            "It should use the repo's `.agentic-workspace/planning/UPGRADE-SOURCE.toml`, prefer an installed "
            "`agentic-planning` command with `--non-interactive` when available, and rerun render/check validation. "
            "If `doctor` still flags older active execplans, reconcile those plans to the current contract by "
            "adding or refreshing `Intent Continuity`, `Required Continuation`, `Delegated Judgment`, "
            "`Active Milestone`, and `Execution Summary` instead of treating the upgrade as broken."
        )
        if runner is None:
            return upgrade_guidance
        return upgrade_guidance + f" If a local install is unavailable, fall back to `{runner} upgrade --target <repo> --non-interactive`."
    if runner is None:
        return (
            "No pinned remote runner is published for this bootstrap version yet. "
            "Use an installed `agentic-planning` command if it is already available locally."
        )
    return (
        f"Run `{runner} adopt{target_args}{non_interactive_args}` conservatively. "
        "Do not overwrite repo-owned planning files unless the user asks for it. "
        "Afterwards run `agentic-workspace doctor --target ./repo --modules planning --format json` inside the target repo."
    )


def _preferred_runner(source: UpgradeSource) -> str | None:
    if source.source_type == "none" or not source.source_ref:
        return None
    if source.source_type == "local":
        return _runner_command_for_local_source(source.source_ref)
    if shutil.which("uvx"):
        return f"uvx --from {source.source_ref} agentic-planning"
    if shutil.which("pipx"):
        return f"pipx run --spec {source.source_ref} agentic-planning"
    return f"uvx --from {source.source_ref} agentic-planning"


def _runner_command_for_local_source(source_ref: str) -> str:
    if shutil.which("uvx"):
        return f"uvx --from {source_ref} agentic-planning"
    if shutil.which("pipx"):
        return f"pipx run --spec {source_ref} agentic-planning"
    return f"uvx --from {source_ref} agentic-planning"


def _managed_skills_path(target: str | None) -> str:
    target_root = target or "./repo"
    return f"{target_root}/skills"
