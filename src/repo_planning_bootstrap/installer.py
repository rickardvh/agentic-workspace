from __future__ import annotations

import importlib.util
import json
import shutil
import re
from dataclasses import dataclass, field
from pathlib import Path

from repo_planning_bootstrap import __version__
from repo_planning_bootstrap._render import load_manifest, render_quickstart


REQUIRED_PAYLOAD_FILES = (
    Path("AGENTS.md"),
    Path("TODO.md"),
    Path("ROADMAP.md"),
    Path("docs/execplans/README.md"),
    Path("docs/execplans/TEMPLATE.md"),
    Path("docs/execplans/archive/README.md"),
    Path("scripts/check/check_planning_surfaces.py"),
    Path("scripts/render_agent_docs.py"),
    Path("tools/agent-manifest.json"),
    Path("tools/AGENT_QUICKSTART.md"),
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


def payload_root() -> Path:
    packaged = Path(__file__).resolve().parent / "_payload"
    if packaged.exists():
        return packaged
    return Path(__file__).resolve().parents[2] / "bootstrap"


def resolve_target_root(target: str | Path | None) -> Path:
    resolved = Path(target).resolve() if target else Path.cwd().resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def list_payload_files() -> list[str]:
    root = payload_root()
    return [path.relative_to(root).as_posix() for path in sorted(root.rglob("*")) if path.is_file()]


def install_bootstrap(*, target: str | Path | None = None, dry_run: bool = False, force: bool = False) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Install plan", dry_run=dry_run)
    _copy_payload(target_root=target_root, result=result, conservative=False, force=force)
    _render_quickstart_file(target_root=target_root, result=result, apply=not dry_run)
    return result


def adopt_bootstrap(*, target: str | Path | None = None, dry_run: bool = False) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Adoption plan for existing repository", dry_run=dry_run)
    _copy_payload(target_root=target_root, result=result, conservative=True, force=False)
    _render_quickstart_file(target_root=target_root, result=result, apply=not dry_run)
    return result


def collect_status(*, target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Status report", dry_run=False)
    for relative in REQUIRED_PAYLOAD_FILES:
        destination = target_root / relative
        result.add("present" if destination.exists() else "missing", destination, "file exists" if destination.exists() else "file missing")
    return result


def doctor_bootstrap(*, target: str | Path | None = None) -> InstallResult:
    target_root = resolve_target_root(target)
    result = InstallResult(target_root=target_root, message="Doctor report", dry_run=True)
    for relative in REQUIRED_PAYLOAD_FILES:
        destination = target_root / relative
        result.add("current" if destination.exists() else "manual review", destination, "required file present" if destination.exists() else "required file missing")

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

    manifest_path = target_root / "tools/agent-manifest.json"
    quickstart_path = target_root / "tools/AGENT_QUICKSTART.md"
    if manifest_path.exists() and quickstart_path.exists():
        rendered = _render_quickstart_for_repo(target_root)
        if quickstart_path.read_text(encoding="utf-8") != rendered:
            result.add("manual review", quickstart_path, "quickstart is out of sync with tools/agent-manifest.json; run python scripts/render_agent_docs.py")
    return result


def verify_payload() -> InstallResult:
    root = payload_root()
    result = InstallResult(target_root=root, message="Payload verification", dry_run=False)
    payload_files = {Path(item) for item in list_payload_files()}
    for relative in REQUIRED_PAYLOAD_FILES:
        result.add("current" if relative in payload_files else "manual review", root / relative, "required payload file present" if relative in payload_files else "required payload file missing")

    manifest_path = root / "tools/agent-manifest.json"
    quickstart_path = root / "tools/AGENT_QUICKSTART.md"
    if manifest_path.exists() and quickstart_path.exists():
        rendered = _render_quickstart_for_repo(root)
        result.add("current" if quickstart_path.read_text(encoding="utf-8") == rendered else "manual review", quickstart_path, "quickstart matches manifest" if quickstart_path.read_text(encoding="utf-8") == rendered else "quickstart does not match manifest")
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


def _copy_payload(*, target_root: Path, result: InstallResult, conservative: bool, force: bool) -> None:
    root = payload_root()
    for source in sorted(root.rglob("*")):
        if not source.is_file():
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


def _render_quickstart_file(*, target_root: Path, result: InstallResult, apply: bool) -> None:
    manifest_path = target_root / "tools/agent-manifest.json"
    quickstart_path = target_root / "tools/AGENT_QUICKSTART.md"
    if not manifest_path.exists():
        result.add("manual review", manifest_path, "cannot render quickstart because tools/agent-manifest.json is missing")
        return
    rendered = _render_quickstart_for_repo(target_root)
    existing = quickstart_path.read_text(encoding="utf-8") if quickstart_path.exists() else None
    if existing == rendered:
        result.add("current", quickstart_path, "quickstart already matches manifest")
        return
    if not apply:
        result.add("would update", quickstart_path, "render quickstart from manifest")
        return
    quickstart_path.parent.mkdir(parents=True, exist_ok=True)
    quickstart_path.write_text(rendered, encoding="utf-8")
    result.add("updated" if existing is not None else "created", quickstart_path, "rendered quickstart from manifest")


def _run_planning_checker(target_root: Path) -> list[dict[str, str]]:
    checker_path = target_root / "scripts" / "check" / "check_planning_surfaces.py"
    if not checker_path.exists():
        return []
    spec = importlib.util.spec_from_file_location("planning_checker", checker_path)
    if spec is None or spec.loader is None:
        return [{"warning_class": "planning_checker_load_failure", "path": "scripts/check/check_planning_surfaces.py", "message": "Unable to load planning checker."}]
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [warning._asdict() for warning in module.gather_planning_warnings(repo_root=target_root)]


def _render_quickstart_for_repo(target_root: Path) -> str:
    script_path = target_root / "scripts" / "render_agent_docs.py"
    manifest_path = target_root / "tools" / "agent-manifest.json"
    if not script_path.exists() or not manifest_path.exists():
        return render_quickstart(load_manifest(manifest_path))
    spec = importlib.util.spec_from_file_location("render_agent_docs", script_path)
    if spec is None or spec.loader is None:
        return render_quickstart(load_manifest(manifest_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.render_quickstart(module.load_manifest())


def _has_unresolved_placeholders(text: str) -> bool:
    return bool(re.search(r"<[A-Z][A-Z0-9_]+>", text))
