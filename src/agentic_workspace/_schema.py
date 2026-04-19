from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict


@dataclass(frozen=True)
class ModuleResultContract:
    schema_version: str
    guaranteed_fields: tuple[str, ...]
    action_fields: tuple[str, ...]
    warning_fields: tuple[str, ...]


@dataclass(frozen=True)
class RootAgentsCleanupBlock:
    block: str
    start_marker: str
    end_marker: str
    label: str


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


class ModuleReportFinding(TypedDict, total=False):
    path: str
    detail: str
    kind: str
    message: str


class ModuleReport(TypedDict, total=False):
    module: str
    actions: list[ModuleReportFinding]
    warnings: list[ModuleReportFinding]
    findings: list[ModuleReportFinding]
