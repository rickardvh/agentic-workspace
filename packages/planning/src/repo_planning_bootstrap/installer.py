from __future__ import annotations

import importlib.util
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from repo_planning_bootstrap import __version__
from repo_planning_bootstrap._ownership import module_root
from repo_planning_bootstrap._render import (
    load_manifest,
    render_quickstart,
    render_routing,
)
from repo_planning_bootstrap._source import UPGRADE_SOURCE_PATH, resolve_upgrade_source

PLANNING_MANAGED_ROOT = module_root("planning")
PLANNING_SKILLS_MANAGED_ROOT = PLANNING_MANAGED_ROOT / "skills"
PLANNING_MANIFEST_PATH = PLANNING_MANAGED_ROOT / "agent-manifest.json"
PLANNING_RENDER_SCRIPT_PATH = PLANNING_MANAGED_ROOT / "scripts" / "render_agent_docs.py"
PLANNING_CHECKER_SCRIPT_PATH = PLANNING_MANAGED_ROOT / "scripts" / "check" / "check_planning_surfaces.py"
PLANNING_MAINTAINER_CHECKER_SCRIPT_PATH = PLANNING_MANAGED_ROOT / "scripts" / "check" / "check_maintainer_surfaces.py"
ROOT_RENDER_SCRIPT_PATH = Path("scripts/render_agent_docs.py")
ROOT_CHECKER_SCRIPT_PATH = Path("scripts/check/check_planning_surfaces.py")
ROOT_MAINTAINER_CHECKER_PATH = Path("scripts/check/check_maintainer_surfaces.py")
ROOT_MANIFEST_MIRROR_PATH = Path("tools/agent-manifest.json")

REQUIRED_PAYLOAD_FILES = (
    Path("AGENTS.md"),
    Path("TODO.md"),
    Path("ROADMAP.md"),
    Path("docs/capability-aware-execution.md"),
    Path("docs/execplans/README.md"),
    Path("docs/execplans/TEMPLATE.md"),
    Path("docs/execplans/archive/README.md"),
    Path("docs/reviews/README.md"),
    Path("docs/reviews/TEMPLATE.md"),
    Path("docs/upstream-task-intake.md"),
    ROOT_RENDER_SCRIPT_PATH,
    ROOT_CHECKER_SCRIPT_PATH,
    ROOT_MAINTAINER_CHECKER_PATH,
    UPGRADE_SOURCE_PATH,
    PLANNING_MANIFEST_PATH,
    PLANNING_RENDER_SCRIPT_PATH,
    PLANNING_CHECKER_SCRIPT_PATH,
    PLANNING_MAINTAINER_CHECKER_SCRIPT_PATH,
    ROOT_MANIFEST_MIRROR_PATH,
    Path("tools/AGENT_QUICKSTART.md"),
    Path("tools/AGENT_ROUTING.md"),
)

PLANNING_COMPATIBILITY_CONTRACT_FILES = (
    Path("AGENTS.md"),
    Path("TODO.md"),
    Path("ROADMAP.md"),
    Path("docs/capability-aware-execution.md"),
    Path("docs/execplans/README.md"),
    Path("docs/execplans/TEMPLATE.md"),
    Path("docs/execplans/archive/README.md"),
    Path("docs/reviews/README.md"),
    Path("docs/reviews/TEMPLATE.md"),
    Path("docs/upstream-task-intake.md"),
    PLANNING_MANIFEST_PATH,
)

PLANNING_LOWER_STABILITY_HELPER_FILES = tuple(
    relative for relative in REQUIRED_PAYLOAD_FILES if relative not in PLANNING_COMPATIBILITY_CONTRACT_FILES
)

ROOT_SURFACE_FILES = (
    Path("AGENTS.md"),
    Path("TODO.md"),
    Path("ROADMAP.md"),
)

GENERATED_PAYLOAD_FILES = (
    ROOT_MANIFEST_MIRROR_PATH,
    Path("tools/AGENT_QUICKSTART.md"),
    Path("tools/AGENT_ROUTING.md"),
)

PAYLOAD_GUIDANCE_FRAGMENTS = {
    Path("docs/execplans/TEMPLATE.md"): (
        "concurrent edits merge cleanly",
        "do not add retrospective sections such as `Added In This Pass`",
        "Replace stale immediate-action text when the next step changes",
    ),
    Path("docs/execplans/README.md"): (
        "Do not add sections such as `Added In This Pass`",
        "Treat active plan state as branch-local and low half-life",
    ),
}

TODO_EMPTY_STATE_LINE = "- No active work right now."

PACKAGE_MANAGED_FILES = tuple(
    relative for relative in REQUIRED_PAYLOAD_FILES if relative not in ROOT_SURFACE_FILES and relative not in GENERATED_PAYLOAD_FILES
)


def skills_root() -> Path:
    packaged = Path(__file__).resolve().parent / "_skills"
    if packaged.exists():
        return packaged
    return Path(__file__).resolve().parents[2] / "skills"


def _add_contract_surface_summary(result: InstallResult, root: Path) -> None:
    compatibility = ", ".join(path.as_posix() for path in PLANNING_COMPATIBILITY_CONTRACT_FILES)
    helpers = ", ".join(path.as_posix() for path in PLANNING_LOWER_STABILITY_HELPER_FILES)
    result.add(
        "current",
        root / PLANNING_MANIFEST_PATH,
        f"compatibility contract files: {compatibility}",
    )
    result.add(
        "current",
        root / PLANNING_RENDER_SCRIPT_PATH,
        f"lower-stability helper files: {helpers}",
    )


@dataclass
class Action:
    kind: str
    path: Path
    detail: str


@dataclass
class InstallResult:
    target_root: Path
    message: str
    dry_run: bool
    bootstrap_version: str = __version__
    actions: list[Action] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)

    def add(self, kind: str, path: Path, detail: str) -> None:
        self.actions.append(Action(kind=kind, path=path, detail=detail))


@dataclass
class TodoItem:
    fields: dict[str, str]
    field_order: list[str]
    start: int
    end: int

    @property
    def item_id(self) -> str:
        return self.fields.get("id", "")


def payload_root() -> Path:
    packaged = Path(__file__).resolve().parent / "_payload"
    if packaged.exists():
        return packaged
    return Path(__file__).resolve().parents[2] / "bootstrap"


def _bundled_skill_relative_paths() -> tuple[Path, ...]:
    root = skills_root()
    if not root.exists():
        return ()
    return tuple(
        path.relative_to(root)
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )


PLANNING_BUNDLED_SKILL_FILES = tuple(PLANNING_SKILLS_MANAGED_ROOT / relative for relative in _bundled_skill_relative_paths())


def _installed_surface_files() -> tuple[Path, ...]:
    return REQUIRED_PAYLOAD_FILES + PLANNING_BUNDLED_SKILL_FILES


def resolve_target_root(target: str | Path | None) -> Path:
    resolved = Path(target).resolve() if target else Path.cwd().resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def list_payload_files() -> list[str]:
    root = payload_root()
    return [path.relative_to(root).as_posix() for path in sorted(root.rglob("*")) if _should_include_payload_path(path, root)]


def install_bootstrap(*, target: str | Path | None = None, dry_run: bool = False, force: bool = False) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Install plan", dry_run=dry_run)
    _copy_payload(target_root=target_root, result=result, conservative=False, force=force)
    _copy_bundled_skills(target_root=target_root, result=result, conservative=False, force=force)
    _render_generated_agent_files(target_root=target_root, result=result, apply=not dry_run)
    return result


def adopt_bootstrap(*, target: str | Path | None = None, dry_run: bool = False) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Adoption plan for existing repository", dry_run=dry_run)
    _copy_payload(target_root=target_root, result=result, conservative=True, force=False)
    _copy_bundled_skills(target_root=target_root, result=result, conservative=True, force=False)
    _render_generated_agent_files(target_root=target_root, result=result, apply=not dry_run)
    return result


def upgrade_bootstrap(*, target: str | Path | None = None, dry_run: bool = False) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Upgrade plan", dry_run=dry_run)

    for relative in PACKAGE_MANAGED_FILES:
        _copy_payload_file(relative=relative, target_root=target_root, result=result, overwrite=True)

    _copy_bundled_skills(target_root=target_root, result=result, conservative=False, force=True)

    for relative in ROOT_SURFACE_FILES:
        _copy_payload_file(relative=relative, target_root=target_root, result=result, overwrite=False)

    _render_generated_agent_files(target_root=target_root, result=result, apply=not dry_run)
    return result


def uninstall_bootstrap(*, target: str | Path | None = None, dry_run: bool = False) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Uninstall plan", dry_run=dry_run)

    removable: list[Path] = []
    for relative in _installed_surface_files():
        destination = target_root / relative
        if not destination.exists():
            result.add("skipped", destination, "already absent")
            continue
        if relative in PLANNING_BUNDLED_SKILL_FILES:
            removable_check = _remove_bundled_skill_file(relative=relative, target_root=target_root)
        else:
            removable_check = _can_remove_payload_file(relative=relative, target_root=target_root)
        if removable_check:
            removable.append(relative)
            result.add("would remove" if dry_run else "removed", destination, "matches managed payload content")
            continue
        result.add("manual review", destination, "local file differs from managed payload; remove manually if intended")

    if dry_run:
        return result

    for relative in removable:
        destination = target_root / relative
        if destination.exists():
            destination.unlink()

    _prune_empty_parent_dirs(target_root=target_root, relatives=removable)
    return result


def collect_status(*, target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    mode = _detect_adoption_mode(target_root)
    result = InstallResult(target_root=target_root, message=f"Status report ({mode} mode)", dry_run=False)
    result.add("mode", target_root, f"detected adoption mode: {mode}")
    for relative in _installed_surface_files():
        destination = target_root / relative
        detail = "file exists" if destination.exists() else "file missing"
        result.add("present" if destination.exists() else "missing", destination, detail)
    return result


def doctor_bootstrap(*, target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Doctor report", dry_run=True)
    result.add("mode", target_root, f"detected adoption mode: {_detect_adoption_mode(target_root)}")
    upgrade_source = resolve_upgrade_source(target_root)
    source_detail = f"{upgrade_source.source_label}: {upgrade_source.source_ref}"
    result.add("source", target_root / UPGRADE_SOURCE_PATH, source_detail)
    source_age = upgrade_source.age_days()
    if source_age is not None:
        result.add("source age", target_root / UPGRADE_SOURCE_PATH, f"{source_age} days since {upgrade_source.recorded_at}")
        if source_age >= upgrade_source.recommended_upgrade_after_days:
            result.warnings.append(
                {
                    "warning_class": "upgrade_source_stale",
                    "path": UPGRADE_SOURCE_PATH.as_posix(),
                    "message": (
                        f"Recorded upgrade source is {source_age} days old; consider refreshing from "
                        f"{upgrade_source.source_label} when it is safe."
                    ),
                }
            )

    for relative in _installed_surface_files():
        destination = target_root / relative
        detail = "required file present" if destination.exists() else "required file missing"
        result.add("current" if destination.exists() else "manual review", destination, detail)

    _add_contract_surface_summary(result, target_root)

    for relative in (Path("AGENTS.md"), Path("TODO.md"), Path("ROADMAP.md")):
        path = target_root / relative
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if _has_unresolved_placeholders(text):
                result.add("manual review", path, "starter placeholders still need custom values")

    warnings = _run_planning_checker(target_root)
    result.warnings.extend(warnings)
    for warning in warnings:
        result.add("warning", target_root / warning["path"], warning["message"])
        remediation = _warning_remediation(warning["warning_class"])
        if remediation:
            result.add("suggested fix", target_root / warning["path"], remediation)

    for relative, rendered, label in _generated_agent_file_expectations(target_root):
        destination = target_root / relative
        if destination.exists() and destination.read_text(encoding="utf-8") != rendered:
            result.add(
                "manual review",
                destination,
                f"{label} is out of sync with .agentic-workspace/planning/agent-manifest.json; run python scripts/render_agent_docs.py",
            )
    return result


def verify_payload() -> InstallResult:
    root = payload_root()
    result = InstallResult(target_root=root, message="Payload verification", dry_run=False)
    payload_files = {Path(item) for item in list_payload_files()}
    for relative in REQUIRED_PAYLOAD_FILES:
        detail = "required payload file present" if relative in payload_files else "required payload file missing"
        result.add("current" if relative in payload_files else "manual review", root / relative, detail)

    _add_contract_surface_summary(result, root)

    for relative, fragments in PAYLOAD_GUIDANCE_FRAGMENTS.items():
        destination = root / relative
        if not destination.exists():
            continue
        text = destination.read_text(encoding="utf-8")
        missing = [fragment for fragment in fragments if fragment not in text]
        if missing:
            result.add(
                "manual review",
                destination,
                "payload guidance is missing collaboration-safe template wording",
            )
        else:
            result.add("current", destination, "payload guidance includes collaboration-safe template wording")

    for relative, rendered, label in _generated_agent_file_expectations(root):
        destination = root / relative
        if not destination.exists():
            continue
        current = destination.read_text(encoding="utf-8") == rendered
        detail = f"{label} matches manifest" if current else f"{label} does not match manifest"
        result.add("current" if current else "manual review", destination, detail)
    return result


def planning_summary(*, target: str | Path | None = None) -> dict[str, Any]:
    target_root = resolve_target_root(target)
    todo_path = target_root / "TODO.md"
    roadmap_path = target_root / "ROADMAP.md"
    execplan_dir = target_root / "docs" / "execplans"

    todo_lines, todo_items = _read_todo_items(todo_path)
    active_items = []
    for item in todo_items:
        status = item.fields.get("status", "").lower()
        if "in-progress" in status or "active" in status or "ongoing" in status:
            active_items.append(
                {
                    "id": item.fields.get("id", ""),
                    "surface": item.fields.get("surface", ""),
                    "why_now": item.fields.get("why now", ""),
                }
            )

    candidate_lines = _section_lines(_read_lines(roadmap_path), "Next Candidate Queue")
    candidate_count = sum(1 for line in candidate_lines if re.match(r"^\s*-\s+", line))

    active_execplans: list[dict[str, str]] = []
    archived_execplans = 0
    if execplan_dir.exists():
        for path in sorted(execplan_dir.glob("*.md")):
            if path.name in {"README.md", "TEMPLATE.md"}:
                continue
            status = _execplan_status(path)
            if status and status not in {"completed", "done", "closed", "planned", "pending", "not-started"}:
                active_execplans.append({"path": path.relative_to(target_root).as_posix(), "status": status})
        archive_dir = execplan_dir / "archive"
        if archive_dir.exists():
            archived_execplans = sum(1 for path in archive_dir.glob("*.md") if path.is_file())

    warnings = _run_planning_checker(target_root)
    return {
        "target_root": str(target_root),
        "adoption_mode": _detect_adoption_mode(target_root),
        "todo": {
            "line_count": len(todo_lines),
            "item_count": len(todo_items),
            "active_count": len(active_items),
            "active_items": active_items,
        },
        "execplans": {
            "active_count": len(active_execplans),
            "active_execplans": active_execplans,
            "archived_count": archived_execplans,
        },
        "roadmap": {
            "candidate_count": candidate_count,
        },
        "warnings": [warning.copy() for warning in warnings],
        "warning_count": len(warnings),
    }


def promote_todo_item_to_execplan(
    item_id: str,
    *,
    target: str | Path | None = None,
    plan_slug: str | None = None,
    dry_run: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message=f"Promote TODO item '{item_id}' to execplan", dry_run=dry_run)
    todo_path = target_root / "TODO.md"
    todo_lines, todo_items = _read_todo_items(todo_path)
    item = next((candidate for candidate in todo_items if candidate.item_id == item_id), None)
    if item is None:
        result.add("manual review", todo_path, f"TODO item '{item_id}' was not found")
        return result

    current_surface = item.fields.get("surface", "")
    existing_execplan_ref = _surface_execplan_reference(current_surface)
    if existing_execplan_ref:
        result.add("manual review", todo_path, f"TODO item '{item_id}' already points at '{existing_execplan_ref}'")
        return result

    slug = _slugify(plan_slug or item_id)
    execplan_relative = Path("docs") / "execplans" / f"{slug}.md"
    execplan_path = target_root / execplan_relative
    if execplan_path.exists():
        result.add("manual review", execplan_path, "target execplan already exists")
        return result

    next_action = item.fields.get("next action", "").strip()
    done_when = item.fields.get("done when", "").strip()
    why_now = item.fields.get("why now", "").strip()
    status = _normalize_status(item.fields.get("status", "planned"))
    plan_text = _render_execplan_from_todo_item(
        title=_title_from_slug(slug),
        item_id=item_id,
        status=status,
        why_now=why_now,
        next_action=next_action,
        done_when=done_when,
    )

    updated_fields = dict(item.fields)
    updated_fields["surface"] = execplan_relative.as_posix()
    updated_fields.pop("next action", None)
    updated_fields.pop("done when", None)
    new_todo_lines = _rewrite_todo_item(todo_lines, item, updated_fields)

    if dry_run:
        result.add("would create", execplan_path, "scaffold execplan from TODO item")
        result.add("would update", todo_path, f"point '{item_id}' at {execplan_relative.as_posix()} and remove direct-task fields")
        return result

    execplan_path.parent.mkdir(parents=True, exist_ok=True)
    execplan_path.write_text(plan_text, encoding="utf-8")
    todo_path.write_text("\n".join(new_todo_lines).rstrip() + "\n", encoding="utf-8")
    result.add("created", execplan_path, "scaffolded execplan from TODO item")
    result.add("updated", todo_path, f"pointed '{item_id}' at {execplan_relative.as_posix()} and removed direct-task fields")
    return result


def archive_execplan(
    plan: str,
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    apply_cleanup: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message=f"Archive execplan '{plan}'", dry_run=dry_run)
    plan_path = _resolve_execplan_path(target_root, plan)
    if plan_path is None or not plan_path.exists():
        result.add("manual review", target_root / plan, "execplan was not found")
        return result

    archive_dir = target_root / "docs" / "execplans" / "archive"
    if archive_dir in plan_path.parents:
        result.add("manual review", plan_path, "execplan is already archived")
        return result

    status = _execplan_status(plan_path)
    if status not in {"completed", "done", "closed"}:
        result.add("manual review", plan_path, "archive requires the active milestone status to be completed/done/closed")
        return result

    todo_ref_items = _todo_referencing_items(target_root / "TODO.md", plan_path, target_root)
    blocking_todo_refs = [item for item in todo_ref_items if _normalize_status(item.fields.get("status", "")) != "completed"]
    if blocking_todo_refs:
        for item in blocking_todo_refs:
            item_id = item.item_id or "?"
            result.warnings.append(
                {
                    "warning_class": "archive_blocked_by_todo_reference",
                    "path": "TODO.md",
                    "message": f"TODO item '{item_id}' still references this execplan; remove or redirect it before archiving.",
                }
            )
            result.add("manual review", target_root / "TODO.md", f"TODO item '{item_id}' still references this execplan")
        return result

    destination = archive_dir / plan_path.name
    if destination.exists():
        result.add("manual review", destination, "archive destination already exists")
        return result

    cleanup_todo_lines: list[str] | None = None
    completed_todo_refs = [item for item in todo_ref_items if _normalize_status(item.fields.get("status", "")) == "completed"]
    if apply_cleanup and completed_todo_refs:
        cleanup_todo_lines = _remove_todo_items(target_root / "TODO.md", completed_todo_refs)
        for item in completed_todo_refs:
            result.add(
                "would update" if dry_run else "updated",
                target_root / "TODO.md",
                (f"remove completed TODO item '{item.item_id}' while archiving its plan"),
            )
    elif apply_cleanup:
        compact_cleanup = _cleanup_compact_todo_archive_followup(target_root / "TODO.md", plan_path, target_root)
        if compact_cleanup["changed"]:
            cleanup_todo_lines = compact_cleanup["text"].splitlines()
            for detail in compact_cleanup["details"]:
                result.add("would update" if dry_run else "updated", target_root / "TODO.md", detail)

    cleanup_roadmap = _cleanup_roadmap_archive_followup(target_root / "ROADMAP.md", plan_path)
    if cleanup_roadmap["changed"] and apply_cleanup:
        action_kind = "would update" if dry_run else "updated"
        for detail in cleanup_roadmap["details"]:
            result.add(action_kind, target_root / "ROADMAP.md", detail)
    elif cleanup_roadmap["changed"] or cleanup_roadmap["note"]:
        note = cleanup_roadmap["note"] or "ROADMAP has cleanup-ready residue tied to the archived plan."
        result.warnings.append(
            {
                "warning_class": "roadmap_archive_followup",
                "path": "ROADMAP.md",
                "message": note,
            }
        )
        result.add("suggested fix", target_root / "ROADMAP.md", note)

    if dry_run:
        result.add("would move", destination, f"archive {plan_path.relative_to(target_root).as_posix()}")
        return result

    archive_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(plan_path), str(destination))
    if cleanup_todo_lines is not None:
        (target_root / "TODO.md").write_text("\n".join(cleanup_todo_lines).rstrip() + "\n", encoding="utf-8")
    if cleanup_roadmap["changed"] and apply_cleanup:
        (target_root / "ROADMAP.md").write_text(cleanup_roadmap["text"], encoding="utf-8")
    result.add("moved", destination, f"archived {plan_path.relative_to(target_root).as_posix()}")
    return result


def format_actions(actions: list[Action], target_root: Path) -> list[str]:
    lines: list[str] = []
    for action in actions:
        try:
            relative = action.path.relative_to(target_root).as_posix()
        except ValueError:
            relative = action.path.as_posix()
        lines.append(f"{action.kind}: {relative} ({action.detail})")
    return lines


def format_result_json(result: InstallResult) -> str:
    payload = {
        "target_root": str(result.target_root),
        "message": result.message,
        "dry_run": result.dry_run,
        "bootstrap_version": result.bootstrap_version,
        "actions": [{"kind": action.kind, "path": str(action.path), "detail": action.detail} for action in result.actions],
        "warnings": result.warnings,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_summary_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2)


def _copy_payload(*, target_root: Path, result: InstallResult, conservative: bool, force: bool) -> None:
    root = payload_root()
    for source in sorted(root.rglob("*")):
        if not _should_include_payload_path(source, root):
            continue
        relative = source.relative_to(root)
        destination = target_root / relative
        existed = destination.exists()
        if existed and conservative:
            result.add("skipped", destination, "already present")
            continue
        if existed and not force:
            result.add("skipped", destination, "already present")
            continue
        if result.dry_run:
            result.add("would copy" if not existed else "would overwrite", destination, source.as_posix())
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        result.add("copied" if not existed else "overwritten", destination, source.as_posix())


def _copy_bundled_skills(*, target_root: Path, result: InstallResult, conservative: bool, force: bool) -> None:
    root = skills_root()
    if not root.exists():
        destination = target_root / PLANNING_SKILLS_MANAGED_ROOT
        result.add("manual review", destination, "bundled planning skills directory is missing")
        return
    for source in sorted(root.rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts or source.suffix == ".pyc":
            continue
        relative = source.relative_to(root)
        destination = target_root / PLANNING_SKILLS_MANAGED_ROOT / relative
        existed = destination.exists()
        if existed and conservative:
            result.add("skipped", destination, "already present")
            continue
        if existed and not force:
            result.add("skipped", destination, "already present")
            continue
        if result.dry_run:
            result.add("would copy" if not existed else "would overwrite", destination, source.as_posix())
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        result.add("copied" if not existed else "overwritten", destination, source.as_posix())


def _copy_payload_file(*, relative: Path, target_root: Path, result: InstallResult, overwrite: bool) -> None:
    source = payload_root() / relative
    destination = target_root / relative
    if not source.exists():
        result.add("manual review", destination, "payload source file is missing")
        return

    if destination.exists():
        if not overwrite:
            result.add("skipped", destination, "repo-owned surface left unchanged")
            return
        if _files_match(source, destination):
            result.add("current", destination, "already matches managed payload")
            return
        if result.dry_run:
            result.add("would overwrite", destination, source.as_posix())
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        result.add("overwritten", destination, source.as_posix())
        return

    if result.dry_run:
        result.add("would copy", destination, source.as_posix())
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    result.add("copied", destination, source.as_posix())


def _remove_bundled_skill_file(*, relative: Path, target_root: Path) -> bool:
    destination = target_root / relative
    if not destination.exists() or not destination.is_file():
        return False
    source = skills_root() / relative.relative_to(PLANNING_SKILLS_MANAGED_ROOT)
    if not source.exists() or not source.is_file():
        return False
    return destination.read_bytes() == source.read_bytes()


def _render_generated_agent_files(*, target_root: Path, result: InstallResult, apply: bool) -> None:
    manifest_path = target_root / PLANNING_MANIFEST_PATH
    if not manifest_path.exists():
        result.add(
            "manual review",
            manifest_path,
            "cannot render generated agent docs because .agentic-workspace/planning/agent-manifest.json is missing",
        )
        return
    for relative, rendered, label in _generated_agent_file_expectations(target_root):
        destination = target_root / relative
        existing = destination.read_text(encoding="utf-8") if destination.exists() else None
        if existing == rendered:
            result.add("current", destination, f"{label} already matches manifest")
            continue
        if not apply:
            result.add("would update", destination, f"render {label} from manifest")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        result.add("updated" if existing is not None else "created", destination, f"rendered {label} from manifest")


def _run_planning_checker(target_root: Path) -> list[dict[str, str]]:
    checker_path = target_root / ROOT_CHECKER_SCRIPT_PATH
    if not checker_path.exists():
        return []
    spec = importlib.util.spec_from_file_location("planning_checker", checker_path)
    if spec is None or spec.loader is None:
        return [
            {
                "warning_class": "planning_checker_load_failure",
                "path": "scripts/check/check_planning_surfaces.py",
                "message": "Unable to load planning checker.",
            }
        ]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [warning._asdict() for warning in module.gather_planning_warnings(repo_root=target_root)]


def _render_quickstart_for_repo(target_root: Path) -> str:
    script_path = target_root / ROOT_RENDER_SCRIPT_PATH
    manifest_path = target_root / PLANNING_MANIFEST_PATH
    if not script_path.exists() or not manifest_path.exists():
        return render_quickstart(load_manifest(manifest_path))
    spec = importlib.util.spec_from_file_location("render_agent_docs", script_path)
    if spec is None or spec.loader is None:
        return render_quickstart(load_manifest(manifest_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_quickstart(module.load_manifest())


def _render_routing_for_repo(target_root: Path) -> str:
    script_path = target_root / ROOT_RENDER_SCRIPT_PATH
    manifest_path = target_root / PLANNING_MANIFEST_PATH
    if not script_path.exists() or not manifest_path.exists():
        return render_routing(load_manifest(manifest_path))
    spec = importlib.util.spec_from_file_location("render_agent_docs", script_path)
    if spec is None or spec.loader is None:
        return render_routing(load_manifest(manifest_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_routing(module.load_manifest())


def _generated_agent_file_expectations(target_root: Path) -> list[tuple[Path, str, str]]:
    manifest_path = target_root / PLANNING_MANIFEST_PATH
    if not manifest_path.exists():
        return []
    return [
        (ROOT_MANIFEST_MIRROR_PATH, json.dumps(load_manifest(manifest_path), ensure_ascii=False, indent=2) + "\n", "manifest mirror"),
        (Path("tools/AGENT_QUICKSTART.md"), _render_quickstart_for_repo(target_root), "quickstart"),
        (Path("tools/AGENT_ROUTING.md"), _render_routing_for_repo(target_root), "routing guide"),
    ]


def _has_unresolved_placeholders(text: str) -> bool:
    return bool(re.search(r"<[A-Z][A-Z0-9_]+>", text))


def _warning_remediation(warning_class: str) -> str | None:
    return {
        "todo_shape_drift": "Keep TODO focused on activation only; move execution detail into an execplan or durable docs.",
        "todo_activation_overflow": "Prune completed or speculative TODO detail until only the bounded active queue remains.",
        "todo_missing_execplan_linkage": "Create or promote this item to a docs/execplans plan and point Surface at it.",
        "todo_plan_required_hint": "This direct task has grown beyond direct-task shape; scaffold an execplan for it.",
        "todo_broken_surface_reference": "Repair Surface so it points at a live docs/execplans path, or remove the stale item.",
        "execplan_structure_drift": "Restore the template sections and keep the plan contract-shaped rather than inventory-shaped.",
        "execplan_immediate_next_action_drift": "Reduce Immediate Next Action to one concrete next step.",
        "execplan_readiness_drift": "Set Ready/Blocked explicitly so the active milestone can be resumed without re-deriving state.",
        "execplan_log_drift": "Compress the drift log into short decision notes or archive the completed plan.",
        "execplan_notebook_drift": "Strip status-journal residue out of the plan and keep only the current execution contract.",
        "execplan_under_specified": "Fill in the thin sections so the plan can be executed without extra chat context.",
        "roadmap_execution_drift": "Reduce ROADMAP back to candidate framing; keep active sequencing in TODO and execplans.",
        "roadmap_stale_candidate_pressure": "Prune stale candidate detail and leave compact candidate stubs only.",
        "promotion_linkage_drift": "Make the promotion signal explicit in TODO or ROADMAP so activation has a visible trigger.",
        "upgrade_source_stale": (
            "Refresh .agentic-workspace/planning/UPGRADE-SOURCE.toml after intentionally upgrading the bootstrap source."
        ),
        "archive_accumulation_drift": "Remove completed residue from active surfaces or move completed plans into archive.",
        "planning_memory_boundary_blur": "Move durable technical facts into memory or canonical docs, then leave planning surfaces lean.",
        "startup_policy_drift": "Restore the minimal startup order in AGENTS, quickstart, and manifest.",
    }.get(warning_class)


def _detect_adoption_mode(target_root: Path) -> str:
    required_present = sum(1 for relative in _installed_surface_files() if (target_root / relative).exists())
    if required_present == 0:
        return "uninitialised"
    if (target_root / "src" / "repo_planning_bootstrap").exists() and (target_root / "bootstrap").exists():
        return "self-hosted"
    if required_present >= len(_installed_surface_files()) // 2:
        return "installed"
    return "partial"


def _should_include_payload_path(path: Path, root: Path) -> bool:
    if not path.is_file():
        return False
    relative_parts = path.relative_to(root).parts
    if "__pycache__" in relative_parts:
        return False
    return path.suffix != ".pyc"


def _can_remove_payload_file(*, relative: Path, target_root: Path) -> bool:
    destination = target_root / relative
    if not destination.exists() or not destination.is_file():
        return False
    if relative in GENERATED_PAYLOAD_FILES:
        expectations = dict((path, text) for path, text, _ in _generated_agent_file_expectations(target_root))
        expected_text = expectations.get(relative)
        if expected_text is None:
            return False
        return destination.read_text(encoding="utf-8") == expected_text
    expected = _expected_target_file_bytes(relative=relative, target_root=target_root)
    if expected is None:
        return False
    return destination.read_bytes() == expected


def _expected_target_file_bytes(*, relative: Path, target_root: Path) -> bytes | None:
    source = payload_root() / relative
    if not source.exists() or not source.is_file():
        return None
    return source.read_bytes()


def _files_match(source: Path, destination: Path) -> bool:
    return source.is_file() and destination.is_file() and source.read_bytes() == destination.read_bytes()


def _prune_empty_parent_dirs(*, target_root: Path, relatives: list[Path]) -> None:
    candidates = sorted(
        {parent for relative in relatives for parent in relative.parents if parent != Path(".")},
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for relative_dir in candidates:
        directory = target_root / relative_dir
        if directory.exists() and directory.is_dir():
            try:
                directory.rmdir()
            except OSError:
                continue


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _section_lines(lines: list[str], heading: str) -> list[str]:
    target = f"## {heading}".lower()
    start = -1
    for index, line in enumerate(lines):
        if line.strip().lower() == target:
            start = index + 1
            break
    if start < 0:
        return []
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## "):
            end = index
            break
    return lines[start:end]


def _read_todo_items(path: Path) -> tuple[list[str], list[TodoItem]]:
    lines = _read_lines(path)
    items: list[TodoItem] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not re.match(r"^\s*-\s*ID\s*:\s*\S+", line):
            index += 1
            continue

        start = index
        fields: dict[str, str] = {}
        field_order: list[str] = []
        while index < len(lines):
            row = lines[index]
            if index != start and re.match(r"^\s*-\s*ID\s*:\s*\S+", row):
                break
            match = re.match(r"^\s*(?:-\s*)?([^:]+):\s*(.*)\s*$", row)
            if match:
                key = match.group(1).strip().lower()
                if key not in field_order:
                    field_order.append(key)
                fields[key] = match.group(2).strip()
            index += 1
            if index >= len(lines):
                break
            if lines[index].strip() == "":
                break
        items.append(TodoItem(fields=fields, field_order=field_order, start=start, end=index))
        index += 1
    return lines, items


def _rewrite_todo_item(lines: list[str], item: TodoItem, updated_fields: dict[str, str]) -> list[str]:
    ordered_keys = ["id", "status", "surface", "why now", "next action", "done when"]
    for key in item.field_order:
        if key not in ordered_keys:
            ordered_keys.append(key)

    block_lines: list[str] = []
    for key in ordered_keys:
        value = updated_fields.get(key)
        if not value:
            continue
        prefix = "- " if key == "id" else "  "
        label = "ID" if key == "id" else key.title()
        block_lines.append(f"{prefix}{label}: {value}")
    return lines[: item.start] + block_lines + lines[item.end :]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "new-plan"


def _title_from_slug(slug: str) -> str:
    return " ".join(token.capitalize() for token in slug.split("-"))


def _normalize_status(status: str) -> str:
    lowered = status.strip().lower()
    if lowered in {"in-progress", "active", "ongoing", "current"}:
        return "in-progress"
    if lowered in {"done", "completed", "closed"}:
        return "completed"
    return "planned"


def _render_execplan_from_todo_item(
    *,
    title: str,
    item_id: str,
    status: str,
    why_now: str,
    next_action: str,
    done_when: str,
) -> str:
    goal = why_now or f"Complete the bounded work for TODO item `{item_id}`."
    immediate = next_action or "Fill the execution contract and begin the first bounded implementation step."
    completion = done_when or f"TODO item `{item_id}` is implemented, validated, and can leave the active queue."
    blocked = "none" if status != "completed" else "n/a"
    ready = "ready" if status != "completed" else "false"
    return (
        f"# {title}\n\n"
        "## Goal\n\n"
        f"- {goal}\n\n"
        "## Non-Goals\n\n"
        "- Leave adjacent backlog or follow-on work out of this plan.\n\n"
        "## Active Milestone\n\n"
        f"- ID: {item_id}\n"
        f"- Status: {status}\n"
        "- Scope: Keep this execution thread bounded to the promoted TODO item.\n"
        f"- Ready: {ready}\n"
        f"- Blocked: {blocked}\n"
        "- optional_deps: none\n\n"
        "## Immediate Next Action\n\n"
        f"- {immediate}\n\n"
        "## Blockers\n\n"
        "- None.\n\n"
        "## Touched Paths\n\n"
        "- Fill in the concrete files before implementation starts.\n\n"
        "## Invariants\n\n"
        "- Preserve the planning contract and keep the work bounded to this plan.\n\n"
        "## Validation Commands\n\n"
        "- Fill in the narrowest command that proves the promoted work.\n\n"
        "## Completion Criteria\n\n"
        f"- {completion}\n\n"
        "## Drift Log\n\n"
        f"- {date.today().isoformat()}: Promoted from TODO direct-task shape into an execplan.\n"
    )


def _surface_execplan_reference(surface_value: str) -> str | None:
    inline_path_match = re.search(r"docs/execplans/[A-Za-z0-9._/\-]+\.md", surface_value)
    if inline_path_match:
        return inline_path_match.group(0)
    markdown_target = re.search(r"\]\(([^)]+)\)", surface_value)
    if markdown_target:
        target_match = re.search(r"docs/execplans/[A-Za-z0-9._/\-]+\.md", markdown_target.group(1))
        if target_match:
            return target_match.group(0)
    return None


def _resolve_execplan_path(target_root: Path, plan: str) -> Path | None:
    candidate = Path(plan)
    if candidate.is_absolute():
        return candidate
    if candidate.suffix == ".md" and (target_root / candidate).exists():
        return (target_root / candidate).resolve()
    normalized = plan if plan.endswith(".md") else f"{plan}.md"
    direct = target_root / "docs" / "execplans" / normalized
    if direct.exists():
        return direct.resolve()
    archive = target_root / "docs" / "execplans" / "archive" / normalized
    if archive.exists():
        return archive.resolve()
    return None


def _execplan_status(path: Path) -> str:
    lines = _read_lines(path)
    for line in _section_lines(lines, "Active Milestone"):
        match = re.match(r"^\s*-\s*Status\s*:\s*(.*)\s*$", line, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    return ""


def _execplan_item_id(path: Path) -> str:
    lines = _read_lines(path)
    for line in _section_lines(lines, "Active Milestone"):
        match = re.match(r"^\s*-\s*ID\s*:\s*(.*)\s*$", line, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    return ""


def _todo_referencing_items(todo_path: Path, plan_path: Path, target_root: Path) -> list[TodoItem]:
    _, items = _read_todo_items(todo_path)
    relative = plan_path.relative_to(target_root).as_posix()
    matches: list[TodoItem] = []
    for item in items:
        if _surface_execplan_reference(item.fields.get("surface", "")) == relative:
            matches.append(item)
    return matches


def _remove_todo_items(todo_path: Path, items_to_remove: list[TodoItem]) -> list[str]:
    lines, _ = _read_todo_items(todo_path)
    indexes_to_remove: set[int] = set()
    for item in items_to_remove:
        indexes_to_remove.update(range(item.start, item.end))
        if item.end < len(lines) and lines[item.end].strip() == "":
            indexes_to_remove.add(item.end)

    filtered_lines = [line for index, line in enumerate(lines) if index not in indexes_to_remove]
    while filtered_lines and filtered_lines[-1] == "":
        filtered_lines.pop()
    return _restore_todo_empty_state(filtered_lines)


def _restore_todo_empty_state(lines: list[str]) -> list[str]:
    for heading in ("Now", "Next"):
        lines = _restore_todo_empty_state_for_heading(lines, heading)
    return lines


def _restore_todo_empty_state_for_heading(lines: list[str], heading: str) -> list[str]:
    heading_index = next((index for index, line in enumerate(lines) if line.strip().lower() == f"## {heading.lower()}"), -1)
    if heading_index < 0:
        return lines
    section_end = len(lines)
    for index in range(heading_index + 1, len(lines)):
        if lines[index].startswith("## "):
            section_end = index
            break

    section_body = lines[heading_index + 1 : section_end]
    if any(line.strip() and line.strip() != TODO_EMPTY_STATE_LINE for line in section_body):
        return lines

    normalized_lines = lines[: heading_index + 1] + ["", TODO_EMPTY_STATE_LINE] + lines[section_end:]
    while len(normalized_lines) > 2 and normalized_lines[-1] == "" and normalized_lines[-2] == "":
        normalized_lines.pop()
    return normalized_lines


def _cleanup_compact_todo_archive_followup(todo_path: Path, plan_path: Path, target_root: Path) -> dict[str, Any]:
    if not todo_path.exists():
        return {"changed": False, "text": None, "details": []}

    lines = _read_lines(todo_path)
    relative = plan_path.relative_to(target_root).as_posix()
    queue_id = _execplan_item_id(plan_path) or plan_path.stem.lower()
    changed = False
    details: list[str] = []

    action_lines, action_removed = _cleanup_todo_action_section(lines, relative)
    if action_removed:
        lines = action_lines
        changed = True
        details.append("remove Action reference to the archived plan")

    now_lines, now_removed = _cleanup_todo_now_section(lines, queue_id)
    if now_removed:
        lines = now_lines
        changed = True
        details.append("remove compact Now item tied to the archived plan")

    if not changed:
        return {"changed": False, "text": None, "details": []}
    lines = _restore_todo_empty_state(lines)
    return {"changed": True, "text": "\n".join(lines).rstrip() + "\n", "details": details}


def _cleanup_todo_action_section(lines: list[str], relative_plan_path: str) -> tuple[list[str], bool]:
    section = _section_lines(lines, "Action")
    if not section:
        return lines, False
    heading_index = next((index for index, line in enumerate(lines) if line.strip().lower() == "## action"), -1)
    if heading_index < 0:
        return lines, False
    section_start = heading_index + 1
    section_end = section_start + len(section)

    kept_lines: list[str] = []
    removed = False
    for line in section:
        if relative_plan_path in line:
            removed = True
            continue
        kept_lines.append(line)

    if not removed:
        return lines, False
    if not any(line.strip() for line in kept_lines):
        kept_lines = [
            "",
            "- Promote the next bounded candidate only when fresh repeated friction or explicit maintainer choice justifies activation.",
        ]
    return lines[:section_start] + kept_lines + lines[section_end:], True


def _cleanup_todo_now_section(lines: list[str], plan_stem: str) -> tuple[list[str], bool]:
    section = _section_lines(lines, "Now")
    if not section:
        return lines, False
    heading_index = next((index for index, line in enumerate(lines) if line.strip().lower() == "## now"), -1)
    if heading_index < 0:
        return lines, False
    section_start = heading_index + 1
    section_end = section_start + len(section)

    compact_pattern = re.compile(r"^\s*-\s*([a-z0-9._-]+)\s*:\s*(.*)$", re.IGNORECASE)
    kept_lines: list[str] = []
    removed = False
    for line in section:
        match = compact_pattern.match(line)
        if match and match.group(1).strip().lower() == plan_stem:
            removed = True
            continue
        kept_lines.append(line)

    if not removed:
        return lines, False
    return lines[:section_start] + kept_lines + lines[section_end:], True


def _plan_stem_tokens(plan_path: Path) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", plan_path.stem.lower()) if len(token) >= 4 and not token.isdigit()]


def _cleanup_roadmap_archive_followup(roadmap_path: Path, plan_path: Path) -> dict[str, Any]:
    if not roadmap_path.exists():
        return {"changed": False, "text": None, "details": [], "note": None}

    lines = _read_lines(roadmap_path)
    tokens = _plan_stem_tokens(plan_path)
    details: list[str] = []
    changed = False

    lines, handoff_removed = _cleanup_roadmap_section(lines, "Active Handoff", tokens, empty_line="- No active handoff right now.")
    if handoff_removed:
        changed = True
        details.append("compress Active Handoff residue tied to the archived plan")

    lines, queue_removed = _cleanup_roadmap_section(lines, "Next Candidate Queue", tokens, empty_line=None)
    if queue_removed:
        changed = True
        details.append("remove archived-plan candidate residue from Next Candidate Queue")

    if not changed:
        return {"changed": False, "text": None, "details": [], "note": None}
    return {
        "changed": True,
        "text": "\n".join(lines).rstrip() + "\n",
        "details": details,
        "note": None,
    }


def _cleanup_roadmap_section(lines: list[str], heading: str, tokens: list[str], *, empty_line: str | None) -> tuple[list[str], bool]:
    section = _section_lines(lines, heading)
    if not section:
        return lines, False

    start = next((index for index, line in enumerate(lines) if line.strip().lower() == f"## {heading.lower()}"), -1)
    if start < 0:
        return lines, False
    section_start = start + 1
    section_end = section_start + len(section)

    kept_lines: list[str] = []
    removed = False
    for line in section:
        if not re.match(r"^\s*-\s+", line):
            kept_lines.append(line)
            continue
        lowered = line.lower()
        if tokens and any(token in lowered for token in tokens):
            removed = True
            continue
        kept_lines.append(line)

    if not removed:
        return lines, False

    replacement = [line for line in kept_lines if line.strip()]
    if empty_line is not None and not any(re.match(r"^\s*-\s+", line) for line in replacement):
        replacement = [empty_line]

    return lines[:section_start] + replacement + lines[section_end:], True
