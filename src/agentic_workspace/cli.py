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
        _emit_modules(format_name=args.format)
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

    detected = [module_name for module_name in MODULE_ORDER if module_name in descriptors and descriptors[module_name].detector(target_root)]
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
    inspection = _inspect_repo_state(target_root=target_root, selected_modules=selected_modules, descriptors=descriptors, force_adopt=force_adopt)
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
        module_generated_artifacts = {
            path.as_posix() for path in descriptors[report["module"]].generated_artifacts
        }
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
        module_generated_artifacts = {
            path.as_posix() for path in descriptors[report["module"]].generated_artifacts
        }
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


def _init_next_steps(*, target_root: Path, mode: str, prompt_requirement: str, needs_review: list[str], placeholders: list[str]) -> list[str]:
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


def _emit_modules(*, format_name: str) -> None:
    descriptors = _module_operations()
    payload = {
        "modules": [
            {
                "name": descriptor.name,
                "description": descriptor.description,
                "commands": sorted(descriptor.commands),
                "install_signals": [path.as_posix() for path in descriptor.install_signals],
                "workflow_surfaces": [path.as_posix() for path in descriptor.workflow_surfaces],
                "generated_artifacts": [path.as_posix() for path in descriptor.generated_artifacts],
                "command_args": {name: list(args) for name, args in descriptor.command_args.items()},
            }
            for descriptor in descriptors.values()
        ]
    }
    _emit_payload(payload=payload, format_name=format_name)


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
