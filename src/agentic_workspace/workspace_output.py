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
    print(f"Target: {payload['target']}")
    print("Command: report")
    print(f"Health: {payload['health']}")
    installed = ", ".join(payload.get("installed_modules", []))
    selected = ", ".join(payload.get("selected_modules", []))
    print(f"Installed modules: {installed if installed else '(none)'}")
    if selected:
        print(f"Selected modules: {selected}")
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
    findings = payload.get("findings", [])
    if isinstance(findings, list) and findings:
        print("Findings:")
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            module = f"[{finding['module']}] " if finding.get("module") else ""
            path = f"{finding['path']}: " if finding.get("path") else ""
            print(f"- {finding.get('severity', 'info')}: {module}{path}{finding.get('message', '')}")


def _emit_setup_text(payload: dict[str, Any]) -> None:
    print(f"Target: {payload['target']}")
    print("Command: setup")
    print(f"Health: {payload['health']}")
    print(f"Mode: {payload['orientation']['mode']}")
    print(f"Summary: {payload['orientation']['summary']}")
    if payload["orientation"].get("reason"):
        print(f"Reason: {payload['orientation']['reason']}")
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
