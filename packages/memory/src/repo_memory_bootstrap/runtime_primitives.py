from __future__ import annotations

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
    memory_report,
    promotion_report,
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


def _compact_promotion_report(result, *, requested_mode: object = None) -> dict[str, object]:
    payload = result.to_dict()
    actions = payload.get("actions", [])
    action_count = len(actions) if isinstance(actions, list) else 0
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
    no_candidate_actions = bool(
        action_count
        and all(
            isinstance(action, dict) and str(action.get("detail", "")).startswith("no promotion or elimination candidates found")
            for action in actions
        )
    )
    command = "agentic-memory promotion-report --target . --mode remediation --format json"
    next_action = (
        {
            "action": "no-promotion-action",
            "summary": "No promotion or elimination candidates found.",
            "command": None,
            "run": None,
            "required": False,
        }
        if no_candidate_actions
        else {
            "action": "review-promotion-candidates",
            "summary": "Review memory promotion or elimination candidates before changing durable memory or docs.",
            "command": command,
            "run": command,
            "required": True,
        }
        if action_count
        else {
            "action": "no-promotion-action",
            "summary": "No promotion or elimination candidates found.",
            "command": None,
            "run": None,
            "required": False,
        }
    )
    return {
        "kind": "memory-promotion-report/v1",
        "target_root": payload.get("target_root", ""),
        "dry_run": payload.get("dry_run", False),
        "mode": requested_mode or payload.get("mode", ""),
        "message": payload.get("message", ""),
        "next_action": next_action,
        "context": {
            "action_count": action_count,
            "actions": compact_actions,
            "detected_version": payload.get("detected_version"),
            "bootstrap_version": payload.get("bootstrap_version"),
            "route_summary": payload.get("route_summary", {}),
            "missing_note_hint": payload.get("missing_note_hint", ""),
            "review_summary": payload.get("review_summary", {}),
            "sync_summary": payload.get("sync_summary", {}),
        },
        "drill_down": {
            "ordinary_profile": "primary=next_action;context=compact promotion state",
            "detail_command": command,
            "available_selectors": [
                "next_action",
                "context.action_count",
                "context.actions",
                "context.route_summary",
                "context.review_summary",
                "context.sync_summary",
            ],
        },
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


def _load_memory_promotion_report(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> Any:
    mode = str(values.get("mode") or "all")
    raw_notes = values.get("notes")
    notes = raw_notes if isinstance(raw_notes, list) else None
    result = promotion_report(mode=mode, notes=notes, target=values.get("target"))
    if str(values.get("format") or "text") == "json" and not values.get("verbose"):
        return _compact_promotion_report(result, requested_mode=mode)
    return result


def _load_memory_report(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> dict[str, object]:
    report = memory_report(target=values.get("target"))
    if not values.get("verbose"):
        return _tiny_memory_report(report)
    return report


def _load_memory_route_report(values: dict[str, Any], _arguments: dict[str, Any], _context: Any) -> Any:
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
