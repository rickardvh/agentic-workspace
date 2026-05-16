from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path
from typing import Any, cast

from repo_memory_bootstrap._installer_output import _new_result
from repo_memory_bootstrap._installer_paths import _record_repo_context_warnings, payload_root, skills_root
from repo_memory_bootstrap._installer_payload import _payload_entries
from repo_memory_bootstrap._installer_shared import OPTIONAL_APPEND_TARGETS, InstallResult
from repo_memory_bootstrap.installer import (
    BOOTSTRAP_WORKSPACE_ROOT,
    MANIFEST_PATH,
    check_current_memory,
    collect_status,
    detect_bootstrap_layout,
    doctor_bootstrap,
    format_actions,
    format_result_json,
    memory_report,
    report_routes,
    resolve_target_root,
    resolve_upgrade_source,
    show_current_memory,
)


def _compact_result_dict(result, *, detail_command: str) -> dict[str, object]:
    payload = result.to_dict()
    actions = payload.get("actions", [])
    compact_actions: list[dict[str, object]] = []
    if isinstance(actions, list):
        for action in actions[:5]:
            if isinstance(action, dict):
                compact_actions.append(
                    {
                        key: action.get(key)
                        for key in ("kind", "path", "detail", "category", "remediation_kind", "memory_action")
                        if action.get(key) not in (None, "")
                    }
                )
    return {
        "target_root": payload.get("target_root", ""),
        "dry_run": payload.get("dry_run", False),
        "mode": payload.get("mode", ""),
        "message": payload.get("message", ""),
        "detected_version": payload.get("detected_version"),
        "bootstrap_version": payload.get("bootstrap_version"),
        "action_count": len(actions) if isinstance(actions, list) else 0,
        "actions": compact_actions,
        "route_summary": payload.get("route_summary", {}),
        "missing_note_hint": payload.get("missing_note_hint", ""),
        "review_summary": payload.get("review_summary", {}),
        "sync_summary": payload.get("sync_summary", {}),
        "detail_command": detail_command,
    }


def _tiny_memory_manifest_counts(*, target_root: Path) -> dict[str, object]:
    manifest_path = target_root / MANIFEST_PATH
    if not manifest_path.exists():
        return {
            "status": "missing",
            "note_count": 0,
            "required_count": 0,
            "optional_count": 0,
            "routing_only_count": 0,
            "path": MANIFEST_PATH.as_posix(),
        }
    try:
        payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {
            "status": "invalid",
            "note_count": 0,
            "required_count": 0,
            "optional_count": 0,
            "routing_only_count": 0,
            "path": MANIFEST_PATH.as_posix(),
        }
    notes = payload.get("notes", {}) if isinstance(payload, dict) else {}
    note_values = list(notes.values()) if isinstance(notes, dict) else []
    required_count = 0
    optional_count = 0
    routing_only_count = 0
    for note in note_values:
        if not isinstance(note, dict):
            continue
        note_map = cast(dict[str, object], note)
        relevance = str(note_map.get("task_relevance", "")).strip().lower()
        if relevance == "required":
            required_count += 1
        elif relevance == "optional":
            optional_count += 1
        if bool(note_map.get("routing_only", False)):
            routing_only_count += 1
    return {
        "status": "present",
        "note_count": len(note_values),
        "required_count": required_count,
        "optional_count": optional_count,
        "routing_only_count": routing_only_count,
        "path": MANIFEST_PATH.as_posix(),
    }


def _tiny_memory_lifecycle_payload(*, target: str | Path | None, command: str) -> dict[str, object]:
    target_root = resolve_target_root(target)
    counts = _tiny_memory_manifest_counts(target_root=target_root)
    health = "healthy" if counts["status"] == "present" else "attention-needed"
    return {
        "target_root": str(target_root),
        "dry_run": command == "doctor",
        "mode": "",
        "message": "Status report" if command == "status" else "Doctor report",
        "health": health,
        "detected_version": None,
        "bootstrap_version": None,
        "action_count": 0 if health == "healthy" else 1,
        "actions": []
        if health == "healthy"
        else [
            {
                "kind": counts["status"],
                "path": counts["path"],
                "detail": "memory manifest is not readable; run full doctor for remediation detail",
            }
        ],
        "active": counts,
        "detail_command": f"agentic-memory {command} --target . --verbose --format json",
    }


def _tiny_memory_report_fast(*, target: str | Path | None) -> dict[str, object]:
    target_root = resolve_target_root(target)
    counts = _tiny_memory_manifest_counts(target_root=target_root)
    health = "healthy" if counts["status"] == "present" else "attention-needed"
    findings = []
    if health != "healthy":
        findings.append(
            {
                "severity": "warning",
                "path": counts["path"],
                "message": "Memory manifest is not readable; run full report for remediation detail.",
            }
        )
    return {
        "kind": "memory-module-report/v1",
        "profile": "tiny",
        "module": "memory",
        "target_root": str(target_root),
        "health": health,
        "status": {
            "detected_version": None,
            "bootstrap_version": None,
            "note_count": counts["note_count"],
            "manifest_status": counts["status"],
        },
        "active": {
            "note_count": counts["note_count"],
            "manifest_note_count": counts["note_count"],
            "required_count": counts["required_count"],
            "optional_count": counts["optional_count"],
            "routing_only_count": counts["routing_only_count"],
        },
        "habitual_pull": {
            "status": "available" if counts["status"] == "present" else "unavailable",
            "read_first": [".agentic-workspace/memory/repo/index.md"],
            "do_not_bulk_read": True,
        },
        "promotion_pressure": {"status": "not-evaluated", "detail_command": "agentic-memory report --target . --verbose --format json"},
        "trust": {"status": "not-evaluated", "detail_command": "agentic-memory report --target . --verbose --format json"},
        "finding_count": len(findings),
        "findings": findings,
        "next_action": {
            "summary": "No immediate memory action." if health == "healthy" else "Run full memory report for remediation detail.",
            "commands": [] if health == "healthy" else ["agentic-memory report --target . --verbose --format json"],
        },
        "detail_commands": {
            "full": "agentic-memory report --target . --verbose --format json",
            "route": "agentic-memory route --target . --files <paths> --format json",
        },
    }


def _tiny_route_report_payload(*, target: str | Path | None) -> dict[str, object]:
    target_root = resolve_target_root(target)
    feedback_path = target_root / ".agentic-workspace" / "memory" / "repo" / "current" / "routing-feedback.md"
    fixtures_root = target_root / "tests" / "fixtures" / "routing"
    fixture_count = len(list(fixtures_root.glob("*.json"))) if fixtures_root.exists() else 0
    feedback_present = feedback_path.exists()
    return {
        "target_root": str(target_root),
        "dry_run": True,
        "message": "Routing report",
        "health": "healthy",
        "route_report_summary": {
            "feedback": {"status": "present" if feedback_present else "missing", "path": feedback_path.as_posix()},
            "fixtures": {"status": "present" if fixture_count else "missing", "fixture_count": fixture_count},
            "detail": "Run full route-report for fixture evaluation and feedback-case matching.",
        },
        "detail_command": "agentic-memory route-report --target . --verbose --format json",
    }


def _tiny_memory_report(report: dict[str, object]) -> dict[str, object]:
    findings = report.get("findings", [])
    active = report.get("active", {})
    if isinstance(active, dict):
        active_map = cast(dict[str, object], active)
        active = {
            key: active_map.get(key)
            for key in ("note_count", "manifest_note_count", "required_count", "optional_count", "routing_only_count")
            if key in active_map
        }
    habitual_pull = report.get("habitual_pull", {})
    if isinstance(habitual_pull, dict):
        habitual_pull_map = cast(dict[str, object], habitual_pull)
        habitual_pull = {
            key: habitual_pull_map.get(key) for key in ("status", "read_first", "max_notes", "do_not_bulk_read") if key in habitual_pull_map
        }
    trust = report.get("trust", {})
    if isinstance(trust, dict):
        trust_map = cast(dict[str, object], trust)
        trust = {key: trust_map.get(key) for key in ("status", "attention_count", "finding_count", "detail_command") if key in trust_map}
    return {
        "kind": report.get("kind", "memory-report/v1"),
        "profile": "tiny",
        "module": report.get("module", "memory"),
        "target_root": report.get("target_root", ""),
        "health": report.get("health", "unknown"),
        "status": report.get("status", {}),
        "active": active,
        "habitual_pull": habitual_pull,
        "promotion_pressure": report.get("promotion_pressure", {}),
        "trust": trust,
        "finding_count": len(findings) if isinstance(findings, list) else 0,
        "findings": findings[:5] if isinstance(findings, list) else [],
        "next_action": report.get("next_action", {}),
        "detail_commands": {
            "full": "agentic-memory report --target . --verbose --format json",
            "route": "agentic-memory route --target . --files <paths> --format json",
        },
    }


def _resolve_memory_target_root(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> Path:
    return resolve_target_root(values.get("target"))


def _load_memory_bootstrap_status(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> Any:
    if values.get("format") == "json" and (not values.get("verbose")):
        return _tiny_memory_lifecycle_payload(target=values.get("target"), command="status")
    return collect_status(target=values.get("target"))


def _load_memory_bootstrap_doctor(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> Any:
    if values.get("format") == "json" and (not values.get("verbose")):
        return _tiny_memory_lifecycle_payload(target=values.get("target"), command="doctor")
    return doctor_bootstrap(
        target=values.get("target"),
        strict_doc_ownership=bool(values.get("strict_doc_ownership", False)),
        project_name=values.get("project_name"),
        project_purpose=values.get("project_purpose"),
        key_repo_docs=values.get("key_repo_docs"),
        key_subsystems=values.get("key_subsystems"),
        primary_build_command=values.get("primary_build_command"),
        primary_test_command=values.get("primary_test_command"),
        other_key_commands=values.get("other_key_commands"),
    )


def _load_memory_current(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> Any:
    if str(values.get("current_command") or "show") == "check":
        return check_current_memory(target=values.get("target"))
    return show_current_memory(target=values.get("target"))


def _load_memory_prompt(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> str:
    return _build_agent_prompt(str(values.get("prompt_command") or "install"), target=values.get("target"))


def _load_memory_report(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> dict[str, object]:
    if values.get("format") == "json" and (not values.get("verbose")):
        return _tiny_memory_report_fast(target=values.get("target"))
    report = memory_report(target=values.get("target"))
    if not values.get("verbose"):
        return _tiny_memory_report(report)
    return report


def _load_memory_route_report(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> Any:
    if values.get("format") == "json" and (not values.get("verbose")):
        return _tiny_route_report_payload(target=values.get("target"))
    return report_routes(target=values.get("target"))


def _assemble_memory_operation_payload(values: dict[str, Any], arguments: dict[str, Any], _context: Any) -> Any:
    operation_id = str(values.get("operation_id", ""))
    if operation_id == "memory.list-files.report":
        return _assemble_memory_list_files_payload(target_root=values["target_root"], files=values["files"], arguments=arguments)
    if operation_id == "memory.list-skills.report":
        return _assemble_memory_list_skills_payload(registry=values["registry"], arguments=arguments)
    raise RuntimeError(f"unsupported payload assembly operation: {operation_id!r}")


def _assemble_memory_list_files_payload(*, target_root: Path, files: list[dict[str, str]], arguments: dict[str, Any]) -> InstallResult:
    fields = arguments.get("fields", {})
    if not isinstance(fields, dict) or fields.get("actions_from") != "files":
        raise RuntimeError("payload.assemble must declare actions_from='files'")
    result = _new_result(
        target_root, dry_run=bool(fields.get("dry_run", True)), message=str(fields.get("message", "Packaged bootstrap file preview"))
    )
    _record_repo_context_warnings(target_root, result)
    payload_entries = _memory_payload_entries_by_relative()
    for file_entry in _enriched_memory_payload_files(files=files, payload_entries=payload_entries):
        result.add(
            file_entry["kind"],
            target_root / file_entry["relative_path"],
            file_entry["strategy"],
            role=file_entry["role"],
            safety="safe",
            source=file_entry["source"],
        )
    return result


def _memory_payload_entries_by_relative() -> dict[str, dict[str, str]]:
    entries = {
        entry.source_path.relative_to(payload_root()).as_posix(): {
            "relative_path": entry.relative_path.as_posix(),
            "role": entry.role,
            "strategy": entry.strategy,
            "kind": "managed file",
            "source": entry.relative_path.as_posix(),
        }
        for entry in _payload_entries(payload_root(), target_layout="managed-root")
    }
    entries.update(
        {
            f"__append_target__/{target_file.as_posix()}": {
                "relative_path": target_file.as_posix(),
                "role": "append-target",
                "strategy": f"optional fragment {fragment_path}",
                "kind": "append target",
                "source": fragment_path.as_posix(),
            }
            for target_file, fragment_path in OPTIONAL_APPEND_TARGETS.items()
        }
    )
    return entries


def _enriched_memory_payload_files(*, files: list[dict[str, str]], payload_entries: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    entries = []
    for file_entry in files:
        relative_path = str(file_entry.get("relative_path", ""))
        payload_entry = payload_entries.get(relative_path)
        if payload_entry is not None:
            entries.append(payload_entry)
    entries.extend((payload_entry for key, payload_entry in payload_entries.items() if key.startswith("__append_target__/")))
    return sorted(entries, key=lambda item: (item["kind"], item["relative_path"], item["source"]))


def _assemble_memory_list_skills_payload(*, registry: Any, arguments: dict[str, Any]) -> InstallResult:
    fields = arguments.get("fields", {})
    if not isinstance(fields, dict) or fields.get("actions_from") != "registry.skills":
        raise RuntimeError("payload.assemble must declare actions_from='registry.skills'")
    if not isinstance(registry, dict):
        raise RuntimeError("memory skill registry must parse to an object")
    skills_dir = skills_root()
    result = InstallResult(target_root=skills_dir, dry_run=bool(fields.get("dry_run", True)), message=str(fields["message"]))
    result.mode = str(fields.get("mode", "skills"))
    result.detected_version = None
    for skill in registry.get("skills", []):
        if not isinstance(skill, dict):
            continue
        skill_id = str(skill.get("id", "")).strip()
        relative = Path(str(skill.get("path", "")).strip())
        if not skill_id or not relative.as_posix():
            continue
        result.add(
            "bundled skill", skills_dir / relative.parent, "registered packaged product skill", role="skill", safety="safe", source=skill_id
        )
    return result


def _emit_memory_operation_output(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> None:
    result = values["result"]
    output_format = str(values.get("format") or "text")
    if values.get("operation_id") == "memory.capture-note.report":
        _emit_memory_capture_note_output(result, output_format=output_format)
        return
    if values.get("operation_id") == "memory.current.report" and str(values.get("current_command") or "show") == "show":
        _emit_current_view(result, output_format=output_format)
        return
    if values.get("operation_id") == "memory.prompt.render":
        print(str(result))
        return
    if output_format == "json":
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
            return
        print(format_result_json(result))
        return
    if values.get("operation_id") in {"memory.install.lifecycle", "memory.init.lifecycle", "memory.adopt.lifecycle"}:
        _emit_result(result, output_format=output_format, include_install_summary=True)
        return
    if isinstance(result, dict):
        _print_report(result)
        return
    _emit_result(result, output_format=output_format)


def _emit_memory_capture_note_output(payload: Any, *, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, indent=2))
        return
    if not isinstance(payload, dict):
        print(str(payload))
        return
    print(f"Recommended action: {payload.get('recommended_action', 'unknown')}")
    print(f"Reason: {payload.get('reason', '')}")
    commands = payload.get("commands", [])
    for command in commands if isinstance(commands, list) else []:
        print(f"Command: {command}")


def _emit_result(result, *, output_format: str, include_install_summary: bool = False) -> None:
    if output_format == "json":
        print(format_result_json(result))
        return
    print(f"Target: {result.target_root}")
    print(result.message)
    if result.route_summary:
        print(
            f"Route summary: notes={result.route_summary.get('routed_note_count', 0)}, required={result.route_summary.get('required_count', 0)}, optional={result.route_summary.get('optional_count', 0)}, exceeded_target={result.route_summary.get('exceeded_target', 'no')}"
        )
        if result.route_summary.get("justification"):
            print(f"Route justification: {result.route_summary['justification']}")
        if result.route_summary.get("warning"):
            print(f"Route warning: {result.route_summary['warning']}")
    if result.missing_note_hint:
        print(f"Routing feedback: {result.missing_note_hint}")
    if result.review_summary:
        print(
            f"Route review: reviewed={result.review_summary.get('reviewed_case_count', 0)}, still_missed={result.review_summary.get('still_missed_count', 0)}, still_over_routed={result.review_summary.get('still_over_routed_count', 0)}, unresolved={result.review_summary.get('unresolved_case_count', 0)}"
        )
    if result.sync_summary:
        primary = result.sync_summary.get("primary_note", {})
        summary = result.sync_summary.get("summary", "")
        if summary:
            print(f"Sync summary: {summary}")
        if isinstance(primary, dict) and primary.get("path"):
            print(f"Primary note: {primary.get('path')} ({primary.get('action', 'review')})")
    if result.route_report_summary:
        feedback = result.route_report_summary.get("feedback", {})
        fixtures = result.route_report_summary.get("fixtures", {})
        missed_note = result.route_report_summary.get("missed_note", {})
        over_routing = result.route_report_summary.get("over_routing", {})
        working_set = result.route_report_summary.get("working_set", {})
        startup_cost = result.route_report_summary.get("startup_cost", {})
        print("Feedback cases:")
        print(
            f"  total={feedback.get('total_feedback_case_count', 0)}, reviewed={feedback.get('reviewed_feedback_case_count', 0)}, unresolved={feedback.get('unresolved_feedback_case_count', 0)}, externalized={feedback.get('externalized_case_count', 0)}, missed_note_cases={feedback.get('missed_note_case_count', 0)}, still_missed={feedback.get('still_missed_count', 0)}, over_routing_cases={feedback.get('over_routing_case_count', 0)}, still_over_routed={feedback.get('still_over_routed_count', 0)}, open={feedback.get('open_case_count', 0)}, tuned={feedback.get('tuned_case_count', 0)}, rejected={feedback.get('rejected_case_count', 0)}"
        )
        if result.route_report_summary.get("feedback_guidance"):
            print(f"  note: {result.route_report_summary['feedback_guidance']}")
        print("Fixture coverage:")
        print(
            f"  fixtures={fixtures.get('fixture_count', 0)}, passing={fixtures.get('passing_fixture_count', 0)}, failing={fixtures.get('failing_fixture_count', 0)}, invalid={fixtures.get('invalid_fixture_count', 0)}"
        )
        if result.route_report_summary.get("fixture_guidance"):
            print(f"  note: {result.route_report_summary['fixture_guidance']}")
        print("Missed-note summary:")
        print(
            f"  feedback_cases={missed_note.get('feedback_case_count', 0)}, still_failing_feedback={missed_note.get('still_failing_feedback_case_count', 0)}, fixtures={missed_note.get('fixture_case_count', 0)}, failing_fixtures={missed_note.get('failing_fixture_count', 0)}, fixture_failure_rate={missed_note.get('fixture_failure_rate', 0)}"
        )
        print("Over-routing summary:")
        print(
            f"  feedback_cases={over_routing.get('feedback_case_count', 0)}, still_failing_feedback={over_routing.get('still_failing_feedback_case_count', 0)}, fixtures={over_routing.get('fixture_case_count', 0)}, failing_fixtures={over_routing.get('failing_fixture_count', 0)}, fixture_failure_rate={over_routing.get('fixture_failure_rate', 0)}"
        )
        print("Working-set pressure:")
        print(
            f"  average={working_set.get('average_routed_note_count', 0)}, average_required={working_set.get('average_required_note_count', 0)}, average_optional={working_set.get('average_optional_note_count', 0)}, max={working_set.get('max_routed_note_count', 0)}, over_target={working_set.get('fixture_count_exceeding_target', 0)}, over_strong_warning={working_set.get('fixture_count_exceeding_strong_warning', 0)}"
        )
        print("Startup cost:")
        print(
            f"  average_lines={startup_cost.get('average_routed_line_count', 0)}, max_lines={startup_cost.get('max_routed_line_count', 0)}"
        )
    if result.detected_version is None:
        print(f"Detected version: none (payload version {result.bootstrap_version})")
    else:
        print(f"Detected version: {result.detected_version} (payload version {result.bootstrap_version})")
    for line in format_actions(result.actions, result.target_root):
        print(f"- {line}")
    if include_install_summary:
        _print_install_summary(result)


def _emit_current_view(result, *, output_format: str) -> None:
    if output_format == "json":
        print(format_result_json(result))
        return
    print(f"Target: {result.target_root}")
    if result.detected_version is None:
        print(f"Detected version: none (payload version {result.bootstrap_version})")
    else:
        print(f"Detected version: {result.detected_version} (payload version {result.bootstrap_version})")
    for note in result.notes:
        print(f"\n[{note.path.as_posix()}]")
        if not note.exists:
            print("(missing)")
            continue
        print(note.content.rstrip())


def _print_install_summary(result) -> None:
    counts = result.counts()
    summary = ", ".join((f"{kind}={count}" for kind, count in sorted(counts.items())))
    print(f"Summary: {summary}")
    bootstrap_skills_path = result.target_root / BOOTSTRAP_WORKSPACE_ROOT / "skills"
    print("Next steps:")
    print(
        "- Review repository-specific details in AGENTS.md, then use `.agentic-workspace/memory/skills/memory-router/` for day-to-day note selection."
    )
    print(
        f"- Use the temporary bootstrap skills under {bootstrap_skills_path} to finish install or adopt lifecycle work, then run `agentic-memory bootstrap-cleanup --target <repo>` when that work is complete."
    )
    print("- Treat `.agentic-workspace/memory/` as the bootstrap-managed surface, and keep repo-specific memory procedures outside it.")
    print("- Keep .agentic-workspace/memory/repo/current/project-state.md as a short overview note, not a task list.")
    print(
        "- Populate .agentic-workspace/memory/repo/current/task-context.md only when active work would benefit from short checked-in continuation compression, not a shadow planner."
    )
    print("- Use `.agentic-workspace/memory/skills/memory-refresh/` after code or docs changes that may have shifted durable memory.")
    print("- Confirm the repo's active planning/status surface separately; this bootstrap does not install one.")
    if _created_current_memory_notes(result):
        print(
            f"- If current-memory files were created, use the `populate` skill under {bootstrap_skills_path} to fill them conservatively before cleanup."
        )
    print("- Run `agentic-workspace doctor --target <repo> --format json` before upgrading an older install.")
    print(
        "- Run `agentic-workspace report --target <repo> --format json` after customising memory notes or when recurring friction should stay visible."
    )


def _print_report(report: dict[str, object]) -> None:
    print(f"Target: {report['target_root']}")
    print("Command: report")
    print(f"Health: {report['health']}")
    status = cast(dict[str, Any], report.get("status", {}))
    if isinstance(status, dict):
        print(
            f"Status: {status.get('note_count', 0)} notes / {status.get('current_note_count', 0)} current notes / version {status.get('detected_version', 'unknown')}"
        )
    trust = cast(dict[str, Any], report.get("trust", {}))
    if isinstance(trust, dict):
        state_counts = cast(dict[str, Any], trust.get("state_counts", {}))
        print(
            f"Trust: {trust.get('manual_review_count', 0)} manual-review / {trust.get('warning_count', 0)} warning / {trust.get('promotion_candidate_count', 0)} promotion candidates"
        )
        if isinstance(state_counts, dict) and state_counts:
            print(
                f"Trust states: {state_counts.get('supported', 0)} supported / {state_counts.get('questionable', 0)} questionable / {state_counts.get('stale', 0)} stale / {state_counts.get('elimination_candidate', 0)} elimination-biased"
            )
    recurring_friction = cast(dict[str, Any], report.get("recurring_friction", {}))
    if isinstance(recurring_friction, dict) and recurring_friction.get("status") == "present":
        print(
            f"Recurring friction: {recurring_friction.get('entry_count', 0)} entries / {recurring_friction.get('promotion_pressure_count', 0)} promotion-pressure / {recurring_friction.get('structure_warning_count', 0)} structure warnings"
        )
    usefulness_audit = cast(dict[str, Any], report.get("usefulness_audit", {}))
    if isinstance(usefulness_audit, dict) and usefulness_audit.get("summary"):
        print(f"Usefulness: {usefulness_audit['summary']}")
    habitual_pull = cast(dict[str, Any], report.get("habitual_pull", {}))
    if isinstance(habitual_pull, dict) and habitual_pull.get("summary"):
        print(f"Habitual pull: {habitual_pull['summary']}")
    next_action = cast(dict[str, Any], report.get("next_action", {}))
    if isinstance(next_action, dict) and next_action.get("summary"):
        print(f"Next action: {next_action['summary']}")
        commands = cast(list[str], next_action.get("commands", []))
        if isinstance(commands, list) and commands:
            print("Commands:")
            for command in commands:
                print(f"- {command}")
    findings = report.get("findings", [])
    if isinstance(findings, list) and findings:
        print("Findings:")
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            f_dict = cast(dict[str, Any], finding)
            path = f"{f_dict['path']}: " if f_dict.get("path") else ""
            print(f"- {f_dict.get('severity', 'info')}: {path}{f_dict.get('message', '')}")


def _created_current_memory_notes(result) -> bool:
    current_paths = {".agentic-workspace/memory/repo/current/project-state.md", ".agentic-workspace/memory/repo/current/task-context.md"}
    for action in result.actions:
        if action.kind not in {"created", "copied", "would create", "would copy"}:
            continue
        try:
            relative = action.path.relative_to(result.target_root).as_posix()
        except ValueError:
            relative = action.path.as_posix()
        if relative in current_paths:
            return True
    return False


def _build_agent_prompt(command: str, *, target: str | None) -> str:
    target_root = target or "./repo"
    source = resolve_upgrade_source(target)
    runner = _preferred_git_runner_command(source)
    target_args = _target_args(target)
    bootstrap_skills = _bootstrap_skills_path(target)
    upgrade_runner = _upgrade_runner_command(target)
    if command == "install":
        return f"Do not ask the user to install or clone anything locally first. Run `{runner} init{target_args}`. Next, use the `install` skill at `{bootstrap_skills}` to finish installation conservatively. When installation is complete, run `{runner} bootstrap-cleanup{target_args}` and point out that `{target_root}/.agentic-workspace/memory/` is the bootstrap-managed surface while repo-specific memory notes stay under `.agentic-workspace/memory/repo/`."
    if command == "adopt":
        return f"Do not ask the user to install or clone anything locally first. Run `{runner} adopt{target_args}`. Next, use the `install` skill at `{bootstrap_skills}` to finish installation conservatively. When installation is complete, run `{runner} bootstrap-cleanup{target_args}` and point out that `{target_root}/.agentic-workspace/memory/` is the bootstrap-managed surface while repo-specific memory notes stay under `.agentic-workspace/memory/repo/`."
    if command == "populate":
        return f"Run `{runner} current show{target_args}`. Treat any shared `project-state.md` or `task-context.md` output as migration residue. Move durable facts into normal Memory notes or canonical docs, active state into planning/status, and transient context into local-only scratch before deleting those legacy files."
    if command == "upgrade":
        return f"Do not ask the user to install or clone anything locally first. Use the checked-in `memory-upgrade` skill under `{_managed_skills_path(target)}/`. It should use the recorded upgrade source automatically, run the packaged upgrade flow for this repo, prefer the installed `agentic-memory` CLI when available, otherwise fall back to `{upgrade_runner} upgrade --target <repo>`, and report any conservative manual-review items."
    if command == "uninstall":
        return f"Run `{runner} uninstall{target_args}`. Review any manual-review items before removing repo-local memory content. If bundled product skills are available, use `bootstrap-uninstall` to finish the uninstall conservatively."
    raise ValueError(f"Unknown prompt command: {command}")


def _uvx_git_runner_command() -> str:
    source = resolve_upgrade_source(None)
    return f"uvx --from {source['source_ref']} agentic-memory"


def _pipx_git_runner_command() -> str:
    source = resolve_upgrade_source(None)
    return f"pipx run --spec {source['source_ref']} agentic-memory"


def _preferred_git_runner_command(source: dict[str, str | int | Path | None]) -> str:
    source_ref = str(source["source_ref"])
    if shutil.which("uvx"):
        return f"uvx --from {source_ref} agentic-memory"
    if shutil.which("pipx"):
        return f"pipx run --spec {source_ref} agentic-memory"
    return f"uvx --from {source_ref} agentic-memory"


def _upgrade_runner_command(target: str | None) -> str:
    source = resolve_upgrade_source(target)
    if source["source_type"] == "local":
        return _runner_command_for_local_source(str(source["source_ref"]))
    return _preferred_git_runner_command(source)


def _target_args(target: str | None) -> str:
    if not target:
        return ""
    return f" --target {target}"


def _bootstrap_skills_path(target: str | None) -> str:
    target_root = target or "./repo"
    return f"{target_root}/{BOOTSTRAP_WORKSPACE_ROOT.as_posix()}/skills"


def _managed_skills_path(target: str | None) -> str:
    target_root = target or "./repo"
    if target and Path(target).exists():
        if detect_bootstrap_layout(Path(target).resolve()) == "legacy":
            return f"{target_root}/memory/skills"
    return f"{target_root}/.agentic-workspace/memory/skills"


def _runner_command_for_local_source(source_ref: str) -> str:
    if shutil.which("uvx"):
        return f"uvx --from {source_ref} agentic-memory"
    if shutil.which("pipx"):
        return f"pipx run --spec {source_ref} agentic-memory"
    return f"uvx --from {source_ref} agentic-memory"
