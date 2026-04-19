from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentic_workspace.result_adapter import serialise_value


def _emit_init_text(payload: dict[str, Any]) -> None:
    print(f"Target: {payload['target']}")
    print(f"Command: init{' (dry-run)' if payload.get('dry_run') else ''}")
    print(f"Modules: {', '.join(payload['modules'])}")
    if isinstance(payload.get("config"), dict):
        print(f"Config: {payload['config']['config_path']}")
    print(f"Mode: {payload['mode']}")
    print(f"Prompt requirement: {payload['prompt_requirement']}")
    _print_path_list("Detected surfaces", payload["detected_surfaces"])
    _print_path_list("Created", payload["created"])
    _print_path_list("Updated managed", payload["updated_managed"])
    _print_path_list("Preserved existing", payload["preserved_existing"])
    _print_path_list("Needs review", payload["needs_review"])
    _print_path_list("Placeholders", payload["placeholders"])
    _print_path_list("Generated artifacts", payload["generated_artifacts"])
    _print_path_list("Validation", payload["validation"])
    _print_path_list("Next steps", payload["next_steps"])
    if payload.get("handoff_prompt_path"):
        print(f"Handoff prompt file: {payload['handoff_prompt_path']}")
    if payload.get("handoff_record_path"):
        print(f"Handoff record file: {payload['handoff_record_path']}")
    if payload.get("handoff_prompt"):
        print("")
        print("Handoff Prompt:")
        print(payload["handoff_prompt"])
    if payload.get("handoff_record"):
        print("")
        print("Handoff Record:")
        print(json.dumps(serialise_value(payload["handoff_record"]), indent=2))


def _emit_lifecycle_text(payload: dict[str, Any]) -> None:
    print(f"Target: {payload['target']}")
    print(f"Command: {payload['command']}{' (dry-run)' if payload.get('dry_run') else ''}")
    print(f"Modules: {', '.join(payload['modules'])}")
    if isinstance(payload.get("config"), dict):
        print(f"Config: {payload['config']['config_path']}")
    print(f"Health: {payload['health']}")
    _print_path_list("Created", payload["created"])
    _print_path_list("Updated managed", payload["updated_managed"])
    _print_path_list("Preserved existing", payload["preserved_existing"])
    _print_path_list("Needs review", payload["needs_review"])
    _print_path_list("Generated artifacts", payload["generated_artifacts"])
    _print_path_list("Warnings", payload["warnings"])
    _print_path_list("Placeholders", payload["placeholders"])
    _print_path_list("Stale generated surfaces", payload["stale_generated_surfaces"])
    for report in payload["reports"]:
        print(f"[{report['module']}] {report['message']}")
        for action in report["actions"]:
            detail = f" ({action['detail']})" if action.get("detail") else ""
            print(f"- {action['kind']}: {_display_path(action['path'], Path(payload['target']))}{detail}")
    _print_path_list("Next steps", payload["next_steps"])


def _emit_report_text(payload: dict[str, Any]) -> None:
    output_contract = payload.get("output_contract", {})
    bias = output_contract.get("optimization_bias")
    bias_source = output_contract.get("optimization_bias_source")
    rendered_view_style = output_contract.get("rendered_view_style")
    print(f"Target: {payload['target']}")
    print("Command: report")
    print(f"Health: {payload['health']}")
    if bias:
        source_suffix = f" ({bias_source})" if bias_source else ""
        print(f"Output bias: {bias}{source_suffix}")
        if rendered_view_style == "minimal-prose":
            print("Rendering: keep this view terse when machine-readable state already carries the contract.")
        elif rendered_view_style == "explicit-labels-and-context":
            print("Rendering: prefer explicit labels and a little more context for human inspection.")
    installed = ", ".join(payload.get("installed_modules", []))
    selected = ", ".join(payload.get("selected_modules", []))
    print(f"Installed modules: {installed if installed else '(none)'}")
    if selected:
        print(f"Selected modules: {selected}")
    execution_shape = payload.get("execution_shape", {})
    if isinstance(execution_shape, dict) and execution_shape.get("status") == "present":
        recommendation = execution_shape.get("recommendation", {})
        if isinstance(recommendation, dict):
            print("Execution shape:")
            print(f"- default: {recommendation.get('summary', '')}")
            task_shape = execution_shape.get("task_shape", {})
            if isinstance(task_shape, dict) and task_shape.get("summary"):
                print(f"  task shape: {task_shape['summary']}")
            for reason in recommendation.get("why", [])[:2]:
                print(f"  why: {reason}")
            deviation_visibility = recommendation.get("deviation_visibility")
            if deviation_visibility:
                print(f"  deviation: {deviation_visibility}")
    next_action = payload.get("next_action", {})
    if isinstance(next_action, dict):
        summary = next_action.get("summary")
        if summary:
            print(f"Next action: {summary}")
        commands = next_action.get("commands", [])
        if isinstance(commands, list) and commands:
            print("Commands:")
            for command in commands:
                print(f"- {command}")
    discovery = payload.get("discovery", {})
    if isinstance(discovery, dict):
        for bucket_name, heading in (
            ("memory_candidates", "Memory candidates"),
            ("planning_candidates", "Planning candidates"),
            ("ambiguous", "Ambiguous areas"),
        ):
            bucket = discovery.get(bucket_name, [])
            if not isinstance(bucket, list) or not bucket:
                continue
            print(f"{heading}:")
            for item in bucket:
                if not isinstance(item, dict):
                    continue
                surface = item.get("surface", "")
                reason = item.get("reason", "")
                print(f"- {surface}: {reason}")
    standing_intent = payload.get("standing_intent", {})
    if isinstance(standing_intent, dict):
        effective_view = standing_intent.get("effective_view", {})
        if isinstance(effective_view, dict):
            conflict_rule = effective_view.get("conflict_rule")
            if conflict_rule:
                print(f"Standing intent rule: {conflict_rule}")
            items = effective_view.get("items", [])
            present_items = [item for item in items if isinstance(item, dict) and item.get("status") == "present"]
            if present_items:
                print("Standing intent:")
                for item in present_items:
                    owner_surface = item.get("owner_surface", "")
                    print(f"- {item.get('class', '')}: {item.get('summary', '')}")
                    if owner_surface:
                        print(f"  owner: {owner_surface}")
        stronger_home_model = standing_intent.get("stronger_home_model", {})
        if isinstance(stronger_home_model, dict):
            examples = stronger_home_model.get("examples", [])
            if isinstance(examples, list) and examples:
                print("Stronger-home examples:")
                for example in examples[:3]:
                    if not isinstance(example, dict):
                        continue
                    print(f"- {example.get('concern', '')}: {example.get('current_owner', '')}")
    findings = payload.get("findings", [])
    if isinstance(findings, list) and findings:
        print("Findings:")
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            module = f"[{finding['module']}] " if finding.get("module") else ""
            path = f"{finding['path']}: " if finding.get("path") else ""
            print(f"- {finding.get('severity', 'info')}: {module}{path}{finding.get('message', '')}")
    module_reports = payload.get("module_reports", [])
    if isinstance(module_reports, list) and module_reports:
        print("Module reports:")
        for report in module_reports:
            if not isinstance(report, dict):
                continue
            print(f"- {report.get('module', '')}: {report.get('health', 'unknown')}")


def _emit_setup_text(payload: dict[str, Any]) -> None:
    print(f"Target: {payload['target']}")
    print("Command: setup")
    print(f"Health: {payload['health']}")
    print(f"Mode: {payload['orientation']['mode']}")
    print(f"Summary: {payload['orientation']['summary']}")
    if payload["orientation"].get("reason"):
        print(f"Reason: {payload['orientation']['reason']}")
    findings_promotion = payload.get("findings_promotion", {})
    if isinstance(findings_promotion, dict):
        artifact_path = findings_promotion.get("artifact_path")
        if artifact_path:
            print(f"Findings artifact: {artifact_path}")
    analysis_input = payload.get("analysis_input", {})
    if isinstance(analysis_input, dict):
        status = analysis_input.get("status")
        if status and status != "not-found":
            print(f"Analysis input: {status}")
        if isinstance(analysis_input.get("loaded_count"), int) and analysis_input["loaded_count"]:
            print(f"Loaded findings: {analysis_input['loaded_count']}")
    next_action = payload.get("next_action", {})
    if isinstance(next_action, dict):
        summary = next_action.get("summary")
        if summary:
            print(f"Next action: {summary}")
        commands = next_action.get("commands", [])
        if isinstance(commands, list) and commands:
            print("Commands:")
            for command in commands:
                print(f"- {command}")
    current = payload.get("current", {})
    if isinstance(current, dict):
        warnings = current.get("warnings", [])
        if isinstance(warnings, list) and warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"- {warning}")
        needs_review = current.get("needs_review", [])
        if isinstance(needs_review, list) and needs_review:
            print("Needs review:")
            for item in needs_review:
                print(f"- {item}")


def _emit_prompt_text(payload: dict[str, Any]) -> None:
    print(f"Target: {payload['target']}")
    print(f"Command: prompt {payload['prompt_command']}")
    print(f"Modules: {', '.join(payload['modules'])}")
    if isinstance(payload.get("config"), dict):
        print(f"Config: {payload['config']['config_path']}")
    if payload.get("prompt_requirement"):
        print(f"Prompt requirement: {payload['prompt_requirement']}")
    _print_path_list("Needs review", payload.get("needs_review", []))
    _print_path_list("Warnings", payload.get("warnings", []))
    if payload.get("handoff_record_path"):
        print(f"Handoff record file: {payload['handoff_record_path']}")
    print("")
    print("Handoff Prompt:")
    print(payload["handoff_prompt"])
    if payload.get("handoff_record"):
        print("")
        print("Handoff Record:")
        print(json.dumps(serialise_value(payload["handoff_record"]), indent=2))


def _print_path_list(heading: str, values: list[str]) -> None:
    if not values:
        return
    print(f"{heading}:")
    for value in values:
        print(f"- {value}")


def _display_path(path_value: str, target_root: Path) -> str:
    path = Path(path_value)
    try:
        return path.relative_to(target_root).as_posix()
    except ValueError:
        return path.as_posix()
