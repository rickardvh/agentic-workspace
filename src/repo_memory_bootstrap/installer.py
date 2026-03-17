from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

PROJECT_MARKERS = ("pyproject.toml", "package.json", "Cargo.toml", ".hg")
AGENT_ROOT_MARKERS = (Path("AGENTS.md"), Path("TODO.md"), Path("memory"))
VERSION_PATH = Path("memory/system/VERSION.md")
WORKFLOW_PATH = Path("memory/system/WORKFLOW.md")
UPGRADE_PLAYBOOK_PATH = Path("memory/system/UPGRADE.md")
AGENTS_PATH = Path("AGENTS.md")
TODO_PATH = Path("TODO.md")
AUDIT_SCRIPT_PATH = Path("scripts/check/check_memory_freshness.py")
BOOTSTRAP_VERSION = 4

WORKFLOW_MARKER_START = "<!-- agentic-memory:workflow:start -->"
WORKFLOW_MARKER_END = "<!-- agentic-memory:workflow:end -->"
WORKFLOW_POINTER_BLOCK = (
    f"{WORKFLOW_MARKER_START}\n"
    "Read `memory/system/WORKFLOW.md` for shared workflow rules.\n"
    f"{WORKFLOW_MARKER_END}"
)

OLD_WORKFLOW_HEADINGS = (
    "## TODO discipline",
    "## Memory discipline",
    "## Memory admission rule",
    "## Memory freshness rule",
    "## Memory routing",
)
PLACEHOLDER_RE = re.compile(r"<[A-Z0-9_/-]+>")
VERSION_RE = re.compile(r"^\s*Version:\s*(\d+)\s*$", re.MULTILINE)

OPTIONAL_APPEND_TARGETS = {
    Path("Makefile"): Path("optional/Makefile.fragment.mk"),
    Path("CONTRIBUTING.md"): Path("optional/CONTRIBUTING.fragment.md"),
    Path(".github/pull_request_template.md"): Path("optional/pull_request_template.fragment.md"),
}
LOCAL_TEMPLATE_TREES = [Path(".agent-work")]


@dataclass(slots=True)
class Action:
    kind: str
    path: Path
    detail: str = ""
    role: str = ""
    safety: str = ""
    source: str = ""

    def to_dict(self, target_root: Path) -> dict[str, str]:
        relative_path = self.path.relative_to(target_root) if self.path.is_relative_to(target_root) else self.path
        return {
            "kind": self.kind,
            "path": relative_path.as_posix() if isinstance(relative_path, Path) else str(relative_path),
            "detail": self.detail,
            "role": self.role,
            "safety": self.safety,
            "source": self.source,
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
    ) -> None:
        self.actions.append(
            Action(kind=kind, path=path, detail=detail, role=role, safety=safety, source=source)
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


def install_bootstrap(
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    project_name: str | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    substitutions = build_substitutions(target_root=target_root, project_name=project_name)
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

    _plan_gitignore_append(source_root, target_root, result, apply=not dry_run)
    _plan_optional_appends(source_root, target_root, result, apply=not dry_run)
    _plan_local_template_note(target_root, result)
    return result


def adopt_bootstrap(
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    apply_local_entrypoint: bool = False,
    project_name: str | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    substitutions = build_substitutions(target_root=target_root, project_name=project_name)
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
    )
    _plan_gitignore_append(source_root, target_root, result, apply=not dry_run)
    _plan_optional_appends(source_root, target_root, result, apply=not dry_run)
    _plan_local_template_note(target_root, result)
    return result


def upgrade_bootstrap(
    *,
    target: str | Path | None = None,
    dry_run: bool = False,
    force: bool = False,
    apply_local_entrypoint: bool = False,
    project_name: str | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    substitutions = build_substitutions(target_root=target_root, project_name=project_name)
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
    )
    _plan_gitignore_append(source_root, target_root, result, apply=not dry_run)
    _plan_optional_appends(source_root, target_root, result, apply=not dry_run)
    _plan_local_template_note(target_root, result)
    return result


def collect_status(target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    result = _new_result(target_root, dry_run=False, message="Status report")
    _record_repo_context_warnings(target_root, result)

    for entry in _payload_entries(payload_root()):
        destination = target_root / entry.relative_path
        if destination.exists():
            result.add("present", destination, "file exists", role=entry.role, safety="safe", source=str(entry.relative_path))
        else:
            result.add("missing", destination, "file missing", role=entry.role, safety="safe", source=str(entry.relative_path))

    _plan_gitignore_append(payload_root(), target_root, result, apply=False, status_only=True)
    _plan_optional_appends(payload_root(), target_root, result, apply=False, status_only=True)
    _plan_local_template_note(target_root, result)
    return result


def doctor_bootstrap(
    *,
    target: str | Path | None = None,
    project_name: str | None = None,
) -> InstallResult:
    target_root = resolve_target_root(target)
    source_root = payload_root()
    substitutions = build_substitutions(target_root=target_root, project_name=project_name)
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
    )
    _plan_gitignore_append(source_root, target_root, result, apply=False, status_only=True)
    _plan_optional_appends(source_root, target_root, result, apply=False, status_only=True)
    _plan_local_template_note(target_root, result)
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

    result.add("append target", target_root / ".gitignore", "append .agent-work/ ignore rule if needed", role="append-target", safety="safe")
    for target_file, fragment_path in OPTIONAL_APPEND_TARGETS.items():
        result.add(
            "append target",
            target_root / target_file,
            f"optional fragment {fragment_path}",
            role="append-target",
            safety="safe",
            source=str(fragment_path),
        )

    for relative_tree in LOCAL_TEMPLATE_TREES:
        for source_path in sorted((source_root / relative_tree).rglob("*")):
            if source_path.is_dir():
                continue
            result.add(
                "local template",
                target_root / source_path.relative_to(source_root),
                "create locally if you want disposable task notes",
                role="local-scratch-template",
                safety="safe",
                source=str(source_path.relative_to(source_root)),
            )

    return result


def build_substitutions(*, target_root: Path, project_name: str | None) -> dict[str, str]:
    return {
        "<PROJECT_NAME>": project_name or target_root.name,
    }


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
        detail = f" ({'; '.join(details)})" if details else ""
        lines.append(f"{action.kind}: {relative_path}{detail}")
    return lines


def format_result_json(result: InstallResult) -> str:
    return json.dumps(result.to_dict(), indent=2)


def _new_result(target_root: Path, *, dry_run: bool, message: str) -> InstallResult:
    result = InstallResult(target_root=target_root, dry_run=dry_run)
    result.mode = detect_install_mode(target_root)
    result.detected_version = _read_installed_version(target_root / VERSION_PATH)
    result.message = message
    return result


def _payload_entries(source_root: Path) -> list[PayloadEntry]:
    entries: list[PayloadEntry] = []

    files = [AGENTS_PATH, TODO_PATH, AUDIT_SCRIPT_PATH]
    for relative_path in files:
        source_path = source_root / relative_path
        entries.append(
            PayloadEntry(
                relative_path=relative_path,
                role=_classify_role(relative_path),
                strategy=_strategy_for_role(_classify_role(relative_path)),
                source_path=source_path,
            )
        )

    for source_path in sorted((source_root / "memory").rglob("*")):
        if source_path.is_dir():
            continue
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
    return entries


def _classify_role(relative_path: Path) -> str:
    path_str = relative_path.as_posix()
    if relative_path == AGENTS_PATH:
        return "local-entrypoint"
    if relative_path == TODO_PATH:
        return "execution-surface"
    if relative_path == AUDIT_SCRIPT_PATH:
        return "shared-replaceable"
    if path_str.startswith("memory/system/"):
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
        "execution-surface": "create-only",
        "shared-replaceable": "replace",
        "shared-template": "replace",
        "seed-note": "seed",
        "managed-file": "create-only",
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
) -> None:
    for entry in _payload_entries(source_root):
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

    if entry.role == "execution-surface":
        if force and not doctor_mode:
            _write_text(destination, rendered, result, "overwritten", "would overwrite", role=entry.role, source=str(entry.relative_path))
        else:
            result.add(
                "manual review",
                destination,
                "TODO.md is local execution state and is not auto-replaced",
                role=entry.role,
                safety="manual",
                source=str(entry.relative_path),
            )
        return

    if entry.role in {"shared-replaceable", "shared-template"}:
        _write_text(destination, rendered, result, "replaced", "would replace", role=entry.role, source=str(entry.relative_path))
        return

    if entry.role == "seed-note":
        if _has_placeholders(existing) or force:
            detail = "seed note still contains placeholders" if _has_placeholders(existing) else "forced replacement"
            _write_text(destination, rendered, result, "replaced", "would replace", role=entry.role, source=str(entry.relative_path), detail=detail)
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
    embeds_old_rules = any(heading in existing for heading in OLD_WORKFLOW_HEADINGS)

    if has_reference and WORKFLOW_MARKER_START in existing and not embeds_old_rules:
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
            detail="added or refreshed workflow pointer block",
        )
        if embeds_old_rules:
            result.add(
                "manual review",
                destination,
                "older AGENTS.md still embeds shared workflow rules; slim it manually after patching",
                role="local-entrypoint",
                safety="manual",
                source=str(AGENTS_PATH),
            )
        return

    detail = "missing workflow pointer block"
    if embeds_old_rules:
        detail = "older AGENTS.md still embeds shared workflow rules"
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


def _plan_gitignore_append(
    source_root: Path,
    target_root: Path,
    result: InstallResult,
    *,
    apply: bool,
    status_only: bool = False,
) -> None:
    destination = target_root / ".gitignore"
    fragment = (source_root / ".gitignore.append").read_text(encoding="utf-8").strip()
    existing = destination.read_text(encoding="utf-8") if destination.exists() else ""
    if fragment in existing:
        result.add("current" if status_only else "skipped", destination, "already contains .agent-work/ ignore rule", role="append-target", safety="safe", source=".gitignore.append")
        return

    if status_only:
        result.add("missing", destination, "missing .agent-work/ ignore rule", role="append-target", safety="safe", source=".gitignore.append")
        return

    if not apply:
        result.add("would append", destination, "add .agent-work/ ignore rule", role="append-target", safety="safe", source=".gitignore.append")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(_append_text(existing, fragment), encoding="utf-8")
    result.add("appended", destination, "added .agent-work/ ignore rule", role="append-target", safety="safe", source=".gitignore.append")


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
                f"add fragment from {fragment_path.name}",
                role="append-target",
                safety="safe",
                source=str(fragment_path),
            )
            continue

        destination.write_text(_append_text(existing, fragment), encoding="utf-8")
        result.add(
            "appended",
            destination,
            f"added fragment from {fragment_path.name}",
            role="append-target",
            safety="safe",
            source=str(fragment_path),
        )


def _plan_local_template_note(target_root: Path, result: InstallResult) -> None:
    result.add(
        "note",
        target_root / ".agent-work",
        "Templates are bundled in the bootstrap payload; create this directory locally if needed.",
        role="local-scratch-template",
        safety="safe",
    )


def _append_text(existing: str, fragment: str) -> str:
    normalized = existing.rstrip()
    if not normalized:
        return f"{fragment}\n"
    return f"{normalized}\n\n{fragment}\n"


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
    return f"equivalent Makefile target{plural} already present ({joined})"


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


def _patch_agents_workflow_block(existing: str) -> str:
    if WORKFLOW_MARKER_START in existing and WORKFLOW_MARKER_END in existing:
        pattern = re.compile(
            re.escape(WORKFLOW_MARKER_START) + r".*?" + re.escape(WORKFLOW_MARKER_END),
            re.DOTALL,
        )
        return pattern.sub(WORKFLOW_POINTER_BLOCK, existing, count=1)

    lines = existing.splitlines()
    if lines and lines[0].startswith("#"):
        insert_at = 1
        while insert_at < len(lines) and lines[insert_at].strip():
            insert_at += 1
        prefix = lines[:insert_at]
        suffix = lines[insert_at:]
        pieces = prefix + ["", *WORKFLOW_POINTER_BLOCK.splitlines()]
        if suffix:
            pieces.append("")
            pieces.extend(suffix)
        return "\n".join(pieces).rstrip() + "\n"

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

    nested_repos = _find_nested_repo_roots(target_root)
    for nested_repo in nested_repos:
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
