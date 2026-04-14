from __future__ import annotations

import argparse
import fnmatch
import json
import re
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from agentic_workspace import __version__
from agentic_workspace.result_adapter import adapt_module_result, serialise_value

MODULE_COMMAND_ARGS: dict[str, tuple[str, ...]] = {
    "install": ("target", "dry_run", "force"),
    "adopt": ("target", "dry_run"),
    "upgrade": ("target", "dry_run"),
    "uninstall": ("target", "dry_run"),
    "doctor": ("target",),
    "status": ("target",),
}
PLACEHOLDER_RE = re.compile(r"<[A-Z][A-Z0-9_]+>")
MIXED_AGENT_LOCAL_OVERRIDE_FIELDS = (
    "runtime.supports_internal_delegation",
    "runtime.strong_planner_available",
    "runtime.cheap_bounded_executor_available",
    "handoff.prefer_internal_delegation_when_available",
)
WORKSPACE_PAYLOAD_FILES = (
    Path(".agentic-workspace/WORKFLOW.md"),
    Path(".agentic-workspace/OWNERSHIP.toml"),
)
WORKSPACE_CONFIG_PATH = Path("agentic-workspace.toml")
WORKSPACE_LOCAL_CONFIG_PATH = Path("agentic-workspace.local.toml")
WORKSPACE_EXTERNAL_AGENT_PATH = Path("llms.txt")
WORKSPACE_BOOTSTRAP_HANDOFF_PATH = Path(".agentic-workspace/bootstrap-handoff.md")
WORKSPACE_BOOTSTRAP_HANDOFF_RECORD_PATH = Path(".agentic-workspace/bootstrap-handoff.json")
WORKSPACE_AGENTS_PATH = Path("AGENTS.md")
WORKSPACE_HANDOFF_SURFACES = (
    WORKSPACE_EXTERNAL_AGENT_PATH,
    WORKSPACE_BOOTSTRAP_HANDOFF_PATH,
    WORKSPACE_BOOTSTRAP_HANDOFF_RECORD_PATH,
)
MODULE_UPGRADE_SOURCE_PATHS = {
    "planning": Path(".agentic-workspace/planning/UPGRADE-SOURCE.toml"),
    "memory": Path(".agentic-workspace/memory/UPGRADE-SOURCE.toml"),
}
WORKSPACE_WORKFLOW_MARKER_START = "<!-- agentic-workspace:workflow:start -->"
WORKSPACE_WORKFLOW_MARKER_END = "<!-- agentic-workspace:workflow:end -->"
WORKSPACE_POINTER_BLOCK = (
    f"{WORKSPACE_WORKFLOW_MARKER_START}\nRead `.agentic-workspace/WORKFLOW.md` for shared workflow rules.\n{WORKSPACE_WORKFLOW_MARKER_END}"
)
MEMORY_WORKFLOW_MARKER_START = "<!-- agentic-memory:workflow:start -->"
MEMORY_WORKFLOW_MARKER_END = "<!-- agentic-memory:workflow:end -->"
MEMORY_POINTER_BLOCK = (
    f"{MEMORY_WORKFLOW_MARKER_START}\nRead `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules.\n{MEMORY_WORKFLOW_MARKER_END}"
)
COMPACT_CONTRACT_PROFILE = "compact-contract-answer/v1"
COMPACT_CONTRACT_PROFILE_DOC = "docs/compact-contract-profile.md"


@dataclass(frozen=True)
class RootAgentsCleanupBlock:
    block: str
    start_marker: str
    end_marker: str
    label: str


@dataclass(frozen=True)
class ModuleResultContract:
    schema_version: str
    guaranteed_fields: tuple[str, ...]
    action_fields: tuple[str, ...]
    warning_fields: tuple[str, ...]


@dataclass(frozen=True)
class ModuleDescriptor:
    name: str
    description: str
    commands: dict[str, Callable[..., Any]]
    detector: Callable[[Path], bool]
    selection_rank: int
    include_in_full_preset: bool
    install_signals: tuple[Path, ...]
    workflow_surfaces: tuple[Path, ...]
    generated_artifacts: tuple[Path, ...]
    command_args: dict[str, tuple[str, ...]]
    startup_steps: tuple[str, ...]
    sources_of_truth: tuple[str, ...]
    root_agents_cleanup_blocks: tuple[RootAgentsCleanupBlock, ...]
    capabilities: tuple[str, ...]
    dependencies: tuple[str, ...]
    conflicts: tuple[str, ...]
    result_contract: ModuleResultContract


@dataclass(frozen=True)
class RepoInspection:
    repo_state: str
    inferred_policy: str
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
    lifecycle_hook_expectations: tuple[str, ...]
    autodetects_installation: bool
    installed: bool | None
    install_signals: tuple[Path, ...]
    workflow_surfaces: tuple[Path, ...]
    generated_artifacts: tuple[Path, ...]
    dry_run_commands: tuple[str, ...]
    force_commands: tuple[str, ...]
    capabilities: tuple[str, ...]
    dependencies: tuple[str, ...]
    conflicts: tuple[str, ...]
    result_contract: ModuleResultContract


@dataclass(frozen=True)
class SkillCatalogSource:
    name: str
    registry_path: Path
    skills_root: Path
    owner: str
    source_kind: str
    default_scope: str
    default_stability: str


@dataclass(frozen=True)
class SkillActivationHints:
    verbs: tuple[str, ...]
    nouns: tuple[str, ...]
    phrases: tuple[str, ...]
    when: tuple[str, ...]


@dataclass(frozen=True)
class RegisteredSkill:
    skill_id: str
    path: Path
    owner: str
    source_kind: str
    scope: str
    stability: str
    summary: str
    activation_hints: SkillActivationHints
    registration: str


@dataclass(frozen=True)
class SkillRecommendation:
    skill: RegisteredSkill
    hint_score: int
    score: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ModuleUpdatePolicy:
    module: str
    source_type: str
    source_ref: str
    source_label: str
    recommended_upgrade_after_days: int
    source: str


@dataclass(frozen=True)
class WorkspaceConfig:
    target_root: Path | None
    path: Path | None
    exists: bool
    schema_version: int
    default_preset: str
    update_modules: dict[str, ModuleUpdatePolicy]
    local_override: "MixedAgentLocalOverride"


@dataclass(frozen=True)
class MixedAgentLocalOverride:
    path: Path | None
    exists: bool
    applied: bool
    supports_internal_delegation: bool | None
    strong_planner_available: bool | None
    cheap_bounded_executor_available: bool | None
    prefer_internal_delegation_when_available: bool | None


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

    defaults_parser = subparsers.add_parser(
        "defaults",
        help="Show the machine-readable default-route contract for startup, lifecycle, skills, validation, and combined installs.",
    )
    defaults_parser.add_argument("--section", help="Return only one top-level defaults section in the compact contract profile.")
    _add_format_argument(defaults_parser)

    proof_parser = subparsers.add_parser(
        "proof",
        help="Show the canonical proof routes and current workspace proof summary.",
    )
    proof_parser.add_argument("--target", help="Optional repository path used to inspect installed modules and proof state.")
    proof_parser.add_argument("--route", help="Return one proof route by id instead of the full proof surface.")
    proof_parser.add_argument("--current", action="store_true", help="Return only the current proof summary.")
    _add_format_argument(proof_parser)

    ownership_parser = subparsers.add_parser(
        "ownership",
        help="Show the canonical ownership and authority mapping for the target repository.",
    )
    ownership_parser.add_argument("--target", help="Optional repository path used to inspect the ownership ledger.")
    ownership_parser.add_argument("--concern", help="Return one authority-surface answer by concern.")
    ownership_parser.add_argument("--path", help="Return the ownership answer for one repo-relative path.")
    _add_format_argument(ownership_parser)

    config_parser = subparsers.add_parser(
        "config",
        help="Show the resolved repo-owned workspace config layered onto product defaults.",
    )
    config_parser.add_argument("--target", help="Optional repository path used to resolve repo-owned config.")
    _add_format_argument(config_parser)

    skills_parser = subparsers.add_parser(
        "skills",
        help="List registered workspace skills from installed package registries and repo-owned skill registries.",
    )
    skills_parser.add_argument("--target", help="Optional repository path used to inspect installed and repo-owned skills.")
    skills_parser.add_argument("--task", help="Optional task description used to recommend likely skills.")
    _add_format_argument(skills_parser)

    init_parser = subparsers.add_parser("init", help="Bootstrap selected modules into a target repository.")
    _add_selection_arguments(init_parser)
    init_parser.add_argument("--adopt", action="store_true", help="Force conservative adopt behavior.")
    init_parser.add_argument("--dry-run", action="store_true", help="Show planned changes without mutating files.")
    init_parser.add_argument("--print-prompt", action="store_true", help="Print the generated handoff prompt.")
    init_parser.add_argument("--write-prompt", help="Write the generated handoff prompt to a file.")

    prompt_parser = subparsers.add_parser("prompt", help="Print a ready-to-paste workspace lifecycle handoff prompt.")
    prompt_subparsers = prompt_parser.add_subparsers(dest="prompt_command", required=True)
    prompt_init_parser = prompt_subparsers.add_parser("init", help="Print the workspace bootstrap handoff prompt.")
    _add_selection_arguments(prompt_init_parser)
    prompt_init_parser.add_argument("--adopt", action="store_true", help="Force conservative adopt behavior.")
    prompt_upgrade_parser = prompt_subparsers.add_parser("upgrade", help="Print the workspace upgrade handoff prompt.")
    _add_selection_arguments(prompt_upgrade_parser)
    prompt_uninstall_parser = prompt_subparsers.add_parser("uninstall", help="Print the workspace uninstall handoff prompt.")
    _add_selection_arguments(prompt_uninstall_parser)

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
    parser.add_argument("--preset", help="Named module bundle.")
    parser.add_argument("--modules", help="Comma-separated module selection.")
    _add_format_argument(parser)


def _add_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    descriptors = _module_operations()
    _validate_descriptor_contract(descriptors)
    _configure_parser_contract(parser=parser, descriptors=descriptors)

    if args.command == "modules":
        target_root = _resolve_target_root(args.target) if args.target else None
        if target_root is not None:
            _validate_target_root(command_name="modules", target_root=target_root)
        _emit_modules(format_name=args.format, target_root=target_root)
        return 0

    if args.command == "defaults":
        try:
            _emit_defaults(format_name=args.format, section=getattr(args, "section", None))
            return 0
        except WorkspaceUsageError as exc:
            parser.error(str(exc))

    if args.command in {"proof", "ownership", "config"}:
        try:
            target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
            _validate_target_root(command_name=args.command, target_root=target_root)
            if args.command == "proof":
                _emit_proof(
                    format_name=args.format,
                    target_root=target_root,
                    descriptors=descriptors,
                    route=getattr(args, "route", None),
                    current_only=bool(getattr(args, "current", False)),
                )
            elif args.command == "ownership":
                _emit_ownership(
                    format_name=args.format,
                    target_root=target_root,
                    descriptors=descriptors,
                    concern=getattr(args, "concern", None),
                    repo_path=getattr(args, "path", None),
                )
            else:
                _emit_config(format_name=args.format, config=_load_workspace_config(target_root=target_root, descriptors=descriptors))
            return 0
        except WorkspaceUsageError as exc:
            parser.error(str(exc))

    if args.command == "skills":
        target_root = _resolve_target_root(args.target) if args.target else None
        if target_root is not None:
            _validate_target_root(command_name="skills", target_root=target_root)
        _emit_skills(format_name=args.format, target_root=target_root, task_text=args.task)
        return 0

    try:
        target_root = _resolve_target_root(args.target)
        _validate_target_root(command_name=args.command, target_root=target_root)
        config = _load_workspace_config(target_root=target_root, descriptors=descriptors)
        selected_modules, resolved_preset = _selected_modules(
            command_name=args.command,
            preset_name=args.preset,
            module_arg=args.modules,
            target_root=target_root,
            descriptors=descriptors,
            config=config,
        )
        _validate_selected_module_contract(selected_modules=selected_modules, descriptors=descriptors)
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
            config=config,
        )
        _emit_payload(payload=payload, format_name=args.format)
        return 0

    if args.command == "prompt":
        payload = _run_prompt_command(
            prompt_command=args.prompt_command,
            target_root=target_root,
            selected_modules=selected_modules,
            resolved_preset=resolved_preset,
            descriptors=descriptors,
            force_adopt=bool(getattr(args, "adopt", False)),
            config=config,
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
        config=config,
    )
    _emit_payload(payload=payload, format_name=args.format)
    return 0


def _configure_parser_contract(*, parser: argparse.ArgumentParser, descriptors: dict[str, ModuleDescriptor]) -> None:
    preset_choices = tuple(_preset_modules(descriptors))
    for action in parser._actions:
        if action.dest == "preset":
            action.choices = preset_choices


def _validate_descriptor_contract(descriptors: dict[str, ModuleDescriptor]) -> None:
    known_modules = set(descriptors)
    for descriptor in descriptors.values():
        unknown_dependencies = [dependency for dependency in descriptor.dependencies if dependency not in known_modules]
        unknown_conflicts = [conflict for conflict in descriptor.conflicts if conflict not in known_modules]
        if unknown_dependencies:
            missing_text = ", ".join(unknown_dependencies)
            raise WorkspaceUsageError(f"Module '{descriptor.name}' declares unknown dependencies: {missing_text}.")
        if unknown_conflicts:
            conflict_text = ", ".join(unknown_conflicts)
            raise WorkspaceUsageError(f"Module '{descriptor.name}' declares unknown conflicts: {conflict_text}.")


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
            selection_rank=10,
            include_in_full_preset=True,
            detector=lambda target_root: (
                (target_root / "TODO.md").exists() and (target_root / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
            ),
            install_signals=(
                Path("TODO.md"),
                Path("docs/execplans"),
                Path(".agentic-workspace/planning"),
            ),
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
            startup_steps=(
                "Read `TODO.md`.",
                "Read the active feature plan in `docs/execplans/` when the TODO surface points there.",
                "Read `ROADMAP.md` only when promoting work.",
            ),
            sources_of_truth=(
                "Active queue: `TODO.md`",
                "Long-horizon candidate work: `ROADMAP.md`",
            ),
            root_agents_cleanup_blocks=(),
            capabilities=(
                "active-execution-state",
                "execplan-routing",
                "generated-maintainer-guidance",
            ),
            dependencies=(),
            conflicts=(),
            result_contract=ModuleResultContract(
                schema_version="workspace-module-report/v1",
                guaranteed_fields=("module", "message", "target_root", "dry_run", "actions", "warnings"),
                action_fields=("kind", "path", "detail"),
                warning_fields=("path", "message"),
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
            selection_rank=20,
            include_in_full_preset=True,
            detector=lambda target_root: (
                (target_root / "memory" / "index.md").exists() and (target_root / ".agentic-workspace" / "memory").exists()
            ),
            install_signals=(
                Path("memory/index.md"),
                Path("memory/current"),
                Path(".agentic-workspace/memory"),
            ),
            workflow_surfaces=(
                Path("AGENTS.md"),
                Path("memory/index.md"),
                Path("memory/current"),
                Path(".agentic-workspace/memory"),
            ),
            generated_artifacts=(),
            startup_steps=(
                "Read `memory/index.md` only when memory is installed and the task is not already well-routed.",
                "Read `.agentic-workspace/memory/WORKFLOW.md` only when changing memory behavior or the memory workflow itself.",
            ),
            sources_of_truth=("Durable routed knowledge, when installed: `memory/index.md`",),
            root_agents_cleanup_blocks=(
                RootAgentsCleanupBlock(
                    block=MEMORY_POINTER_BLOCK,
                    start_marker=MEMORY_WORKFLOW_MARKER_START,
                    end_marker=MEMORY_WORKFLOW_MARKER_END,
                    label="memory workflow pointer block",
                ),
            ),
            capabilities=(
                "durable-repo-knowledge",
                "anti-rediscovery-memory",
                "runbook-routing",
            ),
            dependencies=(),
            conflicts=(),
            result_contract=ModuleResultContract(
                schema_version="workspace-module-report/v1",
                guaranteed_fields=("module", "message", "target_root", "dry_run", "actions", "warnings"),
                action_fields=("kind", "path", "detail"),
                warning_fields=("path", "message"),
            ),
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
    selection_rank: int,
    include_in_full_preset: bool,
    install_signals: tuple[Path, ...],
    workflow_surfaces: tuple[Path, ...],
    generated_artifacts: tuple[Path, ...],
    startup_steps: tuple[str, ...],
    sources_of_truth: tuple[str, ...],
    root_agents_cleanup_blocks: tuple[RootAgentsCleanupBlock, ...],
    capabilities: tuple[str, ...],
    dependencies: tuple[str, ...],
    conflicts: tuple[str, ...],
    result_contract: ModuleResultContract,
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
        selection_rank=selection_rank,
        include_in_full_preset=include_in_full_preset,
        install_signals=install_signals,
        workflow_surfaces=workflow_surfaces,
        generated_artifacts=generated_artifacts,
        command_args=MODULE_COMMAND_ARGS,
        startup_steps=startup_steps,
        sources_of_truth=sources_of_truth,
        root_agents_cleanup_blocks=root_agents_cleanup_blocks,
        capabilities=capabilities,
        dependencies=dependencies,
        conflicts=conflicts,
        result_contract=result_contract,
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


def _workspace_agents_template(*, selected_modules: list[str], descriptors: dict[str, ModuleDescriptor]) -> str:
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

    for module_name in selected_modules:
        descriptor = descriptors[module_name]
        startup_steps.extend(descriptor.startup_steps)
        sources_of_truth.extend(descriptor.sources_of_truth)

    startup_steps.append("Load package-local docs only for the package being edited.")

    lines = [
        "# Agent Instructions",
        "",
        WORKSPACE_POINTER_BLOCK,
    ]
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
            "Do not start coding from chat context alone when the same information exists in checked-in files.",
            "",
            "## Sources Of Truth",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in sources_of_truth)
    if "planning" in selected_modules:
        lines.extend(["", "Do not bulk-read all planning surfaces."])
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


def _remove_fenced_block(*, text: str, start_marker: str, end_marker: str) -> tuple[str, bool]:
    fenced_re = re.compile(r"\n?" + re.escape(start_marker) + r".*?" + re.escape(end_marker) + r"\n?", re.DOTALL)
    updated, count = fenced_re.subn("\n", text, count=1)
    if count == 0:
        return text, False
    updated = re.sub(r"\n{3,}", "\n\n", updated).lstrip("\n")
    if updated and not updated.endswith("\n"):
        updated += "\n"
    return updated, True


def _workspace_status_report(
    *,
    target_root: Path,
    selected_modules: list[str],
    descriptors: dict[str, ModuleDescriptor],
    command_name: str,
    config: WorkspaceConfig,
) -> dict[str, Any]:
    actions: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    expected_handoff = _external_agent_handoff_text(selected_modules=selected_modules)

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

    for module_name in selected_modules:
        for block in descriptors[module_name].root_agents_cleanup_blocks:
            if block.block not in agents_text:
                continue
            actions.append(
                {
                    "kind": "warning",
                    "path": WORKSPACE_AGENTS_PATH.as_posix(),
                    "detail": (
                        f"redundant top-level {block.label} still present; "
                        "shared workspace workflow should delegate to module-specific guidance"
                    ),
                }
            )
            warnings.append(
                {
                    "path": WORKSPACE_AGENTS_PATH.as_posix(),
                    "message": f"redundant top-level {block.label} still present",
                }
            )

    handoff_path = target_root / WORKSPACE_EXTERNAL_AGENT_PATH
    if not handoff_path.exists():
        actions.append(
            {
                "kind": "warning",
                "path": WORKSPACE_EXTERNAL_AGENT_PATH.as_posix(),
                "detail": "canonical external-agent handoff file missing",
            }
        )
        warnings.append(
            {
                "path": WORKSPACE_EXTERNAL_AGENT_PATH.as_posix(),
                "message": "canonical external-agent handoff file missing",
            }
        )
    elif handoff_path.read_text(encoding="utf-8") != expected_handoff:
        actions.append(
            {
                "kind": "warning",
                "path": WORKSPACE_EXTERNAL_AGENT_PATH.as_posix(),
                "detail": "external-agent handoff file differs from the current workspace contract",
            }
        )
        warnings.append(
            {
                "path": WORKSPACE_EXTERNAL_AGENT_PATH.as_posix(),
                "message": "external-agent handoff file differs from the current workspace contract",
            }
        )
    else:
        actions.append(
            {
                "kind": "current",
                "path": WORKSPACE_EXTERNAL_AGENT_PATH.as_posix(),
                "detail": "canonical external-agent handoff file present",
            }
        )

    policy_actions, policy_warnings = _sync_update_policy_actions(
        target_root=target_root,
        selected_modules=selected_modules,
        dry_run=False,
        command_name=command_name,
        config=config,
        apply=False,
    )
    actions.extend(policy_actions)
    warnings.extend(policy_warnings)

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


def _external_agent_handoff_text(*, selected_modules: list[str]) -> str:
    lines = [
        "# Agentic Workspace External-Agent Handoff",
        "",
        "Use Agentic Workspace as the lifecycle front door for the repository that contains this file.",
        "",
        "Target repository:",
        "- the repository containing this llms.txt file",
        "",
        "Required steps:",
        "- Read AGENTS.md first.",
        "- For normal work, continue through TODO.md and the active execplan only when TODO points to one.",
        "- Do not assume agentic-workspace is already installed; follow the checked-in lifecycle instructions in this repository.",
        "- For lifecycle work, use agentic-workspace rather than package-specific CLIs unless package-local debugging is required.",
        "",
        "Preferred install or adopt intent:",
    ]
    if selected_modules == ["planning"]:
        lines.append("- agentic-workspace init --target ./repo --preset planning")
    elif selected_modules == ["memory"]:
        lines.append("- agentic-workspace init --target ./repo --preset memory")
    else:
        lines.append("- agentic-workspace init --target ./repo --preset full")
    lines.extend(
        [
            "",
            "Preferred follow-up commands:",
            "- agentic-workspace status --target ./repo",
            "- agentic-workspace doctor --target ./repo",
            '- agentic-workspace skills --target ./repo --task "<task>" --format json',
            "- agentic-workspace upgrade --target ./repo",
            "",
            "Rules:",
            "- Prefer conservative review over replacing repo-owned workflow surfaces in ambiguous repos.",
            "- Keep planning and memory ownership boundaries explicit.",
            (
                "- If bootstrap writes .agentic-workspace/bootstrap-handoff.md, "
                "treat that file as the immediate next-action brief before normal work resumes."
            ),
            "",
            "Success means:",
            "- the workspace lifecycle runs through agentic-workspace",
            "- AGENTS.md remains the repo startup entrypoint",
            "- llms.txt stays aligned with the installed workspace contract",
            "",
        ]
    )
    return "\n".join(lines)


def _write_generated_text(*, destination: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def _workspace_init_or_upgrade_report(
    *,
    target_root: Path,
    selected_modules: list[str],
    descriptors: dict[str, ModuleDescriptor],
    dry_run: bool,
    inspection_mode: str,
    command_name: str,
    config: WorkspaceConfig,
) -> dict[str, Any]:
    actions: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    conservative = inspection_mode != "install" and command_name == "init"
    handoff_text = _external_agent_handoff_text(selected_modules=selected_modules)

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
    rendered_agents = _workspace_agents_template(selected_modules=selected_modules, descriptors=descriptors)
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
        cleanup_blocks = [block for module_name in selected_modules for block in descriptors[module_name].root_agents_cleanup_blocks]
        for cleanup_block in cleanup_blocks:
            updated_text, block_changed = _remove_fenced_block(
                text=updated_text,
                start_marker=cleanup_block.start_marker,
                end_marker=cleanup_block.end_marker,
            )
            changed = changed or block_changed
        if changed:
            if not dry_run:
                agents_path.parent.mkdir(parents=True, exist_ok=True)
                agents_path.write_text(updated_text, encoding="utf-8")
            actions.append(
                {
                    "kind": _write_action_kind(dry_run=dry_run, existing=existing_agents),
                    "path": WORKSPACE_AGENTS_PATH.as_posix(),
                    "detail": "patched the shared workspace workflow pointer into AGENTS.md without replacing repo-owned content",
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

    handoff_destination = target_root / WORKSPACE_EXTERNAL_AGENT_PATH
    existing_handoff = handoff_destination.read_text(encoding="utf-8") if handoff_destination.exists() else None
    if existing_handoff == handoff_text:
        actions.append(
            {
                "kind": "current",
                "path": WORKSPACE_EXTERNAL_AGENT_PATH.as_posix(),
                "detail": "canonical external-agent handoff already current",
            }
        )
    elif conservative and existing_handoff is not None:
        actions.append(
            {
                "kind": "manual review",
                "path": WORKSPACE_EXTERNAL_AGENT_PATH.as_posix(),
                "detail": "existing external-agent handoff differs from the managed workspace contract",
            }
        )
    else:
        _write_generated_text(destination=handoff_destination, text=handoff_text, dry_run=dry_run)
        actions.append(
            {
                "kind": _write_action_kind(dry_run=dry_run, existing=existing_handoff),
                "path": WORKSPACE_EXTERNAL_AGENT_PATH.as_posix(),
                "detail": "refresh canonical external-agent handoff surface",
            }
        )

    policy_actions, policy_warnings = _sync_update_policy_actions(
        target_root=target_root,
        selected_modules=selected_modules,
        dry_run=dry_run,
        command_name=command_name,
        config=config,
        apply=True,
    )
    actions.extend(policy_actions)
    warnings.extend(policy_warnings)

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
    config: WorkspaceConfig,
) -> tuple[list[str], str | None]:
    ordered_module_names = _ordered_module_names(descriptors)
    preset_modules = _preset_modules(descriptors)
    if preset_name and module_arg:
        raise ModuleSelectionError("Use either --preset or --modules, not both.")

    if preset_name:
        if preset_name not in preset_modules:
            supported = ", ".join(preset_modules)
            raise ModuleSelectionError(f"Unknown preset: {preset_name}. Supported presets: {supported}.")
        return preset_modules[preset_name], preset_name

    if module_arg:
        requested = _parse_modules(module_arg, ordered_module_names=ordered_module_names)
        return [module_name for module_name in ordered_module_names if module_name in requested], None

    if command_name in {"init", "prompt"}:
        return preset_modules[config.default_preset], config.default_preset

    registry = _module_registry(descriptors=descriptors, target_root=target_root)
    detected = [entry.name for entry in registry if entry.installed]
    if detected:
        return detected, None

    raise ModuleSelectionError("No installed modules were detected for this lifecycle command. Use --modules to target modules explicitly.")


def _ordered_module_names(descriptors: dict[str, ModuleDescriptor]) -> list[str]:
    return [
        descriptor.name for descriptor in sorted(descriptors.values(), key=lambda descriptor: (descriptor.selection_rank, descriptor.name))
    ]


def _preset_modules(descriptors: dict[str, ModuleDescriptor]) -> dict[str, list[str]]:
    ordered_module_names = _ordered_module_names(descriptors)
    presets = {module_name: [module_name] for module_name in ordered_module_names}
    presets["full"] = [module_name for module_name in ordered_module_names if descriptors[module_name].include_in_full_preset]
    return presets


def _parse_modules(module_arg: str, *, ordered_module_names: list[str]) -> set[str]:
    tokens = [token.strip() for token in module_arg.split(",") if token.strip()]
    if not tokens:
        raise ModuleSelectionError("--modules requires at least one module token.")

    unknown = [token for token in tokens if token not in ordered_module_names]
    if unknown:
        supported = ", ".join(ordered_module_names)
        unknown_text = ", ".join(sorted(set(unknown)))
        raise ModuleSelectionError(f"Unknown module token(s): {unknown_text}. Supported modules: {supported}.")

    return set(tokens)


def _validate_selected_module_contract(*, selected_modules: list[str], descriptors: dict[str, ModuleDescriptor]) -> None:
    selected_set = set(selected_modules)
    for module_name in selected_modules:
        descriptor = descriptors[module_name]
        missing = [dependency for dependency in descriptor.dependencies if dependency not in selected_set]
        if missing:
            missing_text = ", ".join(missing)
            raise ModuleSelectionError(f"Module '{module_name}' requires: {missing_text}.")
        conflicts = [conflict for conflict in descriptor.conflicts if conflict in selected_set]
        if conflicts:
            conflict_text = ", ".join(conflicts)
            raise ModuleSelectionError(f"Module '{module_name}' conflicts with: {conflict_text}.")


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
    config: WorkspaceConfig,
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
            descriptors=descriptors,
            dry_run=dry_run,
            inspection_mode=inspection.mode,
            command_name="init",
            config=config,
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
    prompt_path = _default_handoff_prompt_path(target_root=target_root) if summary["prompt_requirement"] != "none" else None
    handoff_record = _build_bootstrap_handoff_record(summary) if summary["prompt_requirement"] != "none" else None
    handoff_record_path = _default_handoff_record_path(target_root=target_root) if handoff_record is not None else None
    if write_prompt:
        prompt_path = Path(write_prompt).expanduser().resolve()
    if prompt_path is not None and (write_prompt or not dry_run):
        _write_prompt_file(prompt_path=prompt_path, prompt_text=prompt_text, dry_run=dry_run)
    if handoff_record is not None and handoff_record_path is not None and not dry_run:
        _write_json_file(destination=handoff_record_path, payload=handoff_record, dry_run=dry_run)
    payload: dict[str, Any] = summary | {
        "dry_run": dry_run,
        "module_reports": reports,
        "config": _config_payload(config=config),
    }
    should_include_prompt = print_prompt or prompt_path is not None or summary["prompt_requirement"] != "none"
    if should_include_prompt:
        payload["handoff_prompt"] = prompt_text
    if prompt_path is not None:
        payload["handoff_prompt_path"] = prompt_path.as_posix()
        payload["next_steps"].append(f"Review the written handoff prompt at {prompt_path.as_posix()}.")
    if handoff_record is not None and handoff_record_path is not None:
        payload["handoff_record"] = handoff_record
        payload["handoff_record_path"] = handoff_record_path.as_posix()
        payload["next_steps"].append(f"Review the structured handoff record at {handoff_record_path.as_posix()}.")
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
    detected_workflow_surfaces = [path.as_posix() for path in workflow_surfaces if (target_root / path).exists()]
    detected_state_surfaces = [path.as_posix() for path in WORKSPACE_HANDOFF_SURFACES if (target_root / path).exists()]
    detected_surfaces = _dedupe([*detected_workflow_surfaces, *detected_state_surfaces])
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
    repo_state, mode, inferred_policy = _classify_repo_state(
        force_adopt=force_adopt,
        managed_root_present=managed_root_present,
        overlap_count=overlap_count,
        workflow_overlap_count=len(detected_workflow_surfaces),
        handoff_surface_count=sum(
            1
            for surface in detected_state_surfaces
            if surface in {WORKSPACE_EXTERNAL_AGENT_PATH.as_posix(), WORKSPACE_BOOTSTRAP_HANDOFF_PATH.as_posix()}
        ),
        partial_state=partial_state,
        placeholders=placeholders,
    )
    prompt_requirement = _prompt_requirement_for_mode(
        mode=mode,
        partial_state=partial_state,
        placeholders=placeholders,
    )

    needs_review = [f"{path}: partial module state detected" for path in _dedupe(partial_state)]
    if mode == "adopt_high_ambiguity":
        needs_review.extend(f"{path}: reconcile existing workflow surface ownership" for path in preserved_existing)

    return RepoInspection(
        repo_state=repo_state,
        inferred_policy=inferred_policy,
        mode=mode,
        prompt_requirement=prompt_requirement,
        detected_surfaces=detected_surfaces,
        preserved_existing=_dedupe(preserved_existing),
        needs_review=_dedupe(needs_review),
        placeholders=_dedupe(placeholders),
    )


def _classify_repo_state(
    *,
    force_adopt: bool,
    managed_root_present: bool,
    overlap_count: int,
    workflow_overlap_count: int,
    handoff_surface_count: int,
    partial_state: list[str],
    placeholders: list[str],
) -> tuple[str, str, str]:
    if partial_state or placeholders:
        return ("partial_or_placeholder_state", "adopt_high_ambiguity", "require_explicit_handoff")
    if not overlap_count and not force_adopt:
        return ("blank_or_unmanaged_repo", "install", "install_direct")
    if (
        overlap_count >= 4
        or (managed_root_present and overlap_count >= 2)
        or handoff_surface_count >= 2
        or (handoff_surface_count >= 1 and workflow_overlap_count >= 1)
    ):
        return ("docs_heavy_existing_repo", "adopt_high_ambiguity", "require_explicit_handoff")
    return ("light_existing_workflow", "adopt", "preserve_existing_and_adopt")


def _prompt_requirement_for_mode(*, mode: str, partial_state: list[str], placeholders: list[str]) -> str:
    prompt_requirement = {
        "install": "none",
        "adopt": "recommended",
        "adopt_high_ambiguity": "required",
    }[mode]
    if partial_state or placeholders:
        return "required"
    return prompt_requirement


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
        "intent": _bootstrap_intent_payload(selected_modules=selected_modules, resolved_preset=resolved_preset),
        "repo_state": inspection.repo_state,
        "inferred_policy": inspection.inferred_policy,
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
            repo_state=inspection.repo_state,
            inferred_policy=inspection.inferred_policy,
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
    config: WorkspaceConfig,
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
        reports.append(
            _workspace_status_report(
                target_root=target_root,
                selected_modules=selected_modules,
                descriptors=descriptors,
                command_name=command_name,
                config=config,
            )
        )
    elif command_name == "upgrade":
        reports.append(
            _workspace_init_or_upgrade_report(
                target_root=target_root,
                selected_modules=selected_modules,
                descriptors=descriptors,
                dry_run=dry_run,
                inspection_mode="upgrade",
                command_name=command_name,
                config=config,
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
                "lifecycle_hook_expectations": list(entry.lifecycle_hook_expectations),
                "autodetects_installation": entry.autodetects_installation,
                "installed": entry.installed,
                "dry_run_commands": list(entry.dry_run_commands),
                "force_commands": list(entry.force_commands),
                "capabilities": list(entry.capabilities),
                "dependencies": list(entry.dependencies),
                "conflicts": list(entry.conflicts),
                "result_contract": {
                    "schema_version": entry.result_contract.schema_version,
                    "guaranteed_fields": list(entry.result_contract.guaranteed_fields),
                    "action_fields": list(entry.result_contract.action_fields),
                    "warning_fields": list(entry.result_contract.warning_fields),
                },
            }
            for entry in registry
        ],
        "next_steps": _lifecycle_next_steps(command_name=command_name, target_root=target_root, warnings=warnings),
        "reports": reports,
        "config": _config_payload(config=config),
    }


def _bootstrap_intent_payload(*, selected_modules: list[str], resolved_preset: str | None) -> dict[str, str]:
    if resolved_preset == "memory":
        return {"key": "memory", "summary": "set up this repo for Agentic Memory"}
    if resolved_preset == "planning":
        return {"key": "planning", "summary": "set up this repo for Agentic Planning"}
    if resolved_preset == "full":
        return {"key": "full", "summary": "set up this repo for both Planning and Memory"}
    if selected_modules == ["memory"]:
        return {"key": "memory", "summary": "set up this repo for Agentic Memory"}
    if selected_modules == ["planning"]:
        return {"key": "planning", "summary": "set up this repo for Agentic Planning"}
    return {"key": "custom", "summary": f"set up this repo for: {', '.join(selected_modules)}"}


def _run_prompt_command(
    *,
    prompt_command: str,
    target_root: Path,
    selected_modules: list[str],
    resolved_preset: str | None,
    descriptors: dict[str, ModuleDescriptor],
    force_adopt: bool,
    config: WorkspaceConfig,
) -> dict[str, Any]:
    if prompt_command == "init":
        payload = _run_init(
            target_root=target_root,
            selected_modules=selected_modules,
            resolved_preset=resolved_preset,
            descriptors=descriptors,
            dry_run=True,
            force_adopt=force_adopt,
            print_prompt=True,
            write_prompt=None,
            config=config,
        )
        return {
            **payload,
            "command": "prompt",
            "prompt_command": "init",
        }

    payload = _run_lifecycle_command(
        command_name=prompt_command,
        target_root=target_root,
        selected_modules=selected_modules,
        resolved_preset=resolved_preset,
        descriptors=descriptors,
        dry_run=True,
        config=config,
    )
    payload["command"] = "prompt"
    payload["prompt_command"] = prompt_command
    payload["handoff_prompt"] = _build_lifecycle_handoff_prompt(payload)
    return payload


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
    repo_state: str,
    inferred_policy: str,
    mode: str,
    prompt_requirement: str,
    needs_review: list[str],
    placeholders: list[str],
) -> list[str]:
    target = target_root.as_posix()
    steps = [f"Run agentic-workspace doctor --target {target} after bootstrap changes settle."]
    if prompt_requirement != "none":
        steps.append(
            f"Use the generated finishing brief at {WORKSPACE_BOOTSTRAP_HANDOFF_PATH.as_posix()} for the next bounded bootstrap action."
        )
    if prompt_requirement == "none":
        steps.append("Tell your coding agent to use AGENTS.md for normal work and llms.txt for lifecycle/front-door guidance.")
        return steps
    if mode == "adopt_high_ambiguity":
        steps.append("Treat the finishing brief as required before normal work resumes.")
    else:
        steps.append("Review preserved and review-needed workflow surfaces before treating bootstrap as complete.")
    if inferred_policy == "require_explicit_handoff" or repo_state == "docs_heavy_existing_repo":
        steps.append("Prefer explicit review and merge decisions over replacing repo-owned workflow surfaces.")
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
    lines = [
        f"Finish the Agentic Workspace bootstrap in {summary['target']}.",
        "",
        "User intent:",
        f"- {summary['intent']['summary']}",
        "",
        "Repo state:",
        f"- {summary['repo_state']}",
        "",
        "Inferred policy:",
        f"- {summary['inferred_policy']}",
        "",
        "Lifecycle mode:",
        f"- {summary['mode']}",
        "",
        "Selected modules:",
    ]
    lines.extend(f"- {module_name}" for module_name in summary["modules"])
    config_payload = summary.get("config")
    if isinstance(config_payload, dict) and config_payload.get("exists"):
        lines.extend(
            [
                "",
                "Repo-owned config:",
                f"- {config_payload['config_path']}",
                "- Treat agentic-workspace.toml as the repo-owned source of lifecycle defaults and update intent.",
            ]
        )
    lines.extend(["", "The CLI already:"])
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
            "- keep agentic-workspace as the lifecycle entrypoint; do not improvise package-level install flows",
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
    lines.append("- keep llms.txt current as the canonical external-agent handoff surface")
    lines.append("- leave only durable workflow residue; do not keep temporary bootstrap notes around")
    return "\n".join(lines)


def _build_bootstrap_handoff_record(summary: dict[str, Any]) -> dict[str, Any]:
    review_items = list(summary["needs_review"])
    review_items.extend(f"{path}: unresolved placeholder or bootstrap marker" for path in summary["placeholders"])
    return {
        "kind": "workspace-bootstrap-handoff/v1",
        "intent": summary["intent"],
        "scope": {
            "target": summary["target"],
            "selected_modules": summary["modules"],
            "repo_state": summary["repo_state"],
            "inferred_policy": summary["inferred_policy"],
            "mode": summary["mode"],
            "prompt_requirement": summary["prompt_requirement"],
            "review_items": review_items,
        },
        "next": {
            "steps": summary["next_steps"],
            "immediate_brief": WORKSPACE_BOOTSTRAP_HANDOFF_PATH.as_posix(),
        },
        "proof": {
            "validation": summary["validation"],
            "done_when": [
                "bootstrap review items are closed or explicitly resolved",
                "llms.txt remains current as the canonical external-agent handoff surface",
                "temporary bootstrap residue is removed before normal work resumes",
            ],
        },
        "must_not_change": [
            "the requested bootstrap intent",
            "repo-owned workflow surfaces without explicit review",
            "planning and memory ownership boundaries",
            "agentic-workspace as the lifecycle entrypoint",
        ],
        "escalate_when": [
            "finishing bootstrap would require replacing preserved repo-owned surfaces blindly",
            "the requested bootstrap intent no longer fits the repo state safely",
            "validation would be meaningless without broader lifecycle scope",
            "the handoff can no longer stay bounded to bootstrap follow-through",
        ],
        "refs": [
            "AGENTS.md",
            "TODO.md",
            "llms.txt",
            "docs/delegated-judgment-contract.md",
            "docs/init-lifecycle.md",
            "agentic-workspace defaults --format json",
            "agentic-workspace config --target ./repo --format json",
        ],
    }


def _build_lifecycle_handoff_prompt(payload: dict[str, Any]) -> str:
    prompt_command = str(payload["prompt_command"])
    target = str(payload["target"])
    lines = [f"Run the Agentic Workspace {prompt_command} flow in {target}.", "", "Selected modules:"]
    lines.extend(f"- {module_name}" for module_name in payload["modules"])
    lines.extend(
        [
            "",
            "Use the workspace CLI as the lifecycle entrypoint for this repo shape.",
            (
                "Keep module-specific lifecycle implementation package-local; "
                "do not switch to package CLIs unless package-local debugging is required."
            ),
        ]
    )
    config_payload = payload.get("config")
    if isinstance(config_payload, dict) and config_payload.get("exists"):
        lines.extend(
            [
                "",
                f"Respect the repo-owned config at {config_payload['config_path']}.",
                "Treat that file as the source of lifecycle defaults and module update intent.",
            ]
        )
        selected_policy_lines = []
        for module_policy in config_payload.get("update", {}).get("modules", []):
            if module_policy.get("module") in payload["modules"]:
                selected_policy_lines.append(f"- {module_policy['module']}: {module_policy['source_type']} {module_policy['source_ref']}")
        if selected_policy_lines:
            lines.extend(["Configured update sources:"])
            lines.extend(selected_policy_lines)
    review_items = []
    for heading in ("updated_managed", "preserved_existing", "needs_review", "warnings"):
        review_items.extend(payload.get(heading, []))
    if review_items:
        lines.extend(["", "Review before applying:"])
        lines.extend(f"- {item}" for item in review_items)
    lines.extend(["", "Validation:"])
    lines.extend(f"- {step}" for step in payload["next_steps"] if step)
    return "\n".join(lines)


def _default_handoff_prompt_path(*, target_root: Path) -> Path:
    return (target_root / WORKSPACE_BOOTSTRAP_HANDOFF_PATH).resolve()


def _default_handoff_record_path(*, target_root: Path) -> Path:
    return (target_root / WORKSPACE_BOOTSTRAP_HANDOFF_RECORD_PATH).resolve()


def _write_prompt_file(*, prompt_path: Path, prompt_text: str, dry_run: bool) -> Path:
    if not dry_run:
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt_text + "\n", encoding="utf-8")
    return prompt_path


def _write_json_file(*, destination: Path, payload: dict[str, Any], dry_run: bool) -> Path:
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(serialise_value(payload), indent=2) + "\n", encoding="utf-8")
    return destination


def _emit_modules(*, format_name: str, target_root: Path | None) -> None:
    descriptors = _module_operations()
    registry = _module_registry(descriptors=descriptors, target_root=target_root)
    payload = {
        "modules": [
            {
                "name": entry.name,
                "description": entry.description,
                "commands": list(entry.lifecycle_commands),
                "lifecycle_hook_expectations": list(entry.lifecycle_hook_expectations),
                "autodetects_installation": entry.autodetects_installation,
                "installed": entry.installed,
                "install_signals": [path.as_posix() for path in entry.install_signals],
                "workflow_surfaces": [path.as_posix() for path in entry.workflow_surfaces],
                "generated_artifacts": [path.as_posix() for path in entry.generated_artifacts],
                "dry_run_commands": list(entry.dry_run_commands),
                "force_commands": list(entry.force_commands),
                "capabilities": list(entry.capabilities),
                "dependencies": list(entry.dependencies),
                "conflicts": list(entry.conflicts),
                "result_contract": {
                    "schema_version": entry.result_contract.schema_version,
                    "guaranteed_fields": list(entry.result_contract.guaranteed_fields),
                    "action_fields": list(entry.result_contract.action_fields),
                    "warning_fields": list(entry.result_contract.warning_fields),
                },
                "command_args": {name: list(args) for name, args in descriptors[entry.name].command_args.items()},
            }
            for entry in registry
        ]
    }
    _emit_payload(payload=payload, format_name=format_name)


def _defaults_payload() -> dict[str, Any]:
    validation_lanes = [
        {
            "id": "workspace_cli",
            "when": [
                "root workspace CLI changes",
                "tests/test_workspace_cli.py changes",
                "root src/agentic_workspace changes",
            ],
            "enough_proof": [
                "uv run pytest tests/test_workspace_cli.py -q",
                "uv run ruff check src tests",
            ],
            "broaden_when": [
                "the change also touches generated maintainer docs",
                "the change also touches installed package payloads or shared orchestration boundaries",
            ],
            "escalate_when": [
                "the narrow lane cannot prove the change on its own",
                "package or repo-wide behavior is now part of the trust question",
            ],
        },
        {
            "id": "planning_package",
            "when": [
                "package-local planning source or tests change",
                "the behavior remains inside packages/planning",
            ],
            "enough_proof": [
                "cd packages/planning && uv run pytest tests/test_installer.py",
                "cd packages/planning && uv run ruff check .",
            ],
            "broaden_when": [
                "the change also touches root workspace orchestration",
                "the change also affects generated maintainer surfaces or installed contract boundaries",
            ],
            "escalate_when": [
                "the package-local lane no longer covers the trust question",
                "the change crosses package, payload, and root install boundaries together",
            ],
        },
        {
            "id": "memory_package",
            "when": [
                "package-local memory source or tests change",
                "the behavior remains inside packages/memory",
            ],
            "enough_proof": [
                "cd packages/memory && uv run pytest tests/test_installer.py",
                "cd packages/memory && uv run ruff check .",
            ],
            "broaden_when": [
                "the change also touches root workspace orchestration",
                "the change also affects generated maintainer surfaces or installed contract boundaries",
            ],
            "escalate_when": [
                "the package-local lane no longer covers the trust question",
                "the change crosses package, payload, and root install boundaries together",
            ],
        },
        {
            "id": "planning_surfaces",
            "when": [
                "TODO.md, ROADMAP.md, or execplans change without broader code changes",
                "the trust question is planning-surface shape or drift only",
            ],
            "enough_proof": [
                "uv run python scripts/check/check_planning_surfaces.py",
            ],
            "broaden_when": [
                "the same change also edits generated maintainer docs or workspace CLI behavior",
            ],
            "escalate_when": [
                "the planning-surface lane no longer proves the touched contract by itself",
            ],
        },
        {
            "id": "maintainer_surfaces",
            "when": [
                "generated maintainer docs, startup routing, or installed contract mirrors change",
                "the trust question is generated-surface freshness or startup-policy consistency",
            ],
            "enough_proof": [
                "make maintainer-surfaces",
            ],
            "broaden_when": [
                "the same change also alters root workspace CLI behavior or package-local logic",
            ],
            "escalate_when": [
                "source, payload, and installed-surface boundaries all changed together",
            ],
        },
    ]
    return {
        "startup": {
            "primary": [
                "Read `AGENTS.md`.",
                "Read `TODO.md`.",
                "Read the active execplan only when `TODO.md` points to one.",
            ],
            "secondary": [
                "Read `ROADMAP.md` only when promoting work.",
                "Read package-local `AGENTS.md` only for the package being edited.",
                "Read memory only when installed and the task needs durable context.",
            ],
            "workflow_recovery": [
                (
                    "When startup or workflow routing is unclear, prefer "
                    "`agentic-workspace defaults --format json`, then use `llms.txt` "
                    "or `AGENTS.md` when those surfaces are present, before "
                    "repo-local workaround guidance."
                ),
            ],
        },
        "compact_contract_profile": {
            "canonical_doc": COMPACT_CONTRACT_PROFILE_DOC,
            "rule": "When one bounded answer is enough, prefer a narrow selector over a whole-surface dump.",
            "answer_shape": [
                "profile",
                "surface",
                "selector",
                "matched",
                "answer",
                "refs",
            ],
            "selectors": {
                "defaults": "agentic-workspace defaults --section <section> --format json",
                "proof_route": "agentic-workspace proof --target ./repo --route <id> --format json",
                "proof_current": "agentic-workspace proof --target ./repo --current --format json",
                "ownership_concern": "agentic-workspace ownership --target ./repo --concern <concern> --format json",
                "ownership_path": "agentic-workspace ownership --target ./repo --path <repo-path> --format json",
            },
        },
        "lifecycle": {
            "primary_entrypoint": "agentic-workspace",
            "default_install_command": "agentic-workspace init --target ./repo --preset <memory|planning|full>",
            "supported_intents": [
                "set up this repo for Agentic Memory",
                "set up this repo for Agentic Planning",
                "set up this repo for both Planning and Memory",
            ],
            "default_operating_commands": [
                "agentic-workspace status --target ./repo",
                "agentic-workspace doctor --target ./repo",
                "agentic-workspace upgrade --target ./repo",
            ],
            "canonical_external_agent_handoff": "llms.txt",
            "canonical_bootstrap_next_action": ".agentic-workspace/bootstrap-handoff.md",
            "canonical_bootstrap_handoff_record": ".agentic-workspace/bootstrap-handoff.json",
            "secondary": [
                "Package CLIs are for package-local maintainer work, advanced debugging, or explicit module-level control.",
            ],
        },
        "config": {
            "path": "agentic-workspace.toml",
            "command": "agentic-workspace config --target ./repo --format json",
            "supported_fields": [
                "workspace.default_preset",
                "update.modules.<module>.source_type",
                "update.modules.<module>.source_ref",
                "update.modules.<module>.source_label",
                "update.modules.<module>.recommended_upgrade_after_days",
            ],
            "rules": [
                "Missing fields use product defaults.",
                "Normal update execution stays behind agentic-workspace.",
                "Repo config may change module update intent without creating separate public module upgrade entrypoints.",
            ],
        },
        "mixed_agent": {
            "rule": "Prefer runtime/task inference first, then stable policy, then explicit prompting.",
            "decision_order": [
                "runtime/task inference",
                "repo-owned policy",
                "optional local capability/cost override",
                "explicit prompting when still unsafe",
            ],
            "repo_policy": {
                "path": WORKSPACE_CONFIG_PATH.as_posix(),
                "scope": [
                    "stable repo policy",
                    "reviewable checked-in defaults",
                    "ownership and validation boundaries",
                ],
            },
            "local_override": {
                "path": WORKSPACE_LOCAL_CONFIG_PATH.as_posix(),
                "supported": True,
                "status": "supported-local-only",
                "supported_fields": list(MIXED_AGENT_LOCAL_OVERRIDE_FIELDS),
                "intended_scope": [
                    "machine-specific capability posture",
                    "account- or cost-profile asymmetry",
                    "local execution preferences that do not redefine repo semantics",
                ],
            },
            "runtime_inference": {
                "tool_owned": True,
                "report_when_behavior_changes": True,
                "scope": [
                    "delegation strategy",
                    "model choice",
                    "reasoning depth",
                    "task shaping when safe",
                ],
            },
            "handoff_quality": {
                "must_recover": [
                    "current intent",
                    "hard constraints",
                    "relevant durable context",
                    "proof expectations",
                    "immediate next action",
                ],
            },
            "success_measures": [
                "lower long-run token cost",
                "lower restart and handoff cost",
                "cheap switching across agents and subscriptions",
                "persisted shared knowledge beats rediscovery",
            ],
        },
        "skill_discovery": {
            "primary": [
                "agentic-workspace skills --target ./repo --format json",
                'agentic-workspace skills --target ./repo --task "<task>" --format json',
            ],
            "secondary": [
                "Read skill registries or SKILL.md files directly only when debugging, authoring, or validating skills.",
            ],
        },
        "validation": {
            "rule": "Run the narrowest proving lane that matches the touched surface.",
            "default_routes": {
                "workspace_cli": "uv run pytest tests/test_workspace_cli.py",
                "planning_package": "cd packages/planning && uv run pytest tests/test_installer.py",
                "memory_package": "cd packages/memory && uv run pytest tests/test_installer.py",
                "maintainer_surfaces": "make maintainer-surfaces",
            },
            "lanes": validation_lanes,
            "escalation_rule": (
                "Broaden validation only when the narrower lane stops proving the touched contract or the change crosses boundaries."
            ),
            "secondary": [
                "Use broader package or repo-wide lanes only when the change crosses boundaries or invalidates the narrower proof.",
            ],
        },
        "proof_surfaces": {
            "canonical_doc": "docs/proof-surfaces-contract.md",
            "command": "agentic-workspace proof --target ./repo --format json",
            "rule": "Use the narrowest proof lane that answers the current trust question.",
            "default_routes": {
                "workspace_proof": "agentic-workspace proof --target ./repo --format json",
                "workspace_status": "agentic-workspace status --target ./repo",
                "workspace_doctor": "agentic-workspace doctor --target ./repo",
                "planning_surfaces": "uv run python scripts/check/check_planning_surfaces.py",
                "maintainer_surfaces": "make maintainer-surfaces",
                "source_payload_install": "uv run pytest tests/test_source_payload_operational_install.py",
                "planning_payload": "uv run agentic-planning-bootstrap upgrade --target .",
                "memory_payload": "uv run agentic-memory-bootstrap upgrade --target .",
            },
            "secondary": [
                "Use package-local tests or payload verification only when the trust question is package-specific.",
            ],
        },
        "ownership_mapping": {
            "canonical_doc": "docs/ownership-authority-contract.md",
            "command": "agentic-workspace ownership --target ./repo --format json",
            "rule": "Resolve the owner and authoritative surface before changing or trusting a contract.",
            "ledger": ".agentic-workspace/OWNERSHIP.toml",
            "default_routes": {
                "workspace_ownership": "agentic-workspace ownership --target ./repo --format json",
                "workflow_contract": ".agentic-workspace/WORKFLOW.md",
                "ownership_ledger": ".agentic-workspace/OWNERSHIP.toml",
                "compatibility_policy": "docs/compatibility-policy.md",
                "generated_surface_trust": "docs/generated-surface-trust.md",
            },
            "secondary": [
                "Read package-local docs only after the ownership map identifies the package as the primary owner.",
            ],
        },
        "combined_install": {
            "primary": "agentic-workspace init --target ./repo --preset full",
            "operating_model": [
                "Planning owns active-now state.",
                "Memory owns durable anti-rediscovery knowledge.",
                "Use the shared workspace lifecycle verbs as the normal operating path.",
            ],
            "secondary": [
                "Direct package CLIs stay available, but they are not the normal path for combined installs.",
            ],
        },
        "recovery": {
            "canonical_doc": "docs/environment-recovery-contract.md",
            "rule": "Inspect state first, refresh contract second, re-run the narrowest proving lane third.",
            "ordered_path": [
                "agentic-workspace status --target ./repo",
                "agentic-workspace doctor --target ./repo",
                "agentic-workspace defaults --format json",
                "agentic-workspace config --target ./repo --format json",
            ],
            "refresh_contract": [
                "uv run agentic-planning-bootstrap upgrade --target .",
                "uv run agentic-memory-bootstrap upgrade --target .",
            ],
            "handoff_surfaces": [
                "llms.txt",
                ".agentic-workspace/bootstrap-handoff.md",
                ".agentic-workspace/bootstrap-handoff.json",
            ],
        },
        "completion": {
            "rule": "When a completed slice came from TODO.md or ROADMAP.md, clear the matched queue residue in the same pass.",
            "prefer_surfaces": [
                "TODO.md",
                "ROADMAP.md",
                "docs/execplans/README.md",
            ],
        },
        "delegated_judgment": {
            "canonical_doc": "docs/delegated-judgment-contract.md",
            "rule": "Improve means locally; do not silently rewrite ends locally.",
            "human_sets": [
                "requested outcome",
                "priorities",
                "hard constraints",
                "explicit approvals or prohibitions",
            ],
            "agent_may_decide": [
                "bounded decomposition",
                "narrower touched-path selection",
                "tighter validation",
                "skill or workflow selection",
                "promotion to an execplan when direct execution stops being safe",
                "residue routing into the correct checked-in surface",
            ],
            "escalate_when": [
                "the better-looking solution changes the requested outcome",
                "the better-looking solution changes the owned surface",
                "the better-looking solution changes the time horizon",
                "the requested path is blocked or unsafe as stated",
                "validation would be meaningless without added scope",
                "confidence is too low for silent continuation",
            ],
            "operational_follow_through": [
                "use a checked-in execplan when the requested outcome must survive across sessions",
                "preserve escalation boundaries in the machine-readable defaults when the task is broad enough to need them",
                "route durable residue into the correct checked-in surface instead of leaving it in chat",
            ],
        },
    }


def _compact_contract_answer(
    *,
    surface: str,
    selector: dict[str, Any],
    answer: Any,
    refs: list[str],
    matched: bool = True,
    target: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "profile": COMPACT_CONTRACT_PROFILE,
        "surface": surface,
        "selector": selector,
        "matched": matched,
        "answer": answer,
        "refs": refs,
    }
    if target is not None:
        payload["target"] = target
    return payload


def _compact_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(serialise_value(value), indent=2)
    return str(value)


def _emit_compact_answer_text(payload: dict[str, Any]) -> None:
    print(f"Profile: {payload['profile']}")
    print(f"Surface: {payload['surface']}")
    print(f"Selector: {json.dumps(serialise_value(payload['selector']), sort_keys=True)}")
    print(f"Matched: {payload['matched']}")
    print("Answer:")
    print(_compact_text(payload["answer"]))
    if payload.get("refs"):
        print("Refs:")
        for ref in payload["refs"]:
            print(f"- {ref}")


def _selector_refs(*, command: str, answer: Any) -> list[str]:
    refs = [COMPACT_CONTRACT_PROFILE_DOC, command]
    if isinstance(answer, dict):
        for key in ("canonical_doc", "command", "path", "surface", "ledger_path"):
            value = answer.get(key)
            if isinstance(value, str) and value not in refs:
                refs.append(value)
    return refs


def _select_defaults_section(payload: dict[str, Any], *, section: str) -> dict[str, Any]:
    normalized = section.strip()
    if normalized not in payload:
        supported = ", ".join(sorted(payload))
        raise WorkspaceUsageError(f"defaults --section must match one of: {supported}.")
    answer = payload[normalized]
    return _compact_contract_answer(
        surface="defaults",
        selector={"section": normalized},
        answer=answer,
        refs=_selector_refs(command="agentic-workspace defaults --format json", answer=answer),
    )


def _emit_defaults(*, format_name: str, section: str | None = None) -> None:
    payload = _defaults_payload()
    if section is not None:
        payload = _select_defaults_section(payload, section=section)
    if format_name == "json":
        print(json.dumps(serialise_value(payload), indent=2))
        return
    if section is not None:
        _emit_compact_answer_text(payload)
        return
    print("Startup:")
    for step in payload["startup"]["primary"]:
        print(f"- {step}")
    for step in payload["startup"].get("workflow_recovery", []):
        print(f"- {step}")
    print("Lifecycle:")
    print(f"- primary entrypoint: {payload['lifecycle']['primary_entrypoint']}")
    print(f"- install: {payload['lifecycle']['default_install_command']}")
    print(f"- external-agent handoff: {payload['lifecycle']['canonical_external_agent_handoff']}")
    print(f"- bootstrap next action: {payload['lifecycle']['canonical_bootstrap_next_action']}")
    print(f"- bootstrap handoff record: {payload['lifecycle']['canonical_bootstrap_handoff_record']}")
    print("Compact contract profile:")
    print(f"- doc: {payload['compact_contract_profile']['canonical_doc']}")
    print(f"- rule: {payload['compact_contract_profile']['rule']}")
    print("Config:")
    print(f"- path: {payload['config']['path']}")
    print(f"- inspect: {payload['config']['command']}")
    print("Mixed-agent:")
    print(f"- rule: {payload['mixed_agent']['rule']}")
    print(f"- local override: {payload['mixed_agent']['local_override']['path']} ({payload['mixed_agent']['local_override']['status']})")
    print("Skill discovery:")
    for step in payload["skill_discovery"]["primary"]:
        print(f"- {step}")
    print("Validation:")
    print(f"- rule: {payload['validation']['rule']}")
    for label, command in payload["validation"]["default_routes"].items():
        print(f"- {label}: {command}")
    print(f"- escalation: {payload['validation']['escalation_rule']}")
    print("Proof surfaces:")
    print(f"- doc: {payload['proof_surfaces']['canonical_doc']}")
    print(f"- command: {payload['proof_surfaces']['command']}")
    print(f"- rule: {payload['proof_surfaces']['rule']}")
    print("Ownership mapping:")
    print(f"- doc: {payload['ownership_mapping']['canonical_doc']}")
    print(f"- command: {payload['ownership_mapping']['command']}")
    print(f"- rule: {payload['ownership_mapping']['rule']}")
    print("Combined install:")
    print(f"- {payload['combined_install']['primary']}")
    print("Recovery:")
    print(f"- doc: {payload['recovery']['canonical_doc']}")
    print(f"- rule: {payload['recovery']['rule']}")
    print("Completion:")
    print(f"- rule: {payload['completion']['rule']}")
    print("Delegated judgment:")
    print(f"- doc: {payload['delegated_judgment']['canonical_doc']}")
    print(f"- rule: {payload['delegated_judgment']['rule']}")
    print("Delegated judgment follow-through:")
    for item in payload["delegated_judgment"]["operational_follow_through"]:
        print(f"- {item}")


def _default_module_update_policies() -> dict[str, ModuleUpdatePolicy]:
    from repo_memory_bootstrap._installer_output import resolve_upgrade_source as resolve_memory_upgrade_source
    from repo_planning_bootstrap._source import resolve_upgrade_source as resolve_planning_upgrade_source

    missing_target = Path(".agentic-workspace-workspace-defaults-missing")
    planning_default = resolve_planning_upgrade_source(missing_target)
    memory_default = resolve_memory_upgrade_source(missing_target)
    return {
        "planning": ModuleUpdatePolicy(
            module="planning",
            source_type=planning_default.source_type,
            source_ref=planning_default.source_ref,
            source_label=planning_default.source_label,
            recommended_upgrade_after_days=planning_default.recommended_upgrade_after_days,
            source="product-default",
        ),
        "memory": ModuleUpdatePolicy(
            module="memory",
            source_type=str(memory_default["source_type"]),
            source_ref=str(memory_default["source_ref"]),
            source_label=str(memory_default["source_label"]),
            recommended_upgrade_after_days=int(memory_default["recommended_upgrade_after_days"]),
            source="product-default",
        ),
    }


def _load_workspace_config(*, target_root: Path, descriptors: dict[str, ModuleDescriptor]) -> WorkspaceConfig:
    defaults = _default_module_update_policies()
    config_path = target_root / WORKSPACE_CONFIG_PATH
    local_override = _load_mixed_agent_local_override(target_root=target_root)
    default_preset = "full"
    if not config_path.exists():
        return WorkspaceConfig(
            target_root=target_root,
            path=config_path,
            exists=False,
            schema_version=1,
            default_preset=default_preset,
            update_modules=defaults,
            local_override=local_override,
        )

    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} is invalid TOML: {exc}.") from exc

    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise WorkspaceUsageError(
            f"{WORKSPACE_CONFIG_PATH.as_posix()} must set schema_version = 1 for the current workspace config contract."
        )

    raw_workspace = payload.get("workspace", {})
    if raw_workspace is None:
        raw_workspace = {}
    if not isinstance(raw_workspace, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} [workspace] section must be a table.")

    configured_preset = str(raw_workspace.get("default_preset", default_preset)).strip() or default_preset
    valid_presets = set(_preset_modules(descriptors))
    if configured_preset not in valid_presets:
        supported = ", ".join(sorted(valid_presets))
        raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} workspace.default_preset must be one of: {supported}.")

    update_modules = dict(defaults)
    raw_update = payload.get("update", {})
    if raw_update is None:
        raw_update = {}
    if not isinstance(raw_update, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} [update] section must be a table.")
    raw_module_updates = raw_update.get("modules", {})
    if raw_module_updates is None:
        raw_module_updates = {}
    if not isinstance(raw_module_updates, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} [update.modules] section must be a table.")

    unknown_modules = [module_name for module_name in raw_module_updates if module_name not in defaults]
    if unknown_modules:
        supported = ", ".join(sorted(defaults))
        unknown = ", ".join(sorted(unknown_modules))
        raise WorkspaceUsageError(
            f"{WORKSPACE_CONFIG_PATH.as_posix()} update.modules contains unknown module(s): {unknown}. Supported modules: {supported}."
        )

    for module_name, module_payload in raw_module_updates.items():
        if not isinstance(module_payload, dict):
            raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} [update.modules.{module_name}] must be a table.")
        default_policy = defaults[module_name]
        source_type = str(module_payload.get("source_type", default_policy.source_type)).strip() or default_policy.source_type
        if source_type not in {"git", "local"}:
            raise WorkspaceUsageError(
                f"{WORKSPACE_CONFIG_PATH.as_posix()} update.modules.{module_name}.source_type must be `git` or `local`."
            )
        source_ref = str(module_payload.get("source_ref", default_policy.source_ref)).strip()
        if not source_ref:
            raise WorkspaceUsageError(
                f"{WORKSPACE_CONFIG_PATH.as_posix()} update.modules.{module_name}.source_ref must be a non-empty string."
            )
        source_label = str(module_payload.get("source_label", default_policy.source_label)).strip() or default_policy.source_label
        recommended_upgrade_after_days = module_payload.get("recommended_upgrade_after_days", default_policy.recommended_upgrade_after_days)
        if not isinstance(recommended_upgrade_after_days, int):
            raise WorkspaceUsageError(
                f"{WORKSPACE_CONFIG_PATH.as_posix()} update.modules.{module_name}.recommended_upgrade_after_days must be an integer."
            )
        update_modules[module_name] = ModuleUpdatePolicy(
            module=module_name,
            source_type=source_type,
            source_ref=source_ref,
            source_label=source_label,
            recommended_upgrade_after_days=recommended_upgrade_after_days,
            source="repo-config",
        )

    return WorkspaceConfig(
        target_root=target_root,
        path=config_path,
        exists=True,
        schema_version=1,
        default_preset=configured_preset,
        update_modules=update_modules,
        local_override=local_override,
    )


def _select_proof_payload(
    payload: dict[str, Any],
    *,
    route: str | None,
    current_only: bool,
) -> dict[str, Any]:
    if route and current_only:
        raise WorkspaceUsageError("proof selectors are mutually exclusive; use either --route or --current.")
    if route:
        answer = {
            "id": route,
            "command": payload["default_routes"].get(route),
        }
        matched = answer["command"] is not None
        refs = [COMPACT_CONTRACT_PROFILE_DOC, payload["command"], payload["canonical_doc"]]
        return _compact_contract_answer(
            surface="proof",
            selector={"route": route},
            answer=answer,
            refs=refs,
            matched=matched,
            target=payload["target"],
        )
    if current_only:
        answer = payload["current"]
        refs = [COMPACT_CONTRACT_PROFILE_DOC, payload["command"], payload["canonical_doc"]]
        return _compact_contract_answer(
            surface="proof",
            selector={"current": True},
            answer=answer,
            refs=refs,
            target=payload["target"],
        )
    return payload


def _emit_proof(
    *,
    format_name: str,
    target_root: Path,
    descriptors: dict[str, ModuleDescriptor],
    route: str | None = None,
    current_only: bool = False,
) -> None:
    payload = _proof_payload(target_root=target_root, descriptors=descriptors)
    payload = _select_proof_payload(payload, route=route, current_only=current_only)
    if format_name == "json":
        print(json.dumps(serialise_value(payload), indent=2))
        return
    if route or current_only:
        _emit_compact_answer_text(payload)
        return
    print(f"Target: {payload['target']}")
    print(f"Rule: {payload['rule']}")
    print(f"Doc: {payload['canonical_doc']}")
    print("Routes:")
    for label, command in payload["default_routes"].items():
        print(f"- {label}: {command}")
    print("Current:")
    installed_modules = payload["current"]["installed_modules"]
    print(f"- installed modules: {', '.join(installed_modules) if installed_modules else 'none'}")
    print(f"- status health: {payload['current']['status_health']}")
    print(f"- doctor health: {payload['current']['doctor_health']}")
    if payload["current"]["warnings"]:
        print("Warnings:")
        for warning in payload["current"]["warnings"]:
            print(f"- {warning}")
    if payload["current"]["needs_review"]:
        print("Needs review:")
        for item in payload["current"]["needs_review"]:
            print(f"- {item}")
    if payload["current"]["stale_generated_surfaces"]:
        print("Stale generated surfaces:")
        for item in payload["current"]["stale_generated_surfaces"]:
            print(f"- {item}")


def _proof_payload(*, target_root: Path, descriptors: dict[str, ModuleDescriptor]) -> dict[str, Any]:
    defaults = _defaults_payload()["proof_surfaces"]
    installed_modules = [
        module_name for module_name in _ordered_module_names(descriptors) if descriptors[module_name].detector(target_root)
    ]
    current: dict[str, Any] = {
        "installed_modules": installed_modules,
        "status_health": "not-run",
        "doctor_health": "not-run",
        "warnings": [],
        "needs_review": [],
        "stale_generated_surfaces": [],
    }
    if not installed_modules:
        current["status_health"] = "not-installed"
        current["doctor_health"] = "not-installed"
    else:
        config = _load_workspace_config(target_root=target_root, descriptors=descriptors)
        status_payload = _run_lifecycle_command(
            command_name="status",
            target_root=target_root,
            selected_modules=installed_modules,
            resolved_preset=None,
            descriptors=descriptors,
            dry_run=False,
            config=config,
        )
        doctor_payload = _run_lifecycle_command(
            command_name="doctor",
            target_root=target_root,
            selected_modules=installed_modules,
            resolved_preset=None,
            descriptors=descriptors,
            dry_run=False,
            config=config,
        )
        current = {
            "installed_modules": installed_modules,
            "status_health": status_payload["health"],
            "doctor_health": doctor_payload["health"],
            "warnings": _dedupe([*status_payload["warnings"], *doctor_payload["warnings"]]),
            "needs_review": _dedupe([*status_payload["needs_review"], *doctor_payload["needs_review"]]),
            "stale_generated_surfaces": _dedupe([*status_payload["stale_generated_surfaces"], *doctor_payload["stale_generated_surfaces"]]),
        }
    return {
        "target": target_root.as_posix(),
        "canonical_doc": defaults["canonical_doc"],
        "command": defaults["command"],
        "rule": defaults["rule"],
        "default_routes": defaults["default_routes"],
        "current": current,
    }


def _normalize_repo_path(path_text: str) -> str:
    return Path(path_text).as_posix().rstrip("/")


def _ownership_answer_for_path(payload: dict[str, Any], *, repo_path: str) -> tuple[dict[str, Any], bool]:
    normalized = _normalize_repo_path(repo_path)
    for entry in payload["authority_surfaces"]:
        surface = str(entry.get("surface", "")).rstrip("/")
        if surface == normalized:
            return (
                {
                    "path": normalized,
                    "owner": entry.get("owner"),
                    "ownership": entry.get("ownership"),
                    "authority": entry.get("authority"),
                    "surface": entry.get("surface"),
                    "summary": entry.get("summary"),
                    "matched_by": "authority_surface",
                },
                True,
            )
    for entry in payload["module_roots"]:
        root_path = str(entry.get("path", "")).rstrip("/")
        if normalized == root_path or normalized.startswith(f"{root_path}/"):
            return (
                {
                    "path": normalized,
                    "owner": entry.get("module"),
                    "ownership": entry.get("ownership"),
                    "authority": "module_root",
                    "surface": entry.get("path"),
                    "uninstall_policy": entry.get("uninstall_policy"),
                    "matched_by": "module_root",
                },
                True,
            )
    for entry in payload["managed_surfaces"]:
        surface = str(entry.get("path", ""))
        if fnmatch.fnmatch(normalized, surface):
            return (
                {
                    "path": normalized,
                    "owner": entry.get("module"),
                    "ownership": entry.get("ownership"),
                    "authority": entry.get("kind"),
                    "surface": entry.get("path"),
                    "uninstall_policy": entry.get("uninstall_policy"),
                    "matched_by": "managed_surface",
                },
                True,
            )
    for entry in payload["fences"]:
        file_path = str(entry.get("file", "")).rstrip("/")
        if normalized == file_path:
            return (
                {
                    "path": normalized,
                    "owner": entry.get("module"),
                    "ownership": entry.get("ownership"),
                    "authority": "managed_fence",
                    "surface": entry.get("file"),
                    "fence": entry.get("name"),
                    "matched_by": "fence_file",
                },
                True,
            )
    return ({"path": normalized}, False)


def _select_ownership_payload(
    payload: dict[str, Any],
    *,
    concern: str | None,
    repo_path: str | None,
) -> dict[str, Any]:
    if concern and repo_path:
        raise WorkspaceUsageError("ownership selectors are mutually exclusive; use either --concern or --path.")
    refs = [COMPACT_CONTRACT_PROFILE_DOC, payload["command"], payload["canonical_doc"], payload["ledger_path"]]
    if concern:
        answer = next((entry for entry in payload["authority_surfaces"] if entry.get("concern") == concern), {"concern": concern})
        return _compact_contract_answer(
            surface="ownership",
            selector={"concern": concern},
            answer=answer,
            refs=refs,
            matched="surface" in answer,
            target=payload["target"],
        )
    if repo_path:
        answer, matched = _ownership_answer_for_path(payload, repo_path=repo_path)
        return _compact_contract_answer(
            surface="ownership",
            selector={"path": _normalize_repo_path(repo_path)},
            answer=answer,
            refs=refs,
            matched=matched,
            target=payload["target"],
        )
    return payload


def _emit_ownership(
    *,
    format_name: str,
    target_root: Path,
    descriptors: dict[str, ModuleDescriptor],
    concern: str | None = None,
    repo_path: str | None = None,
) -> None:
    payload = _ownership_payload(target_root=target_root, descriptors=descriptors)
    payload = _select_ownership_payload(payload, concern=concern, repo_path=repo_path)
    if format_name == "json":
        print(json.dumps(serialise_value(payload), indent=2))
        return
    if concern or repo_path:
        _emit_compact_answer_text(payload)
        return
    print(f"Target: {payload['target']}")
    print(f"Rule: {payload['rule']}")
    print(f"Doc: {payload['canonical_doc']}")
    print(f"Ledger: {payload['ledger_path']}")
    print("Authority surfaces:")
    for entry in payload["authority_surfaces"]:
        print(f"- {entry['concern']}: {entry['surface']} ({entry['owner']}, {entry['ownership']}, authority={entry['authority']})")
    if payload["warnings"]:
        print("Warnings:")
        for warning in payload["warnings"]:
            print(f"- {warning}")


def _ownership_payload(*, target_root: Path, descriptors: dict[str, ModuleDescriptor]) -> dict[str, Any]:
    defaults = _defaults_payload()["ownership_mapping"]
    ledger_path = target_root / defaults["ledger"]
    warnings: list[str] = []
    ownership_classes: dict[str, Any] = {}
    module_roots: list[dict[str, Any]] = []
    managed_surfaces: list[dict[str, Any]] = []
    fences: list[dict[str, Any]] = []
    authority_surfaces: list[dict[str, Any]] = []

    if not ledger_path.exists():
        warnings.append(f"{defaults['ledger']}: ownership ledger missing")
    else:
        payload = tomllib.loads(ledger_path.read_text(encoding="utf-8"))
        ownership_classes = {key: value for key, value in (payload.get("ownership_classes") or {}).items() if isinstance(value, dict)}
        module_roots = [entry for entry in (payload.get("module_roots") or []) if isinstance(entry, dict)]
        managed_surfaces = [entry for entry in (payload.get("managed_surfaces") or []) if isinstance(entry, dict)]
        fences = [entry for entry in (payload.get("fences") or []) if isinstance(entry, dict)]
        authority_surfaces = [entry for entry in (payload.get("authority_surfaces") or []) if isinstance(entry, dict)]
        if not authority_surfaces:
            warnings.append(f"{defaults['ledger']}: authority_surfaces entries missing")

    installed_modules = [
        module_name for module_name in _ordered_module_names(descriptors) if descriptors[module_name].detector(target_root)
    ]
    return {
        "target": target_root.as_posix(),
        "canonical_doc": defaults["canonical_doc"],
        "command": defaults["command"],
        "rule": defaults["rule"],
        "ledger_path": defaults["ledger"],
        "installed_modules": installed_modules,
        "ownership_classes": ownership_classes,
        "module_roots": module_roots,
        "managed_surfaces": managed_surfaces,
        "fences": fences,
        "authority_surfaces": authority_surfaces,
        "warnings": warnings,
    }


def _module_update_policy_payload(*, config: WorkspaceConfig, target_root: Path | None) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for module_name in sorted(config.update_modules):
        policy = config.update_modules[module_name]
        metadata_relative = MODULE_UPGRADE_SOURCE_PATHS[module_name]
        sync_status = "unknown"
        current_source: dict[str, Any] | None = None
        if target_root is not None:
            current_source, sync_status = _current_module_upgrade_source_state(
                target_root=target_root, module_name=module_name, policy=policy
            )
        payload.append(
            {
                "module": module_name,
                "source_type": policy.source_type,
                "source_ref": policy.source_ref,
                "source_label": policy.source_label,
                "recommended_upgrade_after_days": policy.recommended_upgrade_after_days,
                "source": policy.source,
                "metadata_path": metadata_relative.as_posix(),
                "sync_status": sync_status,
                "current_source": current_source,
            }
        )
    return payload


def _empty_mixed_agent_local_override(*, path: Path | None, exists: bool) -> MixedAgentLocalOverride:
    return MixedAgentLocalOverride(
        path=path,
        exists=exists,
        applied=False,
        supports_internal_delegation=None,
        strong_planner_available=None,
        cheap_bounded_executor_available=None,
        prefer_internal_delegation_when_available=None,
    )


def _require_optional_bool(*, payload: dict[str, Any], key: str, config_path: Path) -> bool | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, bool):
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be a boolean.")
    return value


def _load_mixed_agent_local_override(*, target_root: Path) -> MixedAgentLocalOverride:
    local_path = target_root / WORKSPACE_LOCAL_CONFIG_PATH
    if not local_path.exists():
        return _empty_mixed_agent_local_override(path=local_path, exists=False)

    try:
        payload = tomllib.loads(local_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} is invalid TOML: {exc}.") from exc

    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise WorkspaceUsageError(
            f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} must set schema_version = 1 for the current local mixed-agent override contract."
        )

    unknown_top_level = sorted(set(payload) - {"schema_version", "runtime", "handoff"})
    if unknown_top_level:
        unknown_text = ", ".join(unknown_top_level)
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} contains unsupported top-level field(s): {unknown_text}.")

    raw_runtime = payload.get("runtime", {})
    if raw_runtime is None:
        raw_runtime = {}
    if not isinstance(raw_runtime, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [runtime] section must be a table.")
    unknown_runtime = sorted(
        set(raw_runtime) - {"supports_internal_delegation", "strong_planner_available", "cheap_bounded_executor_available"}
    )
    if unknown_runtime:
        unknown_text = ", ".join(unknown_runtime)
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [runtime] contains unsupported field(s): {unknown_text}.")

    raw_handoff = payload.get("handoff", {})
    if raw_handoff is None:
        raw_handoff = {}
    if not isinstance(raw_handoff, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [handoff] section must be a table.")
    unknown_handoff = sorted(set(raw_handoff) - {"prefer_internal_delegation_when_available"})
    if unknown_handoff:
        unknown_text = ", ".join(unknown_handoff)
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [handoff] contains unsupported field(s): {unknown_text}.")

    return MixedAgentLocalOverride(
        path=local_path,
        exists=True,
        applied=True,
        supports_internal_delegation=_require_optional_bool(
            payload=raw_runtime,
            key="supports_internal_delegation",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        strong_planner_available=_require_optional_bool(
            payload=raw_runtime,
            key="strong_planner_available",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        cheap_bounded_executor_available=_require_optional_bool(
            payload=raw_runtime,
            key="cheap_bounded_executor_available",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        prefer_internal_delegation_when_available=_require_optional_bool(
            payload=raw_handoff,
            key="prefer_internal_delegation_when_available",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
    )


def _sourced_value(value: bool | None, *, source: str) -> dict[str, Any]:
    return {"value": value, "source": source if value is not None else "unset"}


def _mixed_agent_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    defaults = _defaults_payload()["mixed_agent"]
    local_override = config.local_override
    planner_executor_pattern = "unspecified"
    if local_override.strong_planner_available and local_override.cheap_bounded_executor_available:
        planner_executor_pattern = "strong-planner-cheap-executor-available"
    handoff_preference = "unspecified"
    if local_override.supports_internal_delegation and local_override.prefer_internal_delegation_when_available:
        handoff_preference = "prefer-internal-when-safe"
    return {
        "status": "reporting-only",
        "rule": defaults["rule"],
        "decision_order": defaults["decision_order"],
        "repo_policy": {
            "path": WORKSPACE_CONFIG_PATH.as_posix(),
            "source": "repo-config" if config.exists else "product-defaults",
            "authoritative": True,
            "supported_fields": [],
        },
        "local_override": {
            "path": WORKSPACE_LOCAL_CONFIG_PATH.as_posix(),
            "supported": defaults["local_override"]["supported"],
            "supported_fields": defaults["local_override"]["supported_fields"],
            "exists": local_override.exists,
            "applied": local_override.applied,
            "status": "applied" if local_override.applied else "available-not-set",
            "rule": "local-only capability/cost posture; may not override repo-owned semantics",
        },
        "runtime_inference": {
            "tool_owned": defaults["runtime_inference"]["tool_owned"],
            "reported_here": False,
            "auditable_when_behavior_changes": defaults["runtime_inference"]["report_when_behavior_changes"],
            "scope": defaults["runtime_inference"]["scope"],
        },
        "effective_posture": {
            "supports_internal_delegation": _sourced_value(
                local_override.supports_internal_delegation,
                source="local-override",
            ),
            "strong_planner_available": _sourced_value(
                local_override.strong_planner_available,
                source="local-override",
            ),
            "cheap_bounded_executor_available": _sourced_value(
                local_override.cheap_bounded_executor_available,
                source="local-override",
            ),
            "prefer_internal_delegation_when_available": _sourced_value(
                local_override.prefer_internal_delegation_when_available,
                source="local-override",
            ),
        },
        "derived_mode": {
            "planner_executor_pattern": planner_executor_pattern,
            "handoff_preference": handoff_preference,
        },
        "handoff_quality": defaults["handoff_quality"],
        "success_measures": defaults["success_measures"],
    }


def _config_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    return {
        "target": config.target_root.as_posix() if config.target_root is not None else None,
        "config_path": config.path.as_posix() if config.path is not None else WORKSPACE_CONFIG_PATH.as_posix(),
        "exists": config.exists,
        "schema_version": config.schema_version,
        "workspace": {"default_preset": config.default_preset},
        "update": {
            "wrapper_rule": "normal update execution stays behind agentic-workspace",
            "modules": _module_update_policy_payload(config=config, target_root=config.target_root),
        },
        "mixed_agent": _mixed_agent_payload(config=config),
    }


def _emit_config(*, format_name: str, config: WorkspaceConfig) -> None:
    payload = _config_payload(config=config)
    if format_name == "json":
        print(json.dumps(serialise_value(payload), indent=2))
        return
    print(f"Target: {payload['target']}")
    print(f"Config path: {payload['config_path']}")
    print(f"Exists: {payload['exists']}")
    print(f"Default preset: {payload['workspace']['default_preset']}")
    print(f"Wrapper rule: {payload['update']['wrapper_rule']}")
    print("Update modules:")
    for module in payload["update"]["modules"]:
        print(f"- {module['module']}: {module['source_type']} {module['source_ref']}")
        print(f"  label: {module['source_label']}")
        print(f"  metadata: {module['metadata_path']} ({module['sync_status']})")
    print("Mixed-agent:")
    print(f"- rule: {payload['mixed_agent']['rule']}")
    print(f"- repo policy: {payload['mixed_agent']['repo_policy']['path']} ({payload['mixed_agent']['repo_policy']['source']})")
    print(f"- local override: {payload['mixed_agent']['local_override']['path']} ({payload['mixed_agent']['local_override']['status']})")
    print(
        "- effective posture: "
        f"internal delegation={payload['mixed_agent']['effective_posture']['supports_internal_delegation']['value']}, "
        f"strong planner={payload['mixed_agent']['effective_posture']['strong_planner_available']['value']}, "
        f"cheap bounded executor={payload['mixed_agent']['effective_posture']['cheap_bounded_executor_available']['value']}"
    )


def _current_module_upgrade_source_state(
    *, target_root: Path, module_name: str, policy: ModuleUpdatePolicy
) -> tuple[dict[str, Any] | None, str]:
    metadata_path = target_root / MODULE_UPGRADE_SOURCE_PATHS[module_name]
    if module_name == "planning":
        from repo_planning_bootstrap._source import resolve_upgrade_source as resolve_planning_upgrade_source

        current = resolve_planning_upgrade_source(target_root)
        current_payload = {
            "source_type": current.source_type,
            "source_ref": current.source_ref,
            "source_label": current.source_label,
            "recommended_upgrade_after_days": current.recommended_upgrade_after_days,
            "recorded_at": current.recorded_at,
            "path": current.path.as_posix() if current.path is not None else None,
        }
    else:
        from repo_memory_bootstrap._installer_output import resolve_upgrade_source as resolve_memory_upgrade_source

        current = resolve_memory_upgrade_source(target_root)
        current_payload = {
            "source_type": current["source_type"],
            "source_ref": current["source_ref"],
            "source_label": current["source_label"],
            "recommended_upgrade_after_days": current["recommended_upgrade_after_days"],
            "recorded_at": current.get("recorded_at"),
            "path": current["path"].as_posix() if current.get("path") is not None else None,
        }
    if not metadata_path.exists():
        return current_payload, "missing"
    if (
        current_payload["source_type"] == policy.source_type
        and current_payload["source_ref"] == policy.source_ref
        and current_payload["source_label"] == policy.source_label
        and current_payload["recommended_upgrade_after_days"] == policy.recommended_upgrade_after_days
    ):
        return current_payload, "current"
    return current_payload, "drift"


def _render_upgrade_source_text(*, policy: ModuleUpdatePolicy, recorded_at: str) -> str:
    return (
        f'source_type = "{policy.source_type}"\n'
        f'source_ref = "{policy.source_ref}"\n'
        f'source_label = "{policy.source_label}"\n'
        f'recorded_at = "{recorded_at}"\n'
        f"recommended_upgrade_after_days = {policy.recommended_upgrade_after_days}\n"
    )


def _sync_update_policy_actions(
    *,
    target_root: Path,
    selected_modules: list[str],
    dry_run: bool,
    command_name: str,
    config: WorkspaceConfig,
    apply: bool,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    actions: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    for module_name in selected_modules:
        policy = config.update_modules[module_name]
        relative = MODULE_UPGRADE_SOURCE_PATHS[module_name]
        destination = target_root / relative
        current_payload, sync_status = _current_module_upgrade_source_state(
            target_root=target_root,
            module_name=module_name,
            policy=policy,
        )
        if sync_status == "current":
            actions.append(
                {
                    "kind": "current",
                    "path": relative.as_posix(),
                    "detail": "module upgrade source metadata already matches the resolved workspace policy",
                }
            )
            continue

        if not apply and sync_status == "missing" and not config.exists:
            continue

        detail = "sync module upgrade source metadata from the resolved workspace policy"
        if not apply:
            actions.append(
                {
                    "kind": "warning" if command_name in {"status", "doctor"} else "manual review",
                    "path": relative.as_posix(),
                    "detail": "module upgrade source metadata differs from agentic-workspace.toml or the product default policy",
                }
            )
            warnings.append(
                {
                    "path": relative.as_posix(),
                    "message": "module upgrade source metadata differs from agentic-workspace.toml or the product default policy",
                }
            )
            continue

        recorded_at = current_payload.get("recorded_at") if current_payload else None
        if sync_status != "current" or not recorded_at:
            recorded_at = date.today().isoformat()
        rendered = _render_upgrade_source_text(policy=policy, recorded_at=str(recorded_at))
        existing = destination.read_text(encoding="utf-8") if destination.exists() else None
        if existing == rendered:
            actions.append({"kind": "current", "path": relative.as_posix(), "detail": detail})
            continue
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(rendered, encoding="utf-8")
        actions.append(
            {
                "kind": _write_action_kind(dry_run=dry_run, existing=existing),
                "path": relative.as_posix(),
                "detail": detail,
            }
        )
    return actions, warnings


def _skill_catalog_sources() -> tuple[SkillCatalogSource, ...]:
    return (
        SkillCatalogSource(
            name="planning-bundled",
            registry_path=Path(".agentic-workspace/planning/skills/REGISTRY.json"),
            skills_root=Path(".agentic-workspace/planning/skills"),
            owner="agentic-planning-bootstrap",
            source_kind="bundled-package-skills",
            default_scope="bundled",
            default_stability="package-managed",
        ),
        SkillCatalogSource(
            name="memory-core",
            registry_path=Path(".agentic-workspace/memory/skills/REGISTRY.json"),
            skills_root=Path(".agentic-workspace/memory/skills"),
            owner="agentic-memory-bootstrap",
            source_kind="installed-core-skills",
            default_scope="bundled",
            default_stability="package-managed",
        ),
        SkillCatalogSource(
            name="repo-memory",
            registry_path=Path("memory/skills/REGISTRY.json"),
            skills_root=Path("memory/skills"),
            owner="repo-local",
            source_kind="repo-owned-memory-skills",
            default_scope="repo-owned",
            default_stability="repo-managed",
        ),
        SkillCatalogSource(
            name="repo-tools",
            registry_path=Path("tools/skills/REGISTRY.json"),
            skills_root=Path("tools/skills"),
            owner="repo-local",
            source_kind="repo-owned-tool-skills",
            default_scope="repo-owned",
            default_stability="repo-managed",
        ),
    )


def _emit_skills(*, format_name: str, target_root: Path | None, task_text: str | None) -> None:
    payload = _skills_payload(target_root=target_root, task_text=task_text)
    if format_name == "json":
        print(json.dumps(serialise_value(payload), indent=2))
        return
    if payload.get("task"):
        print(f"Task: {payload['task']}")
    if payload["recommendations"]:
        print("Recommended:")
        for recommendation in payload["recommendations"]:
            print(f"- {recommendation['id']} ({recommendation['score']}): {recommendation['summary']}")
            print(f"  path: {recommendation['path']}")
            print(f"  reasons: {', '.join(recommendation['reasons'])}")
    elif payload.get("task"):
        print("Recommended:")
        print("- none")
    for skill in payload["skills"]:
        print(f"{skill['id']}: {skill['summary']}")
        print(f"  path: {skill['path']}")
        print(f"  owner: {skill['owner']}")
        print(f"  source: {skill['source_kind']}")
        print(f"  registration: {skill['registration']}")
    if payload["warnings"]:
        print("Warnings:")
        for warning in payload["warnings"]:
            print(f"- {warning}")


def _skills_payload(*, target_root: Path | None, task_text: str | None) -> dict[str, Any]:
    if target_root is None:
        return {"skills": [], "recommendations": [], "warnings": [], "sources": []}
    skills, warnings, sources = _discover_registered_skills(target_root=target_root)
    recommendations = _recommend_skills(task_text=task_text, skills=skills) if task_text else []
    return {
        "target": target_root.as_posix(),
        "task": task_text,
        "skills": [_skill_payload(skill=skill) for skill in skills],
        "recommendations": [
            {
                **_skill_payload(skill=recommendation.skill),
                "score": recommendation.score,
                "reasons": list(recommendation.reasons),
            }
            for recommendation in recommendations
        ],
        "warnings": warnings,
        "sources": sources,
    }


def _discover_registered_skills(*, target_root: Path) -> tuple[list[RegisteredSkill], list[str], list[dict[str, str]]]:
    discovered: list[RegisteredSkill] = []
    warnings: list[str] = []
    sources: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for source in _skill_catalog_sources():
        registry_file = target_root / source.registry_path
        skills_root = target_root / source.skills_root
        source_state = "absent"
        if registry_file.exists():
            source_state = "registry"
            for skill in _load_registered_skills(source=source, registry_file=registry_file):
                key = (skill.skill_id, skill.path.as_posix())
                if key in seen:
                    continue
                seen.add(key)
                discovered.append(skill)
        scanned_paths = _scan_skill_paths(skills_root)
        registered_paths = {
            (target_root / source.skills_root / skill.path.relative_to(source.skills_root)).resolve()
            for skill in discovered
            if skill.path.as_posix().startswith(source.skills_root.as_posix() + "/")
        }
        unregistered = [path for path in scanned_paths if path.resolve() not in registered_paths]
        if unregistered and not registry_file.exists():
            source_state = "implicit-scan"
            warnings.append(
                f"{source.registry_path.as_posix()} is missing; registered discovery for {source.skills_root.as_posix()} is unavailable"
            )
        for path in unregistered:
            relative = path.relative_to(target_root)
            skill_id = relative.parent.name
            key = (skill_id, relative.as_posix())
            if key in seen:
                continue
            seen.add(key)
            discovered.append(
                RegisteredSkill(
                    skill_id=skill_id,
                    path=relative,
                    owner=source.owner,
                    source_kind=source.source_kind,
                    scope=source.default_scope,
                    stability=source.default_stability,
                    summary="unregistered skill discovered by directory scan",
                    activation_hints=SkillActivationHints(verbs=(), nouns=(), phrases=(), when=()),
                    registration="implicit-scan",
                )
            )
        if registry_file.exists():
            missing_files = [
                skill.path.as_posix()
                for skill in discovered
                if skill.registration == "explicit"
                and skill.path.as_posix().startswith(source.skills_root.as_posix() + "/")
                and not (target_root / skill.path).exists()
            ]
            for missing in missing_files:
                warnings.append(f"{source.registry_path.as_posix()} points at missing skill file {missing}")
        if registry_file.exists() or scanned_paths:
            sources.append(
                {
                    "name": source.name,
                    "registry_path": source.registry_path.as_posix(),
                    "skills_root": source.skills_root.as_posix(),
                    "state": source_state,
                }
            )

    discovered.sort(key=lambda skill: (skill.source_kind, skill.skill_id, skill.path.as_posix()))
    return discovered, warnings, sources


def _load_registered_skills(*, source: SkillCatalogSource, registry_file: Path) -> list[RegisteredSkill]:
    payload = json.loads(registry_file.read_text(encoding="utf-8"))
    entries = payload.get("skills", [])
    skills: list[RegisteredSkill] = []
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        relative = Path(str(raw.get("path", "")))
        activation_hints = raw.get("activation_hints", {})
        if not isinstance(activation_hints, dict):
            activation_hints = {}
        skills.append(
            RegisteredSkill(
                skill_id=str(raw.get("id", "")).strip(),
                path=(source.skills_root / relative),
                owner=str(payload.get("owner", source.owner)),
                source_kind=str(payload.get("source_kind", source.source_kind)),
                scope=str(raw.get("scope", source.default_scope)),
                stability=str(raw.get("stability", source.default_stability)),
                summary=str(raw.get("summary", "")).strip(),
                activation_hints=SkillActivationHints(
                    verbs=tuple(str(value).strip() for value in activation_hints.get("verbs", []) if str(value).strip()),
                    nouns=tuple(str(value).strip() for value in activation_hints.get("nouns", []) if str(value).strip()),
                    phrases=tuple(str(value).strip() for value in activation_hints.get("phrases", []) if str(value).strip()),
                    when=tuple(str(value).strip() for value in activation_hints.get("when", []) if str(value).strip()),
                ),
                registration="explicit",
            )
        )
    return [skill for skill in skills if skill.skill_id and skill.path.as_posix()]


def _skill_payload(*, skill: RegisteredSkill) -> dict[str, Any]:
    return {
        "id": skill.skill_id,
        "path": skill.path.as_posix(),
        "owner": skill.owner,
        "source_kind": skill.source_kind,
        "scope": skill.scope,
        "stability": skill.stability,
        "summary": skill.summary,
        "activation_hints": {
            "verbs": list(skill.activation_hints.verbs),
            "nouns": list(skill.activation_hints.nouns),
            "phrases": list(skill.activation_hints.phrases),
            "when": list(skill.activation_hints.when),
        },
        "registration": skill.registration,
    }


def _recommend_skills(*, task_text: str, skills: list[RegisteredSkill]) -> list[SkillRecommendation]:
    task_text_lower = task_text.lower()
    task_tokens = set(_skill_match_tokens(task_text))
    recommendations: list[SkillRecommendation] = []

    for skill in skills:
        score = 0
        hint_score = 0
        reasons: list[str] = []

        matched_phrases = _matched_skill_terms(
            terms=skill.activation_hints.phrases,
            task_text_lower=task_text_lower,
            task_tokens=task_tokens,
        )
        if matched_phrases:
            phrase_score = len(matched_phrases) * 6
            score += phrase_score
            hint_score += phrase_score
            reasons.append(f"phrase match: {', '.join(matched_phrases)}")

        for label, terms, weight in (
            ("verb", skill.activation_hints.verbs, 2),
            ("noun", skill.activation_hints.nouns, 2),
            ("context", skill.activation_hints.when, 1),
        ):
            matched = _matched_skill_terms(terms=terms, task_text_lower=task_text_lower, task_tokens=task_tokens)
            if matched:
                matched_score = len(matched) * weight
                score += matched_score
                hint_score += matched_score
                reasons.append(f"{label} match: {', '.join(matched)}")

        summary_overlap = _summary_overlap_tokens(skill=skill, task_tokens=task_tokens)
        if summary_overlap:
            score += len(summary_overlap)
            reasons.append(f"summary overlap: {', '.join(summary_overlap)}")

        if score > 0:
            recommendations.append(SkillRecommendation(skill=skill, hint_score=hint_score, score=score, reasons=tuple(reasons)))

    if any(recommendation.hint_score > 0 for recommendation in recommendations):
        recommendations = [recommendation for recommendation in recommendations if recommendation.hint_score > 0]

    recommendations.sort(
        key=lambda recommendation: (
            -recommendation.hint_score,
            -recommendation.score,
            recommendation.skill.registration != "explicit",
            recommendation.skill.source_kind,
            recommendation.skill.skill_id,
        )
    )
    return recommendations


def _matched_skill_terms(*, terms: tuple[str, ...], task_text_lower: str, task_tokens: set[str]) -> list[str]:
    matched = [term for term in terms if _skill_term_matches(term=term, task_text_lower=task_text_lower, task_tokens=task_tokens)]
    return sorted(dict.fromkeys(matched))


def _skill_term_matches(*, term: str, task_text_lower: str, task_tokens: set[str]) -> bool:
    normalised = " ".join(_skill_match_tokens(term))
    if not normalised:
        return False
    if " " in normalised:
        return normalised in task_text_lower
    return normalised in task_tokens


def _summary_overlap_tokens(*, skill: RegisteredSkill, task_tokens: set[str]) -> list[str]:
    candidate_tokens = {
        token
        for token in _skill_match_tokens(f"{skill.skill_id} {skill.summary}")
        if len(token) >= 4 and token not in {"skill", "skills", "task", "tasks", "repo", "repository", "current"}
    }
    return sorted(candidate_tokens & task_tokens)


def _skill_match_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _scan_skill_paths(skills_root: Path) -> list[Path]:
    if not skills_root.exists():
        return []
    return sorted(path for path in skills_root.rglob("SKILL.md") if "__pycache__" not in path.parts)


def _module_registry(*, descriptors: dict[str, ModuleDescriptor], target_root: Path | None) -> list[ModuleRegistryEntry]:
    entries: list[ModuleRegistryEntry] = []
    for module_name in _ordered_module_names(descriptors):
        descriptor = descriptors[module_name]
        lifecycle_commands = tuple(sorted(descriptor.commands))
        dry_run_commands = tuple(command_name for command_name in lifecycle_commands if "dry_run" in descriptor.command_args[command_name])
        force_commands = tuple(command_name for command_name in lifecycle_commands if "force" in descriptor.command_args[command_name])
        installed = descriptor.detector(target_root) if target_root is not None else None
        entries.append(
            ModuleRegistryEntry(
                name=descriptor.name,
                description=descriptor.description,
                lifecycle_commands=lifecycle_commands,
                lifecycle_hook_expectations=lifecycle_commands,
                autodetects_installation=True,
                installed=installed,
                install_signals=descriptor.install_signals,
                workflow_surfaces=descriptor.workflow_surfaces,
                generated_artifacts=descriptor.generated_artifacts,
                dry_run_commands=dry_run_commands,
                force_commands=force_commands,
                capabilities=descriptor.capabilities,
                dependencies=descriptor.dependencies,
                conflicts=descriptor.conflicts,
                result_contract=descriptor.result_contract,
            )
        )
    return entries


def _emit_payload(*, payload: dict[str, Any], format_name: str) -> None:
    if format_name == "json":
        print(json.dumps(serialise_value(payload), indent=2))
        return
    if payload.get("command") == "prompt":
        _emit_prompt_text(payload)
        return
    if payload.get("command") == "init":
        _emit_init_text(payload)
        return
    if "modules" in payload and "reports" not in payload and "command" not in payload:
        for module_data in payload["modules"]:
            print(f"{module_data['name']}: {module_data['description']}")
            print(f"  commands: {', '.join(module_data['commands'])}")
            print(f"  capabilities: {', '.join(module_data['capabilities'])}")
        return
    _emit_lifecycle_text(payload)


def _emit_init_text(payload: dict[str, Any]) -> None:
    print(f"Target: {payload['target']}")
    print(f"Command: init{' (dry-run)' if payload.get('dry_run') else ''}")
    print(f"Modules: {', '.join(payload['modules'])}")
    if isinstance(payload.get("config"), dict):
        print(f"Config: {payload['config']['config_path']}")
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
    if payload.get("handoff_record_path"):
        print(f"Handoff record file: {payload['handoff_record_path']}")
    if payload.get("handoff_prompt"):
        print("")
        print("Handoff Prompt:")
        print(payload["handoff_prompt"])
    if payload.get("handoff_record"):
        print("")
        print("Handoff Record:")
        print(json.dumps(serialise_value(payload["handoff_record"]), indent=2))


def _emit_lifecycle_text(payload: dict[str, Any]) -> None:
    print(f"Target: {payload['target']}")
    print(f"Command: {payload['command']}{' (dry-run)' if payload.get('dry_run') else ''}")
    print(f"Modules: {', '.join(payload['modules'])}")
    if isinstance(payload.get("config"), dict):
        print(f"Config: {payload['config']['config_path']}")
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


def _emit_prompt_text(payload: dict[str, Any]) -> None:
    print(f"Target: {payload['target']}")
    print(f"Command: prompt {payload['prompt_command']}")
    print(f"Modules: {', '.join(payload['modules'])}")
    if isinstance(payload.get("config"), dict):
        print(f"Config: {payload['config']['config_path']}")
    if payload.get("prompt_requirement"):
        print(f"Prompt requirement: {payload['prompt_requirement']}")
    _print_path_list("Needs review", payload.get("needs_review", []))
    _print_path_list("Warnings", payload.get("warnings", []))
    if payload.get("handoff_record_path"):
        print(f"Handoff record file: {payload['handoff_record_path']}")
    print("")
    print("Handoff Prompt:")
    print(payload["handoff_prompt"])
    if payload.get("handoff_record"):
        print("")
        print("Handoff Record:")
        print(json.dumps(serialise_value(payload["handoff_record"]), indent=2))


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


def _module_workflow_surfaces(*, selected_modules: list[str], descriptors: dict[str, ModuleDescriptor]) -> tuple[Path, ...]:
    ordered: list[Path] = []
    for module_name in selected_modules:
        for path in descriptors[module_name].workflow_surfaces:
            if path not in ordered:
                ordered.append(path)
    return tuple(ordered)


def _module_generated_artifacts(*, selected_modules: list[str], descriptors: dict[str, ModuleDescriptor]) -> set[str]:
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
