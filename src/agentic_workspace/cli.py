from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_workspace import __version__
from agentic_workspace.result_adapter import adapt_module_result, serialise_value

MODULE_ORDER = ("planning", "memory")
PRESET_MODULES = {
    "memory": ["memory"],
    "planning": ["planning"],
    "full": ["planning", "memory"],
}
MODULE_SIGNAL_PATHS = {
    "planning": (
        Path("TODO.md"),
        Path("docs/execplans"),
        Path(".agentic-workspace/planning"),
    ),
    "memory": (
        Path("memory/index.md"),
        Path("memory/current"),
        Path(".agentic-workspace/memory"),
    ),
}
MODULE_COMMAND_ARGS = {
    "install": ("target", "dry_run", "force"),
    "adopt": ("target", "dry_run"),
    "upgrade": ("target", "dry_run"),
    "uninstall": ("target", "dry_run"),
    "doctor": ("target",),
    "status": ("target",),
}
PLACEHOLDER_RE = re.compile(r"<[A-Z][A-Z0-9_]+>")
WORKSPACE_PAYLOAD_FILES = (
    Path(".agentic-workspace/WORKFLOW.md"),
    Path(".agentic-workspace/OWNERSHIP.toml"),
)
WORKSPACE_AGENTS_PATH = Path("AGENTS.md")
WORKSPACE_WORKFLOW_MARKER_START = "<!-- agentic-workspace:workflow:start -->"
WORKSPACE_WORKFLOW_MARKER_END = "<!-- agentic-workspace:workflow:end -->"
WORKSPACE_POINTER_BLOCK = (
    f"{WORKSPACE_WORKFLOW_MARKER_START}\n"
    "Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules.\n"
    f"{WORKSPACE_WORKFLOW_MARKER_END}"
)
MEMORY_WORKFLOW_MARKER_START = "<!-- agentic-memory:workflow:start -->"
MEMORY_WORKFLOW_MARKER_END = "<!-- agentic-memory:workflow:end -->"
MEMORY_POINTER_BLOCK = (
    f"{MEMORY_WORKFLOW_MARKER_START}\n"
    "Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules.\n"
    f"{MEMORY_WORKFLOW_MARKER_END}"
)


@dataclass(frozen=True)
class ModuleDescriptor:
    name: str
    description: str
    commands: dict[str, Callable[..., Any]]
    detector: Callable[[Path], bool]
    install_signals: tuple[Path, ...]
    workflow_surfaces: tuple[Path, ...]
    generated_artifacts: tuple[Path, ...]
    command_args: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class RepoInspection:
    mode: str
    prompt_requirement: str
    detected_surfaces: list[str]
    preserved_existing: list[str]
    needs_review: list[str]
    placeholders: list[str]


@dataclass(frozen=True)
class ModuleRegistryEntry:
    name: str
    description: str
    lifecycle_commands: tuple[str, ...]
    autodetects_installation: bool
    installed: bool | None
    install_signals: tuple[Path, ...]
    workflow_surfaces: tuple[Path, ...]
    generated_artifacts: tuple[Path, ...]
    dry_run_commands: tuple[str, ...]
    force_commands: tuple[str, ...]


class ModuleSelectionError(ValueError):
    """Raised when the orchestrator cannot resolve a safe module set."""


class WorkspaceUsageError(ValueError):
    """Raised when workspace CLI preconditions are not met."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-workspace",
        description="Workspace-level lifecycle orchestrator for selected agentic-workspace modules.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    modules_parser = subparsers.add_parser("modules", help="List workspace modules available to the orchestrator.")
    modules_parser.add_argument("--target", help="Optional repository path used to report installed modules.")
    _add_format_argument(modules_parser)

    init_parser = subparsers.add_parser("init", help="Bootstrap selected modules into a target repository.")
    _add_selection_arguments(init_parser)
    init_parser.add_argument("--adopt", action="store_true", help="Force conservative adopt behavior.")
    init_parser.add_argument("--dry-run", action="store_true", help="Show planned changes without mutating files.")
    init_parser.add_argument("--print-prompt", action="store_true", help="Print the generated handoff prompt.")
    init_parser.add_argument("--write-prompt", help="Write the generated handoff prompt to a file.")

    status_parser = subparsers.add_parser("status", help="Report installed modules and workspace health summary.")
    _add_selection_arguments(status_parser)

    doctor_parser = subparsers.add_parser("doctor", help="Report drift, missing surfaces, and recommended remediation.")
    _add_selection_arguments(doctor_parser)

    upgrade_parser = subparsers.add_parser("upgrade", help="Refresh managed surfaces for selected installed modules.")
    _add_selection_arguments(upgrade_parser)
    upgrade_parser.add_argument("--dry-run", action="store_true", help="Show planned changes without mutating files.")

    uninstall_parser = subparsers.add_parser("uninstall", help="Remove managed surfaces conservatively for selected installed modules.")
    _add_selection_arguments(uninstall_parser)
    uninstall_parser.add_argument("--dry-run", action="store_true", help="Show planned changes without mutating files.")

    return parser


def _add_selection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--target", help="Target repository path. Defaults to the current directory.")
    parser.add_argument("--preset", choices=tuple(PRESET_MODULES), help="Named module bundle.")
    parser.add_argument("--modules", help="Comma-separated module selection.")
    _add_format_argument(parser)


def _add_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "modules":
        target_root = _resolve_target_root(args.target) if args.target else None
        if target_root is not None:
            _validate_target_root(command_name="modules", target_root=target_root)
        _emit_modules(format_name=args.format, target_root=target_root)
        return 0

    descriptors = _module_operations()
    try:
        target_root = _resolve_target_root(args.target)
        _validate_target_root(command_name=args.command, target_root=target_root)
        selected_modules, resolved_preset = _selected_modules(
            command_name=args.command,
            preset_name=args.preset,
            module_arg=args.modules,
            target_root=target_root,
            descriptors=descriptors,
        )
    except (ModuleSelectionError, WorkspaceUsageError) as exc:
        parser.error(str(exc))

    if args.command == "init":
        payload = _run_init(
            target_root=target_root,
            selected_modules=selected_modules,
            resolved_preset=resolved_preset,
            descriptors=descriptors,
            dry_run=args.dry_run,
            force_adopt=args.adopt,
            print_prompt=args.print_prompt,
            write_prompt=args.write_prompt,
        )
        _emit_payload(payload=payload, format_name=args.format)
        return 0

    payload = _run_lifecycle_command(
        command_name=args.command,
        target_root=target_root,
        selected_modules=selected_modules,
        resolved_preset=resolved_preset,
        descriptors=descriptors,
        dry_run=bool(getattr(args, "dry_run", False)),
    )
    _emit_payload(payload=payload, format_name=args.format)
    return 0


def _module_operations() -> dict[str, ModuleDescriptor]:
    from repo_memory_bootstrap.installer import (
        adopt_bootstrap as memory_adopt_bootstrap,
    )
    from repo_memory_bootstrap.installer import (
        collect_status as memory_collect_status,
    )
    from repo_memory_bootstrap.installer import (
        doctor_bootstrap as memory_doctor_bootstrap,
    )
    from repo_memory_bootstrap.installer import (
        install_bootstrap as memory_install_bootstrap,
    )
    from repo_memory_bootstrap.installer import (
        uninstall_bootstrap as memory_uninstall_bootstrap,
    )
    from repo_memory_bootstrap.installer import (
        upgrade_bootstrap as memory_upgrade_bootstrap,
    )
    from repo_planning_bootstrap.installer import (
        adopt_bootstrap as planning_adopt_bootstrap,
    )
    from repo_planning_bootstrap.installer import (
        collect_status as planning_collect_status,
    )
    from repo_planning_bootstrap.installer import (
        doctor_bootstrap as planning_doctor_bootstrap,
    )
    from repo_planning_bootstrap.installer import (
        install_bootstrap as planning_install_bootstrap,
    )
    from repo_planning_bootstrap.installer import (
        uninstall_bootstrap as planning_uninstall_bootstrap,
    )
    from repo_planning_bootstrap.installer import (
        upgrade_bootstrap as planning_upgrade_bootstrap,
    )

    return {
        "planning": _build_module_descriptor(
            name="planning",
            description="Repo-native execution planning bootstrap and maintenance.",
            install_handler=planning_install_bootstrap,
            adopt_handler=planning_adopt_bootstrap,
            upgrade_handler=planning_upgrade_bootstrap,
            uninstall_handler=planning_uninstall_bootstrap,
            doctor_handler=planning_doctor_bootstrap,
            status_handler=planning_collect_status,
            detector=lambda target_root: (
                (target_root / "TODO.md").exists()
                and (target_root / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
            ),
            install_signals=MODULE_SIGNAL_PATHS["planning"],
            workflow_surfaces=(
                Path("AGENTS.md"),
                Path("TODO.md"),
                Path("ROADMAP.md"),
                Path("docs/execplans"),
                Path("docs/contributor-playbook.md"),
                Path("docs/maintainer-commands.md"),
                Path(".agentic-workspace/planning"),
                Path("tools/AGENT_QUICKSTART.md"),
                Path("tools/AGENT_ROUTING.md"),
            ),
            generated_artifacts=(
                Path("tools/agent-manifest.json"),
                Path("tools/AGENT_QUICKSTART.md"),
                Path("tools/AGENT_ROUTING.md"),
            ),
        ),
        "memory": _build_module_descriptor(
            name="memory",
            description="Durable repository knowledge bootstrap and maintenance.",
            install_handler=memory_install_bootstrap,
            adopt_handler=memory_adopt_bootstrap,
            upgrade_handler=memory_upgrade_bootstrap,
            uninstall_handler=memory_uninstall_bootstrap,
            doctor_handler=memory_doctor_bootstrap,
            status_handler=memory_collect_status,
            detector=lambda target_root: (
                (target_root / "memory" / "index.md").exists() and (target_root / ".agentic-workspace" / "memory").exists()
            ),
            install_signals=MODULE_SIGNAL_PATHS["memory"],
            workflow_surfaces=(
                Path("AGENTS.md"),
                Path("memory/index.md"),
                Path("memory/current"),
                Path(".agentic-workspace/memory"),
            ),
            generated_artifacts=(),
        ),
    }


def _build_module_descriptor(
    *,
    name: str,
    description: str,
    install_handler: Callable[..., Any],
    adopt_handler: Callable[..., Any],
    upgrade_handler: Callable[..., Any],
    uninstall_handler: Callable[..., Any],
    doctor_handler: Callable[..., Any],
    status_handler: Callable[..., Any],
    detector: Callable[[Path], bool],
    install_signals: tuple[Path, ...],
    workflow_surfaces: tuple[Path, ...],
    generated_artifacts: tuple[Path, ...],
) -> ModuleDescriptor:
    return ModuleDescriptor(
        name=name,
        description=description,
        commands={
            "install": lambda *, target, dry_run, force: install_handler(target=target, dry_run=dry_run, force=force),
            "adopt": lambda *, target, dry_run: adopt_handler(target=target, dry_run=dry_run),
            "upgrade": lambda *, target, dry_run: upgrade_handler(target=target, dry_run=dry_run),
            "uninstall": lambda *, target, dry_run: uninstall_handler(target=target, dry_run=dry_run),
            "doctor": lambda *, target: doctor_handler(target=target),
            "status": lambda *, target: status_handler(target=target),
        },
        detector=detector,
        install_signals=install_signals,
        workflow_surfaces=workflow_surfaces,
        generated_artifacts=generated_artifacts,
        command_args=MODULE_COMMAND_ARGS,
    )


def _workspace_payload_root() -> Path:
    return Path(__file__).resolve().parent / "_payload"


def _workspace_payload_source(relative: Path) -> Path:
    return _workspace_payload_root() / relative


def _workspace_payload_bytes(relative: Path) -> bytes:
    return _workspace_payload_source(relative).read_bytes()


def _workspace_report(
    *,
    target_root: Path,
    message: str,
    dry_run: bool,
    actions: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "module": "workspace",
        "message": message,
        "target_root": target_root.as_posix(),
        "dry_run": dry_run,
        "actions": actions,
        "warnings": warnings,
    }


def _workspace_agents_template(*, selected_modules: list[str]) -> str:
    startup_steps = ["Read `AGENTS.md`."]
    sources_of_truth: list[str] = []
    repo_rules = [
        "Keep package boundaries explicit.",
        "Preserve independent package versioning and CLI entry points.",
    ]
    validation_rules = [
        "Run the narrowest validation that proves a change.",
        "Prefer package-local checks after package import.",
        "Add broader cross-package checks only when the change crosses package boundaries.",
    ]

    if "planning" in selected_modules:
        startup_steps.extend(
            [
                "Read `TODO.md`.",
                "Read the active feature plan in `docs/execplans/` when the TODO surface points there.",
                "Read `ROADMAP.md` only when promoting work.",
            ]
        )
        sources_of_truth.extend(
            [
                "Active queue: `TODO.md`",
                "Long-horizon candidate work: `ROADMAP.md`",
            ]
        )
    if "memory" in selected_modules:
        startup_steps.extend(
            [
                "Read `memory/index.md` only when memory is installed and the task is not already well-routed.",
                "Read `.agentic-workspace/memory/WORKFLOW.md` only when changing memory behavior or the memory workflow itself.",
            ]
        )
        sources_of_truth.append("Durable routed knowledge, when installed: `memory/index.md`")

    startup_steps.append("Load package-local docs only for the package being edited.")

    lines = [
        "# Agent Instructions",
        "",
        WORKSPACE_POINTER_BLOCK,
    ]
    if "memory" in selected_modules:
        lines.extend(["", MEMORY_POINTER_BLOCK])
    lines.extend(
        [
            "",
            "Local bootstrap contract for agents working in this repository.",
            "",
            "## Precedence",
            "",
            "1. Explicit user request.",
            "2. `AGENTS.md`.",
            "3. Package-local `AGENTS.md` under `packages/*/` once imported.",
            "4. Routed memory or canonical repo docs when present.",
            "",
            "## Startup Procedure",
            "",
        ]
    )
    lines.extend(f"{index}. {step}" for index, step in enumerate(startup_steps, start=1))
    lines.extend(
        [
            "",
            "Do not bulk-read all planning surfaces.",
            "Do not start coding from chat context alone when the same information exists in checked-in files.",
            "",
            "## Sources Of Truth",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in sources_of_truth)
    lines.extend(
        [
            "",
            "## Repo Rules",
            "",
        ]
    )
    lines.extend(f"- {rule}" for rule in repo_rules)
    lines.extend(
        [
            "",
            "## Validation",
            "",
        ]
    )
    lines.extend(f"- {rule}" for rule in validation_rules)
    return "\n".join(lines) + "\n"


def _replace_or_insert_fenced_block(*, text: str, block: str, start_marker: str, end_marker: str) -> tuple[str, bool]:
    fenced_re = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    existing = fenced_re.search(text)
    if existing:
        current = existing.group(0).strip()
        if current == block:
            return text, False
        return fenced_re.sub(block, text, count=1), True

    stripped = text.lstrip()
    if stripped.startswith("# "):
        lines = text.splitlines()
        if len(lines) == 1:
            return f"{lines[0]}\n\n{block}\n", True
        return "\n".join([lines[0], "", block, *lines[1:]]) + "\n", True
    prefix = "" if not text else text.rstrip() + "\n\n"
    return prefix + block + "\n", True


def _workspace_status_report(*, target_root: Path, selected_modules: list[str], command_name: str) -> dict[str, Any]:
    actions: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for relative in WORKSPACE_PAYLOAD_FILES:
        path = target_root / relative
        exists = path.exists()
        actions.append(
            {
                "kind": "current" if exists else "missing",
                "path": relative.as_posix(),
                "detail": "required workspace file present" if exists else "required workspace file missing",
            }
        )
        if not exists:
            warnings.append({"path": relative.as_posix(), "message": "required workspace file missing"})

    agents_path = target_root / WORKSPACE_AGENTS_PATH
    if not agents_path.exists():
        actions.append({"kind": "missing", "path": WORKSPACE_AGENTS_PATH.as_posix(), "detail": "root AGENTS.md entrypoint missing"})
        warnings.append({"path": WORKSPACE_AGENTS_PATH.as_posix(), "message": "root AGENTS.md entrypoint missing"})
        return _workspace_report(
            target_root=target_root,
            message=f"{command_name.title()} report",
            dry_run=False,
            actions=actions,
            warnings=warnings,
        )

    agents_text = agents_path.read_text(encoding="utf-8")
    if WORKSPACE_POINTER_BLOCK in agents_text:
        actions.append(
                {
                    "kind": "current",
                    "path": WORKSPACE_AGENTS_PATH.as_posix(),
                    "detail": "workspace workflow pointer block present",
                }
        )
    else:
        actions.append(
                {
                    "kind": "warning",
                    "path": WORKSPACE_AGENTS_PATH.as_posix(),
                    "detail": "workspace workflow pointer block missing",
                }
        )
        warnings.append({"path": WORKSPACE_AGENTS_PATH.as_posix(), "message": "workspace workflow pointer block missing"})

    if "memory" in selected_modules:
        if MEMORY_POINTER_BLOCK in agents_text:
            actions.append(
                {
                    "kind": "current",
                    "path": WORKSPACE_AGENTS_PATH.as_posix(),
                    "detail": "memory workflow pointer block present",
                }
            )
        else:
            actions.append(
                {
                    "kind": "warning",
                    "path": WORKSPACE_AGENTS_PATH.as_posix(),
                    "detail": "memory workflow pointer block missing",
                }
            )
            warnings.append({"path": WORKSPACE_AGENTS_PATH.as_posix(), "message": "memory workflow pointer block missing"})

    return _workspace_report(
        target_root=target_root,
        message=f"{command_name.title()} report",
        dry_run=False,
        actions=actions,
        warnings=warnings,
    )


def _write_action_kind(*, dry_run: bool, existing: str | None) -> str:
    if dry_run:
        return "would create" if existing is None else "would update"
    return "created" if existing is None else "updated"


def _workspace_init_or_upgrade_report(
    *,
    target_root: Path,
    selected_modules: list[str],
    dry_run: bool,
    inspection_mode: str,
    command_name: str,
) -> dict[str, Any]:
    actions: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    conservative = inspection_mode != "install" and command_name == "init"

    for relative in WORKSPACE_PAYLOAD_FILES:
        destination = target_root / relative
        source_bytes = _workspace_payload_bytes(relative)
        existing = destination.exists()
        if not existing:
            if not dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source_bytes)
            actions.append(
                {
                    "kind": "would create" if dry_run else "created",
                    "path": relative.as_posix(),
                    "detail": "install workspace shared-layer file",
                }
            )
            continue
        if destination.read_bytes() == source_bytes:
            actions.append({"kind": "current", "path": relative.as_posix(), "detail": "workspace shared-layer file already current"})
            continue
        if conservative:
            actions.append(
                {
                    "kind": "manual review",
                    "path": relative.as_posix(),
                    "detail": "existing workspace shared-layer file differs from managed payload",
                }
            )
            continue
        if not dry_run:
            destination.write_bytes(source_bytes)
        actions.append(
                {
                    "kind": "would update" if dry_run else "updated",
                    "path": relative.as_posix(),
                    "detail": "refresh workspace shared-layer file from package payload",
                }
            )

    agents_path = target_root / WORKSPACE_AGENTS_PATH
    rendered_agents = _workspace_agents_template(selected_modules=selected_modules)
    existing_agents = agents_path.read_text(encoding="utf-8") if agents_path.exists() else None
    if inspection_mode == "install" or command_name == "upgrade":
        if existing_agents != rendered_agents:
            if not dry_run:
                agents_path.parent.mkdir(parents=True, exist_ok=True)
                agents_path.write_text(rendered_agents, encoding="utf-8")
            actions.append(
                {
                    "kind": _write_action_kind(dry_run=dry_run, existing=existing_agents),
                    "path": WORKSPACE_AGENTS_PATH.as_posix(),
                    "detail": "refresh composed root AGENTS.md entrypoint for selected workspace modules",
                }
            )
        else:
            actions.append(
                {
                    "kind": "current",
                    "path": WORKSPACE_AGENTS_PATH.as_posix(),
                    "detail": "composed root AGENTS.md entrypoint already current",
                }
            )
    else:
        base_text = existing_agents or ""
        updated_text, changed = _replace_or_insert_fenced_block(
            text=base_text,
            block=WORKSPACE_POINTER_BLOCK,
            start_marker=WORKSPACE_WORKFLOW_MARKER_START,
            end_marker=WORKSPACE_WORKFLOW_MARKER_END,
        )
        if "memory" in selected_modules:
            updated_text, memory_changed = _replace_or_insert_fenced_block(
                text=updated_text,
                block=MEMORY_POINTER_BLOCK,
                start_marker=MEMORY_WORKFLOW_MARKER_START,
                end_marker=MEMORY_WORKFLOW_MARKER_END,
            )
            changed = changed or memory_changed
        if changed:
            if not dry_run:
                agents_path.parent.mkdir(parents=True, exist_ok=True)
                agents_path.write_text(updated_text, encoding="utf-8")
            actions.append(
                {
                    "kind": _write_action_kind(dry_run=dry_run, existing=existing_agents),
                    "path": WORKSPACE_AGENTS_PATH.as_posix(),
                    "detail": "patched workflow pointer blocks into AGENTS.md without replacing repo-owned content",
                }
            )
        elif existing_agents is not None:
            actions.append(
                {
                    "kind": "current",
                    "path": WORKSPACE_AGENTS_PATH.as_posix(),
                    "detail": "workflow pointer blocks already present in AGENTS.md",
                }
            )

    return _workspace_report(
        target_root=target_root,
        message=f"{command_name.title()} report",
        dry_run=dry_run,
        actions=actions,
        warnings=warnings,
    )


def _workspace_uninstall_report(*, target_root: Path, dry_run: bool) -> dict[str, Any]:
    actions: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    removable: list[Path] = []

    for relative in WORKSPACE_PAYLOAD_FILES:
        destination = target_root / relative
        if not destination.exists():
            actions.append({"kind": "skipped", "path": destination.as_posix(), "detail": "already absent"})
            continue
        if destination.read_bytes() == _workspace_payload_bytes(relative):
            removable.append(relative)
            actions.append(
                {
                    "kind": "would remove" if dry_run else "removed",
                    "path": relative.as_posix(),
                    "detail": "matches managed workspace payload content",
                }
            )
            continue
        actions.append(
            {
                "kind": "manual review",
                "path": relative.as_posix(),
                "detail": "local workspace shared-layer file differs from managed payload; remove manually if intended",
            }
        )

    if not dry_run:
        for relative in removable:
            destination = target_root / relative
            if destination.exists():
                destination.unlink()
        _prune_empty_parent_dirs(target_root=target_root, relatives=removable)

    return _workspace_report(
        target_root=target_root,
        message="Uninstall report",
        dry_run=dry_run,
        actions=actions,
        warnings=warnings,
    )


def _selected_modules(
    *,
    command_name: str,
    preset_name: str | None,
    module_arg: str | None,
    target_root: Path,
    descriptors: dict[str, ModuleDescriptor],
) -> tuple[list[str], str | None]:
    if preset_name and module_arg:
        raise ModuleSelectionError("Use either --preset or --modules, not both.")

    if preset_name:
        return [module_name for module_name in PRESET_MODULES[preset_name] if module_name in descriptors], preset_name

    if module_arg:
        requested = _parse_modules(module_arg)
        return [module_name for module_name in MODULE_ORDER if module_name in requested and module_name in descriptors], None

    if command_name == "init":
        return [module_name for module_name in PRESET_MODULES["full"] if module_name in descriptors], "full"

    registry = _module_registry(descriptors=descriptors, target_root=target_root)
    detected = [entry.name for entry in registry if entry.installed]
    if detected:
        return detected, None

    raise ModuleSelectionError("No installed modules were detected for this lifecycle command. Use --modules to target modules explicitly.")


def _parse_modules(module_arg: str) -> set[str]:
    tokens = [token.strip() for token in module_arg.split(",") if token.strip()]
    if not tokens:
        raise ModuleSelectionError("--modules requires at least one module token.")

    unknown = [token for token in tokens if token not in MODULE_ORDER]
    if unknown:
        supported = ", ".join(MODULE_ORDER)
        unknown_text = ", ".join(sorted(set(unknown)))
        raise ModuleSelectionError(f"Unknown module token(s): {unknown_text}. Supported modules: {supported}.")

    return set(tokens)


def _resolve_target_root(target: str | None) -> Path:
    return Path(target).resolve() if target else Path.cwd().resolve()


def _validate_target_root(*, command_name: str, target_root: Path) -> None:
    if not target_root.exists():
        raise WorkspaceUsageError(f"Target path does not exist: {target_root}")
    if not target_root.is_dir():
        raise WorkspaceUsageError(f"Target path is not a directory: {target_root}")
    if command_name in {"init", "status", "doctor", "upgrade", "uninstall"} and not _is_git_repo_root(target_root):
        raise WorkspaceUsageError("Target must be a git repository root with a .git directory or file.")


def _is_git_repo_root(target_root: Path) -> bool:
    return (target_root / ".git").exists()


def _run_init(
    *,
    target_root: Path,
    selected_modules: list[str],
    resolved_preset: str | None,
    descriptors: dict[str, ModuleDescriptor],
    dry_run: bool,
    force_adopt: bool,
    print_prompt: bool,
    write_prompt: str | None,
) -> dict[str, Any]:
    inspection = _inspect_repo_state(
        target_root=target_root,
        selected_modules=selected_modules,
        descriptors=descriptors,
        force_adopt=force_adopt,
    )
    module_command = "install" if inspection.mode == "install" else "adopt"
    reports = [
        _invoke_module_command(
            command_name=module_command,
            module_name=module_name,
            descriptor=descriptors[module_name],
            target_root=target_root,
            dry_run=dry_run,
            force=False,
        )
        for module_name in selected_modules
    ]
    reports.append(
        _workspace_init_or_upgrade_report(
            target_root=target_root,
            selected_modules=selected_modules,
            dry_run=dry_run,
            inspection_mode=inspection.mode,
            command_name="init",
        )
    )
    summary = _build_init_summary(
        target_root=target_root,
        selected_modules=selected_modules,
        resolved_preset=resolved_preset,
        descriptors=descriptors,
        inspection=inspection,
        reports=reports,
    )
    prompt_text = _build_handoff_prompt(summary)
    prompt_path = _write_prompt_file(write_prompt=write_prompt, prompt_text=prompt_text) if write_prompt else None
    payload: dict[str, Any] = summary | {
        "dry_run": dry_run,
        "module_reports": reports,
    }
    should_include_prompt = print_prompt or prompt_path is not None or summary["prompt_requirement"] != "none"
    if should_include_prompt:
        payload["handoff_prompt"] = prompt_text
    if prompt_path is not None:
        payload["handoff_prompt_path"] = prompt_path.as_posix()
        payload["next_steps"].append(f"Review the written handoff prompt at {prompt_path.as_posix()}.")
    return payload


def _inspect_repo_state(
    *,
    target_root: Path,
    selected_modules: list[str],
    descriptors: dict[str, ModuleDescriptor],
    force_adopt: bool,
) -> RepoInspection:
    workflow_surfaces = _module_workflow_surfaces(selected_modules=selected_modules, descriptors=descriptors)
    generated_artifacts = _module_generated_artifacts(selected_modules=selected_modules, descriptors=descriptors)
    detected_surfaces = [path.as_posix() for path in workflow_surfaces if (target_root / path).exists()]
    preserved_existing = [path for path in detected_surfaces if path not in generated_artifacts]
    partial_state: list[str] = []
    for module_name in selected_modules:
        descriptor = descriptors[module_name]
        installed = descriptor.detector(target_root)
        hits = [marker.as_posix() for marker in descriptor.install_signals if (target_root / marker).exists()]
        if hits and not installed:
            partial_state.extend(hits)

    placeholders = _detect_placeholder_surfaces(target_root=target_root, surfaces=detected_surfaces)
    overlap_count = len(preserved_existing)
    managed_root_present = (target_root / ".agentic-workspace").exists()
    high_ambiguity = bool(partial_state) or bool(placeholders) or overlap_count >= 4 or (managed_root_present and overlap_count >= 2)

    if not preserved_existing and not force_adopt:
        mode = "install"
    elif high_ambiguity:
        mode = "adopt_high_ambiguity"
    else:
        mode = "adopt"

    prompt_requirement = {
        "install": "none",
        "adopt": "recommended",
        "adopt_high_ambiguity": "required",
    }[mode]
    if partial_state or placeholders:
        prompt_requirement = "required"

    needs_review = [f"{path}: partial module state detected" for path in _dedupe(partial_state)]
    if mode == "adopt_high_ambiguity":
        needs_review.extend(f"{path}: reconcile existing workflow surface ownership" for path in preserved_existing)

    return RepoInspection(
        mode=mode,
        prompt_requirement=prompt_requirement,
        detected_surfaces=detected_surfaces,
        preserved_existing=_dedupe(preserved_existing),
        needs_review=_dedupe(needs_review),
        placeholders=_dedupe(placeholders),
    )


def _detect_placeholder_surfaces(*, target_root: Path, surfaces: list[str]) -> list[str]:
    placeholders: list[str] = []
    for surface in surfaces:
        path = target_root / surface
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PLACEHOLDER_RE.search(text):
            placeholders.append(path.relative_to(target_root).as_posix())
    return placeholders


def _build_init_summary(
    *,
    target_root: Path,
    selected_modules: list[str],
    resolved_preset: str | None,
    descriptors: dict[str, ModuleDescriptor],
    inspection: RepoInspection,
    reports: list[dict[str, Any]],
) -> dict[str, Any]:
    created: list[str] = []
    updated_managed: list[str] = []
    preserved_existing = list(inspection.preserved_existing)
    needs_review = list(inspection.needs_review)
    placeholders = list(inspection.placeholders)
    generated_artifacts: list[str] = []

    for report in reports:
        descriptor = descriptors.get(str(report.get("module", "")))
        module_generated_artifacts = {path.as_posix() for path in descriptor.generated_artifacts} if descriptor else set()
        for action in report["actions"]:
            relative_path = _display_path(action.get("path", "."), target_root)
            detail = str(action.get("detail", ""))
            kind = str(action.get("kind", ""))
            if _is_generated_artifact(
                relative_path=relative_path,
                detail=detail,
                generated_artifacts=module_generated_artifacts,
            ):
                _append_unique(generated_artifacts, relative_path)
            if _is_placeholder_issue(detail=detail):
                _append_unique(placeholders, relative_path)
            if kind in {"created", "copied", "would create", "would copy"}:
                _append_unique(created, relative_path)
                continue
            if kind in {"updated", "overwritten", "would update", "would overwrite"}:
                _append_unique(updated_managed, relative_path)
                continue
            if kind == "skipped":
                _append_unique(preserved_existing, relative_path)
                continue
            if kind in {"manual review", "missing", "warning"}:
                _append_unique(needs_review, _format_issue(relative_path=relative_path, detail=detail))

        for warning in report["warnings"]:
            relative_path = _display_path(warning.get("path", "."), target_root)
            message = str(warning.get("message", "needs review"))
            if _is_placeholder_issue(detail=message):
                _append_unique(placeholders, relative_path)
            _append_unique(needs_review, _format_issue(relative_path=relative_path, detail=message))

    prompt_requirement = inspection.prompt_requirement
    if placeholders or any(": partial module state detected" in issue for issue in needs_review):
        prompt_requirement = "required"
    elif prompt_requirement == "none" and (preserved_existing or needs_review):
        prompt_requirement = "recommended"

    return {
        "command": "init",
        "target": target_root.as_posix(),
        "modules": selected_modules,
        "preset": resolved_preset,
        "mode": inspection.mode,
        "prompt_requirement": prompt_requirement,
        "detected_surfaces": inspection.detected_surfaces,
        "created": _dedupe(created),
        "updated_managed": _dedupe(updated_managed),
        "preserved_existing": _dedupe(preserved_existing),
        "needs_review": _dedupe(needs_review),
        "placeholders": _dedupe(placeholders),
        "generated_artifacts": _dedupe(generated_artifacts),
        "validation": _validation_commands(target_root=target_root),
        "next_steps": _init_next_steps(
            target_root=target_root,
            mode=inspection.mode,
            prompt_requirement=prompt_requirement,
            needs_review=needs_review,
            placeholders=placeholders,
        ),
    }


def _run_lifecycle_command(
    *,
    command_name: str,
    target_root: Path,
    selected_modules: list[str],
    resolved_preset: str | None,
    descriptors: dict[str, ModuleDescriptor],
    dry_run: bool,
) -> dict[str, Any]:
    registry = _module_registry(descriptors=descriptors, target_root=target_root)
    reports = [
        _invoke_module_command(
            command_name=command_name,
            module_name=module_name,
            descriptor=descriptors[module_name],
            target_root=target_root,
            dry_run=dry_run,
            force=False,
        )
        for module_name in selected_modules
    ]
    if command_name in {"status", "doctor"}:
        reports.append(_workspace_status_report(target_root=target_root, selected_modules=selected_modules, command_name=command_name))
    elif command_name == "upgrade":
        reports.append(
            _workspace_init_or_upgrade_report(
                target_root=target_root,
                selected_modules=selected_modules,
                dry_run=dry_run,
                inspection_mode="upgrade",
                command_name=command_name,
            )
        )
    elif command_name == "uninstall":
        reports.append(_workspace_uninstall_report(target_root=target_root, dry_run=dry_run))
    summary = _summarise_reports(target_root=target_root, reports=reports, descriptors=descriptors)
    warnings: list[str] = []
    placeholders: list[str] = []
    stale_generated_surfaces: list[str] = []
    warnings.extend(summary["warnings"])
    placeholders.extend(summary["placeholders"])
    stale_generated_surfaces.extend(summary["stale_generated_surfaces"])

    return {
        "command": command_name,
        "target": target_root.as_posix(),
        "modules": selected_modules,
        "preset": resolved_preset,
        "dry_run": dry_run,
        "health": "healthy" if not warnings else "attention-needed",
        "created": summary["created"],
        "updated_managed": summary["updated_managed"],
        "preserved_existing": summary["preserved_existing"],
        "needs_review": summary["needs_review"],
        "generated_artifacts": summary["generated_artifacts"],
        "warnings": warnings,
        "placeholders": placeholders,
        "stale_generated_surfaces": stale_generated_surfaces,
        "registry": [
            {
                "name": entry.name,
                "description": entry.description,
                "commands": list(entry.lifecycle_commands),
                "autodetects_installation": entry.autodetects_installation,
                "installed": entry.installed,
                "dry_run_commands": list(entry.dry_run_commands),
                "force_commands": list(entry.force_commands),
            }
            for entry in registry
        ],
        "next_steps": _lifecycle_next_steps(command_name=command_name, target_root=target_root, warnings=warnings),
        "reports": reports,
    }


def _summarise_reports(
    *, target_root: Path, reports: list[dict[str, Any]], descriptors: dict[str, ModuleDescriptor]
) -> dict[str, list[str]]:
    created: list[str] = []
    updated_managed: list[str] = []
    preserved_existing: list[str] = []
    needs_review: list[str] = []
    generated_artifacts: list[str] = []
    warnings: list[str] = []
    placeholders: list[str] = []
    stale_generated_surfaces: list[str] = []

    for report in reports:
        descriptor = descriptors.get(str(report.get("module", "")))
        module_generated_artifacts = {path.as_posix() for path in descriptor.generated_artifacts} if descriptor else set()
        for action in report["actions"]:
            relative_path = _display_path(action.get("path", "."), target_root)
            detail = str(action.get("detail", ""))
            kind = str(action.get("kind", ""))
            if _is_generated_artifact(
                relative_path=relative_path,
                detail=detail,
                generated_artifacts=module_generated_artifacts,
            ):
                _append_unique(generated_artifacts, relative_path)
            if _is_placeholder_issue(detail=detail):
                _append_unique(placeholders, relative_path)
            if kind in {"created", "copied", "would create", "would copy"}:
                _append_unique(created, relative_path)
            elif kind in {"updated", "overwritten", "would update", "would overwrite"}:
                _append_unique(updated_managed, relative_path)
            elif kind == "skipped":
                _append_unique(preserved_existing, relative_path)
            elif kind in {"manual review", "missing", "warning"}:
                issue = _format_issue(relative_path=relative_path, detail=detail)
                _append_unique(needs_review, issue)
                if kind in {"missing", "warning"}:
                    _append_unique(warnings, issue)
            if _is_generated_artifact(
                relative_path=relative_path,
                detail=detail,
                generated_artifacts=module_generated_artifacts,
            ) and kind in {"manual review", "warning", "updated", "would update"}:
                _append_unique(stale_generated_surfaces, relative_path)

        for warning in report["warnings"]:
            relative_path = _display_path(warning.get("path", "."), target_root)
            message = str(warning.get("message", "needs review"))
            issue = _format_issue(relative_path=relative_path, detail=message)
            _append_unique(needs_review, issue)
            _append_unique(warnings, issue)
            if _is_placeholder_issue(detail=message):
                _append_unique(placeholders, relative_path)

    return {
        "created": _dedupe(created),
        "updated_managed": _dedupe(updated_managed),
        "preserved_existing": _dedupe(preserved_existing),
        "needs_review": _dedupe(needs_review),
        "generated_artifacts": _dedupe(generated_artifacts),
        "warnings": _dedupe(warnings),
        "placeholders": _dedupe(placeholders),
        "stale_generated_surfaces": _dedupe(stale_generated_surfaces),
    }


def _invoke_module_command(
    *,
    command_name: str,
    module_name: str,
    descriptor: ModuleDescriptor,
    target_root: Path,
    dry_run: bool,
    force: bool,
) -> dict[str, Any]:
    command = descriptor.commands[command_name]
    kwargs: dict[str, Any] = {}
    for argument_name in descriptor.command_args[command_name]:
        if argument_name == "target":
            kwargs[argument_name] = str(target_root)
        elif argument_name == "dry_run":
            kwargs[argument_name] = dry_run
        elif argument_name == "force":
            kwargs[argument_name] = force
    result = command(**kwargs)
    return adapt_module_result(module=module_name, result=result).to_dict()


def _validation_commands(*, target_root: Path) -> list[str]:
    target = target_root.as_posix()
    return [
        f"agentic-workspace doctor --target {target}",
        f"agentic-workspace status --target {target}",
    ]


def _init_next_steps(
    *,
    target_root: Path,
    mode: str,
    prompt_requirement: str,
    needs_review: list[str],
    placeholders: list[str],
) -> list[str]:
    target = target_root.as_posix()
    steps = [f"Run agentic-workspace doctor --target {target} after bootstrap changes settle."]
    if prompt_requirement == "none":
        steps.append("Tell your coding agent to use the installed workflow surfaces directly for normal work.")
        return steps
    if mode == "adopt_high_ambiguity":
        steps.append("Paste the generated handoff prompt into your coding agent and treat the finishing pass as required.")
    else:
        steps.append("Review preserved and review-needed workflow surfaces before treating bootstrap as complete.")
        steps.append("Paste the generated handoff prompt into your coding agent if repo-specific reconciliation is still needed.")
    if placeholders:
        steps.append("Resolve remaining placeholders or bootstrap markers before normal workflow begins.")
    elif needs_review:
        steps.append("Close out the listed review items before relying on the installed lifecycle flow.")
    return steps


def _lifecycle_next_steps(*, command_name: str, target_root: Path, warnings: list[str]) -> list[str]:
    target = target_root.as_posix()
    if command_name == "status":
        return [] if not warnings else [f"Run agentic-workspace doctor --target {target} to inspect the reported warnings."]
    if command_name == "doctor":
        return [] if not warnings else ["Review the warning list and apply the narrowest remediation that closes each issue."]
    if command_name == "upgrade":
        return [f"Run agentic-workspace doctor --target {target} after the refresh completes."]
    if command_name == "uninstall":
        return ["Manually review any preserved repo-owned content before deleting it."]
    return []


def _build_handoff_prompt(summary: dict[str, Any]) -> str:
    lines = [f"Finish the Agentic Workspace bootstrap in {summary['target']}.", "", "Selected modules:"]
    lines.extend(f"- {module_name}" for module_name in summary["modules"])
    lines.extend(["", "Bootstrap mode:", f"- {summary['mode']}", "", "The CLI already:"])
    for path in summary["created"]:
        lines.append(f"- created {path}")
    for path in summary["updated_managed"]:
        lines.append(f"- refreshed {path}")
    for path in summary["preserved_existing"]:
        lines.append(f"- preserved {path}")
    for path in summary["generated_artifacts"]:
        lines.append(f"- rendered {path}")
    review_items = list(summary["needs_review"])
    review_items.extend(f"{path}: unresolved placeholder or bootstrap marker" for path in summary["placeholders"])
    if review_items:
        lines.extend(["", "Review and finish:"])
        lines.extend(f"- {item}" for item in review_items)
    lines.extend(
        [
            "",
            "Rules:",
            "- do not overwrite preserved repo-owned surfaces blindly",
            "- prefer conservative merge over replacement when existing docs overlap",
            "- do not edit generated files manually when a canonical source exists",
            "- keep planning and memory boundaries explicit",
            "- avoid creating duplicate source-of-truth workflow surfaces",
            "",
            "Validation:",
        ]
    )
    lines.extend(f"- {command}" for command in summary["validation"])
    lines.extend(["", "When done:"])
    if summary["placeholders"]:
        lines.append("- remove or resolve any remaining placeholders before closing the bootstrap task")
    lines.append("- leave only durable workflow residue; do not keep temporary bootstrap notes around")
    return "\n".join(lines)


def _write_prompt_file(*, write_prompt: str, prompt_text: str) -> Path:
    prompt_path = Path(write_prompt).expanduser().resolve()
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt_text + "\n", encoding="utf-8")
    return prompt_path


def _emit_modules(*, format_name: str, target_root: Path | None) -> None:
    descriptors = _module_operations()
    registry = _module_registry(descriptors=descriptors, target_root=target_root)
    payload = {
        "modules": [
            {
                "name": entry.name,
                "description": entry.description,
                "commands": list(entry.lifecycle_commands),
                "autodetects_installation": entry.autodetects_installation,
                "installed": entry.installed,
                "install_signals": [path.as_posix() for path in entry.install_signals],
                "workflow_surfaces": [path.as_posix() for path in entry.workflow_surfaces],
                "generated_artifacts": [path.as_posix() for path in entry.generated_artifacts],
                "dry_run_commands": list(entry.dry_run_commands),
                "force_commands": list(entry.force_commands),
                "command_args": {name: list(args) for name, args in descriptors[entry.name].command_args.items()},
            }
            for entry in registry
        ]
    }
    _emit_payload(payload=payload, format_name=format_name)


def _module_registry(
    *, descriptors: dict[str, ModuleDescriptor], target_root: Path | None
) -> list[ModuleRegistryEntry]:
    entries: list[ModuleRegistryEntry] = []
    for module_name in MODULE_ORDER:
        if module_name not in descriptors:
            continue
        descriptor = descriptors[module_name]
        lifecycle_commands = tuple(sorted(descriptor.commands))
        dry_run_commands = tuple(
            command_name for command_name in lifecycle_commands if "dry_run" in descriptor.command_args[command_name]
        )
        force_commands = tuple(
            command_name for command_name in lifecycle_commands if "force" in descriptor.command_args[command_name]
        )
        installed = descriptor.detector(target_root) if target_root is not None else None
        entries.append(
            ModuleRegistryEntry(
                name=descriptor.name,
                description=descriptor.description,
                lifecycle_commands=lifecycle_commands,
                autodetects_installation=True,
                installed=installed,
                install_signals=descriptor.install_signals,
                workflow_surfaces=descriptor.workflow_surfaces,
                generated_artifacts=descriptor.generated_artifacts,
                dry_run_commands=dry_run_commands,
                force_commands=force_commands,
            )
        )
    return entries


def _emit_payload(*, payload: dict[str, Any], format_name: str) -> None:
    if format_name == "json":
        print(json.dumps(serialise_value(payload), indent=2))
        return
    if payload.get("command") == "init":
        _emit_init_text(payload)
        return
    if "modules" in payload and "reports" not in payload and "command" not in payload:
        for module_data in payload["modules"]:
            print(f"{module_data['name']}: {module_data['description']}")
            print(f"  commands: {', '.join(module_data['commands'])}")
        return
    _emit_lifecycle_text(payload)


def _emit_init_text(payload: dict[str, Any]) -> None:
    print(f"Target: {payload['target']}")
    print(f"Command: init{' (dry-run)' if payload.get('dry_run') else ''}")
    print(f"Modules: {', '.join(payload['modules'])}")
    print(f"Mode: {payload['mode']}")
    print(f"Prompt requirement: {payload['prompt_requirement']}")
    _print_path_list("Detected surfaces", payload["detected_surfaces"])
    _print_path_list("Created", payload["created"])
    _print_path_list("Updated managed", payload["updated_managed"])
    _print_path_list("Preserved existing", payload["preserved_existing"])
    _print_path_list("Needs review", payload["needs_review"])
    _print_path_list("Placeholders", payload["placeholders"])
    _print_path_list("Generated artifacts", payload["generated_artifacts"])
    _print_path_list("Validation", payload["validation"])
    _print_path_list("Next steps", payload["next_steps"])
    if payload.get("handoff_prompt_path"):
        print(f"Handoff prompt file: {payload['handoff_prompt_path']}")
    if payload.get("handoff_prompt"):
        print("")
        print("Handoff Prompt:")
        print(payload["handoff_prompt"])


def _emit_lifecycle_text(payload: dict[str, Any]) -> None:
    print(f"Target: {payload['target']}")
    print(f"Command: {payload['command']}{' (dry-run)' if payload.get('dry_run') else ''}")
    print(f"Modules: {', '.join(payload['modules'])}")
    print(f"Health: {payload['health']}")
    _print_path_list("Created", payload["created"])
    _print_path_list("Updated managed", payload["updated_managed"])
    _print_path_list("Preserved existing", payload["preserved_existing"])
    _print_path_list("Needs review", payload["needs_review"])
    _print_path_list("Generated artifacts", payload["generated_artifacts"])
    _print_path_list("Warnings", payload["warnings"])
    _print_path_list("Placeholders", payload["placeholders"])
    _print_path_list("Stale generated surfaces", payload["stale_generated_surfaces"])
    for report in payload["reports"]:
        print(f"[{report['module']}] {report['message']}")
        for action in report["actions"]:
            detail = f" ({action['detail']})" if action.get("detail") else ""
            print(f"- {action['kind']}: {_display_path(action['path'], Path(payload['target']))}{detail}")
    _print_path_list("Next steps", payload["next_steps"])


def _print_path_list(heading: str, values: list[str]) -> None:
    if not values:
        return
    print(f"{heading}:")
    for value in values:
        print(f"- {value}")


def _display_path(path_value: str, target_root: Path) -> str:
    path = Path(path_value)
    try:
        return path.relative_to(target_root).as_posix()
    except ValueError:
        return path.as_posix()


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


def _module_workflow_surfaces(
    *, selected_modules: list[str], descriptors: dict[str, ModuleDescriptor]
) -> tuple[Path, ...]:
    ordered: list[Path] = []
    for module_name in selected_modules:
        for path in descriptors[module_name].workflow_surfaces:
            if path not in ordered:
                ordered.append(path)
    return tuple(ordered)


def _module_generated_artifacts(
    *, selected_modules: list[str], descriptors: dict[str, ModuleDescriptor]
) -> set[str]:
    generated: set[str] = set()
    for module_name in selected_modules:
        generated.update(path.as_posix() for path in descriptors[module_name].generated_artifacts)
    return generated


def _is_generated_artifact(*, relative_path: str, detail: str, generated_artifacts: set[str]) -> bool:
    return relative_path in generated_artifacts or detail.lower().startswith("render")


def _is_placeholder_issue(*, detail: str) -> bool:
    detail_lower = detail.lower()
    return "placeholder" in detail_lower or "bootstrap marker" in detail_lower


def _format_issue(*, relative_path: str, detail: str) -> str:
    return f"{relative_path}: {detail}" if detail else relative_path


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _dedupe(values: list[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        _append_unique(ordered, value)
    return ordered
