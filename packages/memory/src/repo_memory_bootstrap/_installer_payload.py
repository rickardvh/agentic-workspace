from __future__ import annotations

import re
from pathlib import Path

from repo_memory_bootstrap._installer_output import (
    _agents_has_current_workflow_pointer,
    _agents_has_workspace_workflow_pointer,
    _embeds_shared_workflow_rules,
    _has_legacy_bootstrap_agents_prose,
    _has_placeholders,
    _is_valid_upgrade_source_text,
    _patch_agents_workflow_block,
    _remove_memory_workflow_block,
)
from repo_memory_bootstrap._installer_shared import (
    AGENTS_PATH,
    AUDIT_SCRIPT_PATH,
    BOOTSTRAP_WORKSPACE_ROOT,
    LEGACY_BOOTSTRAP_WORKSPACE_ROOT,
    LEGACY_SHIPPED_SKILLS_ROOT,
    LEGACY_SYSTEM_ROOT,
    LEGACY_UPGRADE_SOURCE_PATH,
    OBSOLETE_SHARED_FILES,
    OPTIONAL_APPEND_DESCRIPTIONS,
    OPTIONAL_APPEND_TARGETS,
    SHIPPED_SKILLS_ROOT,
    UPGRADE_SOURCE_PATH,
    WORKSPACE_WORKFLOW_PATH,
    PayloadEntry,
)


def _payload_entries(
    source_root: Path, *, include_bootstrap_workspace: bool = True, target_layout: str = "managed-root"
) -> list[PayloadEntry]:
    entries: list[PayloadEntry] = []
    file_roots = [AGENTS_PATH, AUDIT_SCRIPT_PATH, Path("memory"), Path("docs")]
    for relative_root in file_roots:
        source_path = source_root / relative_root
        if not source_path.exists() and relative_root.name.endswith(".md"):
            template_path = source_root / relative_root.with_name(relative_root.name.replace(".md", ".template.md"))
            if template_path.exists():
                source_path = template_path

        if not source_path.exists():
            continue
        if source_path.is_file():
            relative_path = source_path.relative_to(source_root)
            if relative_path.name.endswith(".template.md"):
                relative_path = relative_path.with_name(relative_path.name.replace(".template.md", ".md"))
            role = _classify_role(relative_path)
            entries.append(
                PayloadEntry(
                    relative_path=relative_path,
                    role=role,
                    strategy=_strategy_for_role(role),
                    source_path=source_path,
                )
            )
            continue
        for child in sorted(source_path.rglob("*")):
            if child.is_dir():
                continue
            relative_path = _target_relative_path(child.relative_to(source_root), target_layout=target_layout)
            workspace_root = BOOTSTRAP_WORKSPACE_ROOT if target_layout != "legacy" else LEGACY_BOOTSTRAP_WORKSPACE_ROOT
            if not include_bootstrap_workspace and relative_path.as_posix().startswith(workspace_root.as_posix()):
                continue
            role = _classify_role(relative_path)
            entries.append(
                PayloadEntry(
                    relative_path=relative_path,
                    role=role,
                    strategy=_strategy_for_role(role),
                    source_path=child,
                )
            )

    return entries


def _target_relative_path(relative_path: Path, *, target_layout: str) -> Path:
    if target_layout == "legacy":
        return relative_path
    path_str = relative_path.as_posix()
    if path_str.startswith("memory/system/"):
        return Path(".agentic-workspace/memory") / relative_path.relative_to(LEGACY_SYSTEM_ROOT)
    if path_str.startswith("memory/bootstrap/"):
        return Path(".agentic-workspace/memory/bootstrap") / relative_path.relative_to(LEGACY_BOOTSTRAP_WORKSPACE_ROOT)
    if path_str.startswith("memory/skills/"):
        return Path(".agentic-workspace/memory/skills") / relative_path.relative_to(LEGACY_SHIPPED_SKILLS_ROOT)
    if relative_path.name.endswith(".template.md"):
        relative_path = relative_path.with_name(relative_path.name.replace(".template.md", ".md"))
    return relative_path


def _classify_role(relative_path: Path) -> str:
    path_str = relative_path.as_posix()
    if relative_path == AGENTS_PATH:
        return "local-entrypoint"
    if relative_path == AUDIT_SCRIPT_PATH:
        return "shared-replaceable"
    if path_str.startswith(".agentic-workspace/memory/"):
        return "shared-replaceable"
    if path_str.startswith(BOOTSTRAP_WORKSPACE_ROOT.as_posix()):
        return "shared-replaceable"
    if path_str.startswith(SHIPPED_SKILLS_ROOT.as_posix()):
        return "shared-replaceable"
    if path_str.startswith("memory/templates/"):
        return "shared-template"
    if path_str == "memory/index.md":
        return "seed-note"
    if path_str.startswith("memory/current/"):
        return "seed-note"
    if path_str == "memory/mistakes/recurring-failures.md":
        return "seed-note"
    if path_str.endswith("/README.md"):
        return "seed-note"
    return "managed-file"


def _strategy_for_role(role: str) -> str:
    return {
        "local-entrypoint": "patch-or-review",
        "shared-replaceable": "replace",
        "shared-template": "replace",
        "seed-note": "seed",
        "managed-file": "create-only",
        "current-memory": "seed",
        "memory-route": "analyze",
        "memory-sync": "analyze",
        "payload-contract": "analyze",
    }[role]


def _plan_from_entries(
    *,
    source_root: Path,
    target_root: Path,
    substitutions: dict[str, str],
    result,
    mode: str,
    apply: bool,
    apply_local_entrypoint: bool,
    force: bool,
    include_bootstrap_workspace: bool,
    target_layout: str,
) -> None:
    for entry in _payload_entries(
        source_root,
        include_bootstrap_workspace=include_bootstrap_workspace,
        target_layout=target_layout,
    ):
        destination = target_root / entry.relative_path
        rendered = _render_text(entry.source_path, substitutions)
        existing = destination.read_text(encoding="utf-8") if destination.exists() else None

        if not destination.exists():
            _write_payload_file(
                entry=entry,
                destination=destination,
                substitutions=substitutions,
                result=result,
                action_kind="created",
                dry_kind="would create",
            )
            continue

        if mode == "adopt":
            _plan_existing_file_for_adopt(
                entry=entry,
                destination=destination,
                existing=existing or "",
                rendered=rendered,
                result=result,
                apply=apply,
                apply_local_entrypoint=apply_local_entrypoint,
                target_layout=target_layout,
            )
            continue

        if mode in {"upgrade", "doctor"}:
            _plan_existing_file_for_upgrade(
                entry=entry,
                destination=destination,
                existing=existing or "",
                rendered=rendered,
                result=result,
                apply=apply,
                apply_local_entrypoint=apply_local_entrypoint,
                force=force,
                doctor_mode=(mode == "doctor"),
                target_layout=target_layout,
            )
            continue

        raise ValueError(f"Unknown planning mode: {mode}")


def _plan_obsolete_shared_files(*, target_root: Path, result, apply: bool) -> None:
    for relative_path in OBSOLETE_SHARED_FILES:
        destination = target_root / relative_path
        if not destination.exists():
            continue
        if apply:
            destination.unlink()
            result.add(
                "removed",
                destination,
                "obsolete shared file removed during upgrade",
                role="shared-replaceable",
                safety="safe",
                source=relative_path.as_posix(),
                category="obsolete-managed-file",
            )
            _prune_empty_parents(destination.parent, stop=target_root)
        else:
            result.add(
                "would remove",
                destination,
                "obsolete shared file is no longer part of the payload contract",
                role="shared-replaceable",
                safety="safe",
                source=relative_path.as_posix(),
                category="obsolete-managed-file",
            )


def _plan_existing_file_for_adopt(
    *,
    entry: PayloadEntry,
    destination: Path,
    existing: str,
    rendered: str,
    result,
    apply: bool,
    apply_local_entrypoint: bool,
    target_layout: str,
) -> None:
    if entry.role == "local-entrypoint":
        _plan_agents_entrypoint(
            destination=destination,
            existing=existing,
            result=result,
            apply=apply,
            apply_local_entrypoint=apply_local_entrypoint,
            doctor_mode=False,
            target_layout=target_layout,
        )
        return

    if rendered == existing:
        result.add(
            "current",
            destination,
            "already matches payload",
            role=entry.role,
            safety="safe",
            source=str(entry.relative_path),
        )
        return

    if entry.role in {"shared-replaceable", "shared-template"}:
        result.add(
            "manual review",
            destination,
            ("shared file differs; adoption leaves existing file untouched because it is repo-owned and may be customised"),
            role=entry.role,
            safety="manual",
            source=str(entry.relative_path),
        )
        return

    result.add(
        "skipped",
        destination,
        ("repo-owned file left untouched during adoption; safe to keep as-is unless you want to replace it with the packaged payload"),
        role=entry.role,
        safety="safe",
        source=str(entry.relative_path),
    )


def _plan_existing_file_for_upgrade(
    *,
    entry: PayloadEntry,
    destination: Path,
    existing: str,
    rendered: str,
    result,
    apply: bool,
    apply_local_entrypoint: bool,
    force: bool,
    doctor_mode: bool,
    target_layout: str,
) -> None:
    legacy_upgrade_source_path = _target_relative_path(LEGACY_UPGRADE_SOURCE_PATH, target_layout=target_layout)
    if entry.relative_path == UPGRADE_SOURCE_PATH or entry.relative_path == legacy_upgrade_source_path:
        if _is_valid_upgrade_source_text(existing):
            result.add(
                "current",
                destination,
                "upgrade source metadata already recorded; preserving repo-local source selection",
                role=entry.role,
                safety="safe",
                source=str(entry.relative_path),
            )
            return
        _write_text(
            destination,
            rendered,
            result,
            "replaced",
            "would replace",
            role=entry.role,
            source=str(entry.relative_path),
            detail="upgrade source metadata missing or invalid; refreshing with packaged default",
        )
        return

    if rendered == existing:
        result.add(
            "current",
            destination,
            "already matches payload",
            role=entry.role,
            safety="safe",
            source=str(entry.relative_path),
        )
        return

    if entry.role == "local-entrypoint":
        _plan_agents_entrypoint(
            destination=destination,
            existing=existing,
            result=result,
            apply=apply,
            apply_local_entrypoint=apply_local_entrypoint,
            doctor_mode=doctor_mode,
            target_layout=target_layout,
        )
        return

    if entry.role in {"shared-replaceable", "shared-template"}:
        _write_text(
            destination,
            rendered,
            result,
            "replaced",
            "would replace",
            role=entry.role,
            source=str(entry.relative_path),
        )
        return

    if entry.role == "seed-note":
        if _has_placeholders(existing) or force:
            detail = "seed note still contains placeholders" if _has_placeholders(existing) else "forced replacement"
            _write_text(
                destination,
                rendered,
                result,
                "replaced",
                "would replace",
                role=entry.role,
                source=str(entry.relative_path),
                detail=detail,
            )
        elif doctor_mode:
            result.add(
                "customised",
                destination,
                ("starter note differs from payload; this is expected if the repository has localised the seed note"),
                role=entry.role,
                safety="safe",
                source=str(entry.relative_path),
                category="customisation-present",
            )
        else:
            result.add(
                "customised",
                destination,
                ("starter note differs from payload; preserving repo-local customisation during upgrade"),
                role=entry.role,
                safety="safe",
                source=str(entry.relative_path),
                category="customisation-present",
            )
        return

    result.add(
        "skipped",
        destination,
        ("repo-owned file left untouched because it is already sufficient for the current install state"),
        role=entry.role,
        safety="safe",
        source=str(entry.relative_path),
    )


def _plan_agents_entrypoint(
    *,
    destination: Path,
    existing: str,
    result,
    apply: bool,
    apply_local_entrypoint: bool,
    doctor_mode: bool,
    target_layout: str,
) -> None:
    embeds_shared_rules = _embeds_shared_workflow_rules(existing)
    workspace_shared_layer_present = (destination.parent / WORKSPACE_WORKFLOW_PATH).exists()
    workspace_pointer_present = _agents_has_workspace_workflow_pointer(existing)
    delegated_through_workspace = workspace_shared_layer_present and workspace_pointer_present

    if delegated_through_workspace:
        patched = _remove_memory_workflow_block(existing)
        if patched == existing:
            result.add(
                "current",
                destination,
                "workspace workflow pointer already routes startup through the shared workspace contract",
                role="local-entrypoint",
                safety="safe",
                source=str(AGENTS_PATH),
            )
            return
        if apply_local_entrypoint and not doctor_mode:
            _write_text(
                destination,
                patched,
                result,
                "patched",
                "would patch",
                role="local-entrypoint",
                source=str(AGENTS_PATH),
                detail=(
                    "removed the redundant top-level memory workflow pointer block because the shared workspace pointer is already present"
                ),
            )
            return
        result.add(
            "manual review",
            destination,
            (
                "redundant top-level memory workflow pointer block is still present; "
                "use --apply-local-entrypoint to slim AGENTS.md to the shared workspace pointer"
            ),
            role="local-entrypoint",
            safety="manual",
            source=str(AGENTS_PATH),
        )
        return

    if _agents_has_current_workflow_pointer(existing) and "<!-- agentic-memory:workflow:start -->" in existing and not embeds_shared_rules:
        result.add(
            "current",
            destination,
            "workflow pointer block already present",
            role="local-entrypoint",
            safety="safe",
            source=str(AGENTS_PATH),
        )
        if doctor_mode and _has_legacy_bootstrap_agents_prose(existing):
            result.add(
                "manual review",
                destination,
                (
                    "AGENTS.md still contains older bootstrap prose outside the managed "
                    "workflow pointer block; review and remove stale shared wording manually"
                ),
                role="local-entrypoint",
                safety="manual",
                source=str(AGENTS_PATH),
            )
        return

    patched = _patch_agents_workflow_block(existing)
    if apply_local_entrypoint and not doctor_mode:
        _write_text(
            destination,
            patched,
            result,
            "patched",
            "would patch",
            role="local-entrypoint",
            source=str(AGENTS_PATH),
            detail=("added or refreshed the canonical workflow pointer block near the top of AGENTS.md"),
        )
        if embeds_shared_rules:
            result.add(
                "manual review",
                destination,
                (
                    "older AGENTS.md still embeds shared workflow rules; "
                    "--apply-local-entrypoint can patch the workflow pointer block, "
                    "but copied shared rules still need manual slimming"
                ),
                role="local-entrypoint",
                safety="manual",
                source=str(AGENTS_PATH),
            )
        return

    detail = "missing canonical workflow pointer block near the top of AGENTS.md; use --apply-local-entrypoint to add or refresh it safely"
    if embeds_shared_rules:
        detail = (
            "older AGENTS.md still embeds shared workflow rules; "
            "--apply-local-entrypoint can patch the workflow pointer block, "
            "but copied shared rules still need manual slimming"
        )
    result.add(
        "manual review",
        destination,
        detail,
        role="local-entrypoint",
        safety="manual",
        source=str(AGENTS_PATH),
    )


def _write_payload_file(
    *,
    entry: PayloadEntry,
    destination: Path,
    substitutions: dict[str, str],
    result,
    action_kind: str,
    dry_kind: str,
) -> None:
    rendered = _render_text(entry.source_path, substitutions)
    _write_text(
        destination,
        rendered,
        result,
        action_kind,
        dry_kind,
        role=entry.role,
        source=str(entry.relative_path),
    )


def _write_text(
    destination: Path,
    rendered: str,
    result,
    action_kind: str,
    dry_kind: str,
    *,
    role: str,
    source: str,
    detail: str = "",
) -> None:
    if result.dry_run:
        result.add(
            dry_kind,
            destination,
            detail or "planned change",
            role=role,
            safety="safe",
            source=source,
        )
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    result.add(
        action_kind,
        destination,
        detail or "applied",
        role=role,
        safety="safe",
        source=source,
    )


def _plan_optional_appends(
    source_root: Path,
    target_root: Path,
    result,
    *,
    apply: bool,
    status_only: bool = False,
) -> None:
    for target_file, fragment_path in OPTIONAL_APPEND_TARGETS.items():
        destination = target_root / target_file
        fragment = (source_root / fragment_path).read_text(encoding="utf-8").strip()
        fragment_description = OPTIONAL_APPEND_DESCRIPTIONS.get(target_file, f"optional fragment from {fragment_path.name}")
        if not destination.exists():
            result.add(
                "skipped" if not status_only else "current",
                destination,
                "target file not present" if not status_only else "optional target absent",
                role="append-target",
                safety="safe",
                source=str(fragment_path),
            )
            continue

        existing = destination.read_text(encoding="utf-8")
        if fragment in existing:
            result.add(
                "current" if status_only else "skipped",
                destination,
                "fragment already present",
                role="append-target",
                safety="safe",
                source=str(fragment_path),
            )
            continue

        equivalent_detail = _equivalent_optional_fragment_detail(target_file=target_file, existing=existing, fragment=fragment)
        if equivalent_detail is not None:
            result.add(
                "current" if status_only else "skipped",
                destination,
                equivalent_detail,
                role="append-target",
                safety="safe",
                source=str(fragment_path),
            )
            continue

        if status_only or not apply:
            result.add(
                "would append",
                destination,
                fragment_description,
                role="append-target",
                safety="safe",
                source=str(fragment_path),
            )
            continue

        destination.write_text(_append_text(existing, fragment), encoding="utf-8")
        result.add(
            "appended",
            destination,
            fragment_description,
            role="append-target",
            safety="safe",
            source=str(fragment_path),
        )


def _plan_optional_fragment_removals(
    *,
    source_root: Path,
    target_root: Path,
    result,
    apply: bool,
) -> None:
    for target_file, fragment_path in OPTIONAL_APPEND_TARGETS.items():
        destination = target_root / target_file
        if not destination.exists():
            continue

        fragment = (source_root / fragment_path).read_text(encoding="utf-8").strip()
        existing = destination.read_text(encoding="utf-8")
        if fragment not in existing:
            continue

        updated = _remove_appended_fragment(existing, fragment)
        if not apply:
            result.add(
                "would patch",
                destination,
                "remove bootstrap optional fragment",
                role="append-target",
                safety="safe",
                source=str(fragment_path),
                category="safe-update",
            )
            continue

        destination.write_text(updated, encoding="utf-8")
        result.add(
            "patched",
            destination,
            "removed bootstrap optional fragment",
            role="append-target",
            safety="safe",
            source=str(fragment_path),
            category="safe-update",
        )


def _append_text(existing: str, fragment: str) -> str:
    normalized = existing.rstrip()
    if not normalized:
        return f"{fragment}\n"
    return f"{normalized}\n\n{fragment}\n"


def _remove_appended_fragment(existing: str, fragment: str) -> str:
    lines = existing.splitlines()
    fragment_lines = fragment.splitlines()
    for index in range(len(lines) - len(fragment_lines) + 1):
        if lines[index : index + len(fragment_lines)] != fragment_lines:
            continue
        before = lines[:index]
        after = lines[index + len(fragment_lines) :]
        while before and not before[-1].strip():
            before.pop()
        while after and not after[0].strip():
            after.pop(0)
        updated = before + ([""] if before and after else []) + after
        return "\n".join(updated).rstrip() + ("\n" if updated else "")
    return existing


def _report_remaining_repo_local_memory(
    *,
    target_root: Path,
    managed_paths: set[Path],
    removable_paths: set[Path],
    result,
) -> None:
    memory_root = target_root / "memory"
    if not memory_root.exists():
        return

    remaining: list[Path] = []
    for path in sorted(memory_root.rglob("*")):
        if path.is_dir():
            continue
        if path in managed_paths and path not in removable_paths:
            continue
        if path in removable_paths:
            continue
        remaining.append(path)

    for path in remaining:
        result.add(
            "skipped",
            path,
            (
                "repo-local memory file remains after uninstall; safe to keep if the "
                "repository still owns that note, remove it only if you are fully retiring "
                "memory for this repo"
            ),
            role="repo-local-memory",
            safety="safe",
            source=path.relative_to(target_root).as_posix(),
            category="safe-update",
        )


def _prune_empty_parents(start: Path, *, stop: Path) -> None:
    current = start
    while current != stop and current.exists():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def _equivalent_optional_fragment_detail(*, target_file: Path, existing: str, fragment: str) -> str | None:
    if target_file != Path("Makefile"):
        return None

    targets = _extract_make_targets(fragment)
    if not targets:
        return None

    existing_targets = _extract_make_targets(existing)
    if not targets.issubset(existing_targets):
        return None

    joined = ", ".join(sorted(targets))
    plural = "s" if len(targets) != 1 else ""
    return f"equivalent optional Makefile convenience target{plural} already present ({joined})"


def _extract_make_targets(text: str) -> set[str]:
    targets: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("\t") or line.startswith("#") or "=" in line.split(":", 1)[0]:
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+(?:\s+[A-Za-z0-9_.-]+)*)\s*:(?![=])", line)
        if not match:
            continue
        for target in match.group(1).split():
            targets.add(target)
    return targets


def _render_text(source: Path, substitutions: dict[str, str]) -> str:
    text = source.read_text(encoding="utf-8")
    for placeholder, replacement in substitutions.items():
        text = text.replace(placeholder, replacement)
    return text
