from __future__ import annotations

import json
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

PROJECT_MARKERS = ("pyproject.toml", "package.json", "Cargo.toml", ".hg")
AGENT_ROOT_MARKERS = (Path("AGENTS.md"), Path("memory"))
VERSION_PATH = Path("memory/system/VERSION.md")
WORKFLOW_PATH = Path("memory/system/WORKFLOW.md")
AGENTS_PATH = Path("AGENTS.md")
MANIFEST_PATH = Path("memory/manifest.toml")
AUDIT_SCRIPT_PATH = Path("scripts/check/check_memory_freshness.py")
BOOTSTRAP_VERSION = 18
BUNDLED_SKILLS_ROOT = Path("skills")
BOOTSTRAP_WORKSPACE_ROOT = Path("memory/bootstrap")

CURRENT_MEMORY_BASELINE = (
    Path("memory/current/project-state.md"),
    Path("memory/current/task-context.md"),
)
BOOTSTRAP_WORKSPACE_FILES = (
    Path("memory/bootstrap/README.md"),
    Path("memory/bootstrap/skills/install/SKILL.md"),
    Path("memory/bootstrap/skills/install/agents/openai.yaml"),
    Path("memory/bootstrap/skills/populate/SKILL.md"),
    Path("memory/bootstrap/skills/populate/agents/openai.yaml"),
    Path("memory/bootstrap/skills/upgrade/SKILL.md"),
    Path("memory/bootstrap/skills/upgrade/agents/openai.yaml"),
    Path("memory/bootstrap/skills/cleanup/SKILL.md"),
    Path("memory/bootstrap/skills/cleanup/agents/openai.yaml"),
)
CORE_PAYLOAD_SKILL_FILES = (
    Path("memory/skills/README.md"),
    Path("memory/skills/memory-capture/SKILL.md"),
    Path("memory/skills/memory-capture/agents/openai.yaml"),
    Path("memory/skills/memory-hygiene/SKILL.md"),
    Path("memory/skills/memory-hygiene/agents/openai.yaml"),
    Path("memory/skills/memory-refresh/SKILL.md"),
    Path("memory/skills/memory-refresh/agents/openai.yaml"),
    Path("memory/skills/memory-router/SKILL.md"),
    Path("memory/skills/memory-router/agents/openai.yaml"),
)
PAYLOAD_REQUIRED_FILES = (
    AGENTS_PATH,
    Path("memory/index.md"),
    MANIFEST_PATH,
    Path("memory/system/SKILLS.md"),
    Path("memory/system/WORKFLOW.md"),
    Path("memory/current/project-state.md"),
    Path("memory/current/task-context.md"),
    Path("memory/domains/README.md"),
    Path("memory/invariants/README.md"),
    Path("memory/runbooks/README.md"),
    Path("memory/mistakes/recurring-failures.md"),
    Path("memory/decisions/README.md"),
    AUDIT_SCRIPT_PATH,
    *BOOTSTRAP_WORKSPACE_FILES,
    *CORE_PAYLOAD_SKILL_FILES,
)
FORBIDDEN_PAYLOAD_FILES = (
    Path("TODO.md"),
    Path("memory/current/active-decisions.md"),
)
FORBIDDEN_PAYLOAD_PREFIXES = (".agent-work/",)
CURRENT_TASK_STALE_DAYS = 30
CURRENT_TASK_MAX_LINES = 120

WORKFLOW_MARKER_START = "<!-- agentic-memory:workflow:start -->"
WORKFLOW_MARKER_END = "<!-- agentic-memory:workflow:end -->"
WORKFLOW_POINTER_BLOCK = (
    f"{WORKFLOW_MARKER_START}\n"
    "Read `memory/system/WORKFLOW.md` for shared workflow rules.\n"
    f"{WORKFLOW_MARKER_END}"
)
EMBEDDED_WORKFLOW_HEADINGS = (
    "## Task system boundary",
    "## Memory discipline",
    "## Memory admission rule",
    "## Memory freshness rule",
    "## Memory routing",
    "## Overview file",
    "## Task-context file",
    "## Local working notes (optional)",
)
PLACEHOLDER_RE = re.compile(r"<[A-Z0-9_/-]+>")
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\b")
VERSION_RE = re.compile(r"^\s*Version:\s*(\d+)\s*$", re.MULTILINE)

OPTIONAL_APPEND_TARGETS = {
    Path("Makefile"): Path("optional/Makefile.fragment.mk"),
    Path("CONTRIBUTING.md"): Path("optional/CONTRIBUTING.fragment.md"),
    Path(".github/pull_request_template.md"): Path("optional/pull_request_template.fragment.md"),
}


@dataclass(slots=True)
class Action:
    kind: str
    path: Path
    detail: str = ""
    role: str = ""
    safety: str = ""
    source: str = ""
    category: str = ""

    def to_dict(self, target_root: Path) -> dict[str, str]:
        relative_path = self.path.relative_to(target_root) if self.path.is_relative_to(target_root) else self.path
        return {
            "kind": self.kind,
            "path": relative_path.as_posix() if isinstance(relative_path, Path) else str(relative_path),
            "detail": self.detail,
            "role": self.role,
            "safety": self.safety,
            "source": self.source,
            "category": self.category,
        }


@dataclass(slots=True)
class InstallResult:
    target_root: Path
    dry_run: bool
    mode: str = "augment"
    message: str = ""
    actions: list[Action] = field(default_factory=list)
    detected_version: int | None = None
    bootstrap_version: int = BOOTSTRAP_VERSION

    def add(
        self,
        kind: str,
        path: Path,
        detail: str = "",
        *,
        role: str = "",
        safety: str = "",
        source: str = "",
        category: str = "",
    ) -> None:
        self.actions.append(
            Action(
                kind=kind,
                path=path,
                detail=detail,
                role=role,
                safety=safety,
                source=source,
                category=category or _infer_action_category(kind=kind, path=path, detail=detail, role=role, safety=safety),
            )
        )

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for action in self.actions:
            counts[action.kind] = counts.get(action.kind, 0) + 1
        return counts

    def to_dict(self) -> dict[str, object]:
        return {
            "target_root": str(self.target_root),
            "dry_run": self.dry_run,
            "mode": self.mode,
            "message": self.message,
            "detected_version": self.detected_version,
            "bootstrap_version": self.bootstrap_version,
            "actions": [action.to_dict(self.target_root) for action in self.actions],
        }


@dataclass(frozen=True, slots=True)
class PayloadEntry:
    relative_path: Path
    role: str
    strategy: str
    source_path: Path


@dataclass(frozen=True, slots=True)
class CurrentNoteView:
    path: Path
    exists: bool
    content: str


@dataclass(slots=True)
class CurrentViewResult:
    target_root: Path
    detected_version: int | None = None
    bootstrap_version: int = BOOTSTRAP_VERSION
    notes: list[CurrentNoteView] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "target_root": str(self.target_root),
            "detected_version": self.detected_version,
            "bootstrap_version": self.bootstrap_version,
            "notes": [
                {
                    "path": note.path.as_posix(),
                    "exists": note.exists,
                    "content": note.content,
                }
                for note in self.notes
            ],
        }


@dataclass(frozen=True, slots=True)
class MemoryNoteRecord:
    path: Path
    note_type: str
    canonical_home: Path
    authority: str
    audience: str
    subsystems: tuple[str, ...] = ()
    surfaces: tuple[str, ...] = ()
    routes_from: tuple[str, ...] = ()
    stale_when: tuple[str, ...] = ()
    related_validations: tuple[str, ...] = ()
    routing_only: bool = False
    high_level: bool = False


@dataclass(frozen=True, slots=True)
class MemoryManifest:
    path: Path
    version: int
    notes: tuple[MemoryNoteRecord, ...]
    routing_only: tuple[Path, ...] = ()
    high_level: tuple[Path, ...] = ()
    canonical_dirs: tuple[Path, ...] = ()
    task_board_globs: tuple[str, ...] = ()


class RepoDetectionError(ValueError):
    """Raised when the installer cannot safely determine the target root."""


def resolve_target_root(target: str | Path | None) -> Path:
    explicit_target = target is not None
    start = Path(target or Path.cwd()).resolve()
    if not start.exists():
        raise RepoDetectionError(f"Target does not exist: {start}")
    if start.is_file():
        raise RepoDetectionError(f"Target must be a directory: {start}")
    if explicit_target:
        return start

    candidates = _find_repo_candidates(start)
    if not candidates:
        raise RepoDetectionError(
            "Could not find a repository root from the current directory. Pass --target explicitly."
        )
    if len(candidates) > 1:
        roots = ", ".join(str(path) for path in candidates)
        raise RepoDetectionError(
            f"Ambiguous repository root detected ({roots}). Pass --target explicitly."
        )
    return candidates[0]


def payload_root() -> Path:
    package_root = Path(__file__).resolve().parent
    packaged = package_root / "_payload"
    if packaged.exists():
        return packaged

    dev_payload = package_root.parents[1] / "bootstrap"
    if dev_payload.exists():
        return dev_payload

    raise FileNotFoundError("Bootstrap payload directory is not available.")


def skills_root() -> Path:
    package_root = Path(__file__).resolve().parent
    packaged = package_root / "_skills"
    if packaged.exists():
        return packaged

    dev_skills = package_root.parents[1] / "skills"
    if dev_skills.exists():
        return dev_skills

    raise FileNotFoundError("Bundled skills directory is not available.")


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

    for entry in _payload_entries(source_root):
        destination = target_root / entry.relative_path
        if destination.exists() and not force:
            result.add("skipped", destination, "already present", role=entry.role, safety="safe", source=str(entry.relative_path))
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
    _plan_from_entries(
        source_root=source_root,
        target_root=target_root,
        substitutions=substitutions,
        result=result,
        mode="upgrade",
        apply=not dry_run,
        apply_local_entrypoint=apply_local_entrypoint,
        force=force,
        include_bootstrap_workspace=True,
    )
    _plan_optional_appends(source_root, target_root, result, apply=not dry_run)
    return result


def collect_status(target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    result = _new_result(target_root, dry_run=False, message="Status report")
    _record_repo_context_warnings(target_root, result)

    for entry in _payload_entries(payload_root(), include_bootstrap_workspace=False):
        destination = target_root / entry.relative_path
        if destination.exists():
            result.add("present", destination, "file exists", role=entry.role, safety="safe", source=str(entry.relative_path))
        else:
            result.add("missing", destination, "file missing", role=entry.role, safety="safe", source=str(entry.relative_path))

    _plan_optional_appends(payload_root(), target_root, result, apply=False, status_only=True)
    return result


def doctor_bootstrap(
    *,
    target: str | Path | None = None,
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
    result = _new_result(target_root, dry_run=True, message="Doctor report")
    _record_repo_context_warnings(target_root, result)
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
    )
    _plan_optional_appends(source_root, target_root, result, apply=False, status_only=True)
    return result


def list_payload_files(target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    result = _new_result(target_root, dry_run=True, message="Packaged bootstrap file preview")
    _record_repo_context_warnings(target_root, result)

    for entry in _payload_entries(source_root):
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
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
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
        detected_version=_read_installed_version(target_root / VERSION_PATH),
    )
    for relative_path in CURRENT_MEMORY_BASELINE:
        note_path = target_root / relative_path
        if note_path.exists():
            result.notes.append(CurrentNoteView(path=relative_path, exists=True, content=note_path.read_text(encoding="utf-8")))
        else:
            result.notes.append(CurrentNoteView(path=relative_path, exists=False, content=""))
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
        if _has_placeholders(text):
            result.add(
                "manual review",
                note_path,
                "current-memory note still contains placeholders",
                role="current-memory",
                safety="manual",
                source=relative_path.as_posix(),
                category="placeholder-review",
            )
        else:
            result.add(
                "current",
                note_path,
                "current-memory note present",
                role="current-memory",
                safety="safe",
                source=relative_path.as_posix(),
                category="safe-update",
            )
        if relative_path == Path("memory/current/task-context.md"):
            stale_reason = _current_task_staleness_reason(text)
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

    suggestions: list[tuple[str, str]] = [(path.as_posix(), "always relevant current-memory note") for path in CURRENT_MEMORY_BASELINE]
    suggestions.extend(
        _find_manifest_matches(
            manifest,
            files=files or [],
            surfaces=selected_surfaces,
            use_staleness=False,
        )
    )
    for section_surface, notes in _parse_route_sections(target_root / "memory" / "index.md"):
        if section_surface in selected_surfaces:
            for note in notes:
                suggestions.append((note, f"matched route surface '{section_surface}'"))

    seen: set[str] = set()
    for note, reason in suggestions:
        if note in seen:
            continue
        seen.add(note)
        result.add(
            "recommended",
            target_root / Path(note),
            reason,
            role="memory-route",
            safety="safe",
            source=note,
            category="safe-update",
        )

    if files and len(seen) == len(CURRENT_MEMORY_BASELINE):
        result.add(
            "manual review",
            target_root / Path("memory/index.md"),
            "no route-specific notes matched; review memory/index.md and related notes manually",
            role="memory-route",
            safety="manual",
            source="memory/index.md",
            category="manual-review",
        )
    return result


def sync_memory(
    *,
    target: str | Path | None = None,
    files: list[str] | None = None,
    notes: list[str] | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    changed_files = list(files or [])
    if not changed_files:
        changed_files = _git_changed_files(target_root)

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
    for note, reason in manifest_suggestions:
        note_path = target_root / Path(note)
        note_exists = note_path.exists()
        note_text = note_path.read_text(encoding="utf-8") if note_exists else ""
        recommendation = "review"
        if not note_exists or _has_placeholders(note_text):
            recommendation = "update"
        if note_path.name == "index.md":
            recommendation = "update index"
        result.add(
            recommendation,
            note_path,
            f"{reason}; manifest staleness trigger matched {', '.join(changed_files) if changed_files else 'explicit input'}",
            role="memory-sync",
            safety="manual",
            source=note,
            category="manual-review",
        )
        seen_sync_paths.add(note_path)

    routed = route_memory(target=target_root, files=changed_files)
    for action in routed.actions:
        if action.kind != "recommended":
            continue
        note_path = action.path
        if note_path in seen_sync_paths:
            continue
        note_exists = note_path.exists()
        note_text = note_path.read_text(encoding="utf-8") if note_exists else ""
        recommendation = "review"
        if not note_exists or _has_placeholders(note_text):
            recommendation = "update"
        if note_path.name == "index.md":
            recommendation = "update index"
        result.add(
            recommendation,
            note_path,
            f"{action.detail}; suggested by changed files {', '.join(changed_files) if changed_files else 'explicit input'}",
            role="memory-sync",
            safety="manual",
            source=action.source,
            category="manual-review",
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


def verify_payload(target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    result = _new_result(target_root, dry_run=True, message="Payload verification")
    payload_paths = {entry.relative_path for entry in _payload_entries(source_root)}
    manifest = _load_memory_manifest(source_root / MANIFEST_PATH)

    for required in PAYLOAD_REQUIRED_FILES:
        if required in payload_paths:
            result.add(
                "current",
                target_root / required,
                "required payload file present",
                role="payload-contract",
                safety="safe",
                source=required.as_posix(),
                category="safe-update",
            )
        else:
            result.add(
                "manual review",
                target_root / required,
                "required payload file missing",
                role="payload-contract",
                safety="manual",
                source=required.as_posix(),
                category="contract-drift",
            )

    current_payload = {path for path in payload_paths if path.as_posix().startswith("memory/current/")}
    expected_current = set(CURRENT_MEMORY_BASELINE)
    for extra in sorted(current_payload - expected_current):
        result.add(
            "manual review",
            target_root / extra,
            "local-only or unexpected current-memory note is in the shipped payload",
            role="payload-contract",
            safety="manual",
            source=extra.as_posix(),
            category="contract-drift",
        )
    for missing in sorted(expected_current - current_payload):
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


def cleanup_bootstrap_workspace(target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    workspace = target_root / BOOTSTRAP_WORKSPACE_ROOT
    result = _new_result(target_root, dry_run=False, message="Bootstrap workspace cleanup")

    if not workspace.exists():
        result.add(
            "skipped",
            workspace,
            "temporary bootstrap workspace is already absent",
            role="bootstrap-workspace",
            safety="safe",
            source=BOOTSTRAP_WORKSPACE_ROOT.as_posix(),
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
        source=BOOTSTRAP_WORKSPACE_ROOT.as_posix(),
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

    workspace = target_root / BOOTSTRAP_WORKSPACE_ROOT
    if workspace.exists():
        if dry_run:
            result.add(
                "would remove",
                workspace,
                "temporary bootstrap workspace",
                role="bootstrap-workspace",
                safety="safe",
                source=BOOTSTRAP_WORKSPACE_ROOT.as_posix(),
                category="safe-update",
            )
        else:
            cleanup_result = cleanup_bootstrap_workspace(target=target_root)
            result.actions.extend(cleanup_result.actions)

    managed_paths: set[Path] = set()
    removable_paths: set[Path] = set()
    for entry in _payload_entries(source_root, include_bootstrap_workspace=False):
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
    _report_remaining_repo_local_memory(target_root=target_root, managed_paths=managed_paths, removable_paths=removable_paths, result=result)
    return result


def build_substitutions(
    *,
    target_root: Path,
    project_name: str | None,
    project_purpose: str | None = None,
    key_repo_docs: str | None = None,
    key_subsystems: str | None = None,
    primary_build_command: str | None = None,
    primary_test_command: str | None = None,
    other_key_commands: str | None = None,
) -> dict[str, str]:
    substitutions = {
        "<PROJECT_NAME>": project_name or target_root.name,
        "<LAST_CONFIRMED_DATE>": datetime.now(UTC).date().isoformat(),
    }
    optional_values = {
        "<PROJECT_PURPOSE>": project_purpose,
        "<KEY_REPO_DOCS>": key_repo_docs,
        "<KEY_SUBSYSTEMS>": key_subsystems,
        "<PRIMARY_BUILD_COMMAND>": primary_build_command,
        "<PRIMARY_TEST_COMMAND>": primary_test_command,
        "<OTHER_KEY_COMMANDS>": other_key_commands,
    }
    for placeholder, value in optional_values.items():
        if value:
            substitutions[placeholder] = value
    return substitutions


def detect_install_mode(target_root: Path) -> str:
    present_count = sum(1 for marker in AGENT_ROOT_MARKERS if (target_root / marker).exists())
    if present_count == 0:
        return "bootstrap"
    if present_count == len(AGENT_ROOT_MARKERS):
        return "full"
    return "augment"


def format_actions(actions: Iterable[Action], target_root: Path) -> list[str]:
    lines: list[str] = []
    for action in actions:
        relative_path = action.path.relative_to(target_root) if action.path.is_relative_to(target_root) else action.path
        details: list[str] = []
        if action.detail:
            details.append(action.detail)
        if action.role:
            details.append(f"role={action.role}")
        if action.safety:
            details.append(f"safety={action.safety}")
        if action.category:
            details.append(f"category={action.category}")
        detail = f" ({'; '.join(details)})" if details else ""
        lines.append(f"{action.kind}: {relative_path}{detail}")
    return lines


def format_result_json(result) -> str:
    return json.dumps(result.to_dict(), indent=2)


def _new_result(target_root: Path, *, dry_run: bool, message: str) -> InstallResult:
    result = InstallResult(target_root=target_root, dry_run=dry_run)
    result.mode = detect_install_mode(target_root)
    result.detected_version = _read_installed_version(target_root / VERSION_PATH)
    result.message = message
    return result


def _payload_entries(source_root: Path, *, include_bootstrap_workspace: bool = True) -> list[PayloadEntry]:
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
            if not include_bootstrap_workspace and relative_path.as_posix().startswith("memory/bootstrap/"):
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
    result: InstallResult,
    mode: str,
    apply: bool,
    apply_local_entrypoint: bool,
    force: bool,
    include_bootstrap_workspace: bool,
) -> None:
    for entry in _payload_entries(source_root, include_bootstrap_workspace=include_bootstrap_workspace):
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


def _plan_existing_file_for_adopt(
    *,
    entry: PayloadEntry,
    destination: Path,
    existing: str,
    rendered: str,
    result: InstallResult,
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
        result.add("current", destination, "already matches payload", role=entry.role, safety="safe", source=str(entry.relative_path))
        return

    if entry.role in {"shared-replaceable", "shared-template"}:
        result.add(
            "manual review",
            destination,
            "shared file differs; adoption leaves existing file untouched",
            role=entry.role,
            safety="manual",
            source=str(entry.relative_path),
        )
        return

    result.add("skipped", destination, "existing file left untouched during adoption", role=entry.role, safety="safe", source=str(entry.relative_path))


def _plan_existing_file_for_upgrade(
    *,
    entry: PayloadEntry,
    destination: Path,
    existing: str,
    rendered: str,
    result: InstallResult,
    apply: bool,
    apply_local_entrypoint: bool,
    force: bool,
    doctor_mode: bool,
) -> None:
    if rendered == existing:
        result.add("current", destination, "already matches payload", role=entry.role, safety="safe", source=str(entry.relative_path))
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
        _write_text(destination, rendered, result, "replaced", "would replace", role=entry.role, source=str(entry.relative_path))
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
        else:
            result.add(
                "manual review",
                destination,
                "starter note looks customised; review before replacing",
                role=entry.role,
                safety="manual",
                source=str(entry.relative_path),
            )
        return

    result.add("skipped", destination, "existing file left untouched", role=entry.role, safety="safe", source=str(entry.relative_path))


def _plan_agents_entrypoint(
    *,
    destination: Path,
    existing: str,
    result: InstallResult,
    apply: bool,
    apply_local_entrypoint: bool,
    doctor_mode: bool,
) -> None:
    has_reference = "memory/system/WORKFLOW.md" in existing
    embeds_shared_rules = _embeds_shared_workflow_rules(existing)

    if has_reference and WORKFLOW_MARKER_START in existing and not embeds_shared_rules:
        result.add("current", destination, "workflow pointer block already present", role="local-entrypoint", safety="safe", source=str(AGENTS_PATH))
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
            detail="added or refreshed the canonical workflow pointer block near the top of AGENTS.md",
        )
        if embeds_shared_rules:
            result.add(
                "manual review",
                destination,
                "older AGENTS.md still embeds shared workflow rules; --apply-local-entrypoint can patch the workflow pointer block, but copied shared rules still need manual slimming",
                role="local-entrypoint",
                safety="manual",
                source=str(AGENTS_PATH),
            )
        return

    detail = "missing canonical workflow pointer block near the top of AGENTS.md; use --apply-local-entrypoint to add or refresh it safely"
    if embeds_shared_rules:
        detail = "older AGENTS.md still embeds shared workflow rules; --apply-local-entrypoint can patch the workflow pointer block, but copied shared rules still need manual slimming"
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
    result: InstallResult,
    action_kind: str,
    dry_kind: str,
) -> None:
    rendered = _render_text(entry.source_path, substitutions)
    _write_text(destination, rendered, result, action_kind, dry_kind, role=entry.role, source=str(entry.relative_path))


def _write_text(
    destination: Path,
    rendered: str,
    result: InstallResult,
    action_kind: str,
    dry_kind: str,
    *,
    role: str,
    source: str,
    detail: str = "",
) -> None:
    if result.dry_run:
        result.add(dry_kind, destination, detail or "planned change", role=role, safety="safe", source=source)
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    result.add(action_kind, destination, detail or "applied", role=role, safety="safe", source=source)


def _plan_optional_appends(
    source_root: Path,
    target_root: Path,
    result: InstallResult,
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
    result: InstallResult,
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
    result: InstallResult,
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
            "manual review",
            path,
            "repo-local memory file remains after uninstall; remove manually if the repository should no longer keep memory",
            role="repo-local-memory",
            safety="manual",
            source=path.relative_to(target_root).as_posix(),
            category="manual-review",
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


def _read_installed_version(path: Path) -> int | None:
    if not path.exists():
        return None
    match = VERSION_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        return None
    return int(match.group(1))


def _has_placeholders(text: str) -> bool:
    return bool(PLACEHOLDER_RE.search(text))


def _infer_action_category(*, kind: str, path: Path, detail: str, role: str, safety: str) -> str:
    detail_lower = detail.lower()
    path_str = path.as_posix()
    if "placeholder" in detail_lower:
        return "placeholder-review"
    if any(path_str.endswith(current_path.as_posix()) for current_path in CURRENT_MEMORY_BASELINE):
        if kind in {"missing", "manual review"}:
            return "current-memory-review"
    if role in {"payload-contract", "local-entrypoint"} or role.startswith("shared-"):
        if kind in {"manual review", "missing"}:
            return "contract-drift"
    if kind in {"would create", "would copy", "would replace", "created", "copied", "replaced", "current", "present", "recommended"}:
        return "safe-update"
    if kind == "manual review":
        return "manual-review"
    if safety == "safe":
        return "safe-update"
    return ""


def _current_task_staleness_reason(text: str) -> str | None:
    lines = text.splitlines()
    if len(lines) > CURRENT_TASK_MAX_LINES:
        return f"task-context note is oversized ({len(lines)} lines)"
    for idx, line in enumerate(lines):
        if line.strip().lower() == "## last confirmed":
            for follow in lines[idx + 1 :]:
                stripped = follow.strip()
                if not stripped:
                    continue
                date_match = DATE_RE.match(stripped)
                if date_match:
                    confirmed = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(tzinfo=UTC)
                    if confirmed < datetime.now(UTC) - timedelta(days=CURRENT_TASK_STALE_DAYS):
                        return f"task-context note has not been confirmed in over {CURRENT_TASK_STALE_DAYS} days"
                break
    return None


def _load_memory_manifest(path: Path) -> MemoryManifest | None:
    if not path.exists():
        return None

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None
    notes_table = data.get("notes", {})
    rules_table = data.get("rules", {})
    version = int(data.get("version", 1))

    notes: list[MemoryNoteRecord] = []
    for note_path, raw in notes_table.items():
        if not isinstance(raw, dict):
            continue
        notes.append(
            MemoryNoteRecord(
                path=Path(note_path),
                note_type=str(raw.get("note_type", "memory-note")),
                canonical_home=Path(str(raw.get("canonical_home", note_path))),
                authority=str(raw.get("authority", "supporting")),
                audience=str(raw.get("audience", "human+agent")),
                subsystems=tuple(_string_list(raw.get("subsystems"))),
                surfaces=tuple(_normalise_surface_name(value) for value in _string_list(raw.get("surfaces"))),
                routes_from=tuple(_string_list(raw.get("routes_from"))),
                stale_when=tuple(_string_list(raw.get("stale_when"))),
                related_validations=tuple(_string_list(raw.get("related_validations"))),
                routing_only=bool(raw.get("routing_only", False)),
                high_level=bool(raw.get("high_level", False)),
            )
        )

    return MemoryManifest(
        path=path,
        version=version,
        notes=tuple(notes),
        routing_only=tuple(Path(value) for value in _string_list(rules_table.get("routing_only"))),
        high_level=tuple(Path(value) for value in _string_list(rules_table.get("high_level"))),
        canonical_dirs=tuple(Path(value) for value in _string_list(rules_table.get("canonical_dirs"))),
        task_board_globs=tuple(_string_list(rules_table.get("task_board_globs"))),
    )


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _find_manifest_matches(
    manifest: MemoryManifest | None,
    *,
    files: list[str],
    surfaces: set[str],
    use_staleness: bool,
) -> list[tuple[str, str]]:
    if manifest is None:
        return []

    suggestions: list[tuple[str, str]] = []
    for note in manifest.notes:
        reasons: list[str] = []
        if surfaces and any(surface in surfaces for surface in note.surfaces):
            matched = ", ".join(sorted({surface for surface in note.surfaces if surface in surfaces}))
            reasons.append(f"manifest surface match ({matched})")

        globs = note.stale_when if use_staleness else note.routes_from
        if files and globs:
            matched_globs = sorted({pattern for pattern in globs if any(_path_matches_pattern(path, pattern) for path in files)})
            if matched_globs:
                reasons.append(f"manifest path match ({', '.join(matched_globs)})")

        if reasons:
            suggestions.append((note.path.as_posix(), "; ".join(reasons)))
    return suggestions


def _path_matches_pattern(raw_path: str, pattern: str) -> bool:
    normalised_path = raw_path.replace("\\", "/").strip("./")
    normalised_pattern = pattern.replace("\\", "/").strip()
    if not normalised_path or not normalised_pattern:
        return False
    return Path(normalised_path).match(normalised_pattern)


def _parse_route_sections(index_path: Path) -> list[tuple[str, list[str]]]:
    if not index_path.exists():
        return []
    sections: list[tuple[str, list[str]]] = []
    current_heading: str | None = None
    current_notes: list[str] = []
    in_task_routing = False
    for raw_line in index_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "## Task routing":
            in_task_routing = True
            continue
        if in_task_routing and line.startswith("## "):
            break
        if not in_task_routing:
            continue
        if line.startswith("### "):
            if current_heading is not None:
                sections.append((_normalise_surface_name(current_heading), current_notes))
            current_heading = line.removeprefix("### ").strip()
            current_notes = []
            continue
        if line.startswith("- `") and line.endswith("`"):
            current_notes.append(line[3:-1])
    if current_heading is not None:
        sections.append((_normalise_surface_name(current_heading), current_notes))
    return sections


def _normalise_surface_name(text: str) -> str:
    lowered = text.lower()
    if "runtime" in lowered or "deployment" in lowered:
        return "runtime"
    if "api" in lowered or "interface" in lowered or "tool behaviour" in lowered:
        return "api"
    if "retrieval" in lowered or "search" in lowered:
        return "retrieval"
    if "test" in lowered or "validation" in lowered:
        return "tests"
    if "data model" in lowered or "architecture" in lowered:
        return "architecture"
    if "choosing an approach" in lowered or "multiple subsystems" in lowered:
        return "decision"
    return lowered


def _infer_surfaces_from_paths(paths: list[str]) -> set[str]:
    surfaces: set[str] = set()
    for raw_path in paths:
        path = raw_path.replace("\\", "/").lower()
        if any(token in path for token in ("test", "/tests/", "_test.", "spec.")):
            surfaces.add("tests")
        if any(token in path for token in ("deploy", "infra", "docker", "k8s", "terraform", "compose")):
            surfaces.add("runtime")
        if any(token in path for token in ("api", "route", "contract", "interface", "cli")):
            surfaces.add("api")
        if any(token in path for token in ("search", "retriev", "vector", "index")):
            surfaces.add("retrieval")
        if any(token in path for token in ("schema", "model", "architect", "design", "invariant")):
            surfaces.add("architecture")
    return surfaces


def _git_changed_files(target_root: Path) -> list[str]:
    if not (target_root / ".git").exists():
        return []
    try:
        completed = subprocess.run(
            ["git", "status", "--short", "--porcelain"],
            cwd=target_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    files: list[str] = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        candidate = line[3:]
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        files.append(candidate)
    return files


def _embeds_shared_workflow_rules(text: str) -> bool:
    matches = {heading for heading in EMBEDDED_WORKFLOW_HEADINGS if heading in text}
    return "## Task system boundary" in matches or len(matches) >= 2


def _patch_agents_workflow_block(existing: str) -> str:
    if WORKFLOW_MARKER_START in existing and WORKFLOW_MARKER_END in existing:
        pattern = re.compile(
            re.escape(WORKFLOW_MARKER_START) + r".*?" + re.escape(WORKFLOW_MARKER_END),
            re.DOTALL,
        )
        return pattern.sub(WORKFLOW_POINTER_BLOCK, existing, count=1)

    lines = existing.splitlines()
    if lines and lines[0].startswith("#"):
        rest_index = 1
        while rest_index < len(lines) and not lines[rest_index].strip():
            rest_index += 1
        rest = lines[rest_index:]
        body = "\n".join(rest).lstrip("\n")
        if body:
            return f"{lines[0]}\n\n{WORKFLOW_POINTER_BLOCK}\n\n{body.rstrip()}\n"
        return f"{lines[0]}\n\n{WORKFLOW_POINTER_BLOCK}\n"

    return f"{WORKFLOW_POINTER_BLOCK}\n\n{existing.lstrip()}"


def _record_repo_context_warnings(target_root: Path, result: InstallResult) -> None:
    parent_repo = _find_parent_repo_root(target_root)
    if parent_repo is not None:
        result.add(
            "warning",
            target_root,
            f"target is inside parent repository {parent_repo}; --target is being treated as authoritative",
            role="target-context",
            safety="safe",
        )

    for nested_repo in _find_nested_repo_roots(target_root):
        result.add(
            "warning",
            nested_repo,
            "nested repository detected under target; installer will not recurse into repo roots automatically",
            role="target-context",
            safety="safe",
        )


def _find_repo_candidates(start: Path) -> list[Path]:
    candidates: list[Path] = []
    for candidate in [start, *start.parents]:
        git_dir = candidate / ".git"
        if git_dir.is_dir() or git_dir.is_file():
            candidates.append(candidate)
            continue
        if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
            candidates.append(candidate)
    return candidates


def _find_parent_repo_root(target_root: Path) -> Path | None:
    for candidate in target_root.parents:
        git_dir = candidate / ".git"
        if git_dir.is_dir() or git_dir.is_file():
            return candidate
        if any((candidate / marker).exists() for marker in PROJECT_MARKERS):
            return candidate
    return None


def _find_nested_repo_roots(target_root: Path) -> list[Path]:
    nested: list[Path] = []
    seen: set[Path] = set()
    for candidate in target_root.rglob(".git"):
        repo_root = candidate.parent
        if repo_root == target_root or repo_root in seen:
            continue
        nested.append(repo_root)
        seen.add(repo_root)
    return sorted(nested)
OPTIONAL_APPEND_DESCRIPTIONS = {
    Path("Makefile"): "optional convenience target for running the memory freshness audit locally or in CI",
    Path("CONTRIBUTING.md"): "optional contributor guidance fragment",
    Path(".github/pull_request_template.md"): "optional pull request checklist fragment",
}
