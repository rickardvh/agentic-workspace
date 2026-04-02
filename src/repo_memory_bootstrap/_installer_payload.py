from __future__ import annotations

import re
from pathlib import Path

from repo_memory_bootstrap._installer_output import (
    _embeds_shared_workflow_rules,
    _has_placeholders,
    _is_valid_upgrade_source_text,
    _patch_agents_workflow_block,
)
from repo_memory_bootstrap._installer_shared import (
    AGENTS_PATH,
    AUDIT_SCRIPT_PATH,
    OBSOLETE_SHARED_FILES,
    OPTIONAL_APPEND_DESCRIPTIONS,
    OPTIONAL_APPEND_TARGETS,
    UPGRADE_SOURCE_PATH,
    PayloadEntry,
)


def _payload_entries(
    source_root: Path, *, include_bootstrap_workspace: bool = True
) -> list[PayloadEntry]:
    entries: list[PayloadEntry] = []
    file_roots = [AGENTS_PATH, AUDIT_SCRIPT_PATH, Path("memory")]
    for relative_root in file_roots:
        source_path = source_root / relative_root
        if not source_path.exists():
            continue
        if source_path.is_file():
            relative_path = source_path.relative_to(source_root)
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
            relative_path = child.relative_to(source_root)
            if not include_bootstrap_workspace and relative_path.as_posix().startswith(
                "memory/bootstrap/"
            ):
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


def _classify_role(relative_path: Path) -> str:
    path_str = relative_path.as_posix()
    if relative_path == AGENTS_PATH:
        return "local-entrypoint"
    if relative_path == AUDIT_SCRIPT_PATH:
        return "shared-replaceable"
    if path_str.startswith("memory/system/"):
        return "shared-replaceable"
    if path_str.startswith("memory/bootstrap/"):
        return "shared-replaceable"
    if path_str.startswith("memory/skills/"):
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
) -> None:
    for entry in _payload_entries(
        source_root, include_bootstrap_workspace=include_bootstrap_workspace
    ):
        destination = target_root / entry.relative_path
        rendered = _render_text(entry.source_path, substitutions)
        existing = (
            destination.read_text(encoding="utf-8") if destination.exists() else None
        )

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
) -> None:
    if entry.role == "local-entrypoint":
        _plan_agents_entrypoint(
            destination=destination,
            existing=existing,
            result=result,
            apply=apply,
            apply_local_entrypoint=apply_local_entrypoint,
            doctor_mode=False,
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
            (
                "shared file differs; adoption leaves existing file untouched because "
                "it is repo-owned and may be customised"
            ),
            role=entry.role,
            safety="manual",
            source=str(entry.relative_path),
        )
        return

    result.add(
        "skipped",
        destination,
        (
            "repo-owned file left untouched during adoption; safe to keep as-is "
            "unless you want to replace it with the packaged payload"
        ),
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
) -> None:
    if entry.relative_path == UPGRADE_SOURCE_PATH:
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
            detail = (
                "seed note still contains placeholders"
                if _has_placeholders(existing)
                else "forced replacement"
            )
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
                (
                    "starter note differs from payload; this is expected if the "
                    "repository has localised the seed note"
                ),
                role=entry.role,
                safety="safe",
                source=str(entry.relative_path),
                category="customisation-present",
            )
        else:
            result.add(
                "manual review",
                destination,
                (
                    "starter note looks customised; keep as-is if the localised "
                    "content is intentional, or replace it only after review"
                ),
                role=entry.role,
                safety="manual",
                source=str(entry.relative_path),
            )
        return

    result.add(
        "skipped",
        destination,
        (
            "repo-owned file left untouched because it is already sufficient for the "
            "current install state"
        ),
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
) -> None:
    has_reference = "memory/system/WORKFLOW.md" in existing
    embeds_shared_rules = _embeds_shared_workflow_rules(existing)

    if (
        has_reference
        and "<!-- agentic-memory:workflow:start -->" in existing
        and not embeds_shared_rules
    ):
        result.add(
            "current",
            destination,
            "workflow pointer block already present",
            role="local-entrypoint",
            safety="safe",
            source=str(AGENTS_PATH),
        )
        result.add(
            "manual review",
            destination,
            (
                "payload AGENTS.md differs from the local entrypoint; upgrade leaves "
                "AGENTS.md untouched once the workflow pointer block is already current, "
                "so review manually if you want newer entrypoint guidance"
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
            detail=(
                "added or refreshed the canonical workflow pointer block near the top "
                "of AGENTS.md"
            ),
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

    detail = (
        "missing canonical workflow pointer block near the top of AGENTS.md; "
        "use --apply-local-entrypoint to add or refresh it safely"
    )
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
        fragment_description = OPTIONAL_APPEND_DESCRIPTIONS.get(
            target_file, f"optional fragment from {fragment_path.name}"
        )
        if not destination.exists():
            result.add(
                "skipped" if not status_only else "missing",
                destination,
                "target file not present",
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

        equivalent_detail = _equivalent_optional_fragment_detail(
            target_file=target_file, existing=existing, fragment=fragment
        )
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


def _equivalent_optional_fragment_detail(
    *, target_file: Path, existing: str, fragment: str
) -> str | None:
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
        if (
            not line
            or line.startswith("\t")
            or line.startswith("#")
            or "=" in line.split(":", 1)[0]
        ):
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
