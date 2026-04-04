from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from repo_memory_bootstrap._installer_memory import (
    _audit_memory_doc_ownership,
    _audit_routing_feedback_note,
    _build_route_summary,
    _build_route_report_feedback_summary,
    _build_route_report_case_type_summary,
    _build_route_review_cases,
    _dedupe_route_suggestions,
    _build_remediation_recommendation,
    _evaluate_route_report_fixtures,
    _emit_improvement_pressure,
    _emit_memory_shape_pressure,
    _find_manifest_matches,
    _high_level_paths,
    _load_routing_feedback_cases,
    _load_route_report_fixtures,
    _first_route_match_source,
    _first_improvement_hint,
    _format_route_reason,
    _git_changed_files,
    _infer_surfaces_from_paths,
    _iter_promotion_candidates,
    _load_memory_manifest,
    _lookup_manifest_note,
    _normalise_surface_name,
    _parse_route_sections,
    _path_matches_pattern,
    _routing_baseline_paths,
)
from repo_memory_bootstrap._installer_output import (
    _current_task_structure_findings,
    _current_task_staleness_reason,
    _existing_version_path,
    _has_placeholders,
    _new_result,
    _patch_agents_workflow_block,
    _project_state_structure_findings,
    _project_state_staleness_reason,
    _read_installed_version,
    _routing_feedback_staleness_reason,
    _routing_feedback_structure_findings,
    _validate_upgrade_source_record,
    build_substitutions,
    detect_install_mode,
    format_actions,
    format_result_json,
    resolve_upgrade_source,
)
from repo_memory_bootstrap._installer_paths import (
    _record_repo_context_warnings,
    detect_bootstrap_layout,
    payload_root,
    resolve_target_root,
    skills_root,
)
from repo_memory_bootstrap._installer_payload import (
    _equivalent_optional_fragment_detail,
    _extract_make_targets,
    _payload_entries,
    _plan_from_entries,
    _plan_obsolete_shared_files,
    _plan_optional_appends,
    _plan_optional_fragment_removals,
    _prune_empty_parents,
    _render_text,
    _report_remaining_repo_local_memory,
    _write_payload_file,
)
from repo_memory_bootstrap._installer_shared import (
    AGENTS_PATH,
    AUDIT_SCRIPT_PATH,
    BOOTSTRAP_VERSION,
    BOOTSTRAP_WORKSPACE_ROOT,
    CORE_PAYLOAD_SKILL_FILES,
    CURRENT_MEMORY_BASELINE,
    CURRENT_PROJECT_STATE_MAX_LINES,
    CURRENT_TASK_MAX_LINES,
    OPTIONAL_CURRENT_MEMORY_FILES,
    ROUTING_FEEDBACK_MAX_LINES,
    ROUTING_FEEDBACK_MAX_RESOLVED,
    ROUTE_WORKING_SET_TARGET,
    FORBIDDEN_PAYLOAD_FILES,
    FORBIDDEN_PAYLOAD_PREFIXES,
    LEGACY_BOOTSTRAP_WORKSPACE_ROOT,
    LEGACY_UPGRADE_SOURCE_PATH,
    MANIFEST_PATH,
    OBSOLETE_SHARED_FILES,
    OPTIONAL_APPEND_TARGETS,
    PAYLOAD_REQUIRED_FILES,
    ROUTING_BASELINE,
    UPGRADE_SOURCE_PATH,
    VERSION_PATH,
    WORKFLOW_POINTER_BLOCK,
    Action,
    CurrentNoteView,
    CurrentViewResult,
    InstallResult,
    RepoDetectionError,
)

__all__ = [
    "subprocess",
    "AGENTS_PATH",
    "AUDIT_SCRIPT_PATH",
    "BOOTSTRAP_VERSION",
    "BOOTSTRAP_WORKSPACE_ROOT",
    "CORE_PAYLOAD_SKILL_FILES",
    "CURRENT_MEMORY_BASELINE",
    "CURRENT_PROJECT_STATE_MAX_LINES",
    "CURRENT_TASK_MAX_LINES",
    "FORBIDDEN_PAYLOAD_FILES",
    "FORBIDDEN_PAYLOAD_PREFIXES",
    "MANIFEST_PATH",
    "OBSOLETE_SHARED_FILES",
    "OPTIONAL_APPEND_TARGETS",
    "PAYLOAD_REQUIRED_FILES",
    "UPGRADE_SOURCE_PATH",
    "VERSION_PATH",
    "WORKFLOW_POINTER_BLOCK",
    "Action",
    "CurrentNoteView",
    "CurrentViewResult",
    "InstallResult",
    "RepoDetectionError",
    "build_substitutions",
    "cleanup_bootstrap_workspace",
    "collect_status",
    "detect_install_mode",
    "detect_bootstrap_layout",
    "doctor_bootstrap",
    "format_actions",
    "format_result_json",
    "install_bootstrap",
    "list_bundled_skills",
    "list_payload_files",
    "payload_root",
    "promotion_report",
    "report_routes",
    "review_routes",
    "resolve_target_root",
    "resolve_upgrade_source",
    "route_memory",
    "show_current_memory",
    "skills_root",
    "sync_memory",
    "migrate_layout",
    "uninstall_bootstrap",
    "upgrade_bootstrap",
    "verify_payload",
    "_audit_memory_doc_ownership",
    "_audit_routing_feedback_note",
    "_current_task_staleness_reason",
    "_equivalent_optional_fragment_detail",
    "_extract_make_targets",
    "_find_manifest_matches",
    "_git_changed_files",
    "_has_placeholders",
    "_infer_surfaces_from_paths",
    "_iter_promotion_candidates",
    "_load_memory_manifest",
    "_lookup_manifest_note",
    "_new_result",
    "_normalise_surface_name",
    "_parse_route_sections",
    "_patch_agents_workflow_block",
    "_path_matches_pattern",
    "_payload_entries",
    "_plan_from_entries",
    "_plan_obsolete_shared_files",
    "_plan_optional_appends",
    "_plan_optional_fragment_removals",
    "_project_state_staleness_reason",
    "_prune_empty_parents",
    "_read_installed_version",
    "_render_text",
    "_report_remaining_repo_local_memory",
    "_validate_upgrade_source_record",
]


def install_bootstrap(
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    project_name: str | None = None,
    project_purpose: str | None = None,
    key_repo_docs: str | None = None,
    key_subsystems: str | None = None,
    primary_build_command: str | None = None,
    primary_test_command: str | None = None,
    other_key_commands: str | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    substitutions = build_substitutions(
        target_root=target_root,
        project_name=project_name,
        project_purpose=project_purpose,
        key_repo_docs=key_repo_docs,
        key_subsystems=key_subsystems,
        primary_build_command=primary_build_command,
        primary_test_command=primary_test_command,
        other_key_commands=other_key_commands,
    )
    result = _new_result(target_root, dry_run=dry_run, message="Install plan")
    _record_repo_context_warnings(target_root, result)

    for entry in _payload_entries(source_root, target_layout="managed-root"):
        destination = target_root / entry.relative_path
        if destination.exists() and not force:
            result.add(
                "skipped",
                destination,
                "already present",
                role=entry.role,
                safety="safe",
                source=str(entry.relative_path),
            )
            continue
        _write_payload_file(
            entry=entry,
            destination=destination,
            substitutions=substitutions,
            result=result,
            action_kind="copied" if not destination.exists() else "overwritten",
            dry_kind="would copy" if not destination.exists() else "would overwrite",
        )

    _plan_optional_appends(source_root, target_root, result, apply=not dry_run)
    return result


def adopt_bootstrap(
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    apply_local_entrypoint: bool = False,
    project_name: str | None = None,
    project_purpose: str | None = None,
    key_repo_docs: str | None = None,
    key_subsystems: str | None = None,
    primary_build_command: str | None = None,
    primary_test_command: str | None = None,
    other_key_commands: str | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    substitutions = build_substitutions(
        target_root=target_root,
        project_name=project_name,
        project_purpose=project_purpose,
        key_repo_docs=key_repo_docs,
        key_subsystems=key_subsystems,
        primary_build_command=primary_build_command,
        primary_test_command=primary_test_command,
        other_key_commands=other_key_commands,
    )
    result = _new_result(target_root, dry_run=dry_run, message="Adoption plan for existing repository")
    _record_repo_context_warnings(target_root, result)
    _plan_from_entries(
        source_root=source_root,
        target_root=target_root,
        substitutions=substitutions,
        result=result,
        mode="adopt",
        apply=not dry_run,
        apply_local_entrypoint=apply_local_entrypoint,
        force=False,
        include_bootstrap_workspace=True,
        target_layout="managed-root",
    )
    _plan_optional_appends(source_root, target_root, result, apply=not dry_run)
    return result


def upgrade_bootstrap(
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    apply_local_entrypoint: bool = False,
    project_name: str | None = None,
    project_purpose: str | None = None,
    key_repo_docs: str | None = None,
    key_subsystems: str | None = None,
    primary_build_command: str | None = None,
    primary_test_command: str | None = None,
    other_key_commands: str | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    substitutions = build_substitutions(
        target_root=target_root,
        project_name=project_name,
        project_purpose=project_purpose,
        key_repo_docs=key_repo_docs,
        key_subsystems=key_subsystems,
        primary_build_command=primary_build_command,
        primary_test_command=primary_test_command,
        other_key_commands=other_key_commands,
    )
    result = _new_result(target_root, dry_run=dry_run, message="Upgrade plan")
    _record_repo_context_warnings(target_root, result)
    detected_layout = detect_bootstrap_layout(target_root)
    source_choice = resolve_upgrade_source(target_root)
    upgrade_source_path = UPGRADE_SOURCE_PATH
    result.add(
        "current",
        target_root / upgrade_source_path,
        f"upgrade source resolved to {source_choice['source_type']} ({source_choice['source_ref']})",
        role="payload-contract",
        safety="safe",
        source=upgrade_source_path.as_posix(),
        category="safe-update",
    )
    if detected_layout == "legacy":
        migration_result = migrate_layout(target=target_root, dry_run=dry_run)
        result.actions.extend(migration_result.actions)
        if any(action.kind == "manual review" for action in migration_result.actions):
            return result
        if dry_run:
            _plan_upgrade_against_migrated_layout(
                source_root=source_root,
                target_root=target_root,
                substitutions=substitutions,
                result=result,
                apply_local_entrypoint=apply_local_entrypoint,
                force=force,
            )
            _dedupe_agents_pointer_status(result, target_root=target_root)
            return result
    target_layout = "managed-root"
    _plan_from_entries(
        source_root=source_root,
        target_root=target_root,
        substitutions=substitutions,
        result=result,
        mode="upgrade",
        apply=not dry_run,
        apply_local_entrypoint=apply_local_entrypoint,
        force=force,
        include_bootstrap_workspace=False,
        target_layout=target_layout,
    )
    _plan_obsolete_shared_files(target_root=target_root, result=result, apply=not dry_run)
    _plan_optional_appends(source_root, target_root, result, apply=not dry_run)
    _dedupe_agents_pointer_status(result, target_root=target_root)
    return result


def collect_status(target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    result = _new_result(target_root, dry_run=False, message="Status report")
    _record_repo_context_warnings(target_root, result)
    target_layout = "legacy" if detect_bootstrap_layout(target_root) == "legacy" else "managed-root"

    for entry in _payload_entries(payload_root(), include_bootstrap_workspace=False, target_layout=target_layout):
        destination = target_root / entry.relative_path
        result.add(
            "present" if destination.exists() else "missing",
            destination,
            "file exists" if destination.exists() else "file missing",
            role=entry.role,
            safety="safe",
            source=str(entry.relative_path),
        )

    for obsolete in OBSOLETE_SHARED_FILES:
        destination = target_root / obsolete
        if destination.exists():
            result.add(
                "obsolete",
                destination,
                "legacy shared file should be removed on upgrade",
                role="shared-replaceable",
                safety="safe",
                source=obsolete.as_posix(),
                category="obsolete-managed-file",
            )

    _plan_optional_appends(payload_root(), target_root, result, apply=False, status_only=True)
    return result


def doctor_bootstrap(
    *,
    target: str | Path | None = None,
    strict_doc_ownership: bool = False,
    project_name: str | None = None,
    project_purpose: str | None = None,
    key_repo_docs: str | None = None,
    key_subsystems: str | None = None,
    primary_build_command: str | None = None,
    primary_test_command: str | None = None,
    other_key_commands: str | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    manifest = _load_memory_manifest(target_root / MANIFEST_PATH)
    substitutions = build_substitutions(
        target_root=target_root,
        project_name=project_name,
        project_purpose=project_purpose,
        key_repo_docs=key_repo_docs,
        key_subsystems=key_subsystems,
        primary_build_command=primary_build_command,
        primary_test_command=primary_test_command,
        other_key_commands=other_key_commands,
    )
    result = _new_result(target_root, dry_run=True, message="Doctor report")
    _record_repo_context_warnings(target_root, result)
    target_layout = "legacy" if detect_bootstrap_layout(target_root) == "legacy" else "managed-root"
    _plan_from_entries(
        source_root=source_root,
        target_root=target_root,
        substitutions=substitutions,
        result=result,
        mode="doctor",
        apply=False,
        apply_local_entrypoint=False,
        force=False,
        include_bootstrap_workspace=False,
        target_layout=target_layout,
    )
    if target_layout == "legacy":
        result.add(
            "current",
            target_root / LEGACY_UPGRADE_SOURCE_PATH,
            (
                "legacy managed layout detected; the next "
                "`agentic-memory-bootstrap upgrade --target <repo>` will "
                "migrate bootstrap-managed files into `.agentic-memory/` "
                "automatically"
            ),
            role="payload-contract",
            safety="safe",
            source=LEGACY_UPGRADE_SOURCE_PATH.as_posix(),
            category="safe-update",
        )
    _plan_obsolete_shared_files(target_root=target_root, result=result, apply=False)
    _plan_optional_appends(source_root, target_root, result, apply=False, status_only=True)
    _audit_memory_doc_ownership(
        target_root=target_root,
        result=result,
        force_enforcement=strict_doc_ownership,
    )
    _audit_routing_feedback_note(target_root=target_root, result=result)
    routing_feedback_path = target_root / "memory/current/routing-feedback.md"
    if routing_feedback_path.exists():
        routing_feedback_text = routing_feedback_path.read_text(encoding="utf-8")
        for finding in _routing_feedback_structure_findings(routing_feedback_text):
            result.add(
                "manual review",
                routing_feedback_path,
                finding,
                role="routing-feedback-audit",
                safety="manual",
                source=routing_feedback_path.relative_to(target_root).as_posix(),
                category="manual-review",
            )
        if stale_reason := _routing_feedback_staleness_reason(routing_feedback_text):
            result.add(
                "manual review",
                routing_feedback_path,
                stale_reason,
                role="routing-feedback-audit",
                safety="manual",
                source=routing_feedback_path.relative_to(target_root).as_posix(),
                category="manual-review",
            )
    _emit_memory_shape_pressure(target_root=target_root, manifest=manifest, result=result)
    _emit_improvement_pressure(target_root=target_root, manifest=manifest, result=result)
    return result


def list_payload_files(target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    result = _new_result(target_root, dry_run=True, message="Packaged bootstrap file preview")
    _record_repo_context_warnings(target_root, result)

    for entry in _payload_entries(source_root, target_layout="managed-root"):
        result.add(
            "managed file",
            target_root / entry.relative_path,
            f"strategy={entry.strategy}",
            role=entry.role,
            safety="safe",
            source=str(entry.relative_path),
        )

    for target_file, fragment_path in OPTIONAL_APPEND_TARGETS.items():
        result.add(
            "append target",
            target_root / target_file,
            f"optional fragment {fragment_path}",
            role="append-target",
            safety="safe",
            source=str(fragment_path),
        )

    return result


def list_bundled_skills() -> InstallResult:
    skills_dir = skills_root()
    result = InstallResult(target_root=skills_dir, dry_run=True, message="Bundled skills")
    result.mode = "skills"
    result.detected_version = None

    for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
        if not (skill_dir / "SKILL.md").exists():
            continue
        result.add(
            "bundled skill",
            skill_dir,
            "packaged product skill",
            role="skill",
            safety="safe",
            source=skill_dir.name,
        )
    return result


def show_current_memory(target: str | Path | None = None) -> CurrentViewResult:
    target_root = resolve_target_root(target)
    result = CurrentViewResult(
        target_root=target_root,
        detected_version=_read_installed_version(_existing_version_path(target_root)),
    )
    for relative_path in CURRENT_MEMORY_BASELINE:
        note_path = target_root / relative_path
        result.notes.append(
            CurrentNoteView(
                path=relative_path,
                exists=note_path.exists(),
                content=note_path.read_text(encoding="utf-8") if note_path.exists() else "",
            )
        )
    return result


def check_current_memory(target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    result = _new_result(target_root, dry_run=True, message="Current-memory check")
    for relative_path in CURRENT_MEMORY_BASELINE:
        note_path = target_root / relative_path
        if not note_path.exists():
            result.add(
                "missing",
                note_path,
                "current-memory note is missing",
                role="current-memory",
                safety="manual",
                source=relative_path.as_posix(),
                category="current-memory-review",
            )
            continue
        text = note_path.read_text(encoding="utf-8")
        has_placeholders = _has_placeholders(text)
        result.add(
            "manual review" if has_placeholders else "current",
            note_path,
            "current-memory note still contains placeholders" if has_placeholders else "current-memory note present",
            role="current-memory",
            safety="manual" if has_placeholders else "safe",
            source=relative_path.as_posix(),
            category="placeholder-review" if has_placeholders else "safe-update",
        )
        stale_reason = (
            _current_task_staleness_reason(text)
            if relative_path == Path("memory/current/task-context.md")
            else _project_state_staleness_reason(text)
            if relative_path == Path("memory/current/project-state.md")
            else None
        )
        if stale_reason is not None:
            result.add(
                "manual review",
                note_path,
                stale_reason,
                role="current-memory",
                safety="manual",
                source=relative_path.as_posix(),
                category="current-memory-review",
            )
        structure_findings = (
            _current_task_structure_findings(text)
            if relative_path == Path("memory/current/task-context.md")
            else _project_state_structure_findings(text)
            if relative_path == Path("memory/current/project-state.md")
            else []
        )
        for finding in structure_findings:
            result.add(
                "manual review",
                note_path,
                finding,
                role="current-memory",
                safety="manual",
                source=relative_path.as_posix(),
                category="current-memory-review",
            )
    return result


def route_memory(
    *,
    target: str | Path | None = None,
    files: list[str] | None = None,
    surfaces: list[str] | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = _new_result(target_root, dry_run=True, message="Memory routing suggestions")
    if not files and not surfaces:
        result.add(
            "manual review",
            target_root / Path("memory/index.md"),
            "provide --files and/or --surface to request routing suggestions",
            role="memory-route",
            safety="manual",
            source="memory/index.md",
            category="manual-review",
        )
        return result

    selected_surfaces = {_normalise_surface_name(surface) for surface in (surfaces or [])}
    selected_surfaces.update(_infer_surfaces_from_paths(files or []))
    manifest = _load_memory_manifest(target_root / MANIFEST_PATH)
    routing_baseline = _routing_baseline_paths(manifest)
    high_level_paths = set(_high_level_paths(manifest))
    suggestions: list[tuple[str, str, str, str, int]] = [
        ("required", path.as_posix(), "always-read routing note", "routing-baseline", 0)
        for path in routing_baseline
    ]
    manifest_suggestions = _find_manifest_matches(
        manifest,
        files=files or [],
        surfaces=selected_surfaces,
        use_staleness=False,
    )
    suggestions.extend((recommendation, note, reason, match_source, 1) for recommendation, note, reason, match_source in manifest_suggestions)
    covered_surfaces = _covered_manifest_surfaces(manifest, manifest_suggestions, selected_surfaces)
    for section_surface, notes in _parse_route_sections(target_root / "memory" / "index.md"):
        if section_surface in selected_surfaces and section_surface not in covered_surfaces:
            for note in notes:
                suggestions.append(("optional", note, f"matched route surface '{section_surface}' from memory/index.md", "index-fallback", 2))
    if Path("memory/current/project-state.md") in high_level_paths and _should_suggest_project_state(
        files=files or [], surfaces=selected_surfaces, manifest_suggestions=manifest_suggestions
    ):
        suggestions.append(
            ("optional", "memory/current/project-state.md", "high-level repo re-orientation is likely useful for this task", "high-level-fallback", 4)
        )
    if _should_suggest_task_context(files=files or []):
        suggestions.append(
            ("optional", "memory/current/task-context.md", "explicit current-context input suggests checking continuation state", "explicit-current-context", 4)
        )

    deduped = _dedupe_route_suggestions(suggestions)
    required = [item for item in deduped if item[0] == "required"]
    optional = [item for item in deduped if item[0] == "optional"]
    kept_optionals: list[tuple[str, str, str, str, int]] = []
    for suggestion in optional:
        _, _, _, match_source, priority = suggestion
        if len(required) + len(kept_optionals) >= ROUTE_WORKING_SET_TARGET and priority >= 4:
            continue
        kept_optionals.append(suggestion)

    kept_suggestions = [*required, *kept_optionals]
    result.route_summary = _build_route_summary(kept_suggestions)
    result.missing_note_hint = "If routing missed something, record which note was missing."

    if result.route_summary.get("warning"):
        result.add(
            "warning",
            target_root / Path("memory/index.md"),
            str(result.route_summary["warning"]),
            role="memory-route",
            safety="advisory",
            source="memory/index.md",
            category="manual-review",
        )

    if justification := result.route_summary.get("justification"):
        result.add(
            "current",
            target_root / Path("memory/index.md"),
            str(justification),
            role="memory-route",
            safety="safe",
            source="memory/index.md",
            category="safe-update",
            match_source="routing-summary",
        )

    for recommendation, note, reason, match_source, _priority in kept_suggestions:
        result.add(
            recommendation,
            target_root / Path(note),
            _format_route_reason(reason=reason, match_source=match_source),
            role="memory-route",
            safety="safe",
            source=note,
            category="safe-update",
            match_source=_first_route_match_source(match_source),
        )
        note_path = target_root / Path(note)
        manifest_note = _lookup_manifest_note(manifest, Path(note))
        note_text = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
        improvement_hint = _first_improvement_hint(manifest_note, note_path, note_text, for_report=False)
        recommendation = _build_remediation_recommendation(manifest_note, note_path, note_text, for_report=False)
        if improvement_hint:
            result.add(
                "consider",
                note_path,
                f"improvement candidate: consider {improvement_hint}",
                role="improvement-pressure",
                safety="advisory",
                source=note,
                category="manual-review",
                remediation_kind=recommendation.kind if recommendation else "",
                remediation_target=recommendation.target_path_hint if recommendation else "",
                remediation_reason=recommendation.reason if recommendation else "",
                remediation_confidence=recommendation.confidence if recommendation else "",
                memory_action=recommendation.memory_action if recommendation else "",
            )

    if files and not any(
        action.role == "memory-route" and action.kind in {"optional", "required"} and action.source != "memory/index.md"
        for action in result.actions
    ):
        result.add(
            "manual review",
            target_root / Path("memory/index.md"),
            "no route-specific notes matched; review memory/index.md and related notes manually",
            role="memory-route",
            safety="manual",
            source="memory/index.md",
            category="manual-review",
        )
    result.add(
        "current",
        target_root / Path("memory/index.md"),
        result.missing_note_hint,
        role="memory-route",
        safety="advisory",
        source="memory/index.md",
        category="safe-update",
        match_source="missing-note-prompt",
    )
    return result


def review_routes(*, target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    result = _new_result(target_root, dry_run=True, message="Routing review")
    feedback_path = target_root / "memory/current/routing-feedback.md"
    if not feedback_path.exists():
        result.add(
            "manual review",
            feedback_path,
            "routing feedback note is absent; create memory/current/routing-feedback.md when you have concrete missed-note or over-routing cases to calibrate",
            role="route-review",
            safety="manual",
            source=feedback_path.relative_to(target_root).as_posix(),
            category="manual-review",
        )
        return result

    text = feedback_path.read_text(encoding="utf-8")
    cases = _load_routing_feedback_cases(feedback_path)
    if not cases:
        result.add(
            "manual review",
            feedback_path,
            "routing feedback note has no parseable cases yet; record only concrete missed-note or over-routing examples worth revisiting",
            role="route-review",
            safety="manual",
            source=feedback_path.relative_to(target_root).as_posix(),
            category="manual-review",
        )
        return result

    routed_results: dict[str, InstallResult] = {}
    for case in cases:
        if not case.expected_notes or (not case.files and not case.surfaces):
            continue
        routed_results[case.case_id] = route_memory(target=target_root, files=list(case.files), surfaces=list(case.surfaces))

    review_cases, summary = _build_route_review_cases(
        target_root=target_root,
        feedback_cases=cases,
        routed_results=routed_results,
    )
    result.review_cases = review_cases
    result.review_summary = summary

    for case in cases:
        review_case = next(item for item in review_cases if item["case_id"] == case.case_id)
        if review_case["unresolved"]:
            result.add(
                "manual review",
                feedback_path,
                f"routing-feedback case '{case.case_id}' lacks enough routing input or expected-note data to review",
                role="route-review",
                safety="manual",
                source=feedback_path.relative_to(target_root).as_posix(),
                category="manual-review",
            )
            continue
        result.add(
            "current" if review_case["matched"] else "manual review",
            feedback_path,
            (
                f"{case.case_type} case '{case.case_id}' "
                f"(status={case.status or 'unknown'}) -> matched={'yes' if review_case['matched'] else 'no'}; "
                f"expected {', '.join(case.expected_notes)}; "
                f"current routed set {', '.join(review_case['current_routed_notes']) if review_case['current_routed_notes'] else 'none'}"
            ),
            role="route-review",
            safety="manual" if not review_case["matched"] else "safe",
            source=feedback_path.relative_to(target_root).as_posix(),
            category="manual-review" if not review_case["matched"] else "safe-update",
        )

    for finding in _routing_feedback_structure_findings(text):
        result.add(
            "manual review",
            feedback_path,
            finding,
            role="route-review",
            safety="manual",
            source=feedback_path.relative_to(target_root).as_posix(),
            category="manual-review",
        )
    stale_reason = _routing_feedback_staleness_reason(text)
    if stale_reason:
        result.add(
            "manual review",
            feedback_path,
            stale_reason,
            role="route-review",
            safety="manual",
            source=feedback_path.relative_to(target_root).as_posix(),
            category="manual-review",
        )
    if len(text.splitlines()) > ROUTING_FEEDBACK_MAX_LINES:
        result.add(
            "manual review",
            feedback_path,
            f"routing feedback note is oversized ({len(text.splitlines())} lines); keep it short and review-shaped",
            role="route-review",
            safety="manual",
            source=feedback_path.relative_to(target_root).as_posix(),
            category="manual-review",
        )
    resolved_count = sum(1 for case in cases if case.status in {"tuned", "rejected"})
    if resolved_count > ROUTING_FEEDBACK_MAX_RESOLVED:
        result.add(
            "manual review",
            feedback_path,
            "routing feedback note contains too many tuned or rejected entries; compress resolved cases into synthesis or remove them",
            role="route-review",
            safety="manual",
            source=feedback_path.relative_to(target_root).as_posix(),
            category="manual-review",
        )
    return result


def report_routes(*, target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    result = _new_result(target_root, dry_run=True, message="Routing report")
    _record_repo_context_warnings(target_root, result)

    feedback_path = target_root / "memory/current/routing-feedback.md"
    feedback_cases = _load_routing_feedback_cases(feedback_path)
    routed_results: dict[str, InstallResult] = {}
    for case in feedback_cases:
        if not case.expected_notes or (not case.files and not case.surfaces):
            continue
        routed_results[case.case_id] = route_memory(target=target_root, files=list(case.files), surfaces=list(case.surfaces))
    review_cases, _review_summary = _build_route_review_cases(
        target_root=target_root,
        feedback_cases=feedback_cases,
        routed_results=routed_results,
    )
    feedback_summary = _build_route_report_feedback_summary(
        feedback_cases=feedback_cases,
        review_cases=review_cases,
    )

    fixtures_root = target_root / "tests/fixtures/routing"
    fixtures = _load_route_report_fixtures(fixtures_root)
    fixture_results, fixture_summary = _evaluate_route_report_fixtures(
        target_root=target_root,
        fixtures=fixtures,
        route_memory_fn=route_memory,
    )

    result.route_report_feedback_cases = review_cases
    result.route_report_fixture_results = fixture_results
    result.route_report_summary = {
        "feedback": feedback_summary,
        "fixtures": fixture_summary,
        "missed_note": _build_route_report_case_type_summary(
            fixture_results=fixture_results,
            feedback_summary=feedback_summary,
            case_type="missed_note",
        ),
        "over_routing": _build_route_report_case_type_summary(
            fixture_results=fixture_results,
            feedback_summary=feedback_summary,
            case_type="over_routing",
        ),
        "working_set": {
            "average_routed_note_count": fixture_summary["average_routed_note_count"],
            "average_required_note_count": fixture_summary["average_required_note_count"],
            "average_optional_note_count": fixture_summary["average_optional_note_count"],
            "max_routed_note_count": fixture_summary["max_routed_note_count"],
            "fixture_count_exceeding_target": fixture_summary["fixture_count_exceeding_target"],
            "fixture_count_exceeding_strong_warning": fixture_summary["fixture_count_exceeding_strong_warning"],
        },
        "startup_cost": {
            "average_routed_line_count": fixture_summary["average_routed_line_count"],
            "max_routed_line_count": fixture_summary["max_routed_line_count"],
        },
        "feedback_guidance": "" if feedback_cases else (
            "No parseable routing-feedback cases yet; record only concrete missed-note or over-routing examples worth revisiting."
        ),
        "fixture_guidance": "" if fixtures else "No routing fixtures found under tests/fixtures/routing/.",
    }

    if not feedback_cases:
        result.add(
            "current",
            feedback_path,
            str(result.route_report_summary["feedback_guidance"]),
            role="route-report",
            safety="safe",
            source=feedback_path.relative_to(target_root).as_posix(),
            category="safe-update",
        )

    for case in review_cases:
        if case.get("matched") and not case.get("unresolved"):
            continue
        if case.get("unresolved"):
            detail = f"{case['case_type']} case '{case['case_id']}' is unresolved; add files or surfaces plus expected notes"
        elif case["case_type"] == "missed_note":
            detail = (
                f"missed-note case '{case['case_id']}' still fails; "
                f"expected {', '.join(case['expected_notes'])}; current routed set "
                f"{', '.join(case['current_routed_notes']) if case['current_routed_notes'] else 'none'}"
            )
        else:
            detail = (
                f"over-routing case '{case['case_id']}' still fails; "
                f"unexpected note(s) still returned: {', '.join(case['expected_notes'])}; current routed set "
                f"{', '.join(case['current_routed_notes']) if case['current_routed_notes'] else 'none'}"
            )
        result.add(
            "manual review",
            feedback_path,
            detail,
            role="route-report",
            safety="manual",
            source=feedback_path.relative_to(target_root).as_posix(),
            category="manual-review",
        )

    if not fixtures:
        result.add(
            "current",
            fixtures_root,
            str(result.route_report_summary["fixture_guidance"]),
            role="route-report",
            safety="safe",
            source="tests/fixtures/routing",
            category="safe-update",
        )

    for fixture in fixture_results:
        if fixture["valid"] and fixture["passed"]:
            continue
        if not fixture["valid"]:
            detail = f"fixture '{fixture['fixture_name']}' is invalid: {fixture['error']}"
        else:
            detail = (
                f"fixture '{fixture['fixture_name']}' fails; missing expected: "
                f"{', '.join(fixture['missing_expected_notes']) or 'none'}; unexpected returned: "
                f"{', '.join(fixture['unexpected_returned_notes']) or 'none'}"
            )
        result.add(
            "manual review" if not fixture["valid"] or not fixture["passed"] else "current",
            fixtures_root / f"{fixture['fixture_name']}.json",
            detail,
            role="route-report",
            safety="manual" if not fixture["valid"] or not fixture["passed"] else "safe",
            source="tests/fixtures/routing",
            category="manual-review" if not fixture["valid"] or not fixture["passed"] else "safe-update",
        )

    return result


def sync_memory(
    *,
    target: str | Path | None = None,
    files: list[str] | None = None,
    notes: list[str] | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    changed_files = list(files or []) or _git_changed_files(target_root)

    result = _new_result(target_root, dry_run=True, message="Memory sync suggestions")
    if not changed_files and not notes:
        result.add(
            "manual review",
            target_root / Path("memory/index.md"),
            "provide --files/--notes or run inside a git repo with changed files",
            role="memory-sync",
            safety="manual",
            source="memory/index.md",
            category="manual-review",
        )
        return result

    manifest = _load_memory_manifest(target_root / MANIFEST_PATH)
    manifest_suggestions = _find_manifest_matches(
        manifest,
        files=changed_files,
        surfaces=_infer_surfaces_from_paths(changed_files),
        use_staleness=True,
    )

    seen_sync_paths: set[Path] = set()
    for _, note, reason, _match_source in manifest_suggestions:
        note_path = target_root / Path(note)
        note_text = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
        manifest_note = _lookup_manifest_note(manifest, Path(note))
        action_kind = "review"
        if not note_path.exists() or _has_placeholders(note_text):
            action_kind = "update"
        if note_path.name == "index.md":
            action_kind = "update index"
        detail = f"{reason}; manifest staleness trigger matched {', '.join(changed_files) if changed_files else 'explicit input'}"
        improvement_hint = _first_improvement_hint(manifest_note, note_path, note_text, for_report=False)
        remediation = _build_remediation_recommendation(manifest_note, note_path, note_text, for_report=False)
        if improvement_hint:
            detail = f"{detail}; consider {improvement_hint}"
        result.add(
            action_kind,
            note_path,
            detail,
            role="memory-sync",
            safety="manual",
            source=note,
            category="manual-review",
            remediation_kind=remediation.kind if remediation else "",
            remediation_target=remediation.target_path_hint if remediation else "",
            remediation_reason=remediation.reason if remediation else "",
            remediation_confidence=remediation.confidence if remediation else "",
            memory_action=remediation.memory_action if remediation else "",
        )
        if improvement_hint:
            result.add(
                "consider",
                note_path,
                f"improvement candidate: consider {improvement_hint}",
                role="improvement-pressure",
                safety="advisory",
                source=note,
                category="manual-review",
                remediation_kind=remediation.kind if remediation else "",
                remediation_target=remediation.target_path_hint if remediation else "",
                remediation_reason=remediation.reason if remediation else "",
                remediation_confidence=remediation.confidence if remediation else "",
                memory_action=remediation.memory_action if remediation else "",
            )
        seen_sync_paths.add(note_path)

    routed = route_memory(target=target_root, files=changed_files)
    routing_baseline = _routing_baseline_paths(manifest)
    baseline_paths = {target_root / path for path in routing_baseline}
    for action in routed.actions:
        if action.kind not in {"optional", "required"} or action.path in seen_sync_paths or action.path in baseline_paths:
            continue
        note_path = action.path
        note_text = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
        relative_note = note_path.relative_to(target_root) if note_path.is_relative_to(target_root) else note_path
        manifest_note = _lookup_manifest_note(manifest, relative_note)
        action_kind = "review"
        if not note_path.exists() or _has_placeholders(note_text):
            action_kind = "update"
        if note_path.name == "index.md":
            action_kind = "update index"
        detail = f"{action.detail}; suggested by changed files {', '.join(changed_files) if changed_files else 'explicit input'}"
        improvement_hint = _first_improvement_hint(manifest_note, note_path, note_text, for_report=False)
        remediation = _build_remediation_recommendation(manifest_note, note_path, note_text, for_report=False)
        if improvement_hint:
            detail = f"{detail}; consider {improvement_hint}"
        result.add(
            action_kind,
            note_path,
            detail,
            role="memory-sync",
            safety="manual",
            source=action.source,
            category="manual-review",
            remediation_kind=remediation.kind if remediation else "",
            remediation_target=remediation.target_path_hint if remediation else "",
            remediation_reason=remediation.reason if remediation else "",
            remediation_confidence=remediation.confidence if remediation else "",
            memory_action=remediation.memory_action if remediation else "",
        )
        if improvement_hint:
            result.add(
                "consider",
                note_path,
                f"improvement candidate: consider {improvement_hint}",
                role="improvement-pressure",
                safety="advisory",
                source=action.source,
                category="manual-review",
                remediation_kind=remediation.kind if remediation else "",
                remediation_target=remediation.target_path_hint if remediation else "",
                remediation_reason=remediation.reason if remediation else "",
                remediation_confidence=remediation.confidence if remediation else "",
                memory_action=remediation.memory_action if remediation else "",
            )
    for note in notes or []:
        result.add(
            "review",
            target_root / Path(note),
            "explicit note supplied for sync review",
            role="memory-sync",
            safety="manual",
            source=note,
            category="manual-review",
            )
    return result


def _covered_manifest_surfaces(
    manifest,
    suggestions: list[tuple[str, str, str, str]],
    selected_surfaces: set[str],
) -> set[str]:
    covered: set[str] = set()
    for _, note, _, _ in suggestions:
        if Path(note) in ROUTING_BASELINE:
            continue
        manifest_note = _lookup_manifest_note(manifest, Path(note))
        if manifest_note is None:
            continue
        covered.update(surface for surface in manifest_note.surfaces if surface in selected_surfaces)
    return covered


def _should_suggest_project_state(
    *,
    files: list[str],
    surfaces: set[str],
    manifest_suggestions: list[tuple[str, str, str, str]],
) -> bool:
    if any(Path(note) == Path("memory/current/project-state.md") for _, note, _, _ in manifest_suggestions):
        return True
    if any(Path(path).as_posix() == "memory/current/project-state.md" for path in files):
        return True
    if surfaces.intersection({"decision", "architecture"}):
        return True
    return any(
        _path_matches_pattern(path, pattern)
        for path in files
        for pattern in ("README.md", "docs/**/*.md", ".agentic-memory/**/*.md", "bootstrap/**/*.md")
    )


def _should_suggest_task_context(*, files: list[str]) -> bool:
    return any(Path(path).as_posix() == "memory/current/task-context.md" for path in files)


def promotion_report(
    *,
    target: str | Path | None = None,
    notes: list[str] | None = None,
    mode: str = "all",
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = _new_result(
        target_root,
        dry_run=True,
        message="Promotion and elimination report",
    )
    manifest = _load_memory_manifest(target_root / MANIFEST_PATH)

    requested = {Path(note) for note in (notes or [])}
    records = _iter_promotion_candidates(
        target_root=target_root,
        manifest=manifest,
        requested=requested,
    )
    if mode == "remediation":
        records = [
            record
            for record in records
            if record[3] is not None and record[3].confidence in {"high", "medium"}
        ]
    records.sort(
        key=lambda record: (
            record[3].kind if record[3] is not None else "zzz",
            record[3].target_path_hint if record[3] is not None else record[0].as_posix(),
            record[0].as_posix(),
        )
    )
    if not records:
        result.add(
            "manual review",
            target_root / MANIFEST_PATH,
            (
                "no promotion or elimination candidates found; mark notes candidate_for_promotion, "
                "improvement_candidate, or pass --notes to inspect specific memory notes"
            ),
            role="promotion-report",
            safety="manual",
            source=MANIFEST_PATH.as_posix(),
            category="manual-review",
        )
        return result

    for note_path, note, detail, recommendation in records:
        result.add(
            "candidate" if note is not None or note_path.exists() else "manual review",
            note_path,
            detail,
            role="promotion-report",
            safety="manual",
            source=note.path.as_posix() if note is not None else note_path.relative_to(target_root).as_posix(),
            category="manual-review",
            remediation_kind=recommendation.kind if recommendation else "",
            remediation_target=recommendation.target_path_hint if recommendation else "",
            remediation_reason=recommendation.reason if recommendation else "",
            remediation_confidence=recommendation.confidence if recommendation else "",
            memory_action=recommendation.memory_action if recommendation else "",
        )
        if note is not None and note.memory_role == "improvement_signal":
            has_remediation = bool(note.preferred_remediation and note.improvement_note)
            has_retention = bool(note.retention_justification)
            if not has_remediation and not has_retention:
                result.add(
                    "manual review",
                    note_path,
                    "improvement-signal lifecycle is incomplete; add remediation metadata or retention_justification before treating this note as stable maintenance residue",
                    role="promotion-report",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="manual-review",
                )
    return result


def verify_payload(target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    result = _new_result(target_root, dry_run=True, message="Payload verification")
    payload_paths = {entry.relative_path for entry in _payload_entries(source_root, target_layout="managed-root")}
    payload_version = _read_installed_version(_existing_version_path(source_root))
    manifest = _load_memory_manifest(source_root / MANIFEST_PATH)

    if payload_version is None:
        result.add(
            "manual review",
            target_root / VERSION_PATH,
            "payload version marker is missing or invalid",
            role="payload-contract",
            safety="manual",
            source=VERSION_PATH.as_posix(),
            category="contract-drift",
        )
    elif payload_version != BOOTSTRAP_VERSION:
        result.add(
            "manual review",
            target_root / VERSION_PATH,
            f"payload version marker ({payload_version}) does not match installer bootstrap version ({BOOTSTRAP_VERSION})",
            role="payload-contract",
            safety="manual",
            source=VERSION_PATH.as_posix(),
            category="contract-drift",
        )

    upgrade_source_path = source_root / UPGRADE_SOURCE_PATH
    if not upgrade_source_path.exists():
        upgrade_source_path = source_root / LEGACY_UPGRADE_SOURCE_PATH
    if upgrade_source_path.exists():
        _validate_upgrade_source_record(upgrade_source_path, result)
    else:
        result.add(
            "manual review",
            target_root / UPGRADE_SOURCE_PATH,
            "upgrade source metadata is missing from the payload",
            role="payload-contract",
            safety="manual",
            source=UPGRADE_SOURCE_PATH.as_posix(),
            category="contract-drift",
        )

    for required in PAYLOAD_REQUIRED_FILES:
        present = required in payload_paths
        result.add(
            "current" if present else "manual review",
            target_root / required,
            "required payload file present" if present else "required payload file missing",
            role="payload-contract",
            safety="safe" if present else "manual",
            source=required.as_posix(),
            category="safe-update" if present else "contract-drift",
        )

    current_payload = {path for path in payload_paths if path.as_posix().startswith("memory/current/")}
    required_current = set(CURRENT_MEMORY_BASELINE)
    allowed_current = required_current | set(OPTIONAL_CURRENT_MEMORY_FILES)
    for extra in sorted(current_payload - allowed_current):
        result.add(
            "manual review",
            target_root / extra,
            "local-only or unexpected current-memory note is in the shipped payload",
            role="payload-contract",
            safety="manual",
            source=extra.as_posix(),
            category="contract-drift",
        )
    for missing in sorted(required_current - current_payload):
        result.add(
            "manual review",
            target_root / missing,
            "baseline current-memory note missing from shipped payload",
            role="payload-contract",
            safety="manual",
            source=missing.as_posix(),
            category="contract-drift",
        )
    for forbidden in FORBIDDEN_PAYLOAD_FILES:
        if forbidden in payload_paths:
            result.add(
                "manual review",
                target_root / forbidden,
                "forbidden file is present in the shipped payload",
                role="payload-contract",
                safety="manual",
                source=forbidden.as_posix(),
                category="contract-drift",
            )
    for payload_path in payload_paths:
        if any(payload_path.as_posix().startswith(prefix) for prefix in FORBIDDEN_PAYLOAD_PREFIXES):
            result.add(
                "manual review",
                target_root / payload_path,
                "forbidden path prefix is present in the shipped payload",
                role="payload-contract",
                safety="manual",
                source=payload_path.as_posix(),
                category="contract-drift",
            )
    if manifest is None:
        result.add(
            "manual review",
            target_root / MANIFEST_PATH,
            "payload manifest is missing or invalid",
            role="payload-contract",
            safety="manual",
            source=MANIFEST_PATH.as_posix(),
            category="contract-drift",
        )
    return result


def migrate_layout(
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    result = _new_result(target_root, dry_run=dry_run, message="Managed layout migration plan")
    _record_repo_context_warnings(target_root, result)
    detected_layout = detect_bootstrap_layout(target_root)

    if detected_layout == "managed-root":
        result.add(
            "current",
            target_root / VERSION_PATH,
            "bootstrap-managed files already use `.agentic-memory/`",
            role="payload-contract",
            safety="safe",
            source=VERSION_PATH.as_posix(),
        )
        return result
    if detected_layout == "none":
        result.add(
            "manual review",
            target_root / VERSION_PATH,
            "no bootstrap-managed layout detected; install or adopt the bootstrap before migrating layout",
            role="payload-contract",
            safety="manual",
            source=VERSION_PATH.as_posix(),
            category="manual-review",
        )
        return result

    legacy_entries = _payload_entries(source_root, target_layout="legacy")
    managed_entries = _payload_entries(source_root, target_layout="managed-root")
    managed_by_source = {entry.source_path.relative_to(source_root): entry for entry in managed_entries}

    for legacy_entry in legacy_entries:
        source_key = legacy_entry.source_path.relative_to(source_root)
        managed_entry = managed_by_source[source_key]
        legacy_path = target_root / legacy_entry.relative_path
        managed_path = target_root / managed_entry.relative_path
        if managed_path == legacy_path:
            continue
        if not legacy_path.exists():
            continue

        if managed_path.exists():
            legacy_text = legacy_path.read_text(encoding="utf-8")
            managed_text = managed_path.read_text(encoding="utf-8")
            if legacy_text == managed_text:
                if dry_run:
                    result.add(
                        "would remove",
                        legacy_path,
                        "legacy managed file already duplicated at the new managed path",
                        role=legacy_entry.role,
                        safety="safe",
                        source=legacy_entry.relative_path.as_posix(),
                    )
                else:
                    legacy_path.unlink()
                    result.add(
                        "removed",
                        legacy_path,
                        "legacy managed file already duplicated at the new managed path",
                        role=legacy_entry.role,
                        safety="safe",
                        source=legacy_entry.relative_path.as_posix(),
                    )
                    _prune_empty_parents(legacy_path.parent, stop=target_root)
            else:
                result.add(
                    "manual review",
                    legacy_path,
                    "legacy and new managed files both exist with different content; review before removing the legacy copy",
                    role=legacy_entry.role,
                    safety="manual",
                    source=legacy_entry.relative_path.as_posix(),
                )
            continue

        if dry_run:
            result.add(
                "would move",
                managed_path,
                f"migrate legacy managed file from {legacy_entry.relative_path.as_posix()} to the new managed root",
                role=managed_entry.role,
                safety="safe",
                source=legacy_entry.relative_path.as_posix(),
            )
        else:
            managed_path.parent.mkdir(parents=True, exist_ok=True)
            managed_path.write_text(legacy_path.read_text(encoding="utf-8"), encoding="utf-8")
            legacy_path.unlink()
            result.add(
                "moved",
                managed_path,
                f"migrated legacy managed file from {legacy_entry.relative_path.as_posix()} to the new managed root",
                role=managed_entry.role,
                safety="safe",
                source=legacy_entry.relative_path.as_posix(),
            )
            _prune_empty_parents(legacy_path.parent, stop=target_root)

    agents_path = target_root / AGENTS_PATH
    if agents_path.exists():
        existing = agents_path.read_text(encoding="utf-8")
        patched = _patch_agents_workflow_block(existing)
        if patched != existing:
            if dry_run:
                result.add(
                    "would patch",
                    agents_path,
                    "refresh AGENTS.md to point at `.agentic-memory/WORKFLOW.md`",
                    role="local-entrypoint",
                    safety="safe",
                    source=AGENTS_PATH.as_posix(),
                )
            else:
                agents_path.write_text(patched, encoding="utf-8")
                result.add(
                    "patched",
                    agents_path,
                    "refreshed AGENTS.md to point at `.agentic-memory/WORKFLOW.md`",
                    role="local-entrypoint",
                    safety="safe",
                    source=AGENTS_PATH.as_posix(),
                )

    for legacy_entry in legacy_entries:
        source_key = legacy_entry.source_path.relative_to(source_root)
        managed_entry = managed_by_source[source_key]
        legacy_path = target_root / legacy_entry.relative_path
        managed_path = target_root / managed_entry.relative_path
        if managed_path == legacy_path or not legacy_path.exists() or not managed_path.exists():
            continue
        legacy_text = legacy_path.read_text(encoding="utf-8")
        managed_text = managed_path.read_text(encoding="utf-8")
        if legacy_text != managed_text:
            continue
        if dry_run:
            result.add(
                "would remove",
                legacy_path,
                "legacy managed file matches the migrated managed copy",
                role=legacy_entry.role,
                safety="safe",
                source=legacy_entry.relative_path.as_posix(),
            )
            continue
        legacy_path.unlink()
        result.add(
            "removed",
            legacy_path,
            "legacy managed file matched the migrated managed copy",
            role=legacy_entry.role,
            safety="safe",
            source=legacy_entry.relative_path.as_posix(),
        )
        _prune_empty_parents(legacy_path.parent, stop=target_root)
    return result


def _plan_upgrade_against_migrated_layout(
    *,
    source_root: Path,
    target_root: Path,
    substitutions: dict[str, str],
    result: InstallResult,
    apply_local_entrypoint: bool,
    force: bool,
) -> None:
    legacy_entries = _payload_entries(source_root, include_bootstrap_workspace=False, target_layout="legacy")
    managed_entries = _payload_entries(source_root, include_bootstrap_workspace=False, target_layout="managed-root")
    mirror_relpaths = {
        AGENTS_PATH,
        *OPTIONAL_APPEND_TARGETS,
        *(entry.relative_path for entry in legacy_entries),
        *(entry.relative_path for entry in managed_entries),
    }

    with tempfile.TemporaryDirectory(prefix="agentic-memory-upgrade-") as temp_dir:
        staging_root = Path(temp_dir)
        (staging_root / ".git").mkdir(parents=True, exist_ok=True)
        for relative_path in sorted(mirror_relpaths):
            source_path = target_root / relative_path
            if not source_path.exists() or not source_path.is_file():
                continue
            destination = staging_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination)

        migrate_layout(target=staging_root, dry_run=False)
        staging_result = _new_result(staging_root, dry_run=True, message="Staged upgrade plan")
        _plan_from_entries(
            source_root=source_root,
            target_root=staging_root,
            substitutions=substitutions,
            result=staging_result,
            mode="upgrade",
            apply=False,
            apply_local_entrypoint=apply_local_entrypoint,
            force=force,
            include_bootstrap_workspace=False,
            target_layout="managed-root",
        )
        _plan_obsolete_shared_files(target_root=staging_root, result=staging_result, apply=False)
        _plan_optional_appends(source_root, staging_root, staging_result, apply=False)
        _rebase_result_actions(source=staging_result, destination=result, from_root=staging_root, to_root=target_root)


def _rebase_result_actions(
    *,
    source: InstallResult,
    destination: InstallResult,
    from_root: Path,
    to_root: Path,
) -> None:
    for action in source.actions:
        try:
            relative_path = action.path.relative_to(from_root)
            rebased_path = to_root / relative_path
        except ValueError:
            rebased_path = action.path
        destination.add(
            action.kind,
            rebased_path,
            action.detail,
            role=action.role,
            safety=action.safety,
            source=action.source,
            category=action.category,
        )


def _dedupe_agents_pointer_status(result: InstallResult, *, target_root: Path) -> None:
    agents_path = target_root / AGENTS_PATH
    patched_kinds = {"patched", "would patch"}
    if not any(action.path == agents_path and action.kind in patched_kinds for action in result.actions):
        return
    result.actions = [
        action
        for action in result.actions
        if not (action.path == agents_path and action.kind == "current" and "workflow pointer block already present" in action.detail)
    ]


def cleanup_bootstrap_workspace(target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    layout = detect_bootstrap_layout(target_root)
    workspace_root = LEGACY_BOOTSTRAP_WORKSPACE_ROOT if layout == "legacy" else BOOTSTRAP_WORKSPACE_ROOT
    workspace = target_root / workspace_root
    result = _new_result(target_root, dry_run=False, message="Bootstrap workspace cleanup")

    if not workspace.exists():
        result.add(
            "skipped",
            workspace,
            "temporary bootstrap workspace is already absent",
            role="bootstrap-workspace",
            safety="safe",
            source=workspace_root.as_posix(),
            category="safe-update",
        )
        return result

    removed_files = 0
    removed_dirs = 0
    for path in sorted(workspace.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
            removed_files += 1
        elif path.is_dir():
            path.rmdir()
            removed_dirs += 1
    workspace.rmdir()
    removed_dirs += 1
    result.add(
        "removed",
        workspace,
        f"removed temporary bootstrap workspace ({removed_files} files, {removed_dirs} directories)",
        role="bootstrap-workspace",
        safety="safe",
        source=workspace_root.as_posix(),
        category="safe-update",
    )
    return result


def uninstall_bootstrap(
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    project_name: str | None = None,
    project_purpose: str | None = None,
    key_repo_docs: str | None = None,
    key_subsystems: str | None = None,
    primary_build_command: str | None = None,
    primary_test_command: str | None = None,
    other_key_commands: str | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    substitutions = build_substitutions(
        target_root=target_root,
        project_name=project_name,
        project_purpose=project_purpose,
        key_repo_docs=key_repo_docs,
        key_subsystems=key_subsystems,
        primary_build_command=primary_build_command,
        primary_test_command=primary_test_command,
        other_key_commands=other_key_commands,
    )
    result = _new_result(target_root, dry_run=dry_run, message="Uninstall plan")
    _record_repo_context_warnings(target_root, result)

    target_layout = "legacy" if detect_bootstrap_layout(target_root) == "legacy" else "managed-root"
    workspace_root = LEGACY_BOOTSTRAP_WORKSPACE_ROOT if target_layout == "legacy" else BOOTSTRAP_WORKSPACE_ROOT
    workspace = target_root / workspace_root
    if workspace.exists():
        if dry_run:
            result.add(
                "would remove",
                workspace,
                "temporary bootstrap workspace",
                role="bootstrap-workspace",
                safety="safe",
                source=workspace_root.as_posix(),
                category="safe-update",
            )
        else:
            cleanup_result = cleanup_bootstrap_workspace(target=target_root)
            result.actions.extend(cleanup_result.actions)

    managed_paths: set[Path] = set()
    removable_paths: set[Path] = set()
    for entry in _payload_entries(source_root, include_bootstrap_workspace=False, target_layout=target_layout):
        destination = target_root / entry.relative_path
        managed_paths.add(destination)
        if not destination.exists():
            continue
        rendered = _render_text(entry.source_path, substitutions)
        existing = destination.read_text(encoding="utf-8")
        if rendered == existing:
            removable_paths.add(destination)
            if dry_run:
                result.add(
                    "would remove",
                    destination,
                    "matches bootstrap payload",
                    role=entry.role,
                    safety="safe",
                    source=str(entry.relative_path),
                    category="safe-update",
                )
            else:
                destination.unlink()
                result.add(
                    "removed",
                    destination,
                    "matched bootstrap payload",
                    role=entry.role,
                    safety="safe",
                    source=str(entry.relative_path),
                    category="safe-update",
                )
                _prune_empty_parents(destination.parent, stop=target_root)
            continue

        result.add(
            "manual review",
            destination,
            "bootstrap-managed file differs from payload; review before removing",
            role=entry.role,
            safety="manual",
            source=str(entry.relative_path),
            category="manual-review",
        )

    _plan_optional_fragment_removals(
        source_root=source_root,
        target_root=target_root,
        result=result,
        apply=not dry_run,
    )
    _report_remaining_repo_local_memory(
        target_root=target_root,
        managed_paths=managed_paths,
        removable_paths=removable_paths,
        result=result,
    )
    return result
