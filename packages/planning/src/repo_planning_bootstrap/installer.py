from __future__ import annotations

import importlib.util
import json
import re
import shutil
import tomllib
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
PLANNING_STATE_PATH = PLANNING_MANAGED_ROOT / "state.toml"
PLANNING_EXTERNAL_INTENT_EVIDENCE_PATH = PLANNING_MANAGED_ROOT / "external-intent-evidence.json"
PLANNING_FINISHED_WORK_EVIDENCE_PATH = PLANNING_MANAGED_ROOT / "finished-work-evidence.json"
PLANNING_RENDER_SCRIPT_PATH = PLANNING_MANAGED_ROOT / "scripts" / "render_agent_docs.py"
PLANNING_CHECKER_SCRIPT_PATH = PLANNING_MANAGED_ROOT / "scripts" / "check" / "check_planning_surfaces.py"
PLANNING_MAINTAINER_CHECKER_SCRIPT_PATH = PLANNING_MANAGED_ROOT / "scripts" / "check" / "check_maintainer_surfaces.py"
ROOT_RENDER_SCRIPT_PATH = Path("scripts/render_agent_docs.py")
ROOT_CHECKER_SCRIPT_PATH = Path("scripts/check/check_planning_surfaces.py")
ROOT_MAINTAINER_CHECKER_PATH = Path("scripts/check/check_maintainer_surfaces.py")
ROOT_MANIFEST_MIRROR_PATH = Path("tools/agent-manifest.json")

REQUIRED_PAYLOAD_FILES = (
    Path("AGENTS.template.md"),
    Path(".agentic-workspace/docs/execution-flow-contract.md"),
    Path(".agentic-workspace/docs/system-intent-contract.md"),
    Path(".agentic-workspace/docs/routing-contract.md"),
    Path(".agentic-workspace/docs/minimum-operating-model.md"),
    Path(".agentic-workspace/docs/lifecycle-and-config-contract.md"),
    Path(".agentic-workspace/docs/extraction-and-discovery-contract.md"),
    Path(".agentic-workspace/docs/reporting-contract.md"),
    Path(".agentic-workspace/docs/capability-aware-execution.md"),
    Path(".agentic-workspace/docs/capability-contract.json"),
    Path(".agentic-workspace/docs/signal-hygiene-contract.md"),
    Path(".agentic-workspace/docs/knowledge-promotion-workflow.md"),
    Path(".agentic-workspace/docs/standing-intent-contract.md"),
    Path(".agentic-workspace/docs/candidate-lanes-contract.md"),
    Path(".agentic-workspace/docs/context-budget-contract.md"),
    Path(".agentic-workspace/docs/external-intent-evidence-contract.md"),
    Path(".agentic-workspace/docs/finished-work-inspection-contract.md"),
    Path(".agentic-workspace/docs/installer-behavior.md"),
    Path(".agentic-workspace/planning/execplans/README.md"),
    Path(".agentic-workspace/planning/execplans/TEMPLATE.md"),
    Path(".agentic-workspace/planning/execplans/archive/README.md"),
    Path(".agentic-workspace/planning/reviews/README.md"),
    Path(".agentic-workspace/planning/reviews/TEMPLATE.md"),
    Path(".agentic-workspace/planning/upstream-task-intake.md"),
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
    Path("AGENTS.template.md"),
    Path(".agentic-workspace/docs/execution-flow-contract.md"),
    Path(".agentic-workspace/docs/system-intent-contract.md"),
    Path(".agentic-workspace/docs/routing-contract.md"),
    Path(".agentic-workspace/docs/minimum-operating-model.md"),
    Path(".agentic-workspace/docs/lifecycle-and-config-contract.md"),
    Path(".agentic-workspace/docs/extraction-and-discovery-contract.md"),
    Path(".agentic-workspace/docs/reporting-contract.md"),
    Path(".agentic-workspace/docs/capability-aware-execution.md"),
    Path(".agentic-workspace/docs/capability-contract.json"),
    Path(".agentic-workspace/docs/signal-hygiene-contract.md"),
    Path(".agentic-workspace/docs/knowledge-promotion-workflow.md"),
    Path(".agentic-workspace/docs/standing-intent-contract.md"),
    Path(".agentic-workspace/docs/candidate-lanes-contract.md"),
    Path(".agentic-workspace/docs/context-budget-contract.md"),
    Path(".agentic-workspace/docs/external-intent-evidence-contract.md"),
    Path(".agentic-workspace/docs/finished-work-inspection-contract.md"),
    Path(".agentic-workspace/docs/installer-behavior.md"),
    Path(".agentic-workspace/planning/execplans/README.md"),
    Path(".agentic-workspace/planning/execplans/TEMPLATE.md"),
    Path(".agentic-workspace/planning/execplans/archive/README.md"),
    Path(".agentic-workspace/planning/reviews/README.md"),
    Path(".agentic-workspace/planning/reviews/TEMPLATE.md"),
    Path(".agentic-workspace/planning/upstream-task-intake.md"),
    PLANNING_MANIFEST_PATH,
)

PLANNING_LOWER_STABILITY_HELPER_FILES = tuple(
    relative for relative in REQUIRED_PAYLOAD_FILES if relative not in PLANNING_COMPATIBILITY_CONTRACT_FILES
)

ROOT_SURFACE_FILES = (Path("AGENTS.template.md"),)

GENERATED_PAYLOAD_FILES = (
    ROOT_MANIFEST_MIRROR_PATH,
    Path("tools/AGENT_QUICKSTART.md"),
    Path("tools/AGENT_ROUTING.md"),
)

PAYLOAD_GUIDANCE_FRAGMENTS = {
    Path(".agentic-workspace/planning/execplans/TEMPLATE.md"): (
        "concurrent edits merge cleanly",
        "do not add retrospective sections such as `Added In This Pass`",
        "Replace stale immediate-action text when the next step changes",
    ),
    Path(".agentic-workspace/planning/execplans/README.md"): (
        "Do not add sections such as `Added In This Pass`",
        "Treat active plan state as branch-local and low half-life",
    ),
}

TODO_EMPTY_STATE_LINE = "- No active work right now."
_COMPATIBILITY_VIEW_NOTICE = "<!-- GENERATED COMPATIBILITY VIEW: authoritative source is .agentic-workspace/planning/state.toml -->"

PACKAGE_MANAGED_FILES = tuple(
    relative for relative in REQUIRED_PAYLOAD_FILES if relative not in ROOT_SURFACE_FILES and relative not in GENERATED_PAYLOAD_FILES
)


def skills_root() -> Path:
    packaged = Path(__file__).resolve().parent / "_skills"
    if packaged.exists():
        return packaged
    return Path(__file__).resolve().parents[2] / "skills"


def _add_contract_surface_summary(result: InstallResult, root: Path) -> None:
    def resolve_template(path: Path) -> str:
        name = path.name
        if name.endswith(".template.md"):
            return (path.parent / (name[:-12] + ".md")).as_posix()
        return path.as_posix()

    compatibility = ", ".join(resolve_template(path) for path in PLANNING_COMPATIBILITY_CONTRACT_FILES)
    helpers = ", ".join(resolve_template(path) for path in PLANNING_LOWER_STABILITY_HELPER_FILES)
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


def _detect_payload_drift(target_root: Path) -> list[dict[str, str]]:
    """Detect differences between root source files and bootstrap payload mirror."""
    mirror_root = payload_root()
    # In a packaged installation, mirror_root will be '_payload' inside the site-packages.
    # We only report drift if we can find the development workspace root.
    dev_workspace_root = mirror_root.parents[2]
    if not (dev_workspace_root / "pyproject.toml").exists():
        return []

    # Only report drift if the target we are reporting on is the dev workspace itself.
    if target_root.resolve() != dev_workspace_root.resolve():
        return []

    drift = []
    managed_by_mirror = set(REQUIRED_PAYLOAD_FILES)

    # Check for missing or differing files in the mirror
    for relative in managed_by_mirror:
        if not (relative.parts[0] == "docs" or relative.name in {"AGENTS.template.md", "TODO.template.md", "ROADMAP.template.md"}):
            continue

        target_relative = relative
        if target_relative.name.endswith(".template.md"):
            target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")

        source_path = dev_workspace_root / target_relative
        mirror_path = mirror_root / relative

        if not source_path.exists():
            # This is a different kind of error: required file missing from root
            continue

        if not mirror_path.exists():
            drift.append(
                {
                    "path": relative.as_posix(),
                    "message": f"Payload mirror missing: '{relative.as_posix()}' exists in root but not in bootstrap mirror.",
                    "warning_class": "payload_drift",
                }
            )
            continue

        if relative in ROOT_SURFACE_FILES:
            # Root surface files are generic templates in the mirror, but active state in the root.
            # They are expected to differ, so we only check existence, not content.
            continue

        if source_path.read_text(encoding="utf-8") != mirror_path.read_text(encoding="utf-8"):
            drift.append(
                {
                    "path": relative.as_posix(),
                    "message": f"Payload drift detected: '{relative.as_posix()}' in root differs from bootstrap mirror.",
                    "warning_class": "payload_drift",
                }
            )

    # Check for extra files in the mirror that aren't in REQUIRED_PAYLOAD_FILES
    for mirror_file in mirror_root.rglob("*"):
        if mirror_file.is_dir() or mirror_file.name == ".git":
            continue

        relative = mirror_file.relative_to(mirror_root)
        if relative not in managed_by_mirror and relative.parts[0] != "skills":
            # Ignore files that are legitimately bootstrap-only if they aren't docs/root surfaces
            if relative.parts[0] == "docs" or relative.name in {"AGENTS.template.md", "TODO.template.md", "ROADMAP.template.md"}:
                drift.append(
                    {
                        "path": relative.as_posix(),
                        "message": f"Extra payload file: '{relative.as_posix()}' exists in bootstrap mirror but is not in REQUIRED_PAYLOAD_FILES.",
                        "warning_class": "payload_drift",
                    }
                )

    return drift


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


def resolve_target_root(target: str | Path | None, *, local_only: bool = False) -> Path:
    resolved = Path(target).resolve() if target else Path.cwd().resolve()
    if local_only:
        resolved = resolved / ".gemini" / "agentic-workspace"
    elif not (resolved / ".agentic-workspace").exists() and (resolved / ".gemini" / "agentic-workspace").exists():
        resolved = resolved / ".gemini" / "agentic-workspace"
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def list_payload_files() -> list[str]:
    root = payload_root()
    return [path.relative_to(root).as_posix() for path in sorted(root.rglob("*")) if _should_include_payload_path(path, root)]


def install_bootstrap(
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    local_only: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target, local_only=local_only)
    result = InstallResult(target_root=target_root, message="Install plan", dry_run=dry_run)
    _copy_payload(target_root=target_root, result=result, conservative=False, force=force)
    _copy_bundled_skills(target_root=target_root, result=result, conservative=False, force=force)
    _render_generated_agent_files(target_root=target_root, result=result, apply=not dry_run)
    if not dry_run:
        _migrate_legacy_planning_surfaces(target_root, force=force)
        _ensure_state_toml_exists(target_root, overwrite=force)
        _remove_generated_planning_views(target_root, result=result)
    if local_only and not dry_run:
        _ensure_local_ignored(target or Path.cwd())
    return result


def _ensure_local_ignored(repo_root: str | Path) -> None:
    gitignore = Path(repo_root) / ".gitignore"
    if not gitignore.exists():
        return
    text = gitignore.read_text(encoding="utf-8")
    if ".gemini/" not in text:
        with gitignore.open("a", encoding="utf-8") as f:
            f.write("\n# Agentic Workspace local-only storage\n.gemini/\n")


def adopt_bootstrap(*, target: str | Path | None = None, dry_run: bool = False) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Adoption plan for existing repository", dry_run=dry_run)
    _copy_payload(target_root=target_root, result=result, conservative=True, force=False)
    _copy_bundled_skills(target_root=target_root, result=result, conservative=True, force=False)
    _render_generated_agent_files(target_root=target_root, result=result, apply=not dry_run)
    if not dry_run:
        _migrate_legacy_planning_surfaces(target_root)
        _ensure_state_toml_exists(target_root)
        _remove_generated_planning_views(target_root, result=result)
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
    if not dry_run:
        _migrate_legacy_planning_surfaces(target_root)
        _ensure_state_toml_exists(target_root)
        _remove_generated_planning_views(target_root, result=result)
    return result


def uninstall_bootstrap(*, target: str | Path | None = None, dry_run: bool = False) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Uninstall plan", dry_run=dry_run)

    removable: list[Path] = []
    for relative in _installed_surface_files():
        target_relative = relative
        if target_relative.name.endswith(".template.md"):
            target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")

        destination = target_root / target_relative
        if not destination.exists():
            result.add("skipped", destination, "already absent")
            continue
        if relative in PLANNING_BUNDLED_SKILL_FILES:
            removable_check = _remove_bundled_skill_file(relative=relative, target_root=target_root)
        else:
            removable_check = _can_remove_payload_file(relative=relative, target_root=target_root)
        if removable_check:
            removable.append(target_relative)
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
        name = relative.name
        if name.endswith(".template.md"):
            installed_relative = relative.parent / (name[:-12] + ".md")
        else:
            installed_relative = relative
        destination = target_root / installed_relative
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
        name = relative.name
        if name.endswith(".template.md"):
            installed_relative = relative.parent / (name[:-12] + ".md")
        else:
            installed_relative = relative
        destination = target_root / installed_relative
        detail = "required file present" if destination.exists() else "required file missing"
        result.add("current" if destination.exists() else "manual review", destination, detail)

    _add_contract_surface_summary(result, target_root)

    for relative in (Path("AGENTS.md"), PLANNING_STATE_PATH):
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
        target_relative = relative
        if target_relative.name.endswith(".template.md"):
            target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")

        detail = "required payload file present" if relative in payload_files else "required payload file missing"
        result.add("current" if relative in payload_files else "manual review", root / target_relative, detail)

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
    legacy_todo_path = target_root / PLANNING_STATE_PATH
    roadmap_path = target_root / "ROADMAP.md"
    execplan_dir = target_root / ".agentic-workspace" / "planning" / "execplans"

    state = _read_state_from_toml(target_root)
    if state:
        todo_data = state.get("todo", {})
        active_items = todo_data.get("active_items", [])
        queued_items = todo_data.get("queued_items", [])
        roadmap_data = state.get("roadmap", {})
        roadmap_lanes = roadmap_data.get("lanes", [])
        roadmap_candidates = roadmap_data.get("candidates", [])
        if not roadmap_candidates and roadmap_lanes:
            roadmap_candidates = [{"priority": lane.get("priority", ""), "summary": lane.get("title", "")} for lane in roadmap_lanes]
        todo_line_count = 0  # We don't have a direct line count for the TOML state
        todo_item_count = len(active_items) + len(queued_items)
    else:
        legacy_todo_lines, legacy_todo_items = _read_todo_items(legacy_todo_path)
        if legacy_todo_items:
            todo_lines, todo_items = legacy_todo_lines, legacy_todo_items
        else:
            todo_lines, todo_items = _read_todo_items(todo_path)
        active_items = []
        queued_items = []
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
                continue
            if status not in {"completed", "done", "closed"}:
                queued_items.append(
                    {
                        "id": item.fields.get("id", ""),
                        "surface": item.fields.get("surface", ""),
                        "why_now": item.fields.get("why now", ""),
                        "status": item.fields.get("status", ""),
                    }
                )
        roadmap_lanes = _roadmap_candidate_lanes(roadmap_path)
        roadmap_candidates = _roadmap_candidates(roadmap_path)
        todo_line_count = len(todo_lines)
        todo_item_count = len(todo_items)

    ownership_review = _ownership_review(target_root)
    # ... rest of the function ...
    active_execplans: list[dict[str, str]] = []
    # ... (skipping some logic) ...
    # Wait, I need to make sure I don't break the existing logic.
    # I'll replace the beginning of planning_summary.
    ownership_review = _ownership_review(target_root)

    active_execplans: list[dict[str, str]] = []
    completed_execplans: list[dict[str, Any]] = []
    archived_execplans = 0
    if execplan_dir.exists():
        for path in sorted(execplan_dir.glob("*.md")):
            if path.name in {"README.md", "TEMPLATE.md"}:
                continue
            status = _execplan_status(path)
            if status and status not in {"completed", "done", "closed", "planned", "pending", "not-started"}:
                active_execplans.append({"path": path.relative_to(target_root).as_posix(), "status": status})
            elif status in {"completed", "done", "closed"}:
                completed_execplans.append(
                    {
                        "path": path.relative_to(target_root).as_posix(),
                        "status": status,
                        "proof_report": _execplan_proof_report(path),
                        "intent_satisfaction": _execplan_intent_satisfaction(path),
                        "closure_check": _execplan_closure_check(path),
                    }
                )
        archive_dir = execplan_dir / "archive"
        if archive_dir.exists():
            archived_execplans = sum(1 for path in archive_dir.glob("*.md") if path.is_file())

    warnings = _run_planning_checker(target_root)
    drift = _detect_payload_drift(target_root)
    warnings.extend(drift)

    active_contract = _active_intent_contract(
        target_root=target_root,
        active_items=active_items,
        active_execplans=active_execplans,
    )
    resumable_contract = _active_resumable_contract(
        target_root=target_root,
        active_contract=active_contract,
        active_execplans=active_execplans,
    )
    planning_record = _canonical_planning_record(
        target_root=target_root,
        active_contract=active_contract,
        resumable_contract=resumable_contract,
    )
    follow_through_contract = _active_follow_through_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_execplans=active_execplans,
    )
    intent_interpretation_contract = _active_intent_interpretation_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_execplans=active_execplans,
    )
    context_budget_contract = _active_context_budget_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_execplans=active_execplans,
    )
    execution_run_contract = _active_execution_run_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_execplans=active_execplans,
    )
    finished_run_review_contract = _active_finished_run_review_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_execplans=active_execplans,
        execution_run_contract=execution_run_contract,
        intent_interpretation_contract=intent_interpretation_contract,
    )
    intent_validation_contract = _intent_validation_contract(
        target_root=target_root,
        active_items=active_items,
        active_execplans=active_execplans,
        roadmap_lanes=roadmap_lanes,
    )
    finished_work_inspection_contract = _finished_work_inspection_contract(target_root=target_root)
    hierarchy_contract = _active_hierarchy_contract(
        target_root=target_root,
        planning_record=planning_record,
        active_contract=active_contract,
        resumable_contract=resumable_contract,
        follow_through_contract=follow_through_contract,
        context_budget_contract=context_budget_contract,
        roadmap_lanes=roadmap_lanes,
        active_execplans=active_execplans,
    )
    handoff_contract = _active_handoff_contract(
        planning_record=planning_record,
        hierarchy_contract=hierarchy_contract,
        context_budget_contract=context_budget_contract,
        intent_interpretation_contract=intent_interpretation_contract,
    )
    return {
        "kind": "planning-summary/v1",
        "schema": _planning_summary_schema(),
        "target_root": str(target_root),
        "adoption_mode": _detect_adoption_mode(target_root),
        "todo": {
            "line_count": todo_line_count,
            "item_count": todo_item_count,
            "active_count": len(active_items),
            "active_items": active_items,
            "queued_count": len(queued_items),
            "queued_items": queued_items,
        },
        "execplans": {
            "active_count": len(active_execplans),
            "active_execplans": active_execplans,
            "completed_count": len(completed_execplans),
            "completed_execplans": completed_execplans,
            "archived_count": archived_execplans,
        },
        "planning_record": planning_record,
        "active_contract": _contract_projection(active_contract, view_name="active_contract"),
        "resumable_contract": _contract_projection(resumable_contract, view_name="resumable_contract"),
        "follow_through_contract": _contract_projection(follow_through_contract, view_name="follow_through_contract"),
        "intent_interpretation_contract": _contract_projection(
            intent_interpretation_contract,
            view_name="intent_interpretation_contract",
        ),
        "context_budget_contract": _contract_projection(context_budget_contract, view_name="context_budget_contract"),
        "execution_run_contract": _contract_projection(execution_run_contract, view_name="execution_run_contract"),
        "finished_run_review_contract": _contract_projection(
            finished_run_review_contract,
            view_name="finished_run_review_contract",
        ),
        "intent_validation_contract": _contract_projection(
            intent_validation_contract,
            view_name="intent_validation_contract",
        ),
        "finished_work_inspection_contract": _contract_projection(
            finished_work_inspection_contract,
            view_name="finished_work_inspection_contract",
        ),
        "hierarchy_contract": _contract_projection(hierarchy_contract, view_name="hierarchy_contract"),
        "handoff_contract": _contract_projection(handoff_contract, view_name="handoff_contract"),
        "system_intent": _system_intent_contract_payload(),
        "roadmap": {
            "lane_count": len(roadmap_lanes),
            "candidate_lanes": roadmap_lanes,
            "candidate_count": len(roadmap_candidates),
            "candidates": roadmap_candidates,
        },
        "ownership_review": ownership_review,
        "warnings": [warning.copy() for warning in warnings],
        "warning_count": len(warnings),
    }


def planning_report(*, target: str | Path | None = None) -> dict[str, Any]:
    summary = planning_summary(target=target)
    planning_record = summary.get("planning_record", {})
    completed_execplans = list(summary.get("execplans", {}).get("completed_execplans", []))
    active_contract = summary.get("active_contract", {})
    resumable_contract = summary.get("resumable_contract", {})
    follow_through_contract = summary.get("follow_through_contract", {})
    intent_interpretation_contract = summary.get("intent_interpretation_contract", {})
    context_budget_contract = summary.get("context_budget_contract", {})
    execution_run_contract = summary.get("execution_run_contract", {})
    finished_run_review_contract = summary.get("finished_run_review_contract", {})
    intent_validation_contract = summary.get("intent_validation_contract", {})
    finished_work_inspection_contract = summary.get("finished_work_inspection_contract", {})
    hierarchy_contract = summary.get("hierarchy_contract", {})
    handoff_contract = summary.get("handoff_contract", {})
    warnings = list(summary.get("warnings", []))
    findings = [
        {
            "severity": "warning",
            "path": warning.get("path"),
            "message": warning.get("message", ""),
            "warning_class": warning.get("warning_class", ""),
        }
        for warning in warnings
    ]
    validation_signals = intent_validation_contract.get("signals", [])
    if isinstance(validation_signals, list):
        for signal in validation_signals:
            if not isinstance(signal, dict):
                continue
            findings.append(
                {
                    "severity": str(signal.get("severity", "warning")),
                    "path": str(signal.get("path", "")) or None,
                    "message": str(signal.get("message", "")),
                    "warning_class": str(signal.get("kind", "")),
                }
            )
    inspection_signals = finished_work_inspection_contract.get("signals", [])
    if isinstance(inspection_signals, list):
        for signal in inspection_signals:
            if not isinstance(signal, dict):
                continue
            findings.append(
                {
                    "severity": str(signal.get("severity", "warning")),
                    "path": str(signal.get("path", "")) or None,
                    "message": str(signal.get("message", "")),
                    "warning_class": str(signal.get("kind", "")),
                }
            )
    next_action = "No active planning work right now."
    commands: list[str] = []
    if planning_record.get("status") == "present":
        next_action = str(planning_record.get("next_action", next_action))
    elif finished_work_inspection_contract.get("status") == "present" and finished_work_inspection_contract.get("counts", {}).get(
        "attention_count", 0
    ):
        next_action = str(
            finished_work_inspection_contract.get(
                "recommended_next_action",
                "Inspect finished-work signals before treating previously closed work as settled.",
            )
        )
        commands.append("Inspect the finished_work_inspection contract in agentic-planning-bootstrap report --format json")
    elif intent_validation_contract.get("status") == "present" and intent_validation_contract.get("counts", {}).get("attention_count", 0):
        next_action = str(
            intent_validation_contract.get("recommended_next_action", "Review intent-validation signals before treating planning as quiet.")
        )
        commands.append("Inspect the intent_validation contract in agentic-planning-bootstrap report --format json")
    elif summary["todo"]["active_count"]:
        first_item = summary["todo"]["active_items"][0]
        next_action = f"Continue active TODO item {first_item.get('id', '')}: {first_item.get('surface', '')}".strip(": ")
    elif summary["roadmap"]["candidate_count"]:
        next_action = "Promote the highest-priority roadmap candidate when the next bounded slice is ready."
        commands.append("Inspect roadmap lanes in .agentic-workspace/planning/state.toml")

    health = "healthy"
    if summary["warning_count"]:
        health = "attention-needed"
    elif summary["todo"]["active_count"] or summary["execplans"]["active_count"]:
        health = "active"

    return {
        "kind": "planning-module-report/v1",
        "schema": {
            "schema_version": "module-report-schema/v1",
            "module": "planning",
            "command": "agentic-planning-bootstrap report --format json",
            "canonical_docs": [
                ".agentic-workspace/docs/reporting-contract.md",
                ".agentic-workspace/docs/system-intent-contract.md",
                ".agentic-workspace/docs/context-budget-contract.md",
                ".agentic-workspace/docs/external-intent-evidence-contract.md",
                "packages/planning/README.md",
            ],
            "shared_fields": [
                "kind",
                "schema",
                "module",
                "target_root",
                "health",
                "status",
                "completed_execplans",
                "ownership_review",
                "active",
                "system_intent",
                "intent_validation",
                "finished_work_inspection",
                "findings",
                "next_action",
            ],
        },
        "module": "planning",
        "target_root": summary["target_root"],
        "health": health,
        "status": {
            "adoption_mode": summary["adoption_mode"],
            "active_todo_count": summary["todo"]["active_count"],
            "queued_todo_count": summary["todo"].get("queued_count", 0),
            "todo_item_count": summary["todo"]["item_count"],
            "active_execplan_count": summary["execplans"]["active_count"],
            "completed_execplan_count": summary["execplans"].get("completed_count", 0),
            "roadmap_lane_count": summary["roadmap"].get("lane_count", 0),
            "roadmap_candidate_count": summary["roadmap"]["candidate_count"],
            "intent_validation_attention_count": intent_validation_contract.get("counts", {}).get("attention_count", 0),
            "finished_work_inspection_attention_count": finished_work_inspection_contract.get("counts", {}).get("attention_count", 0),
            "warning_count": summary["warning_count"],
        },
        "completed_execplans": completed_execplans,
        "ownership_review": summary.get("ownership_review", {}),
        "active": {
            "planning_record": planning_record,
            "active_contract": active_contract,
            "resumable_contract": resumable_contract,
            "follow_through_contract": follow_through_contract,
            "intent_interpretation_contract": intent_interpretation_contract,
            "context_budget_contract": context_budget_contract,
            "execution_run_contract": execution_run_contract,
            "finished_run_review_contract": finished_run_review_contract,
            "hierarchy_contract": hierarchy_contract,
            "handoff_contract": handoff_contract,
        },
        "system_intent": summary.get("system_intent", {}),
        "intent_validation": intent_validation_contract,
        "finished_work_inspection": finished_work_inspection_contract,
        "findings": findings,
        "next_action": {
            "summary": next_action,
            "commands": commands,
        },
    }


def planning_handoff(*, target: str | Path | None = None) -> dict[str, Any]:
    summary = planning_summary(target=target)
    return {
        "kind": "planning-handoff/v1",
        "schema": _planning_handoff_schema(),
        "target_root": summary["target_root"],
        "handoff_contract": summary.get("handoff_contract", {}),
        "warnings": [warning.copy() for warning in summary.get("warnings", [])],
        "warning_count": int(summary.get("warning_count", 0)),
    }


def _planning_summary_schema() -> dict[str, Any]:
    return {
        "schema_version": "planning-summary-schema/v1",
        "canonical_docs": [
            ".agentic-workspace/docs/execution-flow-contract.md",
            ".agentic-workspace/docs/system-intent-contract.md",
            ".agentic-workspace/docs/routing-contract.md",
            ".agentic-workspace/docs/lifecycle-and-config-contract.md",
            ".agentic-workspace/docs/extraction-and-discovery-contract.md",
            ".agentic-workspace/docs/candidate-lanes-contract.md",
            ".agentic-workspace/docs/context-budget-contract.md",
            ".agentic-workspace/docs/external-intent-evidence-contract.md",
            ".agentic-workspace/docs/finished-work-inspection-contract.md",
            ".agentic-workspace/planning/execplans/README.md",
        ],
        "command": "agentic-workspace summary --format json",
        "shared_fields": [
            "kind",
            "schema",
            "target_root",
            "adoption_mode",
            "todo",
            "execplans",
            "ownership_review",
            "planning_record",
            "active_contract",
            "resumable_contract",
            "follow_through_contract",
            "intent_interpretation_contract",
            "context_budget_contract",
            "execution_run_contract",
            "finished_run_review_contract",
            "intent_validation_contract",
            "finished_work_inspection_contract",
            "hierarchy_contract",
            "handoff_contract",
            "system_intent",
            "roadmap",
            "warnings",
            "warning_count",
        ],
        "view_fields": {
            "planning_record": [
                "task",
                "requested_outcome",
                "hard_constraints",
                "agent_may_decide",
                "next_action",
                "proof_expectations",
                "proof_report",
                "intent_satisfaction",
                "closure_check",
                "intent_interpretation",
                "execution_bounds",
                "stop_conditions",
                "execution_run",
                "finished_run_review",
                "tool_verification",
                "escalate_when",
                "continuation_owner",
                "touched_scope",
                "completion_criteria",
                "blockers",
                "minimal_refs",
            ],
            "active_contract": [
                "todo_item",
                "intent",
                "touched_scope",
                "proof_expectations",
                "tool_verification",
                "minimal_refs",
            ],
            "resumable_contract": [
                "current_next_action",
                "active_milestone",
                "completion_criteria",
                "proof_expectations",
                "tool_verification",
                "escalate_when",
                "blockers",
                "minimal_refs",
            ],
            "follow_through_contract": [
                "larger_intended_outcome",
                "continuation_surface",
                "what_this_slice_enabled",
                "intentionally_deferred",
                "discovered_implications",
                "proof_achieved_now",
                "validation_still_needed",
                "next_likely_slice",
                "minimal_refs",
            ],
            "intent_interpretation_contract": [
                "literal_request",
                "inferred_intended_outcome",
                "chosen_concrete_what",
                "interpretation_distance",
                "review_guidance",
                "minimal_refs",
            ],
            "context_budget_contract": [
                "live_working_set",
                "recoverable_later",
                "externalize_before_shift",
                "pre_work_memory_pull",
                "tiny_resumability_note",
                "context_shift_triggers",
                "interaction_cost_rule",
                "resume_rule",
                "minimal_refs",
            ],
            "execution_run_contract": [
                "run_status",
                "executor",
                "handoff_source",
                "what_happened",
                "scope_touched",
                "changed_surfaces",
                "validations_run",
                "result_for_continuation",
                "next_step",
                "minimal_refs",
            ],
            "finished_run_review_contract": [
                "review_status",
                "scope_respected",
                "proof_status",
                "intent_served",
                "misinterpretation_risk",
                "follow_on_decision",
                "minimal_refs",
            ],
            "intent_validation_contract": [
                "rule",
                "primary_owner",
                "counts",
                "external_evidence",
                "signals",
                "recommended_next_action",
                "minimal_refs",
            ],
            "finished_work_inspection_contract": [
                "rule",
                "primary_owner",
                "counts",
                "evidence",
                "signals",
                "inspections",
                "recommended_next_action",
                "minimal_refs",
            ],
            "hierarchy_contract": [
                "current_layer",
                "parent_lane",
                "active_chunk",
                "near_term_queue",
                "next_likely_chunk",
                "proof_state",
                "context_shift",
                "required_continuation",
                "closure_check",
                "routing",
                "minimal_refs",
            ],
            "handoff_contract": [
                "task",
                "parent_lane",
                "requested_outcome",
                "hard_constraints",
                "agent_may_decide",
                "next_action",
                "completion_criteria",
                "read_first",
                "owned_write_scope",
                "proof_expectations",
                "intent_interpretation",
                "pre_work_memory_pull",
                "execution_bounds",
                "stop_conditions",
                "tool_verification",
                "continuation_owner",
                "context_budget",
                "return_with",
                "worker_contract",
            ],
            "roadmap": [
                "lane_count",
                "candidate_lanes",
                "candidate_count",
                "candidates",
            ],
        },
        "rules": [
            "planning_record is the canonical compact active planning state when it is available",
            (
                "active_contract, resumable_contract, follow_through_contract, intent_interpretation_contract, "
                "context_budget_contract, execution_run_contract, finished_run_review_contract, intent_validation_contract, finished_work_inspection_contract, and hierarchy_contract "
                "remain thinner projections over that state"
            ),
            "system intent remains durable and queryable even when the active slice is narrower than the parent issue or lane",
            "closure decisions must distinguish bounded slice completion from larger-intent satisfaction",
            "intent validation must still work when there is no active execplan by reconciling checked-in planning state with optional external evidence",
            "finished-work inspection must derive from archived checked-in residue first and treat optional reopening evidence as corroboration only",
            "handoff_contract remains a thinner delegated-worker view over the same active planning state",
            "prefer the summary schema over raw TODO or execplan parsing when one structured answer is enough",
        ],
    }


def _planning_handoff_schema() -> dict[str, Any]:
    return {
        "schema_version": "planning-handoff-schema/v1",
        "canonical_doc": ".agentic-workspace/docs/execution-flow-contract.md",
        "command": "agentic-planning-bootstrap handoff --format json",
        "shared_fields": [
            "kind",
            "schema",
            "target_root",
            "handoff_contract",
            "warnings",
            "warning_count",
        ],
        "rules": [
            "derive delegated worker handoff from the active planning record instead of authoring a second durable plan",
            "treat runtime delegation method as tool-owned and agent-agnostic",
            "keep worker closure bounded; lane shaping and roadmap routing stay orchestrator-owned",
            "use the handoff packet to preserve execution bounds, stop conditions, and return-with residue instead of reconstructing them from chat",
        ],
    }


def _intent_validation_contract(
    *,
    target_root: Path,
    active_items: list[dict[str, Any]],
    active_execplans: list[dict[str, str]],
    roadmap_lanes: list[dict[str, Any]],
) -> dict[str, Any]:
    surface_index = _planning_surface_reference_index(target_root)
    external_evidence = _load_external_intent_evidence(target_root)
    signals: list[dict[str, Any]] = []

    internal_signals = _internal_continuation_signals(
        target_root=target_root,
        roadmap_lanes=roadmap_lanes,
    )
    signals.extend(internal_signals)
    if external_evidence.get("status") == "invalid":
        signals.append(
            {
                "kind": "external_evidence_invalid",
                "severity": "warning",
                "path": external_evidence.get("path", ""),
                "message": str(external_evidence.get("reason", "optional external intent evidence could not be loaded")),
                "refs": [external_evidence.get("path", "")],
            }
        )

    tracked_open = 0
    untracked_open = 0
    lower_trust_closeouts = 0
    external_items = external_evidence.get("items", [])
    if isinstance(external_items, list):
        for item in external_items:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id", "")).strip()
            if not item_id:
                continue
            refs = _reference_locations(token=item_id, surface_index=surface_index)
            active_refs = [ref for ref in refs if _is_live_planning_tracking_ref(ref)]
            status = str(item.get("status", "")).strip().lower()
            if status == "open":
                if active_refs:
                    tracked_open += 1
                else:
                    untracked_open += 1
                    signals.append(
                        {
                            "kind": "external_open_untracked",
                            "severity": "warning",
                            "path": external_evidence.get("path", ""),
                            "message": (
                                f"Open external planning item {item_id} is not represented in active or candidate checked-in planning state."
                            ),
                            "refs": [external_evidence.get("path", ""), *refs],
                        }
                    )
            elif status == "closed" and str(item.get("planning_residue_expected", "")).strip().lower() == "required" and not refs:
                lower_trust_closeouts += 1
                signals.append(
                    {
                        "kind": "closed_without_planning_residue",
                        "severity": "warning",
                        "path": external_evidence.get("path", ""),
                        "message": (
                            f"Closed external planning item {item_id} has no visible checked-in planning residue; treat closeout trust as lower."
                        ),
                        "refs": [external_evidence.get("path", "")],
                    }
                )

    counts = {
        "internal_dangling_count": len(internal_signals),
        "tracked_external_open_count": tracked_open,
        "untracked_external_open_count": untracked_open,
        "lower_trust_closeout_count": lower_trust_closeouts,
        "attention_count": len(signals),
    }
    recommended_next_action = "No dangling larger intent or lower-trust closeout signals detected."
    if untracked_open:
        recommended_next_action = (
            "Route open external planning items into checked-in active or candidate planning state before treating the repo as quiet."
        )
    elif lower_trust_closeouts:
        recommended_next_action = "Review lower-trust closeout signals before assuming recently closed work is fully evidenced."
    elif internal_signals:
        recommended_next_action = "Restore missing checked-in continuation ownership for partially archived intent."

    refs = [
        ".agentic-workspace/planning/state.toml",
        *([str(external_evidence.get("path", ""))] if external_evidence.get("path") else []),
    ]
    for path in active_execplans:
        relative = str(path.get("path", "")).strip()
        if relative:
            refs.append(relative)
    for item in active_items:
        surface = str(item.get("surface", "")).strip()
        if surface:
            refs.append(surface)

    return {
        "status": "present",
        "rule": (
            "Treat checked-in planning state as primary, then reconcile optional external planning evidence when present to spot dangling larger intent and lower-trust closeout."
        ),
        "primary_owner": ".agentic-workspace/planning/state.toml",
        "primary_owner_rule": (
            "Active items, candidate lanes, execplans, and archived continuation residue remain the product-owned planning truth."
        ),
        "external_evidence": {
            "status": external_evidence.get("status", "absent"),
            "path": external_evidence.get("path", ""),
            "kind": external_evidence.get("kind", ""),
            "systems": external_evidence.get("systems", []),
            "item_count": external_evidence.get("item_count", 0),
            "reason": external_evidence.get("reason", ""),
        },
        "counts": counts,
        "signals": signals,
        "recommended_next_action": recommended_next_action,
        "minimal_refs": [ref for ref in refs if ref],
    }


def _finished_work_inspection_contract(*, target_root: Path) -> dict[str, Any]:
    archive_dir = target_root / ".agentic-workspace" / "planning" / "execplans" / "archive"
    evidence = _load_finished_work_evidence(target_root)
    signals: list[dict[str, Any]] = []
    inspections: list[dict[str, Any]] = []
    clearly_landed = 0
    partial = 0
    likely_premature = 0

    archived_paths = (
        [path for path in sorted(archive_dir.glob("*.md")) if path.exists() and path.is_file() and path.name != "README.md"]
        if archive_dir.exists()
        else []
    )
    evidence_items = evidence.get("items", [])

    for path in archived_paths:
        issue_refs = sorted(_execplan_issue_refs(path))
        reopened_by = _finished_work_reopeners(issue_refs=issue_refs, evidence_items=evidence_items)
        closure_check = _execplan_closure_check(path)
        intent_satisfaction = _execplan_intent_satisfaction(path)
        closure_decision = str(closure_check.get("closure decision", "")).strip().lower()
        larger_intent_status = str(closure_check.get("larger-intent status", "")).strip().lower()
        intent_satisfied = str(intent_satisfaction.get("was original intent fully satisfied?", "")).strip().lower()
        classification = "clearly_landed"
        reason = "Archived closeout reports fully satisfied intent and no reopening evidence points back at it."
        if reopened_by:
            classification = "likely_premature_closeout"
            reason = (
                "Optional reopening evidence points back at this archived closeout, so treat the original close decision as lower trust."
            )
            likely_premature += 1
            signals.append(
                {
                    "kind": "likely_premature_closeout",
                    "severity": "warning",
                    "path": path.relative_to(target_root).as_posix(),
                    "message": (
                        f"Archived closeout {path.relative_to(target_root).as_posix()} now has follow-on evidence reopening {', '.join(item['id'] for item in reopened_by)}."
                    ),
                    "refs": [
                        path.relative_to(target_root).as_posix(),
                        *[item["id"] for item in reopened_by],
                    ],
                }
            )
        elif closure_decision == "archive-but-keep-lane-open" or larger_intent_status in {"open", "unfinished"} or intent_satisfied == "no":
            classification = "partial"
            reason = "Archived residue itself says the bounded slice landed while larger intent or required continuation remained open."
            partial += 1
        else:
            clearly_landed += 1
        inspections.append(
            {
                "plan": path.relative_to(target_root).as_posix(),
                "title": _execplan_title(path),
                "classification": classification,
                "closure_decision": closure_check.get("closure decision", ""),
                "larger_intent_status": closure_check.get("larger-intent status", ""),
                "intent_satisfied": intent_satisfaction.get("was original intent fully satisfied?", ""),
                "tracked_refs": issue_refs,
                "reopened_by": reopened_by,
                "reason": reason,
            }
        )

    if evidence.get("status") == "invalid":
        signals.append(
            {
                "kind": "finished_work_evidence_invalid",
                "severity": "warning",
                "path": evidence.get("path", ""),
                "message": str(evidence.get("reason", "optional finished-work evidence could not be loaded")),
                "refs": [evidence.get("path", "")],
            }
        )

    counts = {
        "archived_closeout_count": len(archived_paths),
        "clearly_landed_count": clearly_landed,
        "partial_count": partial,
        "likely_premature_closeout_count": likely_premature,
        "attention_count": len(signals),
    }
    recommended_next_action = "No suspicious finished-work signals detected."
    if likely_premature:
        recommended_next_action = (
            "Inspect archived closeouts flagged by reopening evidence before trusting previously closed lanes as fully landed."
        )
    elif evidence.get("status") == "invalid":
        recommended_next_action = "Repair optional finished-work evidence or remove it so closeout inspection trust is explicit."
    elif partial:
        recommended_next_action = "Previously archived partial-intent lanes are visible; verify their continuation owners before assuming historical work was complete."

    refs = [".agentic-workspace/planning/execplans/archive/"]
    if evidence.get("path"):
        refs.append(str(evidence.get("path", "")))

    return {
        "status": "present",
        "rule": (
            "Inspect archived checked-in closeout residue first, then use optional generic reopening evidence only to lower trust when a supposedly finished lane clearly points back into active follow-on."
        ),
        "primary_owner": ".agentic-workspace/planning/execplans/archive/",
        "primary_owner_rule": (
            "Archived execplans remain the durable closeout evidence; optional reopening evidence may challenge trust but must not replace the archive as source of record."
        ),
        "counts": counts,
        "evidence": {
            "status": evidence.get("status", "absent"),
            "path": evidence.get("path", ""),
            "kind": evidence.get("kind", ""),
            "systems": evidence.get("systems", []),
            "item_count": evidence.get("item_count", 0),
            "reason": evidence.get("reason", ""),
        },
        "signals": signals,
        "inspections": inspections,
        "recommended_next_action": recommended_next_action,
        "minimal_refs": [ref for ref in refs if ref],
    }


def _planning_surface_reference_index(target_root: Path) -> dict[str, str]:
    surface_index: dict[str, str] = {}
    candidate_paths = [
        target_root / PLANNING_STATE_PATH,
        *[
            path
            for path in sorted((target_root / ".agentic-workspace" / "planning" / "execplans").glob("*.md"))
            if path.name not in {"README.md", "TEMPLATE.md"}
        ],
        *[
            path
            for path in sorted((target_root / ".agentic-workspace" / "planning" / "execplans" / "archive").glob("*.md"))
            if path.name != "README.md"
        ],
        *[
            path
            for path in sorted((target_root / ".agentic-workspace" / "planning" / "reviews").glob("*.md"))
            if path.name not in {"README.md", "TEMPLATE.md"}
        ],
    ]
    for path in candidate_paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            surface_index[path.relative_to(target_root).as_posix()] = path.read_text(encoding="utf-8")
        except OSError:
            continue
    return surface_index


def _reference_locations(*, token: str, surface_index: dict[str, str]) -> list[str]:
    return [path for path, text in surface_index.items() if token in text]


def _is_live_planning_tracking_ref(relative_path: str) -> bool:
    if relative_path == ".agentic-workspace/planning/state.toml":
        return True
    return relative_path.startswith(".agentic-workspace/planning/execplans/") and "/archive/" not in relative_path


def _load_external_intent_evidence(target_root: Path) -> dict[str, Any]:
    path = target_root / PLANNING_EXTERNAL_INTENT_EVIDENCE_PATH
    relative_path = PLANNING_EXTERNAL_INTENT_EVIDENCE_PATH.as_posix()
    if not path.exists():
        return {
            "status": "absent",
            "path": relative_path,
            "kind": "planning-external-intent-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": "optional evidence file not present",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "status": "invalid",
            "path": relative_path,
            "kind": "planning-external-intent-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": f"failed to load optional evidence: {exc}",
        }
    if not isinstance(payload, dict) or payload.get("kind") != "planning-external-intent-evidence/v1":
        return {
            "status": "invalid",
            "path": relative_path,
            "kind": "planning-external-intent-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": "optional evidence file does not match planning-external-intent-evidence/v1",
        }
    normalized_items: list[dict[str, Any]] = []
    systems: list[str] = []
    for raw in payload.get("items", []):
        if not isinstance(raw, dict):
            continue
        system = str(raw.get("system", "")).strip()
        item = {
            "system": system,
            "id": str(raw.get("id", "")).strip(),
            "title": str(raw.get("title", "")).strip(),
            "status": str(raw.get("status", "")).strip().lower(),
            "kind": str(raw.get("kind", "")).strip(),
            "parent_id": str(raw.get("parent_id", "")).strip(),
            "planning_residue_expected": str(raw.get("planning_residue_expected", "optional")).strip().lower(),
        }
        if not item["id"]:
            continue
        normalized_items.append(item)
        if system and system not in systems:
            systems.append(system)
    return {
        "status": "loaded",
        "path": relative_path,
        "kind": "planning-external-intent-evidence/v1",
        "systems": systems,
        "item_count": len(normalized_items),
        "items": normalized_items,
        "reason": "",
    }


def _load_finished_work_evidence(target_root: Path) -> dict[str, Any]:
    path = target_root / PLANNING_FINISHED_WORK_EVIDENCE_PATH
    relative_path = PLANNING_FINISHED_WORK_EVIDENCE_PATH.as_posix()
    if not path.exists():
        return {
            "status": "absent",
            "path": relative_path,
            "kind": "planning-finished-work-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": "optional evidence file not present",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "status": "invalid",
            "path": relative_path,
            "kind": "planning-finished-work-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": f"failed to load optional evidence: {exc}",
        }
    if not isinstance(payload, dict) or payload.get("kind") != "planning-finished-work-evidence/v1":
        return {
            "status": "invalid",
            "path": relative_path,
            "kind": "planning-finished-work-evidence/v1",
            "systems": [],
            "item_count": 0,
            "items": [],
            "reason": "optional evidence file does not match planning-finished-work-evidence/v1",
        }
    normalized_items: list[dict[str, Any]] = []
    systems: list[str] = []
    for raw in payload.get("items", []):
        if not isinstance(raw, dict):
            continue
        system = str(raw.get("system", "")).strip()
        item = {
            "system": system,
            "id": str(raw.get("id", "")).strip(),
            "title": str(raw.get("title", "")).strip(),
            "status": str(raw.get("status", "")).strip().lower(),
            "kind": str(raw.get("kind", "")).strip(),
            "reopens": [str(entry).strip() for entry in raw.get("reopens", []) if str(entry).strip()],
            "reason": str(raw.get("reason", "")).strip(),
        }
        if not item["id"]:
            continue
        normalized_items.append(item)
        if system and system not in systems:
            systems.append(system)
    return {
        "status": "loaded",
        "path": relative_path,
        "kind": "planning-finished-work-evidence/v1",
        "systems": systems,
        "item_count": len(normalized_items),
        "items": normalized_items,
        "reason": "",
    }


def _finished_work_reopeners(*, issue_refs: list[str], evidence_items: Any) -> list[dict[str, str]]:
    if not issue_refs or not isinstance(evidence_items, list):
        return []
    reopeners: list[dict[str, str]] = []
    for raw in evidence_items:
        if not isinstance(raw, dict):
            continue
        if str(raw.get("status", "")).strip().lower() != "open":
            continue
        reopens = [str(entry).strip() for entry in raw.get("reopens", []) if str(entry).strip()]
        if not reopens or not any(ref in reopens for ref in issue_refs):
            continue
        reopeners.append(
            {
                "id": str(raw.get("id", "")).strip(),
                "title": str(raw.get("title", "")).strip(),
                "system": str(raw.get("system", "")).strip(),
            }
        )
    return reopeners


def _internal_continuation_signals(*, target_root: Path, roadmap_lanes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    archive_dir = target_root / ".agentic-workspace" / "planning" / "execplans" / "archive"
    if not archive_dir.exists():
        return []
    signals: list[dict[str, Any]] = []
    for path in sorted(archive_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        closure = _execplan_closure_check(path)
        if str(closure.get("closure decision", "")).strip().lower() != "archive-but-keep-lane-open":
            continue
        label = _roadmap_continuation_label(path)
        required = _execplan_required_continuation(path)
        owner_surface = str(required.get("owner surface", "")).strip()
        if label and _roadmap_has_lane(roadmap_lanes=roadmap_lanes, label=label):
            continue
        if owner_surface and owner_surface not in {"none", "n/a"} and (target_root / owner_surface).exists():
            continue
        relative = path.relative_to(target_root).as_posix()
        signals.append(
            {
                "kind": "missing_internal_continuation_owner",
                "severity": "warning",
                "path": relative,
                "message": (f"Archived partial-intent plan {relative} no longer has a visible checked-in continuation owner."),
                "refs": [relative, owner_surface or ".agentic-workspace/planning/state.toml"],
            }
        )
    return signals


def _roadmap_has_lane(*, roadmap_lanes: list[dict[str, Any]], label: str) -> bool:
    tokens = _label_tokens(label)
    if not tokens:
        return False
    for lane in roadmap_lanes:
        if not isinstance(lane, dict):
            continue
        identity = " ".join(str(value).strip().lower() for value in (lane.get("title", ""), lane.get("id", "")) if str(value).strip())
        if all(token in identity for token in tokens):
            return True
    return False


def _ownership_review(target_root: Path) -> dict[str, Any]:
    manifest_path = target_root / ".agentic-workspace" / "OWNERSHIP.toml"
    if not manifest_path.exists():
        manifest_path = Path(__file__).resolve().with_name("_ownership.toml")

    with manifest_path.open("rb") as handle:
        ledger = tomllib.load(handle)

    module_roots = [
        {
            "module": str(entry.get("module", "")).strip(),
            "path": str(entry.get("path", "")).strip(),
            "ownership": str(entry.get("ownership", "")).strip(),
            "uninstall_policy": str(entry.get("uninstall_policy", "")).strip(),
        }
        for entry in ledger.get("module_roots", [])
        if isinstance(entry, dict)
    ]
    authority_surfaces = [
        {
            "concern": str(entry.get("concern", "")).strip(),
            "surface": str(entry.get("surface", "")).strip(),
            "owner": str(entry.get("owner", "")).strip(),
            "ownership": str(entry.get("ownership", "")).strip(),
            "authority": str(entry.get("authority", "")).strip(),
            "summary": str(entry.get("summary", "")).strip(),
        }
        for entry in ledger.get("authority_surfaces", [])
        if isinstance(entry, dict)
    ]
    fences = [
        {
            "name": str(entry.get("name", "")).strip(),
            "file": str(entry.get("file", "")).strip(),
            "start": str(entry.get("start", "")).strip(),
            "end": str(entry.get("end", "")).strip(),
            "ownership": str(entry.get("ownership", "")).strip(),
            "uninstall_policy": str(entry.get("uninstall_policy", "")).strip(),
        }
        for entry in ledger.get("fences", [])
        if isinstance(entry, dict)
    ]
    package_owned_roots = [entry["path"] for entry in module_roots if entry.get("path")]
    repo_owned_surfaces = [
        entry["surface"] for entry in authority_surfaces if entry.get("ownership") == "repo_owned" and entry.get("surface")
    ]
    module_managed_surfaces = [
        entry["surface"] for entry in authority_surfaces if entry.get("ownership") == "module_managed" and entry.get("surface")
    ]
    shared_package_surfaces = [
        entry["surface"]
        for entry in authority_surfaces
        if entry.get("ownership") in {"workspace_shared", "module_managed"} and entry.get("surface")
    ]
    repo_specific_package_surfaces = [
        entry["surface"] for entry in authority_surfaces if entry.get("ownership") == "repo_specific_package_owned" and entry.get("surface")
    ]
    minimal_repo_hook = next((f"{entry['file']}#agentic-workspace:workflow" for entry in fences if entry.get("file")), "")
    return {
        "status": "present",
        "package_owned_roots": package_owned_roots,
        "repo_owned_surfaces": repo_owned_surfaces,
        "module_managed_surfaces": module_managed_surfaces,
        "shared_package_surfaces": shared_package_surfaces,
        "repo_specific_package_surfaces": repo_specific_package_surfaces,
        "managed_fences": fences,
        "minimal_repo_hook": minimal_repo_hook,
        "authority_surfaces": authority_surfaces,
    }


def _roadmap_candidate_lanes(roadmap_path: Path) -> list[dict[str, Any]]:
    lane_lines = _section_lines(_read_lines(roadmap_path), "Candidate Lanes")
    if not lane_lines:
        return []

    lanes: list[dict[str, Any]] = []
    current_block: list[str] = []
    for line in lane_lines:
        if re.match(r"^\s*-\s+", line):
            if current_block:
                lane = _parse_candidate_lane_block(current_block)
                if lane is not None:
                    lanes.append(lane)
            current_block = [line]
            continue
        if current_block:
            current_block.append(line)
    if current_block:
        lane = _parse_candidate_lane_block(current_block)
        if lane is not None:
            lanes.append(lane)
    return lanes


def _parse_candidate_lane_block(lines: list[str]) -> dict[str, Any] | None:
    if not lines:
        return None
    first = re.sub(r"^\s*-\s+", "", lines[0]).strip()
    if not first:
        return None

    fields: dict[str, str] = {}
    if ":" in first:
        key, value = first.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    else:
        fields["lane"] = first

    for line in lines[1:]:
        match = re.match(r"^\s+([^:]+):\s*(.*)\s*$", line)
        if not match:
            continue
        fields[match.group(1).strip().lower()] = match.group(2).strip()

    title = fields.get("lane", "").strip()
    if not title:
        return None

    lane_id = fields.get("id", "").strip()
    priority = fields.get("priority", "").strip()
    outcome = fields.get("outcome", "").strip()
    issues = [item.strip() for item in re.split(r"\s*,\s*", fields.get("issues", "")) if item.strip()]
    reason = fields.get("why now", "").strip() or fields.get("why later", "").strip()
    promotion_signal = fields.get("promotion signal", "").strip()
    suggested_first_slice = fields.get("suggested first slice", "").strip()

    return {
        "id": lane_id,
        "title": title,
        "priority": priority,
        "issues": issues,
        "outcome": outcome,
        "reason": reason,
        "promotion_signal": promotion_signal,
        "suggested_first_slice": suggested_first_slice,
    }


def _roadmap_candidates(roadmap_path: Path) -> list[dict[str, str]]:
    lanes = _roadmap_candidate_lanes(roadmap_path)
    if lanes:
        return [
            {
                "priority": str(lane.get("priority", "")),
                "summary": str(lane.get("title", "")),
            }
            for lane in lanes
        ]

    candidate_lines = _section_lines(_read_lines(roadmap_path), "Next Candidate Queue")
    candidates: list[dict[str, str]] = []
    for line in candidate_lines:
        if not re.match(r"^\s*-\s+", line):
            continue
        text = re.sub(r"^\s*-\s+", "", line).strip()
        if not text:
            continue
        priority_match = re.match(r"^Priority\s+(\d+)\s*:\s*(.*)$", text, re.IGNORECASE)
        if priority_match:
            candidates.append(
                {
                    "priority": priority_match.group(1),
                    "summary": priority_match.group(2).strip(),
                }
            )
            continue
        candidates.append({"priority": "", "summary": text})
    return candidates


def _active_intent_contract(
    *,
    target_root: Path,
    active_items: list[dict[str, str]],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if len(active_execplans) != 1 or len(active_items) > 1:
        return {
            "status": "unavailable",
            "reason": "requires exactly one active execplan and at most one active TODO item",
        }

    active_item = active_items[0] if active_items else None
    active_execplan_path = active_execplans[0]["path"].strip()
    surface = active_item.get("surface", "").strip() if active_item else active_execplan_path
    plan_path = _resolve_execplan_path(target_root, surface) or _resolve_execplan_path(target_root, active_execplan_path)
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active planning state does not resolve to a live execplan path",
        }

    delegated_judgment = _execplan_delegated_judgment(plan_path)
    requested_outcome = delegated_judgment.get("requested outcome", "").strip()
    hard_constraints = delegated_judgment.get("hard constraints", "").strip()
    agent_may_decide = delegated_judgment.get("agent may decide locally", "").strip()
    escalate_when = delegated_judgment.get("escalate when", "").strip()
    if not requested_outcome or not hard_constraints or not agent_may_decide or not escalate_when:
        return {
            "status": "unavailable",
            "reason": "active execplan is missing delegated-judgment fields",
        }

    touched_scope = _extract_section_bullets(plan_path, "Touched Paths")
    proof_expectations = _extract_section_bullets(plan_path, "Validation Commands")
    required_tools = [tool for tool in _extract_section_bullets(plan_path, "Required Tools") if tool.lower() not in {"none", "none."}]
    minimal_refs = _dedupe(
        [
            ".agentic-workspace/planning/state.toml",
            plan_path.relative_to(target_root).as_posix(),
            *([surface] if surface else []),
        ]
    )
    return {
        "status": "present",
        "todo_item": {
            "id": active_item.get("id", "").strip() if active_item else "",
            "surface": surface,
            "why_now": active_item.get("why_now", "").strip() if active_item else "",
        },
        "intent": {
            "requested_outcome": requested_outcome,
            "hard_constraints": hard_constraints,
            "agent_may_decide": agent_may_decide,
            "escalate_when": escalate_when,
        },
        "touched_scope": touched_scope,
        "proof_expectations": proof_expectations,
        "tool_verification": {
            "status": "required-tools-declared" if required_tools else "unspecified",
            "required_tools": required_tools,
            "rule": "If a required tool is unavailable, stop or escalate before attempting the task.",
        },
        "minimal_refs": minimal_refs,
    }


def _active_resumable_contract(
    *,
    target_root: Path,
    active_contract: dict[str, Any],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if active_contract.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present active intent contract",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for resumable-contract extraction",
        }

    milestone = _execplan_active_milestone(plan_path)
    current_next_action = _extract_section_bullets(plan_path, "Immediate Next Action")
    completion_criteria = _extract_section_bullets(plan_path, "Completion Criteria")
    blockers = [item for item in _extract_section_bullets(plan_path, "Blockers") if item.lower() != "none."]
    if not current_next_action or not completion_criteria:
        return {
            "status": "unavailable",
            "reason": "active execplan is missing current next action or completion criteria",
        }

    return {
        "status": "present",
        "current_next_action": current_next_action[0],
        "active_milestone": {
            "id": milestone.get("id", "").strip(),
            "status": milestone.get("status", "").strip(),
            "scope": milestone.get("scope", "").strip(),
            "ready": milestone.get("ready", "").strip(),
            "blocked": milestone.get("blocked", "").strip(),
        },
        "completion_criteria": completion_criteria,
        "proof_expectations": list(active_contract["proof_expectations"]),
        "tool_verification": dict(active_contract["tool_verification"]),
        "escalate_when": active_contract["intent"]["escalate_when"],
        "blockers": blockers,
        "minimal_refs": list(active_contract["minimal_refs"]),
    }


def _canonical_planning_record(
    *,
    target_root: Path,
    active_contract: dict[str, Any],
    resumable_contract: dict[str, Any],
) -> dict[str, Any]:
    if active_contract.get("status") != "present" or resumable_contract.get("status") != "present":
        reasons: list[str] = []
        if active_contract.get("status") != "present":
            reasons.append(active_contract.get("reason", "active contract unavailable"))
        if resumable_contract.get("status") != "present":
            reasons.append(resumable_contract.get("reason", "resumable contract unavailable"))
        return {
            "status": "unavailable",
            "reason": "; ".join(_dedupe(reasons)),
        }

    todo_item = active_contract.get("todo_item", {})
    active_milestone = resumable_contract.get("active_milestone", {})
    minimal_refs = list(resumable_contract.get("minimal_refs", []))
    plan_path = _resolve_execplan_path(target_root, str(todo_item.get("surface", "")).strip() or active_milestone.get("id", ""))
    proof_report: dict[str, str] = {}
    intent_satisfaction: dict[str, str] = {}
    closure_check: dict[str, str] = {}
    intent_interpretation: dict[str, str] = {}
    execution_bounds: dict[str, str] = {}
    stop_conditions: dict[str, str] = {}
    execution_run: dict[str, str] = {}
    finished_run_review: dict[str, str] = {}
    if plan_path is not None:
        proof_report = _execplan_proof_report(plan_path)
        intent_satisfaction = _execplan_intent_satisfaction(plan_path)
        closure_check = _execplan_closure_check(plan_path)
        intent_interpretation = _execplan_intent_interpretation(plan_path)
        execution_bounds = _execplan_execution_bounds(plan_path)
        stop_conditions = _execplan_stop_conditions(plan_path)
        execution_run = _execplan_execution_run(plan_path)
        finished_run_review = _execplan_finished_run_review(plan_path)
    continuation_owner = str(todo_item.get("surface", "")).strip()
    if not continuation_owner and minimal_refs:
        continuation_owner = minimal_refs[-1]
    return {
        "status": "present",
        "task": {
            "id": str(todo_item.get("id", "")).strip() or str(active_milestone.get("id", "")).strip(),
            "surface": str(todo_item.get("surface", "")).strip(),
            "status": str(active_milestone.get("status", "")).strip(),
        },
        "requested_outcome": str(active_contract["intent"]["requested_outcome"]).strip(),
        "hard_constraints": str(active_contract["intent"]["hard_constraints"]).strip(),
        "agent_may_decide": str(active_contract["intent"]["agent_may_decide"]).strip(),
        "next_action": str(resumable_contract["current_next_action"]).strip(),
        "proof_expectations": list(resumable_contract.get("proof_expectations", [])),
        "proof_report": proof_report,
        "intent_satisfaction": intent_satisfaction,
        "closure_check": closure_check,
        "intent_interpretation": intent_interpretation,
        "execution_bounds": execution_bounds,
        "stop_conditions": stop_conditions,
        "execution_run": execution_run,
        "finished_run_review": finished_run_review,
        "tool_verification": dict(resumable_contract.get("tool_verification", {})),
        "escalate_when": str(resumable_contract.get("escalate_when", "")).strip(),
        "continuation_owner": continuation_owner,
        "touched_scope": list(active_contract.get("touched_scope", [])),
        "completion_criteria": list(resumable_contract.get("completion_criteria", [])),
        "blockers": list(resumable_contract.get("blockers", [])),
        "minimal_refs": minimal_refs,
    }


def _active_follow_through_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if planning_record.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present planning record",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for follow-through extraction",
        }

    follow_through = _execplan_iterative_follow_through(plan_path)
    required_fields = {
        "what this slice enabled",
        "intentionally deferred",
        "discovered implications",
        "proof achieved now",
        "validation still needed",
        "next likely slice",
    }
    if not required_fields.issubset(follow_through):
        return {
            "status": "unavailable",
            "reason": "active execplan is missing iterative follow-through fields",
        }

    intent_continuity = _execplan_intent_continuity(plan_path)
    larger_intended_outcome = intent_continuity.get("larger intended outcome", "").strip()
    continuation_surface = intent_continuity.get("continuation surface", "").strip()
    if not larger_intended_outcome:
        return {
            "status": "unavailable",
            "reason": "active execplan is missing larger intended outcome for iterative follow-through",
        }

    minimal_refs = _dedupe(
        [
            *planning_record.get("minimal_refs", []),
            *([continuation_surface] if continuation_surface and continuation_surface.lower() != "none" else []),
        ]
    )
    return {
        "status": "present",
        "larger_intended_outcome": larger_intended_outcome,
        "continuation_surface": continuation_surface,
        "what_this_slice_enabled": follow_through.get("what this slice enabled", "").strip(),
        "intentionally_deferred": follow_through.get("intentionally deferred", "").strip(),
        "discovered_implications": follow_through.get("discovered implications", "").strip(),
        "proof_achieved_now": follow_through.get("proof achieved now", "").strip(),
        "validation_still_needed": follow_through.get("validation still needed", "").strip(),
        "next_likely_slice": follow_through.get("next likely slice", "").strip(),
        "minimal_refs": minimal_refs,
    }


def _active_intent_interpretation_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if planning_record.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present planning record",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for intent-interpretation extraction",
        }

    interpretation = _execplan_intent_interpretation(plan_path)
    required_fields = {
        "literal request",
        "inferred intended outcome",
        "chosen concrete what",
        "interpretation distance",
        "review guidance",
    }
    if not required_fields.issubset(interpretation):
        return {
            "status": "unavailable",
            "reason": "active execplan is missing intent-interpretation fields",
        }

    minimal_refs = _dedupe(
        [
            *planning_record.get("minimal_refs", []),
            ".agentic-workspace/docs/execution-flow-contract.md",
        ]
    )
    return {
        "status": "present",
        "literal_request": interpretation.get("literal request", "").strip(),
        "inferred_intended_outcome": interpretation.get("inferred intended outcome", "").strip(),
        "chosen_concrete_what": interpretation.get("chosen concrete what", "").strip(),
        "interpretation_distance": interpretation.get("interpretation distance", "").strip(),
        "review_guidance": interpretation.get("review guidance", "").strip(),
        "minimal_refs": minimal_refs,
    }


def _active_context_budget_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if planning_record.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present planning record",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for context-budget extraction",
        }

    context_budget = _execplan_context_budget(plan_path)
    required_fields = {
        "live working set",
        "recoverable later",
        "externalize before shift",
        "pre-work memory pull",
        "tiny resumability note",
        "context-shift triggers",
    }
    if not required_fields.issubset(context_budget):
        return {
            "status": "unavailable",
            "reason": "active execplan is missing context-budget fields",
        }

    minimal_refs = _dedupe(
        [
            *planning_record.get("minimal_refs", []),
            ".agentic-workspace/docs/context-budget-contract.md",
        ]
    )
    interaction_cost_rule = (
        "Prefer the smallest live bundle that can still finish the current bounded step, "
        "externalize proof/review/continuation residue before shedding context, and reload only on explicit shift triggers."
    )
    return {
        "status": "present",
        "live_working_set": context_budget.get("live working set", "").strip(),
        "recoverable_later": context_budget.get("recoverable later", "").strip(),
        "externalize_before_shift": context_budget.get("externalize before shift", "").strip(),
        "pre_work_memory_pull": context_budget.get("pre-work memory pull", "").strip(),
        "tiny_resumability_note": context_budget.get("tiny resumability note", "").strip(),
        "context_shift_triggers": context_budget.get("context-shift triggers", "").strip(),
        "interaction_cost_rule": interaction_cost_rule,
        "resume_rule": (
            "Use the tiny resumability note plus explicit minimal refs instead of broad rereads when returning after an interruption or tool switch."
        ),
        "minimal_refs": minimal_refs,
    }


def _active_execution_run_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if planning_record.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present planning record",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for execution-run extraction",
        }

    execution_run = _execplan_execution_run(plan_path)
    required_fields = {
        "run status",
        "executor",
        "handoff source",
        "what happened",
        "scope touched",
        "changed surfaces",
        "validations run",
        "result for continuation",
        "next step",
    }
    if not required_fields.issubset(execution_run):
        return {
            "status": "unavailable",
            "reason": "active execplan is missing execution-run fields",
        }

    minimal_refs = _dedupe(
        [
            *planning_record.get("minimal_refs", []),
            ".agentic-workspace/docs/execution-flow-contract.md",
        ]
    )
    return {
        "status": "present",
        "run_status": execution_run.get("run status", "").strip(),
        "executor": execution_run.get("executor", "").strip(),
        "handoff_source": execution_run.get("handoff source", "").strip(),
        "what_happened": execution_run.get("what happened", "").strip(),
        "scope_touched": execution_run.get("scope touched", "").strip(),
        "changed_surfaces": execution_run.get("changed surfaces", "").strip(),
        "validations_run": execution_run.get("validations run", "").strip(),
        "result_for_continuation": execution_run.get("result for continuation", "").strip(),
        "next_step": execution_run.get("next step", "").strip(),
        "minimal_refs": minimal_refs,
    }


def _active_finished_run_review_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_execplans: list[dict[str, str]],
    execution_run_contract: dict[str, Any],
    intent_interpretation_contract: dict[str, Any],
) -> dict[str, Any]:
    if planning_record.get("status") != "present" or len(active_execplans) != 1:
        return {
            "status": "unavailable",
            "reason": "requires one active execplan with a present planning record",
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for finished-run review extraction",
        }

    review = _execplan_finished_run_review(plan_path)
    required_fields = {
        "review status",
        "scope respected",
        "proof status",
        "intent served",
        "misinterpretation risk",
        "follow-on decision",
    }
    if not required_fields.issubset(review):
        return {
            "status": "unavailable",
            "reason": "active execplan is missing finished-run review fields",
        }

    minimal_refs = _dedupe(
        [
            *planning_record.get("minimal_refs", []),
            *(execution_run_contract.get("minimal_refs", []) if execution_run_contract.get("status") == "present" else []),
            *(intent_interpretation_contract.get("minimal_refs", []) if intent_interpretation_contract.get("status") == "present" else []),
            ".agentic-workspace/docs/reporting-contract.md",
        ]
    )
    return {
        "status": "present",
        "review_status": review.get("review status", "").strip(),
        "scope_respected": review.get("scope respected", "").strip(),
        "proof_status": review.get("proof status", "").strip(),
        "intent_served": review.get("intent served", "").strip(),
        "misinterpretation_risk": review.get("misinterpretation risk", "").strip(),
        "follow_on_decision": review.get("follow-on decision", "").strip(),
        "minimal_refs": minimal_refs,
    }


def _active_hierarchy_contract(
    *,
    target_root: Path,
    planning_record: dict[str, Any],
    active_contract: dict[str, Any],
    resumable_contract: dict[str, Any],
    follow_through_contract: dict[str, Any],
    context_budget_contract: dict[str, Any],
    roadmap_lanes: list[dict[str, Any]],
    active_execplans: list[dict[str, str]],
) -> dict[str, Any]:
    if (
        planning_record.get("status") != "present"
        or active_contract.get("status") != "present"
        or resumable_contract.get("status") != "present"
        or follow_through_contract.get("status") != "present"
        or context_budget_contract.get("status") != "present"
        or len(active_execplans) != 1
    ):
        reasons: list[str] = []
        for contract in (planning_record, active_contract, resumable_contract, follow_through_contract, context_budget_contract):
            if contract.get("status") != "present":
                reasons.append(contract.get("reason", "required planning contract unavailable"))
        if len(active_execplans) != 1:
            reasons.append("requires exactly one active execplan")
        return {
            "status": "unavailable",
            "reason": "; ".join(_dedupe(reasons)),
        }

    plan_path = _resolve_execplan_path(target_root, active_execplans[0]["path"])
    if plan_path is None or not plan_path.exists():
        return {
            "status": "unavailable",
            "reason": "active execplan path is not available for hierarchy extraction",
        }

    intent_continuity = _execplan_intent_continuity(plan_path)
    required_continuation = _execplan_required_continuation(plan_path)
    active_milestone = resumable_contract.get("active_milestone", {})
    todo_item = active_contract.get("todo_item", {})

    parent_lane_ref = intent_continuity.get("parent lane", "").strip()
    parent_lane = _resolve_parent_lane(parent_lane_ref=parent_lane_ref, roadmap_lanes=roadmap_lanes)
    continuation_surface = str(follow_through_contract.get("continuation_surface", "")).strip()
    required_owner_surface = required_continuation.get("owner surface", "").strip()
    required_follow_on = required_continuation.get("required follow-on for the larger intended outcome", "").strip()
    owner_surface = required_owner_surface or continuation_surface or planning_record.get("continuation_owner", "")
    minimal_refs = _dedupe(
        [
            *follow_through_contract.get("minimal_refs", []),
            *([".agentic-workspace/planning/state.toml"] if parent_lane.get("id") or roadmap_lanes else []),
        ]
    )
    return {
        "status": "present",
        "current_layer": "execution",
        "parent_lane": parent_lane,
        "active_chunk": {
            "todo_id": str(todo_item.get("id", "")).strip() or str(active_milestone.get("id", "")).strip(),
            "todo_surface": str(todo_item.get("surface", "")).strip(),
            "execplan": plan_path.relative_to(target_root).as_posix(),
            "milestone_id": str(active_milestone.get("id", "")).strip(),
            "milestone_status": str(active_milestone.get("status", "")).strip(),
            "milestone_scope": str(active_milestone.get("scope", "")).strip(),
            "next_action": str(resumable_contract.get("current_next_action", "")).strip(),
        },
        "near_term_queue": summary_todo_queue(target_root=target_root),
        "next_likely_chunk": str(follow_through_contract.get("next_likely_slice", "")).strip(),
        "proof_state": {
            "proof_achieved_now": str(follow_through_contract.get("proof_achieved_now", "")).strip(),
            "validation_still_needed": str(follow_through_contract.get("validation_still_needed", "")).strip(),
            "proof_expectations": list(resumable_contract.get("proof_expectations", [])),
        },
        "context_shift": {
            "live_working_set": str(context_budget_contract.get("live_working_set", "")).strip(),
            "externalize_before_shift": str(context_budget_contract.get("externalize_before_shift", "")).strip(),
            "tiny_resumability_note": str(context_budget_contract.get("tiny_resumability_note", "")).strip(),
            "triggers": str(context_budget_contract.get("context_shift_triggers", "")).strip(),
        },
        "required_continuation": {
            "larger_intended_outcome": str(follow_through_contract.get("larger_intended_outcome", "")).strip(),
            "slice_completes_larger_outcome": intent_continuity.get("this slice completes the larger intended outcome", "").strip(),
            "continuation_surface": continuation_surface,
            "required_follow_on": required_follow_on,
            "owner_surface": required_owner_surface,
            "activation_trigger": required_continuation.get("activation trigger", "").strip(),
        },
        "closure_check": _execplan_closure_check(plan_path),
        "routing": {
            "current_owner": str(planning_record.get("continuation_owner", "")).strip(),
            "follow_on_owner": str(owner_surface).strip(),
            "review_queue": ".agentic-workspace/planning/reviews/",
        },
        "minimal_refs": minimal_refs,
    }


def _active_handoff_contract(
    *,
    planning_record: dict[str, Any],
    hierarchy_contract: dict[str, Any],
    context_budget_contract: dict[str, Any],
    intent_interpretation_contract: dict[str, Any],
) -> dict[str, Any]:
    if planning_record.get("status") != "present":
        return {
            "status": "unavailable",
            "reason": planning_record.get("reason", "requires a present planning record"),
        }

    parent_lane = {}
    if hierarchy_contract.get("status") == "present":
        parent_lane = dict(hierarchy_contract.get("parent_lane", {}))

    return {
        "status": "present",
        "task": dict(planning_record.get("task", {})),
        "parent_lane": parent_lane,
        "requested_outcome": str(planning_record.get("requested_outcome", "")).strip(),
        "hard_constraints": str(planning_record.get("hard_constraints", "")).strip(),
        "agent_may_decide": str(planning_record.get("agent_may_decide", "")).strip(),
        "next_action": str(planning_record.get("next_action", "")).strip(),
        "completion_criteria": list(planning_record.get("completion_criteria", [])),
        "read_first": list(planning_record.get("minimal_refs", [])),
        "owned_write_scope": list(planning_record.get("touched_scope", [])),
        "proof_expectations": list(planning_record.get("proof_expectations", [])),
        "proof_report": dict(planning_record.get("proof_report", {})),
        "intent_satisfaction": dict(planning_record.get("intent_satisfaction", {})),
        "intent_interpretation": dict(intent_interpretation_contract if intent_interpretation_contract.get("status") == "present" else {}),
        "pre_work_memory_pull": str(context_budget_contract.get("pre_work_memory_pull", "")).strip(),
        "execution_bounds": dict(planning_record.get("execution_bounds", {})),
        "stop_conditions": dict(planning_record.get("stop_conditions", {})),
        "tool_verification": dict(planning_record.get("tool_verification", {})),
        "continuation_owner": str(planning_record.get("continuation_owner", "")).strip(),
        "context_budget": dict(context_budget_contract if context_budget_contract.get("status") == "present" else {}),
        "return_with": {
            "execution_run_fields": [
                "run status",
                "executor",
                "handoff source",
                "what happened",
                "scope touched",
                "changed surfaces",
                "validations run",
                "result for continuation",
                "next step",
            ],
            "execution_summary_fields": [
                "outcome delivered",
                "validation confirmed",
                "follow-on routed to",
                "post-work posterity capture",
                "knowledge promoted (memory/docs/config)",
                "resume from",
            ],
            "finished_run_review_fields": [
                "review status",
                "scope respected",
                "proof status",
                "intent served",
                "misinterpretation risk",
                "follow-on decision",
            ],
        },
        "worker_contract": {
            "allowed_execution_methods": [
                "internal delegation",
                "external cli or api",
                "single-agent fallback",
            ],
            "worker_owns_by_default": [
                "bounded implementation inside the owned write scope",
                "narrow validation named by the handoff",
                "checked-in updates inside owned surfaces when explicitly assigned",
                "cleanup and commit only when explicitly assigned and still bounded",
            ],
            "worker_must_not_own_by_default": [
                "roadmap routing",
                "issue closure",
                "lane reshaping",
                "repo-wide policy changes",
            ],
            "stop_when": [
                str(planning_record.get("stop_conditions", {}).get("stop when", "")).strip(),
                str(planning_record.get("stop_conditions", {}).get("escalate when boundary reached", "")).strip(),
                str(planning_record.get("stop_conditions", {}).get("escalate on scope drift", "")).strip(),
                str(planning_record.get("stop_conditions", {}).get("escalate on proof failure", "")).strip(),
                str(planning_record.get("escalate_when", "")).strip(),
                "the task needs broad rereads beyond the explicit read-first refs and owned write scope",
                "the chosen delegation method cannot preserve the checked-in handoff contract",
            ],
        },
    }


def _system_intent_contract_payload() -> dict[str, Any]:
    return {
        "status": "present",
        "canonical_doc": ".agentic-workspace/docs/system-intent-contract.md",
        "rule": (
            "Preserve the larger user or product outcome separately from the bounded slice so later archive, review, and continuation decisions stay honest."
        ),
        "authority_ladder": [
            {
                "layer": "confirmed request or live issue cluster",
                "owns": "the higher-level outcome the repo is actually trying to satisfy",
            },
            {
                "layer": "active execplan delegated judgment and intent continuity",
                "owns": "the bounded slice, hard constraints, and the mapping back to the larger intended outcome",
            },
            {
                "layer": "closure check and required continuation",
                "owns": "whether the slice can archive, whether the larger intent is still open, and where follow-through now lives",
            },
        ],
        "reinterpretation_boundary": {
            "allowed": [
                "tighten means, decomposition, and validation",
                "narrow a first slice when the larger requested outcome remains explicit",
                "route required continuation into one checked-in owner",
            ],
            "must_not": [
                "treat a bounded slice as if it closed the larger intent without explicit evidence",
                "leave required continuation only in drift prose or chat",
                "replace the confirmed outcome with a cheaper substitute silently",
            ],
        },
        "recoverability": {
            "ask_first": [
                "agentic-workspace defaults --section system_intent --format json",
                "agentic-workspace summary --format json",
                "agentic-planning-bootstrap report --format json",
            ],
            "must_answer": [
                "what larger outcome this slice serves",
                "whether the larger outcome is actually closed",
                "where required continuation lives now",
                "what evidence justified the closure decision",
            ],
        },
        "checked_in_execplan_rule": (
            "Keep a checked-in execplan whenever later proof, intent validation, or required continuation would be expensive or ambiguous to reconstruct from chat alone."
        ),
    }


def summary_todo_queue(*, target_root: Path) -> list[dict[str, str]]:
    todo_lines, todo_items = _read_todo_items(target_root / ".agentic-workspace/planning/state.toml")
    del todo_lines
    queue: list[dict[str, str]] = []
    for item in todo_items:
        status = item.fields.get("status", "").strip()
        status_lower = status.lower()
        if not status_lower or status_lower in {"completed", "done", "closed"}:
            continue
        if "in-progress" in status_lower or "active" in status_lower or "ongoing" in status_lower:
            continue
        queue.append(
            {
                "id": item.fields.get("id", "").strip(),
                "surface": item.fields.get("surface", "").strip(),
                "status": status,
                "why_now": item.fields.get("why now", "").strip(),
            }
        )
    return queue


def _resolve_parent_lane(*, parent_lane_ref: str, roadmap_lanes: list[dict[str, Any]]) -> dict[str, str]:
    if parent_lane_ref:
        for lane in roadmap_lanes:
            if parent_lane_ref == lane.get("id", "") or parent_lane_ref == lane.get("title", ""):
                return {
                    "id": str(lane.get("id", "")).strip(),
                    "title": str(lane.get("title", "")).strip(),
                    "priority": str(lane.get("priority", "")).strip(),
                    "issues": ", ".join(lane.get("issues", [])),
                    "source": "roadmap",
                }
        return {
            "id": parent_lane_ref,
            "title": "",
            "priority": "",
            "issues": "",
            "source": "execplan",
        }
    return {
        "id": "",
        "title": "",
        "priority": "",
        "issues": "",
        "source": "unspecified",
    }


def _contract_projection(contract: dict[str, Any], *, view_name: str) -> dict[str, Any]:
    if not contract:
        return {}
    projection = dict(contract)
    projection.setdefault("view_role", "projection")
    projection.setdefault("view", view_name)
    projection.setdefault("view_of", "planning_record")
    return projection


def promote_todo_item_to_execplan(
    item_id: str,
    *,
    target: str | Path | None = None,
    plan_slug: str | None = None,
    dry_run: bool = False,
) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message=f"Promote TODO item '{item_id}' to execplan", dry_run=dry_run)
    todo_path = target_root / ".agentic-workspace/planning/state.toml"
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
    execplan_relative = Path(".agentic-workspace") / "planning" / "execplans" / f"{slug}.md"
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


def _render_inactive_execplan_residue(*, plan_path: Path, target_root: Path) -> str:
    title = _execplan_title(plan_path)
    intent_continuity = _execplan_intent_continuity(plan_path)
    required_continuation = _execplan_required_continuation(plan_path)
    delegated_judgment = _execplan_delegated_judgment(plan_path)
    intent_interpretation = _execplan_intent_interpretation(plan_path)
    execution_bounds = _execplan_execution_bounds(plan_path)
    stop_conditions = _execplan_stop_conditions(plan_path)
    context_budget = _execplan_context_budget(plan_path)
    execution_run = _execplan_execution_run(plan_path)
    finished_run_review = _execplan_finished_run_review(plan_path)
    proof_report = _execplan_proof_report(plan_path)
    intent_satisfaction = _execplan_intent_satisfaction(plan_path)
    closure_check = _execplan_closure_check(plan_path)
    execution_summary = _execplan_execution_summary(plan_path)
    relative = plan_path.relative_to(target_root).as_posix()
    lines = [
        f"# {title}",
        "",
        "Compact inactive-plan residue generated at archive time.",
        "Use git history for superseded active-step detail; keep only the closure, continuation, proof, and cheap-resume residue here.",
        "",
        "## Origin",
        "",
        f"- Archived from: {relative}",
        "",
        "## Intent Continuity",
        "",
    ]
    for key in (
        "larger intended outcome",
        "this slice completes the larger intended outcome",
        "continuation surface",
        "parent lane",
    ):
        if key in intent_continuity:
            lines.append(f"- {key.title()}: {intent_continuity[key]}")
    lines.extend(["", "## Required Continuation", ""])
    for key in (
        "required follow-on for the larger intended outcome",
        "owner surface",
        "activation trigger",
    ):
        if key in required_continuation:
            lines.append(f"- {key.title()}: {required_continuation[key]}")
    lines.extend(["", "## Delegated Judgment", ""])
    for key in (
        "requested outcome",
        "hard constraints",
        "agent may decide locally",
        "escalate when",
    ):
        if key in delegated_judgment:
            lines.append(f"- {key.title()}: {delegated_judgment[key]}")
    if intent_interpretation:
        lines.extend(["", "## Intent Interpretation", ""])
        for key in (
            "literal request",
            "inferred intended outcome",
            "chosen concrete what",
            "interpretation distance",
            "review guidance",
        ):
            if key in intent_interpretation:
                lines.append(f"- {key.title()}: {intent_interpretation[key]}")
    if execution_bounds:
        lines.extend(["", "## Execution Bounds", ""])
        for key in (
            "allowed paths",
            "max changed files",
            "required validation commands",
            "ask-before-refactor threshold",
            "stop before touching",
        ):
            if key in execution_bounds:
                lines.append(f"- {key.title()}: {execution_bounds[key]}")
    if stop_conditions:
        lines.extend(["", "## Stop Conditions", ""])
        for key in (
            "stop when",
            "escalate when boundary reached",
            "escalate on scope drift",
            "escalate on proof failure",
        ):
            if key in stop_conditions:
                lines.append(f"- {key.title()}: {stop_conditions[key]}")
    if context_budget:
        lines.extend(["", "## Context Budget", ""])
        for key in (
            "live working set",
            "recoverable later",
            "externalize before shift",
            "tiny resumability note",
            "context-shift triggers",
        ):
            if key in context_budget:
                lines.append(f"- {key.title()}: {context_budget[key]}")
    if execution_run:
        lines.extend(["", "## Execution Run", ""])
        for key in (
            "run status",
            "executor",
            "handoff source",
            "what happened",
            "scope touched",
            "validations run",
            "result for continuation",
            "next step",
        ):
            if key in execution_run:
                lines.append(f"- {key.title()}: {execution_run[key]}")
    if finished_run_review:
        lines.extend(["", "## Finished-Run Review", ""])
        for key in (
            "review status",
            "scope respected",
            "proof status",
            "intent served",
            "misinterpretation risk",
            "follow-on decision",
        ):
            if key in finished_run_review:
                lines.append(f"- {key.title()}: {finished_run_review[key]}")
    lines.extend(["", "## Proof Report", ""])
    for key in (
        "validation proof",
        "proof achieved now",
        'evidence for "proof achieved" state',
    ):
        if key in proof_report:
            lines.append(f"- {key[0].upper() + key[1:]}: {proof_report[key]}")
    lines.extend(["", "## Intent Satisfaction", ""])
    for key in (
        "original intent",
        "was original intent fully satisfied?",
        "evidence of intent satisfaction",
        "unsolved intent passed to",
    ):
        if key in intent_satisfaction:
            lines.append(f"- {key[0].upper() + key[1:]}: {intent_satisfaction[key]}")
    lines.extend(["", "## Closure Check", ""])
    for key in (
        "slice status",
        "larger-intent status",
        "closure decision",
        "why this decision is honest",
        "evidence carried forward",
        "reopen trigger",
    ):
        if key in closure_check:
            lines.append(f"- {key[0].upper() + key[1:]}: {closure_check[key]}")
    lines.extend(["", "## Execution Summary", ""])
    for key in (
        "outcome delivered",
        "validation confirmed",
        "follow-on routed to",
        "post-work posterity capture",
        "knowledge promoted (memory/docs/config)",
        "resume from",
    ):
        if key in execution_summary:
            lines.append(f"- {key[0].upper() + key[1:]}: {execution_summary[key]}")
    lines.append("")
    return "\n".join(lines)


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

    archive_dir = target_root / ".agentic-workspace" / "planning" / "execplans" / "archive"
    if archive_dir in plan_path.parents:
        result.add("manual review", plan_path, "execplan is already archived")
        return result

    status = _execplan_status(plan_path)
    if status not in {"completed", "done", "closed"}:
        result.add("manual review", plan_path, "archive requires the active milestone status to be completed/done/closed")
        return result
    intent_continuity = _execplan_intent_continuity(plan_path)
    completes_larger_outcome = intent_continuity.get("this slice completes the larger intended outcome", "").strip().lower()
    continuation_surface = intent_continuity.get("continuation surface", "").strip()
    required_continuation = _execplan_required_continuation(plan_path)
    required_follow_on = required_continuation.get("required follow-on for the larger intended outcome", "").strip().lower()
    required_owner_surface = required_continuation.get("owner surface", "").strip()
    activation_trigger = required_continuation.get("activation trigger", "").strip()
    delegated_judgment = _execplan_delegated_judgment(plan_path)
    requested_outcome = delegated_judgment.get("requested outcome", "").strip()
    hard_constraints = delegated_judgment.get("hard constraints", "").strip()
    agent_may_decide = delegated_judgment.get("agent may decide locally", "").strip()
    escalate_when = delegated_judgment.get("escalate when", "").strip()
    execution_summary = _execplan_execution_summary(plan_path)
    outcome_delivered = execution_summary.get("outcome delivered", "").strip()
    validation_confirmed = execution_summary.get("validation confirmed", "").strip()
    follow_on_routed_to = execution_summary.get("follow-on routed to", "").strip()
    post_work_posterity_capture = execution_summary.get("post-work posterity capture", "").strip()
    resume_from = execution_summary.get("resume from", "").strip()
    proof_report = _execplan_proof_report(plan_path)
    validation_proof = proof_report.get("validation proof", "").strip()
    proof_achieved_now = proof_report.get("proof achieved now", "").strip()
    proof_evidence = proof_report.get('evidence for "proof achieved" state', "").strip()
    intent_satisfaction = _execplan_intent_satisfaction(plan_path)
    original_intent = intent_satisfaction.get("original intent", "").strip()
    fully_satisfied = intent_satisfaction.get("was original intent fully satisfied?", "").strip().lower()
    satisfaction_evidence = intent_satisfaction.get("evidence of intent satisfaction", "").strip()
    unsolved_intent = intent_satisfaction.get("unsolved intent passed to", "").strip()
    closure_check = _execplan_closure_check(plan_path)
    slice_status = closure_check.get("slice status", "").strip().lower()
    larger_intent_status = closure_check.get("larger-intent status", "").strip().lower()
    closure_decision = closure_check.get("closure decision", "").strip().lower()
    closure_reason = closure_check.get("why this decision is honest", "").strip()
    closure_evidence = closure_check.get("evidence carried forward", "").strip()
    reopen_trigger = closure_check.get("reopen trigger", "").strip()
    validation_commands = _execplan_validation_commands(plan_path)
    if completes_larger_outcome == "no" and (not continuation_surface or continuation_surface.lower() in {"none", "n/a"}):
        result.warnings.append(
            {
                "warning_class": "archive_missing_intent_continuity",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": ("Execplan leaves the larger intended outcome incomplete but does not name the continuation surface."),
            }
        )
        result.add(
            "manual review",
            plan_path,
            "larger intended outcome is unfinished; set Continuation surface before archiving",
        )
        return result
    if completes_larger_outcome == "no" and required_follow_on != "yes":
        result.warnings.append(
            {
                "warning_class": "archive_missing_required_follow_on",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Execplan leaves the larger intended outcome incomplete but does not record required follow-on explicitly.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "larger intended outcome is unfinished; record Required Continuation before archiving",
        )
        return result
    if required_follow_on == "yes" and (
        not required_owner_surface
        or required_owner_surface.lower() in {"none", "n/a"}
        or not activation_trigger
        or activation_trigger.lower() in {"none", "n/a"}
    ):
        result.warnings.append(
            {
                "warning_class": "archive_missing_required_follow_on",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Execplan records required follow-on but does not name both the owner surface and activation trigger.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "required follow-on needs both owner surface and activation trigger before archiving",
        )
        return result
    if not requested_outcome or not hard_constraints or not agent_may_decide or not escalate_when:
        result.warnings.append(
            {
                "warning_class": "archive_missing_delegated_judgment",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": (
                    "Execplan is missing one or more delegated-judgment fields needed "
                    "to preserve intended outcome and escalation boundaries."
                ),
            }
        )
        result.add(
            "manual review",
            plan_path,
            "fill `Delegated Judgment` before archiving",
        )
        return result
    if not outcome_delivered or outcome_delivered.lower() in {"pending", "not completed yet", "todo", "tbd"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_execution_summary",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing an explicit delivered-outcome summary.",
            }
        )
        result.add("manual review", plan_path, "fill `Execution Summary` with the delivered outcome before archiving")
        return result
    if not validation_confirmed or validation_confirmed.lower() in {"pending", "tbd", "todo"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_execution_summary",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing an explicit validation summary.",
            }
        )
        result.add("manual review", plan_path, "fill `Execution Summary` with the validation confirmation before archiving")
        return result
    if not follow_on_routed_to or follow_on_routed_to.lower() in {"pending", "tbd", "todo", "none yet"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_execution_summary",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing an explicit follow-on routing summary.",
            }
        )
        result.add("manual review", plan_path, "fill `Execution Summary` with the follow-on routing before archiving")
        return result
    if not post_work_posterity_capture or post_work_posterity_capture.lower() in {"pending", "tbd", "todo", "none yet"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_execution_summary",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": (
                    "Completed execplan is missing an explicit post-work posterity capture summary "
                    "covering what should survive this slice and where it belongs."
                ),
            }
        )
        result.add(
            "manual review",
            plan_path,
            "fill `Execution Summary` with what should survive this slice and where it belongs before archiving",
        )
        return result
    if not resume_from or resume_from.lower() in {"pending", "tbd", "todo", "current milestone"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_execution_summary",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing an explicit resume cue.",
            }
        )
        result.add("manual review", plan_path, "fill `Execution Summary` with the post-archive resume cue before archiving")
        return result
    if not validation_proof or not proof_achieved_now or not proof_evidence:
        result.warnings.append(
            {
                "warning_class": "archive_missing_proof_report",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing a complete proof report.",
            }
        )
        result.add("manual review", plan_path, "fill `Proof Report` with validation proof and evidence before archiving")
        return result
    if not original_intent or fully_satisfied not in {"yes", "true", "no", "false"} or not satisfaction_evidence:
        result.warnings.append(
            {
                "warning_class": "archive_missing_intent_satisfaction",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing a complete intent satisfaction report.",
            }
        )
        result.add("manual review", plan_path, "fill `Intent Satisfaction` with satisfied intent evidence before archiving")
        return result
    if (
        not slice_status
        or not larger_intent_status
        or not closure_decision
        or not closure_reason
        or not closure_evidence
        or not reopen_trigger
    ):
        result.warnings.append(
            {
                "warning_class": "archive_missing_closure_check",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Completed execplan is missing a complete Closure Check.",
            }
        )
        result.add("manual review", plan_path, "fill `Closure Check` before archiving")
        return result
    if slice_status not in {"complete", "completed", "bounded slice complete"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_closure_check",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Closure Check does not mark the bounded slice as complete.",
            }
        )
        result.add("manual review", plan_path, "mark the bounded slice complete in `Closure Check` before archiving")
        return result
    if closure_decision in {"keep-active", "stay-active", "continue-active"}:
        result.warnings.append(
            {
                "warning_class": "archive_missing_closure_check",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Closure Check still says this plan should remain active.",
            }
        )
        result.add("manual review", plan_path, "keep the plan active until `Closure Check` allows archive")
        return result
    if closure_decision == "archive-and-close":
        if fully_satisfied not in {"yes", "true"} or larger_intent_status not in {"closed", "complete", "completed"}:
            result.warnings.append(
                {
                    "warning_class": "archive_intent_not_fully_satisfied",
                    "path": plan_path.relative_to(target_root).as_posix(),
                    "message": "Archive-and-close requires explicit larger-intent closure evidence.",
                }
            )
            result.add("manual review", plan_path, "record larger-intent closure honestly before using `archive-and-close`")
            return result
        if unsolved_intent and unsolved_intent.lower() not in {"none", "n/a", "none yet"}:
            result.warnings.append(
                {
                    "warning_class": "archive_intent_not_fully_satisfied",
                    "path": plan_path.relative_to(target_root).as_posix(),
                    "message": "Archive-and-close cannot leave unsolved intent routed elsewhere.",
                }
            )
            result.add("manual review", plan_path, "remove unsolved intent routing or switch to `archive-but-keep-lane-open`")
            return result
    elif closure_decision == "archive-but-keep-lane-open":
        if fully_satisfied not in {"no", "false"} or larger_intent_status not in {"open", "partial", "unfinished"}:
            result.warnings.append(
                {
                    "warning_class": "archive_intent_not_fully_satisfied",
                    "path": plan_path.relative_to(target_root).as_posix(),
                    "message": "Archive-but-keep-lane-open requires explicit evidence that the larger intent remains open.",
                }
            )
            result.add("manual review", plan_path, "align `Intent Satisfaction` and `Closure Check` with the partial-intent decision")
            return result
        if not unsolved_intent or unsolved_intent.lower() in {"none", "n/a", "none yet"}:
            result.warnings.append(
                {
                    "warning_class": "archive_missing_required_follow_on",
                    "path": plan_path.relative_to(target_root).as_posix(),
                    "message": "Partial-intent archive must name the checked-in owner that now carries the unsolved intent.",
                }
            )
            result.add("manual review", plan_path, "record the routed unsolved intent before archiving a partial slice")
            return result
    else:
        result.warnings.append(
            {
                "warning_class": "archive_missing_closure_check",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": f"Closure Check uses an unsupported closure decision: {closure_decision}.",
            }
        )
        result.add("manual review", plan_path, "use `archive-and-close` or `archive-but-keep-lane-open` in `Closure Check`")
        return result
    if _execplan_needs_reference_sweep(plan_path) and not _validation_has_reference_sweep(validation_commands):
        result.warnings.append(
            {
                "warning_class": "archive_missing_closure_check",
                "path": plan_path.relative_to(target_root).as_posix(),
                "message": "Rename/refactor-like completed work is missing a stale-reference sweep in Validation Commands.",
            }
        )
        result.add(
            "manual review",
            plan_path,
            "add a stale-reference sweep to `Validation Commands` before archiving rename/refactor-like work",
        )
        return result
    cleanup_todo_lines: list[str] | None = None
    todo_ref_items = _todo_referencing_items(target_root / ".agentic-workspace/planning/state.toml", plan_path, target_root)
    if apply_cleanup and todo_ref_items:
        cleanup_todo_lines = _remove_todo_items(target_root / ".agentic-workspace/planning/state.toml", todo_ref_items)
        for item in todo_ref_items:
            result.add(
                "would update" if dry_run else "updated",
                target_root / ".agentic-workspace/planning/state.toml",
                (f"remove TODO item '{item.item_id}' while archiving its plan"),
            )
    elif apply_cleanup:
        compact_cleanup = _cleanup_compact_todo_archive_followup(
            target_root / ".agentic-workspace/planning/state.toml", plan_path, target_root
        )
        if compact_cleanup["changed"]:
            cleanup_todo_lines = compact_cleanup["text"].splitlines()
            for detail in compact_cleanup["details"]:
                result.add("would update" if dry_run else "updated", target_root / ".agentic-workspace/planning/state.toml", detail)

    remaining_todo_refs = [] if cleanup_todo_lines is not None else todo_ref_items
    blocking_todo_refs = [item for item in remaining_todo_refs if _normalize_status(item.fields.get("status", "")) != "completed"]
    if blocking_todo_refs:
        for item in blocking_todo_refs:
            item_id = item.item_id or "?"
            result.warnings.append(
                {
                    "warning_class": "archive_blocked_by_todo_reference",
                    "path": ".agentic-workspace/planning/state.toml",
                    "message": f"TODO item '{item_id}' still references this execplan; remove or redirect it before archiving.",
                }
            )
            result.add(
                "manual review",
                target_root / ".agentic-workspace/planning/state.toml",
                f"TODO item '{item_id}' still references this execplan",
            )
        return result

    destination = archive_dir / plan_path.name
    if destination.exists():
        result.add("manual review", destination, "archive destination already exists")
        return result

    cleanup_roadmap_state = _cleanup_state_roadmap_followup(target_root, plan_path)
    if cleanup_roadmap_state["changed"] and apply_cleanup:
        action_kind = "would update" if dry_run else "updated"
        for detail in cleanup_roadmap_state["details"]:
            result.add(action_kind, target_root / PLANNING_STATE_PATH, detail)
    elif cleanup_roadmap_state["changed"] or cleanup_roadmap_state["note"]:
        note = (
            cleanup_roadmap_state["note"]
            or ".agentic-workspace/planning/state.toml has cleanup-ready roadmap residue tied to the archived plan."
        )
        result.warnings.append(
            {
                "warning_class": "roadmap_archive_followup",
                "path": PLANNING_STATE_PATH.as_posix(),
                "message": note,
            }
        )
        result.add("suggested fix", target_root / PLANNING_STATE_PATH, note)

    legacy_roadmap_path = target_root / "ROADMAP.md"
    cleanup_legacy_roadmap = _cleanup_roadmap_archive_followup(legacy_roadmap_path, plan_path)
    if cleanup_legacy_roadmap["changed"] and apply_cleanup:
        action_kind = "would update" if dry_run else "updated"
        for detail in cleanup_legacy_roadmap["details"]:
            result.add(action_kind, legacy_roadmap_path, detail)
    elif cleanup_legacy_roadmap["changed"] or cleanup_legacy_roadmap["note"]:
        note = cleanup_legacy_roadmap["note"] or "ROADMAP.md has cleanup-ready residue tied to the archived plan."
        result.warnings.append(
            {
                "warning_class": "roadmap_archive_followup",
                "path": "ROADMAP.md",
                "message": note,
            }
        )
        result.add("suggested fix", legacy_roadmap_path, note)

    if dry_run:
        result.add("would move", destination, f"archive {plan_path.relative_to(target_root).as_posix()}")
        return result

    rendered_archive = _render_inactive_execplan_residue(plan_path=plan_path, target_root=target_root)
    archive_dir.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered_archive, encoding="utf-8")
    plan_path.unlink()
    if cleanup_todo_lines is not None:
        (target_root / ".agentic-workspace/planning/state.toml").write_text("\n".join(cleanup_todo_lines).rstrip() + "\n", encoding="utf-8")
    if cleanup_roadmap_state["changed"] and apply_cleanup:
        _write_state_to_toml(target_root, cleanup_roadmap_state["state"])
    if cleanup_legacy_roadmap["changed"] and apply_cleanup and cleanup_legacy_roadmap["text"] is not None:
        legacy_roadmap_path.write_text(cleanup_legacy_roadmap["text"], encoding="utf-8")
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
        target_relative = relative
        if target_relative.name.endswith(".template.md"):
            target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")
        destination = target_root / target_relative
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
    target_relative = relative
    if target_relative.name.endswith(".template.md"):
        target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")
    destination = target_root / target_relative
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
        "todo_missing_execplan_linkage": "Create or promote this item to a .agentic-workspace/planning/execplans plan and point Surface at it.",
        "todo_plan_required_hint": "This direct task has grown beyond direct-task shape; scaffold an execplan for it.",
        "todo_broken_surface_reference": "Repair Surface so it points at a live .agentic-workspace/planning/execplans path, or remove the stale item.",
        "execplan_structure_drift": (
            "Restore the current template sections, especially Intent Continuity, Required Continuation, "
            "Delegated Judgment, Active Milestone, and Execution Summary, so the plan matches the newer contract; "
            "compare the plan with .agentic-workspace/planning/execplans/README.md and .agentic-workspace/docs/execution-flow-contract.md."
        ),
        "execplan_immediate_next_action_drift": "Reduce Immediate Next Action to one concrete next step.",
        "execplan_readiness_drift": "Set Ready/Blocked explicitly so the active milestone can be resumed without re-deriving state.",
        "execplan_log_drift": "Compress the drift log into short decision notes or archive the completed plan.",
        "execplan_notebook_drift": "Strip status-journal residue out of the plan and keep only the current execution contract.",
        "execplan_under_specified": (
            "Fill in the missing contract sections so the plan can survive upgrades without extra chat context; "
            "compare the plan with .agentic-workspace/planning/execplans/README.md and .agentic-workspace/docs/execution-flow-contract.md."
        ),
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
    count = 0
    for relative in _installed_surface_files():
        target_relative = relative
        if target_relative.name.endswith(".template.md"):
            target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")
        if (target_root / target_relative).exists():
            count += 1
    required_present = count
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
    target_relative = relative
    if target_relative.name.endswith(".template.md"):
        target_relative = target_relative.with_name(target_relative.name[:-12] + ".md")
    destination = target_root / target_relative
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


def _read_todo_items_from_lines(lines: list[str]) -> list[TodoItem]:
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
            if index != start and row.startswith("## "):
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
    return items


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


def _extract_kv_fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^\s*-\s*([^:]+):\s*(.*)\s*$", line)
        if match:
            fields[match.group(1).strip().lower()] = match.group(2).strip()
    return fields


def _extract_section_bullets(path: Path, heading: str) -> list[str]:
    values: list[str] = []
    for line in _section_lines(_read_lines(path), heading):
        match = re.match(r"^\s*-\s+(.*\S)\s*$", line)
        if match:
            values.append(match.group(1).strip())
    return values


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _read_todo_items(path: Path) -> tuple[list[str], list[TodoItem]]:
    lines = _read_lines(path)
    return lines, _read_todo_items_from_lines(lines)


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
        "## Intent Continuity\n\n"
        f"- Larger intended outcome: {goal}\n"
        "- This slice completes the larger intended outcome: yes\n"
        "- Continuation surface: none\n\n"
        "## Required Continuation\n\n"
        "- Required follow-on for the larger intended outcome: no\n"
        "- Owner surface: none\n"
        "- Activation trigger: none\n\n"
        "## Iterative Follow-Through\n\n"
        "- What this slice enabled: none yet\n"
        "- Intentionally deferred: none\n"
        "- Discovered implications: none yet\n"
        "- Proof achieved now: pending\n"
        "- Validation still needed: current milestone validation remains pending\n"
        "- Next likely slice: continue the current milestone until the completion criteria are met\n\n"
        "## Delegated Judgment\n\n"
        f"- Requested outcome: {goal}\n"
        "- Hard constraints: Keep scope bounded to the promoted TODO item and its stated touched paths.\n"
        "- Agent may decide locally: Bounded decomposition, touched-path narrowing, "
        "validation tightening, and plan-local residue routing.\n"
        "- Escalate when: A better-looking fix changes the requested outcome, owned "
        "surface, time horizon, or meaningful validation story.\n\n"
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
        "## Required Tools\n\n"
        "- None.\n\n"
        "## Completion Criteria\n\n"
        f"- {completion}\n\n"
        "## Execution Summary\n\n"
        "- Outcome delivered: not completed yet\n"
        "- Validation confirmed: pending\n"
        "- Follow-on routed to: none yet\n"
        "- Resume from: current milestone\n\n"
        "## Drift Log\n\n"
        f"- {date.today().isoformat()}: Promoted from TODO direct-task shape into an execplan.\n"
    )


def _surface_execplan_reference(surface_value: str) -> str | None:
    inline_path_match = re.search(r".agentic-workspace/planning/execplans/[A-Za-z0-9._/\-]+\.md", surface_value)
    if inline_path_match:
        return inline_path_match.group(0)
    markdown_target = re.search(r"\]\(([^)]+)\)", surface_value)
    if markdown_target:
        target_match = re.search(r".agentic-workspace/planning/execplans/[A-Za-z0-9._/\-]+\.md", markdown_target.group(1))
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
    direct = target_root / ".agentic-workspace" / "planning" / "execplans" / normalized
    if direct.exists():
        return direct.resolve()
    archive = target_root / ".agentic-workspace" / "planning" / "execplans" / "archive" / normalized
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


def _execplan_intent_continuity(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Intent Continuity"))


def _execplan_required_continuation(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Required Continuation"))


def _execplan_iterative_follow_through(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Iterative Follow-Through"))


def _execplan_delegated_judgment(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Delegated Judgment"))


def _execplan_intent_interpretation(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Intent Interpretation"))


def _execplan_execution_bounds(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Execution Bounds"))


def _execplan_stop_conditions(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Stop Conditions"))


def _execplan_context_budget(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Context Budget"))


def _execplan_execution_run(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Execution Run"))


def _execplan_finished_run_review(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Finished-Run Review"))


def _execplan_active_milestone(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Active Milestone"))


def _execplan_execution_summary(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Execution Summary"))


def _execplan_proof_report(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Proof Report"))


def _execplan_intent_satisfaction(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Intent Satisfaction"))


def _execplan_closure_check(path: Path) -> dict[str, str]:
    lines = _read_lines(path)
    return _extract_kv_fields(_section_lines(lines, "Closure Check"))


def _execplan_title(path: Path) -> str:
    for line in _read_lines(path):
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").title()


def _execplan_issue_refs(path: Path) -> set[str]:
    tokens = set(re.findall(r"(?<![A-Za-z0-9_])(?:#[0-9]+|[A-Z][A-Z0-9]+-\d+)(?![A-Za-z0-9_])", path.read_text(encoding="utf-8")))
    return {token.strip() for token in tokens if token.strip()}


def _execplan_validation_commands(path: Path) -> list[str]:
    return _extract_section_bullets(path, "Validation Commands")


def _execplan_needs_reference_sweep(path: Path) -> bool:
    lines = _read_lines(path)
    relevant = [
        *_section_lines(lines, "Goal"),
        *_section_lines(lines, "Active Milestone"),
        *_section_lines(lines, "Touched Paths"),
        *_section_lines(lines, "Execution Summary"),
    ]
    text = "\n".join(relevant).lower()
    return any(token in text for token in ("rename", "renamed", "refactor", "refactored", "move", "moved", "retire", "retired"))


def _validation_has_reference_sweep(commands: list[str]) -> bool:
    lowered = "\n".join(command.lower() for command in commands)
    return any(token in lowered for token in ("rg ", "ripgrep", "grep "))


def _todo_referencing_items(todo_path: Path, plan_path: Path, target_root: Path) -> list[TodoItem]:
    if todo_path.name == "state.toml":
        state = _read_state_from_toml(target_root)
        if state and isinstance(state.get("todo"), dict):
            relative = plan_path.relative_to(target_root).as_posix()
            matches: list[TodoItem] = []
            for bucket in ("active_items", "queued_items"):
                for raw in state.get("todo", {}).get(bucket, []):
                    if not isinstance(raw, dict):
                        continue
                    if _surface_execplan_reference(str(raw.get("surface", ""))) != relative:
                        continue
                    fields = {str(key): str(value) for key, value in raw.items()}
                    matches.append(TodoItem(fields=fields, field_order=list(fields.keys()), start=0, end=0))
            return matches
    _, items = _read_todo_items(todo_path)
    relative = plan_path.relative_to(target_root).as_posix()
    matches: list[TodoItem] = []
    for item in items:
        if _surface_execplan_reference(item.fields.get("surface", "")) == relative:
            matches.append(item)
    return matches


def _remove_todo_items(todo_path: Path, items_to_remove: list[TodoItem]) -> list[str]:
    if todo_path.name == "state.toml":
        target_root = todo_path.parents[2]
        state = _read_state_from_toml(target_root)
        if state and isinstance(state.get("todo"), dict):
            item_ids = {item.item_id for item in items_to_remove if item.item_id}
            if not item_ids:
                return _read_lines(todo_path)
            todo_state = state.setdefault("todo", {})
            for bucket in ("active_items", "queued_items"):
                raw_items = todo_state.get(bucket, [])
                if not isinstance(raw_items, list):
                    continue
                todo_state[bucket] = [item for item in raw_items if not (isinstance(item, dict) and str(item.get("id", "")) in item_ids)]
            return _state_to_toml_lines(state)
    lines, _ = _read_todo_items(todo_path)
    indexes_to_remove: set[int] = set()
    for item in items_to_remove:
        indexes_to_remove.update(range(item.start, item.end))
        if item.end < len(lines) and lines[item.end].strip() == "":
            indexes_to_remove.add(item.end)

    filtered_lines = [line for index, line in enumerate(lines) if index not in indexes_to_remove]
    while filtered_lines and filtered_lines[-1] == "":
        filtered_lines.pop()
    restored = _restore_todo_empty_state(filtered_lines)
    if not _read_todo_items_from_lines(restored):
        restored = _restore_todo_default_action(restored)
    return restored


def _restore_todo_empty_state(lines: list[str]) -> list[str]:
    for heading in ("Now", "Next"):
        lines = _restore_todo_empty_state_for_heading(lines, heading)
    return lines


def _restore_todo_default_action(lines: list[str]) -> list[str]:
    heading_index = next((index for index, line in enumerate(lines) if line.strip().lower() == "## action"), -1)
    if heading_index < 0:
        return lines
    section_end = len(lines)
    for index in range(heading_index + 1, len(lines)):
        if lines[index].startswith("## "):
            section_end = index
            break
    replacement = [
        "",
        "- Promote the next bounded candidate only when fresh repeated friction or explicit maintainer choice justifies activation.",
    ]
    return lines[: heading_index + 1] + replacement + lines[section_end:]


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
    stop_tokens = {"plan", "lane", "slice", "tranche", "candidate", "native"}
    return [
        token
        for token in re.split(r"[^a-z0-9]+", plan_path.stem.lower())
        if len(token) >= 4 and not token.isdigit() and token not in stop_tokens
    ]


def _label_tokens(value: str | None) -> list[str]:
    if not value:
        return []
    return [token for token in re.split(r"[^a-z0-9]+", value.lower()) if len(token) >= 4 and not token.isdigit()]


def _roadmap_continuation_label(plan_path: Path) -> str | None:
    continuation_surface = _execplan_intent_continuity(plan_path).get("continuation surface", "").strip()
    match = re.search(r"`?roadmap\.md`?\s+candidate(?:\s+lane)?\s+`?([^`]+?)`?$", continuation_surface, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _cleanup_roadmap_archive_followup(roadmap_path: Path, plan_path: Path) -> dict[str, Any]:
    if not roadmap_path.exists():
        return {"changed": False, "text": None, "details": [], "note": None}

    lines = _read_lines(roadmap_path)
    tokens = _plan_stem_tokens(plan_path)
    continuation_label = _roadmap_continuation_label(plan_path)
    details: list[str] = []
    changed = False

    lines, handoff_removed = _cleanup_roadmap_section(
        lines,
        "Active Handoff",
        tokens,
        empty_line="- No active handoff right now.",
        preserve_label=None,
    )
    if handoff_removed:
        changed = True
        details.append("compress Active Handoff residue tied to the archived plan")

    lines, queue_removed = _cleanup_roadmap_section(
        lines,
        "Next Candidate Queue",
        tokens,
        empty_line=None,
        preserve_label=continuation_label,
    )
    if queue_removed:
        changed = True
        details.append("remove archived-plan candidate residue from Next Candidate Queue")

    lines, lane_removed = _cleanup_roadmap_section(
        lines,
        "Candidate Lanes",
        tokens,
        empty_line=None,
        preserve_label=continuation_label,
    )
    if lane_removed:
        changed = True
        details.append("remove archived-plan candidate residue from Candidate Lanes")

    if not changed:
        return {"changed": False, "text": None, "details": [], "note": None}
    return {
        "changed": True,
        "text": "\n".join(lines).rstrip() + "\n",
        "details": details,
        "note": None,
    }


def _cleanup_state_roadmap_followup(target_root: Path, plan_path: Path) -> dict[str, Any]:
    state = _read_state_from_toml(target_root)
    if not state:
        return {"changed": False, "state": None, "details": [], "note": None}

    roadmap = state.get("roadmap")
    if not isinstance(roadmap, dict):
        return {"changed": False, "state": None, "details": [], "note": None}

    tokens = _plan_stem_tokens(plan_path)
    continuation_label = _roadmap_continuation_label(plan_path)
    preserved_tokens = set(_label_tokens(continuation_label))
    changed = False
    details: list[str] = []

    lanes = roadmap.get("lanes", [])
    if isinstance(lanes, list):
        kept_lanes: list[dict[str, Any]] = []
        lane_removed = False
        for lane in lanes:
            if not isinstance(lane, dict):
                kept_lanes.append(lane)
                continue
            lane_identity = " ".join(
                str(value).strip().lower() for value in (lane.get("title", ""), lane.get("id", "")) if str(value).strip()
            )
            if preserved_tokens and all(token in lane_identity for token in preserved_tokens):
                kept_lanes.append(lane)
                continue
            if tokens and any(token in lane_identity for token in tokens):
                lane_removed = True
                continue
            kept_lanes.append(lane)
        if lane_removed:
            roadmap["lanes"] = kept_lanes
            changed = True
            details.append("remove archived-plan candidate residue from roadmap lanes")

    candidates = roadmap.get("candidates", [])
    if isinstance(candidates, list):
        kept_candidates: list[dict[str, Any]] = []
        candidate_removed = False
        for candidate in candidates:
            if not isinstance(candidate, dict):
                kept_candidates.append(candidate)
                continue
            summary = str(candidate.get("summary", "")).strip().lower()
            if preserved_tokens and all(token in summary for token in preserved_tokens):
                kept_candidates.append(candidate)
                continue
            if tokens and any(token in summary for token in tokens):
                candidate_removed = True
                continue
            kept_candidates.append(candidate)
        if candidate_removed:
            roadmap["candidates"] = kept_candidates
            changed = True
            details.append("remove archived-plan candidate residue from roadmap summaries")

    if not changed:
        return {"changed": False, "state": None, "details": [], "note": None}
    return {"changed": True, "state": state, "details": details, "note": None}


def _cleanup_roadmap_section(
    lines: list[str],
    heading: str,
    tokens: list[str],
    *,
    empty_line: str | None,
    preserve_label: str | None,
) -> tuple[list[str], bool]:
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
    preserved_tokens = _label_tokens(preserve_label)
    if heading.lower() == "candidate lanes":
        blocks: list[list[str]] = []
        current_block: list[str] = []
        for line in section:
            if re.match(r"^\s*-\s+", line):
                if current_block:
                    blocks.append(current_block)
                current_block = [line]
            elif current_block:
                current_block.append(line)
            else:
                kept_lines.append(line)
        if current_block:
            blocks.append(current_block)

        for block in blocks:
            lane = _parse_candidate_lane_block(block) or {}
            lane_identity = " ".join(
                value for value in (str(lane.get("title", "")).strip(), str(lane.get("id", "")).strip()) if value
            ).lower()
            if preserved_tokens and all(token in lane_identity for token in preserved_tokens):
                kept_lines.extend(block)
                continue
            if tokens and any(token in lane_identity for token in tokens):
                removed = True
                continue
            kept_lines.extend(block)
    else:
        for line in section:
            if not re.match(r"^\s*-\s+", line):
                kept_lines.append(line)
                continue
            lowered = line.lower()
            if preserved_tokens and all(token in lowered for token in preserved_tokens):
                kept_lines.append(line)
                continue
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


def _read_state_from_toml(target_root: Path) -> dict[str, Any] | None:
    state_path = target_root / PLANNING_STATE_PATH
    if not state_path.exists():
        return None

    try:
        with state_path.open("rb") as f:
            return tomllib.load(f)
    except Exception:
        return None


def _write_state_to_toml(target_root: Path, state: dict[str, Any]) -> None:
    state_path = target_root / PLANNING_STATE_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("\n".join(_state_to_toml_lines(state)), encoding="utf-8")


def _state_to_toml_lines(state: dict[str, Any]) -> list[str]:
    lines = []
    if "todo" in state:
        lines.append("[todo]")
        for key in ["active_items", "queued_items"]:
            if key in state["todo"]:
                items = state["todo"][key]
                if not items:
                    lines.append(f"{key} = []")
                else:
                    lines.append(f"{key} = [")
                    for item in items:
                        item_str = ", ".join(f"{k} = {json.dumps(v)}" for k, v in item.items())
                        lines.append(f"  {{ {item_str} }},")
                    lines.append("]")
        lines.append("")

    if "roadmap" in state:
        lines.append("[roadmap]")
        for key in ["lanes", "candidates"]:
            if key in state["roadmap"]:
                items = state["roadmap"][key]
                if not items:
                    lines.append(f"{key} = []")
                else:
                    lines.append(f"{key} = [")
                    for item in items:
                        item_str = ", ".join(f"{k} = {json.dumps(v)}" for k, v in item.items())
                        lines.append(f"  {{ {item_str} }},")
                    lines.append("]")
        lines.append("")
    return lines


def _ensure_state_toml_exists(target_root: Path, *, overwrite: bool = False) -> None:
    """Ensure a baseline state.toml exists in the managed planning root."""
    state_path = target_root / PLANNING_STATE_PATH
    if state_path.exists() and not overwrite:
        return

    state = {
        "todo": {
            "active_items": [],
            "queued_items": [],
        },
        "roadmap": {
            "lanes": [],
            "candidates": [],
        },
    }
    _write_state_to_toml(target_root, state)


def _is_managed_compatibility_view(path: Path) -> bool:
    if not path.exists():
        return False
    return _COMPATIBILITY_VIEW_NOTICE in path.read_text(encoding="utf-8")


def _remove_generated_planning_views(target_root: Path, *, result: InstallResult | None = None) -> None:
    for relative in (
        Path("TODO.md"),
        Path("ROADMAP.md"),
        Path(".agentic-workspace/planning/TODO.md"),
        Path(".agentic-workspace/planning/ROADMAP.md"),
    ):
        path = target_root / relative
        if _is_managed_compatibility_view(path):
            if result is not None:
                result.add(
                    "manual review",
                    path,
                    "managed compatibility view detected; delete manually if no longer needed",
                )


def _migrate_legacy_planning_surfaces(target_root: Path, *, force: bool = False) -> bool:
    todo_path = target_root / "TODO.md"
    roadmap_path = target_root / "ROADMAP.md"
    state_path = target_root / PLANNING_STATE_PATH

    if state_path.exists() and not force:
        return False

    if not todo_path.exists() and not roadmap_path.exists():
        return False

    is_todo_compat_view = _is_managed_compatibility_view(todo_path)
    is_roadmap_compat_view = _is_managed_compatibility_view(roadmap_path)
    todo_owned = is_todo_compat_view
    roadmap_owned = is_roadmap_compat_view

    # These filenames are common in repositories. Only auto-migrate/delete files that
    # carry the managed compatibility marker.
    if not todo_owned and not roadmap_owned:
        return False

    # Conflict detection: look for headers we don't recognize
    # Whitelist expanded based on repo-specific findings
    known_todo_headers = {"active queue", "next candidate queue", "completed tasks", "abandoned queue", "purpose", "now", "next"}
    known_roadmap_headers = {
        "candidate lanes",
        "next candidate queue",
        "purpose",
        "scope",
        "github issue intake",
        "active handoff",
        "reopen conditions",
        "promotion rules",
    }

    guideline_sections = {"github issue intake", "scope", "reopen conditions", "promotion rules"}

    extracted_guidelines = []

    def extract_sections(p: Path, known: set[str], guidelines: set[str]) -> None:
        if not p.exists():
            return
        c = p.read_text(encoding="utf-8")
        if _COMPATIBILITY_VIEW_NOTICE in c:
            return
        headers = re.findall(r"^##\s+(.*)$", c, re.MULTILINE)
        unknown = [h.strip() for h in headers if h.strip().lower() not in known]
        if unknown:
            raise ValueError(
                f"Migration conflict in {p.name}: found unknown sections {unknown}. "
                "These may contain custom user notes or non-standard work. "
                "Please migrate them manually to state.toml or remove them from the root before continuing."
            )

        # Extract guideline sections
        for h in headers:
            h_clean = h.strip()
            if h_clean.lower() in guidelines:
                section_content = _section_lines(c.splitlines(), h_clean)
                extracted_guidelines.append(f"## {h_clean}\n\n" + "\n".join(section_content))

    if todo_owned:
        extract_sections(todo_path, known_todo_headers, guideline_sections)
    if roadmap_owned:
        extract_sections(roadmap_path, known_roadmap_headers, guideline_sections)

    if extracted_guidelines:
        process_path = target_root / "docs" / "planning-process.md"
        process_path.parent.mkdir(parents=True, exist_ok=True)
        process_path.write_text("# Planning Process Guidelines\n\n" + "\n\n".join(extracted_guidelines) + "\n", encoding="utf-8")

    # Read TODO.md
    _, todo_items = _read_todo_items(todo_path) if todo_owned and todo_path.exists() and not is_todo_compat_view else ([], [])

    # Read ROADMAP.md
    roadmap_lanes = _roadmap_candidate_lanes(roadmap_path) if roadmap_owned and roadmap_path.exists() and not is_roadmap_compat_view else []
    roadmap_candidates = _roadmap_candidates(roadmap_path) if roadmap_owned and roadmap_path.exists() and not is_roadmap_compat_view else []

    # Construct state
    active_items = []
    queued_items = []
    for item in todo_items:
        status = item.fields.get("status", "").lower()
        if any(kw in status for kw in ["active", "in-progress", "ongoing"]):
            active_items.append(
                {"id": item.fields.get("id", ""), "surface": item.fields.get("surface", ""), "why_now": item.fields.get("why now", "")}
            )
        else:
            queued_items.append(
                {
                    "id": item.fields.get("id", ""),
                    "surface": item.fields.get("surface", ""),
                    "why_now": item.fields.get("why now", ""),
                    "status": item.fields.get("status", ""),
                }
            )

    state = {
        "todo": {
            "active_items": active_items,
            "queued_items": queued_items,
        },
        "roadmap": {
            "lanes": roadmap_lanes,
            "candidates": roadmap_candidates,
        },
    }

    _write_state_to_toml(target_root, state)

    # Keep root files until a human confirms deletion. Filenames like TODO.md and
    # ROADMAP.md are common and should never be removed implicitly during upgrade.

    return True
