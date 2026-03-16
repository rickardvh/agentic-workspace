from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

PROJECT_MARKERS = ("pyproject.toml", "package.json", "Cargo.toml", ".hg")
AGENT_ROOT_MARKERS = (Path("AGENTS.md"), Path("TODO.md"), Path("memory"))

MANAGED_FILES = [
    Path("AGENTS.md"),
    Path("TODO.md"),
    Path("scripts/check/check_memory_freshness.py"),
]
MANAGED_TREES = [Path("memory")]
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


@dataclass(slots=True)
class InstallResult:
    target_root: Path
    dry_run: bool
    mode: str = "augment"
    message: str = ""
    actions: list[Action] = field(default_factory=list)

    def add(self, kind: str, path: Path, detail: str = "") -> None:
        self.actions.append(Action(kind=kind, path=path, detail=detail))

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for action in self.actions:
            counts[action.kind] = counts.get(action.kind, 0) + 1
        return counts


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
    substitutions = build_substitutions(target_root=target_root, project_name=project_name)
    result = InstallResult(target_root=target_root, dry_run=dry_run)
    source_root = payload_root()
    result.mode = detect_install_mode(target_root)
    result.message = _mode_message(result.mode)

    for relative_path in MANAGED_FILES:
        _copy_file(
            source_root / relative_path,
            target_root / relative_path,
            result=result,
            substitutions=substitutions,
            force=force,
            skip_all_managed=result.mode == "full",
        )

    for relative_tree in MANAGED_TREES:
        for source_path in sorted((source_root / relative_tree).rglob("*")):
            if source_path.is_dir():
                continue
            _copy_file(
                source_path,
                target_root / source_path.relative_to(source_root),
                result=result,
                substitutions=substitutions,
                force=force,
                skip_all_managed=result.mode == "full",
            )

    _append_gitignore(
        source_root / ".gitignore.append",
        target_root / ".gitignore",
        result=result,
    )

    for target_file, fragment_path in OPTIONAL_APPEND_TARGETS.items():
        _append_if_present(
            target_root / target_file,
            source_root / fragment_path,
            result=result,
        )

    result.add(
        "note",
        target_root / ".agent-work",
        "Templates are bundled in the bootstrap payload; create this directory locally if needed.",
    )
    return result


def collect_status(target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, dry_run=False)
    result.mode = detect_install_mode(target_root)
    result.message = _mode_message(result.mode, detected=True)

    for relative_path in MANAGED_FILES:
        _record_presence(target_root / relative_path, result)

    for relative_tree in MANAGED_TREES:
        tree_root = target_root / relative_tree
        if tree_root.exists():
            result.add("present", tree_root, "tree exists")
        else:
            result.add("missing", tree_root, "tree missing")

    gitignore_path = target_root / ".gitignore"
    if gitignore_path.exists() and _contains_line(gitignore_path, ".agent-work/"):
        result.add("present", gitignore_path, "contains .agent-work/")
    else:
        result.add("missing", gitignore_path, "missing .agent-work/ ignore rule")

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


def _copy_file(
    source: Path,
    destination: Path,
    *,
    result: InstallResult,
    substitutions: dict[str, str],
    force: bool,
    skip_all_managed: bool,
) -> None:
    destination_exists = destination.exists()
    action_kind = "copied"

    if skip_all_managed and not force:
        result.add("skipped", destination, "agent memory system already present")
        return

    if destination_exists and not force:
        result.add("skipped", destination, "already present")
        return
    if destination_exists and force:
        action_kind = "overwritten"

    rendered = _render_text(source, substitutions)
    if result.dry_run:
        dry_kind = "would copy" if action_kind == "copied" else "would overwrite"
        result.add(dry_kind, destination, f"from {source.name}")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    result.add(action_kind, destination, f"from {source.name}")


def _append_gitignore(fragment_source: Path, destination: Path, *, result: InstallResult) -> None:
    fragment = fragment_source.read_text(encoding="utf-8").strip()
    if destination.exists() and fragment in destination.read_text(encoding="utf-8"):
        result.add("skipped", destination, "already contains .agent-work/ ignore rule")
        return

    if result.dry_run:
        result.add("would append", destination, "add .agent-work/ ignore rule")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    existing = destination.read_text(encoding="utf-8") if destination.exists() else ""
    merged = _append_text(existing, fragment)
    destination.write_text(merged, encoding="utf-8")
    result.add("appended", destination, "added .agent-work/ ignore rule")


def _append_if_present(destination: Path, fragment_source: Path, *, result: InstallResult) -> None:
    if not destination.exists():
        result.add("skipped", destination, "target file not present")
        return

    fragment = fragment_source.read_text(encoding="utf-8").strip()
    existing = destination.read_text(encoding="utf-8")
    if fragment in existing:
        result.add("skipped", destination, "fragment already present")
        return

    if result.dry_run:
        result.add("would append", destination, f"add fragment from {fragment_source.name}")
        return

    destination.write_text(_append_text(existing, fragment), encoding="utf-8")
    result.add("appended", destination, f"added fragment from {fragment_source.name}")


def _append_text(existing: str, fragment: str) -> str:
    normalized = existing.rstrip()
    if not normalized:
        return f"{fragment}\n"
    return f"{normalized}\n\n{fragment}\n"


def _record_presence(path: Path, result: InstallResult) -> None:
    if path.exists():
        result.add("present", path, "file exists")
    else:
        result.add("missing", path, "file missing")


def _render_text(source: Path, substitutions: dict[str, str]) -> str:
    text = source.read_text(encoding="utf-8")
    for placeholder, replacement in substitutions.items():
        text = text.replace(placeholder, replacement)
    return text


def _contains_line(path: Path, value: str) -> bool:
    return any(line.strip() == value for line in path.read_text(encoding="utf-8").splitlines())


def format_actions(actions: Iterable[Action], target_root: Path) -> list[str]:
    lines: list[str] = []
    for action in actions:
        relative_path = action.path.relative_to(target_root) if action.path.is_relative_to(target_root) else action.path
        detail = f" ({action.detail})" if action.detail else ""
        lines.append(f"{action.kind}: {relative_path}{detail}")
    return lines


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


def _mode_message(mode: str, *, detected: bool = False) -> str:
    messages = {
        "bootstrap": "Bootstrapping agent memory system into empty repo",
        "augment": "Augmenting existing agent memory system",
        "full": "Agent memory system already present",
    }
    if detected:
        return f"Detected {mode} mode: {messages[mode]}"
    return messages[mode]
