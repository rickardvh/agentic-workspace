from __future__ import annotations

import argparse
import fnmatch
import json
import re
import tomllib
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

from agentic_workspace import __version__
from agentic_workspace.contract_tooling import compact_contract_manifest, proof_routes_manifest, report_contract_manifest
from agentic_workspace.reporting_support import (
    output_contract_payload,
    repo_friction_payload,
    setup_discovery_payload,
    standing_intent_payload,
)
from agentic_workspace.result_adapter import adapt_module_result, serialise_value
from agentic_workspace.workspace_output import (
    _display_path,
    _emit_init_text,
    _emit_lifecycle_text,
    _emit_prompt_text,
    _emit_report_text,
    _emit_setup_text,
)

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
    "safety.safe_to_auto_run_commands",
    "safety.requires_human_verification_on_pr",
    "delegation_targets.<target>.strength",
    "delegation_targets.<target>.confidence",
    "delegation_targets.<target>.task_fit",
    "delegation_targets.<target>.execution_methods",
)
WORKSPACE_PAYLOAD_FILES = (
    Path(".agentic-workspace/WORKFLOW.md"),
    Path(".agentic-workspace/OWNERSHIP.toml"),
)
WORKSPACE_CONFIG_PATH = Path("agentic-workspace.toml")
WORKSPACE_LOCAL_CONFIG_PATH = Path("agentic-workspace.local.toml")
WORKSPACE_DELEGATION_OUTCOMES_PATH = Path("agentic-workspace.delegation-outcomes.json")
WORKSPACE_EXTERNAL_AGENT_PATH = Path("llms.txt")
WORKSPACE_BOOTSTRAP_HANDOFF_PATH = Path(".agentic-workspace/bootstrap-handoff.md")
WORKSPACE_BOOTSTRAP_HANDOFF_RECORD_PATH = Path(".agentic-workspace/bootstrap-handoff.json")
DEFAULT_AGENT_INSTRUCTIONS_FILE = "AGENTS.md"
SUPPORTED_AGENT_INSTRUCTIONS_FILES = (
    "AGENTS.md",
    "GEMINI.md",
)
DEFAULT_WORKFLOW_ARTIFACT_PROFILE = "repo-owned"
SUPPORTED_WORKFLOW_ARTIFACT_PROFILES = (
    "repo-owned",
    "gemini",
)
WORKSPACE_AGENTS_PATH = Path(DEFAULT_AGENT_INSTRUCTIONS_FILE)
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
DEFAULT_IMPROVEMENT_LATITUDE = "conservative"
SUPPORTED_IMPROVEMENT_LATITUDES = (
    "none",
    "reporting",
    "conservative",
    "balanced",
    "proactive",
)
DEFAULT_OPTIMIZATION_BIAS = "balanced"
SUPPORTED_OPTIMIZATION_BIASES = (
    "agent-efficiency",
    "balanced",
    "human-legibility",
)
SUPPORTED_DELEGATION_TARGET_STRENGTHS = (
    "strong",
    "medium",
    "weak",
)
SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS = (
    "internal",
    "cli",
    "api",
)
DELEGATION_OUTCOMES_KIND = "agentic-workspace/delegation-outcomes/v1"
SUPPORTED_DELEGATION_OUTCOMES = (
    "success",
    "mixed",
    "failed",
)
SUPPORTED_HANDOFF_SUFFICIENCY = (
    "sufficient",
    "borderline",
    "insufficient",
)
SUPPORTED_REVIEW_BURDENS = (
    "light",
    "normal",
    "high",
)
SETUP_FINDINGS_PATH = Path("tools/setup-findings.json")
SETUP_FINDINGS_KIND = "workspace-setup-findings/v1"
SUPPORTED_SETUP_FINDING_CLASSES = (
    "repo_friction_evidence",
    "planning_candidate",
)


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
    agent_instructions_file: str
    agent_instructions_source: str
    workflow_artifact_profile: str
    workflow_artifact_profile_source: str
    improvement_latitude: str
    improvement_latitude_source: str
    optimization_bias: str
    optimization_bias_source: str
    detected_agent_instructions_files: tuple[str, ...]
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
    safe_to_auto_run_commands: bool | None
    requires_human_verification_on_pr: bool | None
    delegation_targets: tuple["DelegationTargetProfile", ...]


@dataclass(frozen=True)
class DelegationTargetProfile:
    name: str
    strength: str
    execution_methods: tuple[str, ...]
    confidence: float | None
    task_fit: tuple[str, ...]


@dataclass(frozen=True)
class DelegationOutcomeRecord:
    recorded_at: str
    delegation_target: str
    task_class: str
    outcome: str
    handoff_sufficiency: str
    review_burden: str
    escalation_required: bool


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

    setup_parser = subparsers.add_parser(
        "setup",
        help="Show the bounded post-bootstrap setup guidance for a mature repository.",
    )
    _add_selection_arguments(setup_parser)

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

    delegation_outcome_parser = subparsers.add_parser(
        "note-delegation-outcome",
        help="Append one local-only delegation outcome record for target-profile tuning.",
    )
    delegation_outcome_parser.add_argument("--target", help="Optional repository path used to record the local outcome.")
    delegation_outcome_parser.add_argument("--delegation-target", required=True, help="Local delegation target alias.")
    delegation_outcome_parser.add_argument("--task-class", required=True, help="Bounded task class label for this delegated run.")
    delegation_outcome_parser.add_argument(
        "--outcome",
        required=True,
        choices=SUPPORTED_DELEGATION_OUTCOMES,
        help="High-level delegated execution outcome.",
    )
    delegation_outcome_parser.add_argument(
        "--handoff-sufficiency",
        choices=SUPPORTED_HANDOFF_SUFFICIENCY,
        default="sufficient",
        help="Whether the checked-in handoff was enough for the delegated worker.",
    )
    delegation_outcome_parser.add_argument(
        "--review-burden",
        choices=SUPPORTED_REVIEW_BURDENS,
        default="normal",
        help="How much review/rework burden remained after delegation.",
    )
    delegation_outcome_parser.add_argument(
        "--escalation-required",
        action="store_true",
        help="Record that the delegated run had to stop and escalate.",
    )
    _add_format_argument(delegation_outcome_parser)

    skills_parser = subparsers.add_parser(
        "skills",
        help="List registered workspace skills from installed package registries and repo-owned skill registries.",
    )
    skills_parser.add_argument("--target", help="Optional repository path used to inspect installed and repo-owned skills.")
    skills_parser.add_argument("--task", help="Optional task description used to recommend likely skills.")
    _add_format_argument(skills_parser)

    report_parser = subparsers.add_parser(
        "report",
        help="Show a compact combined workspace report for installed modules, mixed-agent posture, and next-action guidance.",
    )
    _add_selection_arguments(report_parser)

    init_parser = subparsers.add_parser("init", help="Bootstrap selected modules into a target repository.")
    _add_selection_arguments(init_parser)
    init_parser.add_argument(
        "--agent-instructions-file",
        help="Canonical startup instructions filename to use for this repo (for example AGENTS.md or GEMINI.md).",
    )
    init_parser.add_argument("--adopt", action="store_true", help="Force conservative adopt behavior.")
    init_parser.add_argument("--dry-run", action="store_true", help="Show planned changes without mutating files.")
    init_parser.add_argument("--print-prompt", action="store_true", help="Print the generated handoff prompt.")
    init_parser.add_argument("--write-prompt", help="Write the generated handoff prompt to a file.")

    prompt_parser = subparsers.add_parser("prompt", help="Print a ready-to-paste workspace lifecycle handoff prompt.")
    prompt_subparsers = prompt_parser.add_subparsers(dest="prompt_command", required=True)
    prompt_init_parser = prompt_subparsers.add_parser("init", help="Print the workspace bootstrap handoff prompt.")
    _add_selection_arguments(prompt_init_parser)
    prompt_init_parser.add_argument(
        "--agent-instructions-file",
        help="Canonical startup instructions filename to use for this repo (for example AGENTS.md or GEMINI.md).",
    )
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
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Require prompt-free lifecycle behavior and handoff guidance suitable for unattended agents.",
    )
    _add_format_argument(parser)


def _add_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format.")


def _validate_agent_instructions_filename(filename: str) -> str:
    normalized = filename.strip()
    if normalized not in SUPPORTED_AGENT_INSTRUCTIONS_FILES:
        supported = ", ".join(SUPPORTED_AGENT_INSTRUCTIONS_FILES)
        raise WorkspaceUsageError(f"agent instructions filename must be one of: {supported}.")
    return normalized


def _validate_workflow_artifact_profile(profile: str) -> str:
    normalized = profile.strip() or DEFAULT_WORKFLOW_ARTIFACT_PROFILE
    if normalized not in SUPPORTED_WORKFLOW_ARTIFACT_PROFILES:
        supported = ", ".join(SUPPORTED_WORKFLOW_ARTIFACT_PROFILES)
        raise WorkspaceUsageError(f"workflow artifact profile must be one of: {supported}.")
    return normalized


def _validate_improvement_latitude(value: str) -> str:
    normalized = value.strip() or DEFAULT_IMPROVEMENT_LATITUDE
    if normalized not in SUPPORTED_IMPROVEMENT_LATITUDES:
        supported = ", ".join(SUPPORTED_IMPROVEMENT_LATITUDES)
        raise WorkspaceUsageError(f"workspace.improvement_latitude must be one of: {supported}.")
    return normalized


def _validate_optimization_bias(value: str) -> str:
    normalized = value.strip() or DEFAULT_OPTIMIZATION_BIAS
    if normalized not in SUPPORTED_OPTIMIZATION_BIASES:
        supported = ", ".join(SUPPORTED_OPTIMIZATION_BIASES)
        raise WorkspaceUsageError(f"workspace.optimization_bias must be one of: {supported}.")
    return normalized


def _workflow_artifact_profile_payload(profile: str) -> dict[str, Any]:
    profiles = {
        "repo-owned": {
            "profile": "repo-owned",
            "summary": "Use only the repo-owned planning surfaces; do not rely on native runtime artifacts.",
            "native_artifacts": [],
            "canonical_surfaces": ["TODO.md", "docs/execplans/"],
            "sync_rule": "TODO.md and docs/execplans stay authoritative; no extra runtime artifact should carry durable state.",
            "handoff_rule": "Use repo-owned planning surfaces directly for restart, review, and cross-agent continuation.",
        },
        "gemini": {
            "profile": "gemini",
            "summary": (
                "Allow Gemini-style native workflow artifacts as runtime scratchpads, but "
                "project durable state back into repo-owned planning before handoff or review."
            ),
            "native_artifacts": ["implementation_plan.md", "task.md", "walkthrough.md"],
            "canonical_surfaces": ["TODO.md", "docs/execplans/"],
            "sync_rule": (
                "Before review, handoff, or session end, mirror the durable execution state into "
                "TODO.md and the active execplan instead of leaving it only in native artifacts."
            ),
            "handoff_rule": (
                "Treat native artifacts as local execution aids; treat TODO.md and docs/execplans as the only cross-agent source of truth."
            ),
        },
    }
    return profiles[profile].copy()


def _improvement_latitude_payload(mode: str) -> dict[str, Any]:
    policies = {
        "none": {
            "mode": "none",
            "initiative_posture": "no-opportunistic-action",
            "summary": ("Do not perform opportunistic repo-friction reduction outside the explicitly requested work."),
            "allows": [
                "only the cleanup necessary to complete the requested work safely",
                "ignoring incidental friction that does not block the current slice",
            ],
            "forbids": [
                "agent-initiated cleanup prompted only by repo-friction evidence",
                "turning incidental hotspots into side work during the current slice",
            ],
            "reporting_destinations": [
                "agentic-workspace report --target ./repo --format json",
            ],
            "reporting_rule": "Surface friction passively through derived reporting only; do not create follow-on work on your own.",
        },
        "reporting": {
            "mode": "reporting",
            "initiative_posture": "reporting-only",
            "summary": ("Notice and surface notable repo friction, but do not reduce it on the agent's own initiative."),
            "allows": [
                "recording notable friction in bounded reporting or review outputs",
                "capturing durable follow-through in planning residue when the current slice already owns planning state",
                "surfacing evidence-backed hotspots for later human-directed action",
            ],
            "forbids": [
                "opportunistic cleanup outside the explicitly requested work",
                "promoting friction into active work without a bounded promotion step",
            ],
            "reporting_destinations": [
                "agentic-workspace report --target ./repo --format json",
                "review outputs",
                "TODO.md or the active execplan when the current slice already owns planning residue",
            ],
            "reporting_rule": (
                "Surface notable friction through bounded reporting or residue; do not act on it without explicit direction."
            ),
        },
        "conservative": {
            "mode": "conservative",
            "initiative_posture": "local-touched-scope-only",
            "summary": (
                "Only reduce repo friction opportunistically inside already-touched scope; "
                "do not create standalone cleanup work from one hotspot alone."
            ),
            "allows": [
                "small local simplifications inside already-touched files",
                "narrow helper extraction when proof and ownership stay unchanged",
                "recording repeated friction as durable follow-on instead of widening the current slice",
            ],
            "forbids": [
                "standalone cleanup work triggered by one hotspot alone",
                "broad refactors or concept-pruning without explicit promotion",
            ],
            "reporting_destinations": [
                "agentic-workspace report --target ./repo --format json",
                "TODO.md or the active execplan when repeated friction deserves promotion",
            ],
            "reporting_rule": (
                "Use reporting to justify or defer bounded follow-on; do not treat one hotspot as permission for standalone cleanup."
            ),
        },
        "balanced": {
            "mode": "balanced",
            "initiative_posture": "bounded-evidence-backed-action",
            "summary": (
                "Allow bounded friction reduction when evidence is clear and the extra work "
                "stays inside the current proof and ownership boundary."
            ),
            "allows": [
                "simplifying a touched hotspot during the current slice",
                "small repo-friction reductions when repeated shared evidence is present and proof stays narrow",
                "turning repeated friction into a bounded follow-on candidate",
            ],
            "forbids": [
                "rewriting requested ends in the name of cleanup",
                "treating one-off agent discomfort or local taste as enough evidence for repo-directed change",
                "broad cross-owner refactors without promotion",
            ],
            "reporting_destinations": [
                "agentic-workspace report --target ./repo --format json",
                "TODO.md or the active execplan when friction should become bounded follow-on work",
            ],
            "reporting_rule": (
                "Use reporting to preserve evidence and deferred cleanup residue whenever the current slice intentionally stops short."
            ),
        },
        "proactive": {
            "mode": "proactive",
            "initiative_posture": "bounded-standalone-action-allowed",
            "summary": (
                "Allow bounded standalone friction reduction when evidence is strong and the "
                "work can still stay inside clear ownership and proof lanes."
            ),
            "allows": [
                "small standalone cleanup slices backed by repeated shared friction evidence",
                "collapsing low-value local complexity before it grows further",
                "promoting repeated friction into planning earlier",
            ],
            "forbids": [
                "unsignaled broad redesign under a cleanup label",
                "using one-off preference or single-agent discomfort as the proof threshold for repo-directed cleanup",
                "using proactive mode as a scheduler or blanket refactor permission",
            ],
            "reporting_destinations": [
                "agentic-workspace report --target ./repo --format json",
                "TODO.md or the active execplan when proactive cleanup stops before the larger opportunity is complete",
            ],
            "reporting_rule": "Use reporting to preserve evidence and unfinished bounded cleanup residue, not to justify hidden widening.",
        },
    }
    return policies[mode].copy()


def _workspace_self_adaptation_payload() -> dict[str, Any]:
    return {
        "status": "allowed-with-bounds",
        "summary": (
            "Workspace-self-adaptation may reduce friction inside Agentic Workspace-owned surfaces under every improvement-latitude mode."
        ),
        "rule": (
            "Treat improvement_latitude as the policy for repo-directed initiative only; do not read "
            "it as a ban on bounded workspace self-improvement."
        ),
        "applies_to": [
            "reporting surfaces",
            "routing and selector surfaces",
            "recovery surfaces",
            "workspace contract clarity",
        ],
        "bounded_by": [
            "correctness",
            "ownership",
            "proof",
            "portability",
        ],
    }


def _friction_response_order_payload() -> list[dict[str, Any]]:
    return [
        {
            "step": 1,
            "action": "adapt-inside-workspace-first",
            "rule": ("Adapt inside Agentic Workspace first when the friction can be removed there safely and cheaply."),
        },
        {
            "step": 2,
            "action": "promote-repo-directed-improvement-when-external",
            "rule": (
                "Promote repo-directed improvement only when the friction reflects a real repo "
                "problem that should not be masked by workspace adaptation."
            ),
        },
        {
            "step": 3,
            "action": "avoid-externalizing-honestly-absorbable-friction",
            "rule": ("Do not externalize friction to the user when Agentic Workspace can honestly absorb it itself."),
        },
    ]


def _workspace_self_adaptation_guardrail_payload() -> dict[str, Any]:
    return {
        "adapt_when": [
            "the friction is genuinely about workspace fit, reporting, routing, selector design, recovery clarity, or contract wording",
            "one bounded workspace change can remove the friction without hiding repo-owned structural problems",
        ],
        "surface_repo_friction_when": [
            "the root problem is really unclear repo seams, tranche boundaries, validation friction, or ownership",
            "repeated friction would otherwise require accumulating narrow workspace compensations",
        ],
        "keep_true": [
            "new adaptation paths stay general",
            "new adaptation paths stay bounded",
            "new adaptation paths stay cheaper than repeated repo or user burden",
        ],
        "prefer": "one clear adaptation over accumulating many narrow special cases",
    }


def _repo_directed_improvement_evidence_threshold_payload() -> dict[str, Any]:
    return {
        "status": "explicit-contract",
        "summary": (
            "Repo-directed improvement requires repeated shared evidence that the repo is the real friction source, "
            "not one-off agent preference or local discomfort."
        ),
        "minimum_threshold": [
            "at least two independent friction confirmations, or one bounded review artifact plus one repeated maintenance or dogfooding pass",
            "evidence should point to the repo as the real source after honest workspace adaptation has already been tried or would become concealment",
        ],
        "not_enough": [
            "one-off agent discomfort",
            "one contributor or one model preferring a different repo shape",
            "friction the workspace can still remove honestly inside its own surfaces",
        ],
        "promote_when": [
            "repeated evidence shows the same repo-owned seam, boundary, ownership, or validation problem",
            "further workspace adaptation would hide the repo problem instead of solving it honestly",
            "the follow-on can stay bounded and explain why the repo change is more honest than another workspace-only patch",
        ],
        "collaboration_bias": (
            "In collaborative repos, prefer the higher bar: shared repeated evidence beats local agent taste before repo-directed change."
        ),
    }


def _validation_friction_payload() -> dict[str, Any]:
    return {
        "status": "explicit-contract",
        "rule": (
            "Treat validation friction as repo-friction evidence only when otherwise straightforward work keeps "
            "stalling at validation because repo seams, tranche boundaries, proof expectations, or rerun/re-entry "
            "paths stay unclear."
        ),
        "distinguish_from": [
            "ordinary bug-fixing where the failing check and expected fix are already clear",
            "one-off broken tests or environment failures that do not reveal a repeated repo seam problem",
            "genuinely difficult domains where the hard part is the domain logic itself rather than validation fit",
        ],
        "subtypes": [
            "weak_seam",
            "bad_tranche_boundary",
            "unclear_proof_contract",
            "validation_bounce_reentry",
        ],
        "reporting_destinations": [
            "repo_friction review output",
            "bounded planning residue when a follow-on slice is justified",
            "ordinary report output without implicit active work",
        ],
    }


def _improvement_boundary_test_payload() -> dict[str, Any]:
    return {
        "stays_local_when": [
            "the requested outcome still means the same thing after the improvement",
            "the proof lane remains narrow enough to prove the change without cross-owner validation",
            "ownership stays inside the current workspace/planning/memory boundary",
            "the improvement reduces proven friction rather than creating a new capability branch",
        ],
        "changed_task_when": [
            "the improvement changes what counts as success instead of only changing the means",
            "proof must broaden into another lane or owner before the change can be trusted",
            "the work introduces new visible process, routing, tooling, or module responsibility",
            "the friction signal is being used to justify standalone work that the current slice did not already own",
        ],
        "broaden_proof_when": [
            "the touched surface expands from local code cleanup into shared reporting, planning, or memory state",
            "the improvement changes a generated or front-door surface that weaker agents may rely on directly",
            "the concept-friction change alters user-visible routing, startup, or ownership guidance",
        ],
        "escalate_when": [
            "the improvement would rewrite requested ends under a cleanup label",
            "the change would create a new top-level concept or module to fix the friction",
            "the available evidence is too weak to distinguish local means improvement from a different task",
        ],
    }


def _optimization_bias_payload(mode: str) -> dict[str, Any]:
    surface_boundary = {
        "honors_bias": [
            "derived report rendering density",
            "rendered human-facing views",
            "durable residue style when canonical truth is unchanged",
        ],
        "stays_invariant": [
            "execution method",
            "reasoning depth",
            "delegated-judgment boundaries",
            "proof requirements",
            "ownership semantics",
            "machine-readable report truth",
            "canonical state semantics",
        ],
    }
    policies = {
        "agent-efficiency": {
            "mode": "agent-efficiency",
            "summary": "Prefer terse durable outputs and low-token rendered views when canonical state would stay unchanged.",
            "report_density": "compact",
            "residue_density": "compact-carry-forward",
            "rendered_view_style": "minimal-prose",
            "allows": [
                "preferring terse labels when machine-readable state already carries the contract",
                "keeping follow-through and residue compact when explanation would only restate canonical fields",
                "trimming repeated explanatory prose from rendered human views",
            ],
            "does_not_affect": [
                "execution method",
                "reasoning depth",
                "delegated-judgment boundaries",
                "proof requirements",
                "canonical state semantics",
            ],
            "surface_boundary": surface_boundary,
        },
        "balanced": {
            "mode": "balanced",
            "summary": (
                "Keep durable outputs compact by default while preserving enough explanatory rendering for routine human inspection."
            ),
            "report_density": "balanced",
            "residue_density": "compact-with-brief-explanation",
            "rendered_view_style": "brief-explanatory",
            "allows": [
                "keeping machine-readable state terse",
                "adding short explanatory labels in rendered human views",
                "preserving compact residue with only the explanation needed to avoid rereading",
            ],
            "does_not_affect": [
                "execution method",
                "reasoning depth",
                "delegated-judgment boundaries",
                "proof requirements",
                "canonical state semantics",
            ],
            "surface_boundary": surface_boundary,
        },
        "human-legibility": {
            "mode": "human-legibility",
            "summary": "Prefer clearer explanatory rendering and more legible durable residue when truth would remain unchanged.",
            "report_density": "explanatory",
            "residue_density": "legible-with-context",
            "rendered_view_style": "explicit-labels-and-context",
            "allows": [
                "adding brief explanatory context around compact state",
                "rendering section purpose more explicitly for human readers",
                "keeping durable residue slightly more legible when terseness would force rereading",
            ],
            "does_not_affect": [
                "execution method",
                "reasoning depth",
                "delegated-judgment boundaries",
                "proof requirements",
                "canonical state semantics",
            ],
            "surface_boundary": surface_boundary,
        },
    }
    return policies[mode].copy()


def _setup_finding_class_payload(finding_class: str) -> dict[str, Any]:
    payloads = {
        "repo_friction_evidence": {
            "class": "repo_friction_evidence",
            "summary": "Evidence-backed structural or routing friction worth preserving as shared workspace evidence.",
            "promote_to": "agentic-workspace report --target ./repo --format json repo_friction.external_evidence",
            "preserve_when": [
                "confidence is at least 0.75",
                "the finding has a repo-relative path or explicit refs",
                "the finding would reduce rediscovery if it survived the current setup pass",
            ],
            "transient_when": [
                "the finding has no grounding path or refs",
                "confidence is below 0.75",
                "the finding only restates report output already present elsewhere",
            ],
        },
        "planning_candidate": {
            "class": "planning_candidate",
            "summary": "A bounded follow-on or handoff candidate worth preserving as explicit planning promotion guidance.",
            "promote_to": "TODO.md or docs/execplans/ after bounded planning review",
            "preserve_when": [
                "confidence is at least 0.75",
                "the finding includes a bounded next_action",
                "the finding would still matter after the current session or agent ends",
            ],
            "transient_when": [
                "the finding lacks a bounded next_action",
                "confidence is below 0.75",
                "the finding is only generic analysis with no clear planning owner",
            ],
        },
    }
    return payloads[finding_class].copy()


def _normalized_setup_finding(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    finding_class = raw.get("class")
    if not isinstance(finding_class, str) or finding_class not in SUPPORTED_SETUP_FINDING_CLASSES:
        return None
    summary = raw.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return None
    normalized: dict[str, Any] = {
        "class": finding_class,
        "summary": summary.strip(),
    }
    raw_confidence = raw.get("confidence", 0.5)
    try:
        confidence = float(raw_confidence)
    except (TypeError, ValueError):
        confidence = 0.5
    normalized["confidence"] = max(0.0, min(confidence, 1.0))
    path = raw.get("path")
    if isinstance(path, str) and path.strip():
        normalized["path"] = path.strip()
    refs = raw.get("refs")
    if isinstance(refs, list):
        normalized_refs = [str(item).strip() for item in refs if isinstance(item, str) and item.strip()]
        if normalized_refs:
            normalized["refs"] = normalized_refs[:5]
    next_action = raw.get("next_action")
    if isinstance(next_action, str) and next_action.strip():
        normalized["next_action"] = next_action.strip()
    why = raw.get("why")
    if isinstance(why, str) and why.strip():
        normalized["why"] = why.strip()
    return normalized


def _setup_finding_promotion_decision(item: dict[str, Any]) -> tuple[bool, str]:
    confidence = float(item.get("confidence", 0.0))
    if confidence < 0.75:
        return False, "confidence below promotion threshold"
    finding_class = item["class"]
    if finding_class == "repo_friction_evidence":
        if item.get("path") or item.get("refs"):
            return True, "grounded friction evidence is worth preserving"
        return False, "repo-friction evidence needs a path or refs"
    if finding_class == "planning_candidate":
        if item.get("next_action"):
            return True, "bounded next action makes the planning candidate durable"
        return False, "planning candidate needs a bounded next_action"
    return False, "unsupported finding class"


def _setup_findings_input_payload(*, target_root: Path) -> dict[str, Any]:
    artifact = target_root / SETUP_FINDINGS_PATH
    payload: dict[str, Any] = {
        "path": SETUP_FINDINGS_PATH.as_posix(),
        "accepted_kind": SETUP_FINDINGS_KIND,
        "accepted_classes": [_setup_finding_class_payload(finding_class) for finding_class in SUPPORTED_SETUP_FINDING_CLASSES],
        "status": "not-found",
        "loaded_count": 0,
        "promotable": {
            "repo_friction_evidence": [],
            "planning_candidate": [],
        },
        "transient": [],
    }
    if not artifact.exists():
        return payload
    try:
        raw_payload = json.loads(artifact.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        payload["status"] = "invalid"
        payload["reason"] = f"Could not parse {SETUP_FINDINGS_PATH.as_posix()}: {exc}"
        return payload
    if not isinstance(raw_payload, dict) or raw_payload.get("kind") != SETUP_FINDINGS_KIND:
        payload["status"] = "invalid"
        payload["reason"] = f"{SETUP_FINDINGS_PATH.as_posix()} must contain kind {SETUP_FINDINGS_KIND}."
        return payload
    raw_findings = raw_payload.get("findings")
    if not isinstance(raw_findings, list):
        payload["status"] = "invalid"
        payload["reason"] = f"{SETUP_FINDINGS_PATH.as_posix()} must contain a findings list."
        return payload
    payload["status"] = "loaded"
    for raw_item in raw_findings:
        normalized = _normalized_setup_finding(raw_item)
        if normalized is None:
            payload["transient"].append(
                {
                    "reason": "ignored malformed or unsupported finding",
                }
            )
            continue
        should_promote, reason = _setup_finding_promotion_decision(normalized)
        normalized["promotion_reason"] = reason
        payload["loaded_count"] = int(payload["loaded_count"]) + 1
        if should_promote:
            payload["promotable"][str(normalized["class"])].append(normalized)
        else:
            payload["transient"].append(normalized)
    return payload


def _repo_friction_external_setup_findings_payload(*, target_root: Path) -> dict[str, Any] | None:
    setup_findings = _setup_findings_input_payload(target_root=target_root)
    if setup_findings.get("status") != "loaded":
        return None
    items = [item.copy() for item in setup_findings["promotable"]["repo_friction_evidence"]]
    if not items:
        return None
    return {
        "kind": "setup-findings",
        "path": SETUP_FINDINGS_PATH.as_posix(),
        "status": "loaded",
        "items": items,
    }


def _detected_agent_instruction_files(*, target_root: Path) -> tuple[str, ...]:
    return tuple(name for name in SUPPORTED_AGENT_INSTRUCTIONS_FILES if (target_root / name).exists())


def _resolve_effective_agent_instructions_file(*, target_root: Path, configured: str | None) -> tuple[str, str, tuple[str, ...]]:
    detected = _detected_agent_instruction_files(target_root=target_root)
    if configured is not None:
        return configured, "repo-config", detected
    if len(detected) == 1:
        return detected[0], "autodetected-existing", detected
    return DEFAULT_AGENT_INSTRUCTIONS_FILE, "product-default", detected


def _with_agent_instructions_file(config: WorkspaceConfig, *, filename: str, source: str) -> WorkspaceConfig:
    return replace(
        config,
        agent_instructions_file=filename,
        agent_instructions_source=source,
    )


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

    if args.command in {"proof", "ownership", "config", "note-delegation-outcome"}:
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
            elif args.command == "note-delegation-outcome":
                _emit_payload(
                    payload=_record_delegation_outcome(
                        target_root=target_root,
                        delegation_target=args.delegation_target,
                        task_class=args.task_class,
                        outcome=args.outcome,
                        handoff_sufficiency=args.handoff_sufficiency,
                        review_burden=args.review_burden,
                        escalation_required=bool(args.escalation_required),
                    ),
                    format_name=args.format,
                )
            else:
                _emit_config(format_name=args.format, config=_load_workspace_config(target_root=target_root, descriptors=descriptors))
            return 0
        except WorkspaceUsageError as exc:
            parser.error(str(exc))

    if args.command == "setup":
        try:
            target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
            _validate_target_root(command_name="setup", target_root=target_root)
            config = _load_workspace_config(target_root=target_root, descriptors=descriptors)
            selected_modules, resolved_preset = _selected_modules(
                command_name="setup",
                preset_name=args.preset,
                module_arg=args.modules,
                target_root=target_root,
                descriptors=descriptors,
                config=config,
            )
            _validate_selected_module_contract(selected_modules=selected_modules, descriptors=descriptors)
            _emit_setup(
                format_name=args.format,
                target_root=target_root,
                selected_modules=selected_modules,
                resolved_preset=resolved_preset,
                descriptors=descriptors,
                config=config,
            )
            return 0
        except (ModuleSelectionError, WorkspaceUsageError) as exc:
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
        explicit_agent_instructions_file = getattr(args, "agent_instructions_file", None)
        if explicit_agent_instructions_file:
            config = _with_agent_instructions_file(
                config,
                filename=_validate_agent_instructions_filename(explicit_agent_instructions_file),
                source="explicit-argument",
            )
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

    if args.command == "report":
        payload = _run_report_command(
            target_root=target_root,
            selected_modules=selected_modules,
            resolved_preset=resolved_preset,
            descriptors=descriptors,
            config=config,
        )
        _emit_payload(payload=payload, format_name=args.format)
        return 0

    if args.command == "init":
        payload = _run_init(
            target_root=target_root,
            selected_modules=selected_modules,
            resolved_preset=resolved_preset,
            descriptors=descriptors,
            dry_run=args.dry_run,
            force_adopt=args.adopt,
            non_interactive=args.non_interactive,
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
            non_interactive=args.non_interactive,
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
        non_interactive=args.non_interactive,
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


def _workspace_agents_template(
    *,
    selected_modules: list[str],
    descriptors: dict[str, ModuleDescriptor],
    agent_instructions_file: str = DEFAULT_AGENT_INSTRUCTIONS_FILE,
    workflow_artifact_profile: str = DEFAULT_WORKFLOW_ARTIFACT_PROFILE,
) -> str:
    startup_steps = [f"Read `{agent_instructions_file}`."]
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
    artifact_profile = _workflow_artifact_profile_payload(workflow_artifact_profile)

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
            f"2. `{agent_instructions_file}`.",
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
            "## Workflow Artifacts",
            "",
            f"- profile: `{artifact_profile['profile']}`",
            f"- canonical surfaces: {', '.join(artifact_profile['canonical_surfaces'])}",
            f"- sync rule: {artifact_profile['sync_rule']}",
            f"- handoff rule: {artifact_profile['handoff_rule']}",
        ]
    )
    if artifact_profile["native_artifacts"]:
        lines.append(f"- allowed native artifacts: {', '.join(artifact_profile['native_artifacts'])}")
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
    expected_handoff = _external_agent_handoff_text(
        selected_modules=selected_modules,
        agent_instructions_file=config.agent_instructions_file,
        workflow_artifact_profile=config.workflow_artifact_profile,
    )
    agents_relative = Path(config.agent_instructions_file)

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

    agents_path = target_root / agents_relative
    if not agents_path.exists():
        actions.append({"kind": "missing", "path": agents_relative.as_posix(), "detail": "root startup entrypoint missing"})
        warnings.append({"path": agents_relative.as_posix(), "message": "root startup entrypoint missing"})
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
                "path": agents_relative.as_posix(),
                "detail": "workspace workflow pointer block present",
            }
        )
    else:
        actions.append(
            {
                "kind": "warning",
                "path": agents_relative.as_posix(),
                "detail": "workspace workflow pointer block missing",
            }
        )
        warnings.append({"path": agents_relative.as_posix(), "message": "workspace workflow pointer block missing"})

    for module_name in selected_modules:
        for block in descriptors[module_name].root_agents_cleanup_blocks:
            if block.block not in agents_text:
                continue
            actions.append(
                {
                    "kind": "warning",
                    "path": agents_relative.as_posix(),
                    "detail": (
                        f"redundant top-level {block.label} still present; "
                        "shared workspace workflow should delegate to module-specific guidance"
                    ),
                }
            )
            warnings.append(
                {
                    "path": agents_relative.as_posix(),
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


def _external_agent_handoff_text(
    *,
    selected_modules: list[str],
    agent_instructions_file: str = DEFAULT_AGENT_INSTRUCTIONS_FILE,
    workflow_artifact_profile: str = DEFAULT_WORKFLOW_ARTIFACT_PROFILE,
) -> str:
    artifact_profile = _workflow_artifact_profile_payload(workflow_artifact_profile)
    lines = [
        "# Agentic Workspace External-Agent Handoff",
        "",
        "Use Agentic Workspace as the lifecycle front door for the repository that contains this file.",
        "",
        "Target repository:",
        "- the repository containing this llms.txt file",
        "",
        "Required steps:",
        f"- Read {agent_instructions_file} first.",
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
            "Quick state check:",
            "- agentic-workspace config --target ./repo --format json",
            "- agentic-planning-bootstrap summary --format json",
            (
                "- If agentic-workspace.local.toml is present, use the config report to see "
                "local capability/cost posture without treating it as checked-in repo policy."
            ),
            "",
            "Compact routing docs when present:",
            "- tools/AGENT_QUICKSTART.md",
            "- tools/AGENT_ROUTING.md",
            "",
            "Rules:",
            "- Prefer conservative review over replacing repo-owned workflow surfaces in ambiguous repos.",
            "- Keep planning and memory ownership boundaries explicit.",
            f"- Workflow artifact profile: {artifact_profile['profile']}.",
            f"- {artifact_profile['sync_rule']}",
            (
                "- If bootstrap writes .agentic-workspace/bootstrap-handoff.md, "
                "treat that file as the immediate next-action brief before normal work resumes."
            ),
            "",
            "Success means:",
            "- the workspace lifecycle runs through agentic-workspace",
            f"- {agent_instructions_file} remains the repo startup entrypoint",
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
    handoff_text = _external_agent_handoff_text(
        selected_modules=selected_modules,
        agent_instructions_file=config.agent_instructions_file,
        workflow_artifact_profile=config.workflow_artifact_profile,
    )

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

    agents_relative = Path(config.agent_instructions_file)
    agents_path = target_root / agents_relative
    rendered_agents = _workspace_agents_template(
        selected_modules=selected_modules,
        descriptors=descriptors,
        agent_instructions_file=config.agent_instructions_file,
        workflow_artifact_profile=config.workflow_artifact_profile,
    )
    existing_agents = agents_path.read_text(encoding="utf-8") if agents_path.exists() else None
    if inspection_mode == "install":
        if existing_agents != rendered_agents:
            if not dry_run:
                agents_path.parent.mkdir(parents=True, exist_ok=True)
                agents_path.write_text(rendered_agents, encoding="utf-8")
            actions.append(
                {
                    "kind": _write_action_kind(dry_run=dry_run, existing=existing_agents),
                    "path": agents_relative.as_posix(),
                    "detail": "refresh composed root startup entrypoint for selected workspace modules",
                }
            )
        else:
            actions.append(
                {
                    "kind": "current",
                    "path": agents_relative.as_posix(),
                    "detail": "composed root startup entrypoint already current",
                }
            )
    else:
        base_text = existing_agents or rendered_agents
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
                    "path": agents_relative.as_posix(),
                    "detail": (
                        "patched the shared workspace workflow pointer into the root startup file without replacing repo-owned content"
                    ),
                }
            )
        elif existing_agents is not None:
            actions.append(
                {
                    "kind": "current",
                    "path": agents_relative.as_posix(),
                    "detail": "workflow pointer blocks already present in the root startup file",
                }
            )

    default_agents_relative = Path(DEFAULT_AGENT_INSTRUCTIONS_FILE)
    default_agents_path = target_root / default_agents_relative
    if (
        agents_relative != default_agents_relative
        and DEFAULT_AGENT_INSTRUCTIONS_FILE not in config.detected_agent_instructions_files
        and default_agents_path.exists()
    ):
        if not dry_run:
            default_agents_path.unlink()
        actions.append(
            {
                "kind": "would remove" if dry_run else "removed",
                "path": default_agents_relative.as_posix(),
                "detail": ("remove redundant default startup entrypoint because a different canonical startup file is configured"),
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

    if command_name == "report":
        registry = _module_registry(descriptors=descriptors, target_root=target_root)
        detected = [entry.name for entry in registry if entry.installed]
        return detected, None

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
    non_interactive: bool,
    print_prompt: bool,
    write_prompt: str | None,
    config: WorkspaceConfig,
) -> dict[str, Any]:
    inspection = _inspect_repo_state(
        target_root=target_root,
        selected_modules=selected_modules,
        descriptors=descriptors,
        force_adopt=force_adopt,
        config=config,
    )
    module_command = "install" if inspection.mode == "install" else "adopt"
    reports = [
        _normalize_module_report_startup_paths(
            _invoke_module_command(
                command_name=module_command,
                module_name=module_name,
                descriptor=descriptors[module_name],
                target_root=target_root,
                dry_run=dry_run,
                force=False,
            ),
            config=config,
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
        config=config,
    )
    summary["non_interactive"] = non_interactive
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
        "non_interactive": non_interactive,
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
    config: WorkspaceConfig,
) -> RepoInspection:
    workflow_surfaces = _module_workflow_surfaces(selected_modules=selected_modules, descriptors=descriptors)
    generated_artifacts = _module_generated_artifacts(selected_modules=selected_modules, descriptors=descriptors)
    startup_surfaces = [Path(name) for name in config.detected_agent_instructions_files]
    detected_workflow_surfaces = [path.as_posix() for path in [*workflow_surfaces, *startup_surfaces] if (target_root / path).exists()]
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
        startup_surface_count=len(config.detected_agent_instructions_files),
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
    startup_surface_count: int,
    handoff_surface_count: int,
    partial_state: list[str],
    placeholders: list[str],
) -> tuple[str, str, str]:
    if partial_state or placeholders:
        return ("partial_or_placeholder_state", "adopt_high_ambiguity", "require_explicit_handoff")
    if not overlap_count and not force_adopt:
        return ("blank_or_unmanaged_repo", "install", "install_direct")
    if (
        startup_surface_count >= 2
        or overlap_count >= 4
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
    config: WorkspaceConfig,
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
        "agent_instructions_file": config.agent_instructions_file,
        "workflow_artifact_profile": config.workflow_artifact_profile,
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
            agent_instructions_file=config.agent_instructions_file,
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
    non_interactive: bool,
    config: WorkspaceConfig,
) -> dict[str, Any]:
    registry = _module_registry(descriptors=descriptors, target_root=target_root)
    reports = [
        _normalize_module_report_startup_paths(
            _invoke_module_command(
                command_name=command_name,
                module_name=module_name,
                descriptor=descriptors[module_name],
                target_root=target_root,
                dry_run=dry_run,
                force=False,
            ),
            config=config,
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
        "non_interactive": non_interactive,
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


def _run_report_command(
    *,
    target_root: Path,
    selected_modules: list[str],
    resolved_preset: str | None,
    descriptors: dict[str, ModuleDescriptor],
    config: WorkspaceConfig,
) -> dict[str, Any]:
    from repo_memory_bootstrap.installer import memory_report
    from repo_planning_bootstrap.installer import planning_report

    status_payload = _run_lifecycle_command(
        command_name="status",
        target_root=target_root,
        selected_modules=selected_modules,
        resolved_preset=resolved_preset,
        descriptors=descriptors,
        dry_run=False,
        non_interactive=False,
        config=config,
    )
    warnings = list(status_payload.get("warnings", []))
    findings: list[dict[str, Any]] = []
    seen_findings: set[tuple[str, str, str | None, str | None]] = set()

    def _add_finding(*, severity: str, module: str, message: str, path: str | None = None) -> None:
        key = (severity, module, path, message)
        if key in seen_findings:
            return
        seen_findings.add(key)
        finding: dict[str, Any] = {
            "severity": severity,
            "module": module,
            "message": message,
        }
        if path is not None:
            finding["path"] = path
        findings.append(finding)

    for warning in warnings:
        _add_finding(severity="warning", module="workspace", message=warning)
    for report in status_payload.get("reports", []):
        module_name = str(report.get("module", ""))
        for warning in report.get("warnings", []):
            _add_finding(
                severity="warning",
                module=module_name,
                path=warning.get("path"),
                message=str(warning.get("message", "")),
            )
    module_reports: list[dict[str, Any]] = []
    for module_name in selected_modules:
        if module_name == "planning":
            module_report = planning_report(target=target_root)
        elif module_name == "memory":
            module_report = memory_report(target=target_root)
        else:
            continue
        module_reports.append(module_report)
        for finding in module_report.get("findings", []):
            if not isinstance(finding, dict):
                continue
            _add_finding(
                severity=str(finding.get("severity", "info")),
                module=module_name,
                path=str(finding.get("path")) if finding.get("path") else None,
                message=str(finding.get("message", "")),
            )
    next_steps = list(status_payload.get("next_steps", []))
    next_action = {
        "summary": next_steps[0] if next_steps else "No immediate action",
        "commands": next_steps,
    }
    installed_modules = [entry["name"] for entry in status_payload.get("registry", []) if entry.get("installed")]
    discovery = setup_discovery_payload(
        target_root=target_root,
        status_payload=status_payload,
        active_todo_surface=_active_todo_surface(target_root=target_root),
    )
    repo_friction = repo_friction_payload(
        target_root=target_root,
        improvement_latitude=config.improvement_latitude,
        improvement_latitude_source=config.improvement_latitude_source,
        policy_payload=_improvement_latitude_payload(config.improvement_latitude),
        boundary_test_payload=_improvement_boundary_test_payload(),
        external_setup_findings_payload=_repo_friction_external_setup_findings_payload(target_root=target_root),
    )
    standing_intent = standing_intent_payload(
        target_root=target_root,
        config_policy={
            "improvement_latitude": config.improvement_latitude,
            "improvement_latitude_source": config.improvement_latitude_source,
            "optimization_bias": config.optimization_bias,
            "optimization_bias_source": config.optimization_bias_source,
            "workflow_artifact_profile": config.workflow_artifact_profile,
            "workflow_artifact_profile_source": config.workflow_artifact_profile_source,
        },
        active_planning=_effective_active_direction_payload(module_reports=module_reports),
        memory_installed="memory" in installed_modules,
    )
    execution_shape = _execution_shape_payload(config=config, module_reports=module_reports)
    return {
        "kind": "workspace-report/v1",
        "schema": _reporting_schema_payload(),
        "command": "report",
        "target": target_root.as_posix(),
        "selected_modules": selected_modules,
        "installed_modules": installed_modules,
        "health": status_payload["health"],
        "output_contract": output_contract_payload(
            optimization_bias=config.optimization_bias,
            optimization_bias_source=config.optimization_bias_source,
            bias_payload=_optimization_bias_payload(config.optimization_bias),
            surface="report",
        ),
        "execution_shape": execution_shape,
        "findings": findings,
        "next_action": next_action,
        "discovery": discovery,
        "standing_intent": standing_intent,
        "repo_friction": repo_friction,
        "registry": status_payload["registry"],
        "config": status_payload["config"],
        "reports": status_payload["reports"],
        "module_reports": module_reports,
    }


def _effective_active_direction_payload(*, module_reports: list[dict[str, Any]]) -> dict[str, Any] | None:
    planning_report = next(
        (report for report in module_reports if isinstance(report, dict) and report.get("module") == "planning"),
        None,
    )
    if not isinstance(planning_report, dict):
        return None
    planning_record = planning_report.get("active", {}).get("planning_record", {})
    if not isinstance(planning_record, dict) or planning_record.get("status") != "present":
        return None
    task = planning_record.get("task", {})
    refs = planning_record.get("minimal_refs", [])
    owner_surface = ""
    if isinstance(task, dict):
        owner_surface = str(task.get("surface") or "")
    return {
        "owner_surface": owner_surface or "TODO.md",
        "summary": str(planning_record.get("next_action") or "Active planning carries the current bounded direction."),
        "requested_outcome": str(planning_record.get("requested_outcome") or ""),
        "refs": refs if isinstance(refs, list) else [],
    }


def _execution_shape_payload(*, config: WorkspaceConfig, module_reports: list[dict[str, Any]]) -> dict[str, Any]:
    mixed_agent = _mixed_agent_payload(config=config)
    planning_module_report = next(
        (report for report in module_reports if isinstance(report, dict) and report.get("module") == "planning"),
        None,
    )
    if not isinstance(planning_module_report, dict):
        return {
            "owner_surface": "workspace-report",
            "rule": (
                "Treat effective config posture as the authoritative default execution posture, "
                "but keep the recommendation advisory and make justified deviation visible."
            ),
            "advisory_only": True,
            "status": "unavailable",
            "reason": "planning module report is unavailable",
            "sources": [
                "agentic-workspace config --target ./repo --format json",
                "agentic-planning-bootstrap summary --format json",
            ],
        }

    planning_status = planning_module_report.get("status", {})
    active = planning_module_report.get("active", {})
    planning_record = active.get("planning_record", {})
    handoff_contract = active.get("handoff_contract", {})
    has_active_execplan = bool(planning_status.get("active_execplan_count"))
    strong_planner = bool(mixed_agent["effective_posture"]["strong_planner_available"]["value"])
    cheap_executor = bool(mixed_agent["effective_posture"]["cheap_bounded_executor_available"]["value"])
    internal_delegation = bool(mixed_agent["effective_posture"]["supports_internal_delegation"]["value"])
    prefer_internal = bool(mixed_agent["effective_posture"]["prefer_internal_delegation_when_available"]["value"])
    sources = [
        "agentic-workspace config --target ./repo --format json",
        "agentic-planning-bootstrap summary --format json",
    ]
    if isinstance(handoff_contract, dict) and handoff_contract.get("status") == "present":
        sources.append("agentic-planning-bootstrap handoff --format json")

    payload: dict[str, Any] = {
        "owner_surface": "workspace-report",
        "rule": (
            "Treat effective config posture as the authoritative default execution posture, "
            "but keep the recommendation advisory and make justified deviation visible."
        ),
        "advisory_only": True,
        "status": "present",
        "sources": sources,
        "default_posture": {
            "planner_executor_pattern": mixed_agent["derived_mode"]["planner_executor_pattern"],
            "handoff_preference": mixed_agent["derived_mode"]["handoff_preference"],
            "authoritative_sources": [
                "agentic-workspace.toml",
                "agentic-workspace.local.toml",
            ],
        },
    }

    if isinstance(planning_record, dict) and planning_record.get("status") == "present" and has_active_execplan:
        payload["task_shape"] = {
            "id": "planning-backed-broad-work",
            "summary": "The current slice is already planning-backed with an active execplan.",
            "why": (
                "The work already needs checked-in planning continuity, so repeating broad direct rediscovery "
                "is usually more expensive than deriving a bounded handoff once."
            ),
        }
        payload["current_slice"] = {
            "task_id": planning_record.get("task", {}).get("id", ""),
            "surface": planning_record.get("task", {}).get("surface", ""),
            "next_action": planning_record.get("next_action", ""),
        }
        if strong_planner and cheap_executor:
            payload["recommendation"] = {
                "id": "planner-first-then-bounded-executor",
                "summary": "Default to stronger planning plus a bounded executor for the current slice.",
                "why": [
                    "The active slice is broad enough that checked-in planning already exists.",
                    "The effective posture reports both a strong planner and a cheap bounded executor.",
                    "The delegated worker handoff can stay canonical even if execution remains internal, external, or direct.",
                ],
                "consult": ["agentic-planning-bootstrap handoff --format json"],
                "allowed_execution_methods": handoff_contract.get("worker_contract", {}).get(
                    "allowed_execution_methods",
                    ["internal delegation", "external cli or api", "single-agent fallback"],
                ),
                "deviation_visibility": (
                    "If you intentionally stay direct for this planning-backed slice, record the reason in the active "
                    "execplan's Iterative Follow-Through, Execution Summary, or Drift Log instead of leaving the deviation implicit."
                ),
            }
        else:
            payload["recommendation"] = {
                "id": "direct-with-checked-in-plan",
                "summary": "Keep execution direct unless delegation becomes cheaper than rereading.",
                "why": [
                    "The active slice is broad enough to benefit from a compact plan.",
                    "The effective local posture does not currently report the strong-planner/cheap-executor pattern needed for a clear default split.",
                ],
                "consult": ["agentic-planning-bootstrap summary --format json"],
                "allowed_execution_methods": ["single-agent fallback"],
                "deviation_visibility": (
                    "If you later delegate anyway, derive the handoff from checked-in planning and note why the exception beat the direct default."
                ),
            }
        payload["deviation_rule"] = (
            "Local judgment may still choose another execution method, but the deviation should stay explainable in checked-in planning residue."
        )
        return payload

    payload["task_shape"] = {
        "id": "direct-or-no-active-plan",
        "summary": "No planning-backed broad slice is active right now.",
        "why": "Without an active execplan-backed slice, the cheapest honest default is still direct execution.",
    }
    payload["recommendation"] = {
        "id": "stay-direct",
        "summary": "Stay direct unless the work widens enough to need checked-in planning or a compact handoff.",
        "why": [
            "There is no active planning-backed slice that justifies a planner-to-worker split by default.",
            "The mixed-agent posture remains advisory rather than scheduler-like when work is still cheap and self-sufficient.",
        ],
        "consult": ["agentic-workspace config --target ./repo --format json"],
        "allowed_execution_methods": ["single-agent fallback"],
        "deviation_visibility": (
            "If the task stops being cheap and direct, promote or tighten planning first instead of silently widening the run."
        ),
    }
    payload["deviation_rule"] = (
        "Do not force delegation for trivial work; promote into planning first when the cheap direct path stops being safe."
    )
    if internal_delegation and prefer_internal and strong_planner and cheap_executor:
        payload["default_posture"]["note"] = "Delegation is available and preferred when a later slice becomes broad enough."
    return payload


def _active_todo_surface(*, target_root: Path) -> str | None:
    todo_path = target_root / "TODO.md"
    if not todo_path.exists():
        return None
    surface_pattern = re.compile(r"Surface:\s*`?([^`;]+?)`?(?:;|$)")
    for line in todo_path.read_text(encoding="utf-8").splitlines():
        if "Status: active" not in line or "Surface:" not in line:
            continue
        match = surface_pattern.search(line)
        if match:
            return match.group(1).strip()
    return None


def _bootstrap_intent_payload(*, selected_modules: list[str], resolved_preset: str | None) -> dict[str, Any]:
    if resolved_preset == "memory":
        key = "memory"
        summary = "set up this repo for Agentic Memory"
        confirmed_source = "resolved preset: memory"
    elif resolved_preset == "planning":
        key = "planning"
        summary = "set up this repo for Agentic Planning"
        confirmed_source = "resolved preset: planning"
    elif resolved_preset == "full":
        key = "full"
        summary = "set up this repo for both Planning and Memory"
        confirmed_source = "resolved preset: full"
    elif selected_modules == ["memory"]:
        key = "memory"
        summary = "set up this repo for Agentic Memory"
        confirmed_source = "selected modules: memory"
    elif selected_modules == ["planning"]:
        key = "planning"
        summary = "set up this repo for Agentic Planning"
        confirmed_source = "selected modules: planning"
    else:
        key = "custom"
        summary = f"set up this repo for: {', '.join(selected_modules)}"
        confirmed_source = f"selected modules: {', '.join(selected_modules)}"
    return {
        "key": key,
        "summary": summary,
        "confirmed_intent": {
            "key": key,
            "summary": summary,
            "source": confirmed_source,
        },
        "interpreted_intent": {
            "key": key,
            "summary": summary,
            "source": "workspace-normalized lifecycle intent",
        },
    }


def _intent_contract_payload() -> dict[str, Any]:
    return {
        "canonical_doc": "docs/intent-contract.md",
        "command": "agentic-workspace defaults --section intent --format json",
        "rule": "Confirmed intent stays human-owned; interpreted intent must remain visibly inferred.",
        "confirmed_intent": {
            "summary": "the human-owned request before workspace normalization",
            "source": "user request or explicit lifecycle directive",
        },
        "interpreted_intent": {
            "summary": "the workspace-normalized request carried forward by lifecycle commands",
            "source": "workspace normalization",
        },
        "escalate_when": [
            "the interpreted intent changes the requested outcome",
            "the interpreted intent widens the owned surface or time horizon",
            "the compact selector can no longer carry the user-end safely",
        ],
    }


def _clarification_contract_payload() -> dict[str, Any]:
    return {
        "canonical_doc": "docs/intent-contract.md",
        "command": "agentic-workspace defaults --section clarification --format json",
        "rule": "When a prompt is vague, ask the smallest repo-context question that removes the ambiguity.",
        "mode": "minimal-interruption",
        "repo_context": [
            "Use TODO.md or the active execplan when the prompt seems planning-shaped.",
            "Use report before broad file reads when the prompt may touch several workspace surfaces.",
            "Use ownership when the target surface or owner is unclear.",
        ],
        "first_questions": [
            "Which surface should change?",
            "What proof would make the change safe?",
            "Does the work belong in planning, memory, or workspace-level docs?",
        ],
        "fallback": [
            "Use the intent selector first, then clarification, report, and ownership/proof selectors as needed.",
            "Stop or escalate when answering the question would rewrite the requested end state.",
        ],
        "examples": [
            "vague task request",
            "missing target surface",
            "unclear proof boundary",
        ],
    }


def _prompt_routing_contract_payload() -> dict[str, Any]:
    return {
        "canonical_doc": "docs/intent-contract.md",
        "command": "agentic-workspace defaults --section prompt_routing --format json",
        "rule": "Map vague prompt classes to a proof lane and an owner before widening the task.",
        "route_by_class": [
            {
                "class": "workspace lifecycle change",
                "proof_lane": "workspace_cli",
                "owner_surface": "src/agentic_workspace/cli.py",
            },
            {
                "class": "planning state or contract change",
                "proof_lane": "planning_surfaces",
                "owner_surface": "docs/execplans/ or TODO.md",
            },
            {
                "class": "durable repo knowledge change",
                "proof_lane": "memory_payload",
                "owner_surface": "memory/",
            },
            {
                "class": "cross-cutting workspace contract",
                "proof_lane": "workspace_cli",
                "broaden_with": ["planning_surfaces"],
                "owner_surface": "docs/design-principles.md",
            },
        ],
        "proof_inference": [
            "Use workspace_cli when the prompt changes the front-door workspace surface.",
            "Use planning_surfaces when the prompt changes TODO.md, ROADMAP.md, or execplans.",
            "Use memory_payload when the prompt changes durable repo knowledge or routing notes.",
        ],
        "owner_inference": [
            "TODO.md or an active execplan implies planning ownership.",
            "memory/index.md or a runbook implies memory ownership.",
            "workspace lifecycle defaults or routing docs imply workspace ownership.",
        ],
        "escalate_when": [
            "the proof lane is still unclear after one repo-context clarification",
            "the owner inference would change the requested outcome",
            "the prompt spans multiple owners and no narrow lane is enough",
        ],
    }


def _relay_contract_payload() -> dict[str, Any]:
    return {
        "canonical_doc": "docs/orchestrator-workflow-contract.md",
        "command": "agentic-workspace defaults --section relay --format json",
        "rule": "Use a strong planner to normalize the vague prompt, then hand the compact contract to a bounded executor without prescribing the execution method.",
        "selection_rule": (
            "Use the effective mixed-agent posture from agentic-workspace config, then keep the same handoff contract whether execution stays internal, external over cli or api, or direct."
        ),
        "handoff_command": "agentic-planning-bootstrap handoff --format json",
        "planner_role": {
            "summary": "shape confirmed and interpreted intent, choose the proof lane, and freeze the smallest safe contract.",
            "does": [
                "clarify the request with the smallest repo-context follow-up",
                "choose the narrow proof lane and owner surface",
                "preserve escalation boundaries before the handoff freezes",
            ],
        },
        "implementer_role": {
            "summary": "execute the narrow contract without widening the requested end state, whether the executor is internal or external.",
            "does": [
                "follow the compact interpreted contract",
                "stop or escalate when the scope expands",
                "mirror durable follow-through into checked-in surfaces",
            ],
        },
        "execution_methods": [
            {
                "id": "internal delegation",
                "when": "the runtime supports delegation and the local posture prefers it",
            },
            {
                "id": "external cli or api",
                "when": "another bounded executor is available outside the current runtime",
            },
            {
                "id": "single-agent fallback",
                "when": "delegation is unavailable or the handoff would cost more than it saves",
            },
        ],
        "worker_boundary": {
            "worker_owns_by_default": [
                "bounded implementation inside the delegated write scope",
                "narrow validation named by the handoff",
                "cleanup and commit only when explicitly assigned and still bounded",
            ],
            "orchestrator_owns_by_default": [
                "lane shaping",
                "roadmap routing",
                "issue closure",
                "product-shape decisions",
            ],
        },
        "memory_bridge": {
            "summary": "when routed Memory is installed, borrow durable repo understanding before freezing the compact contract.",
            "borrow_from": [
                "memory/index.md",
                "memory/current/",
                "memory/runbooks/",
            ],
            "fallback": [
                "continue from checked-in docs when routed Memory is absent",
                "route missing durable context back into Memory when the work reveals repeated gaps",
            ],
        },
        "hand_off_order": [
            "intent",
            "clarification",
            "prompt_routing",
            "relay",
        ],
        "escalate_when": [
            "the planner would need to rewrite the requested outcome",
            "the cheap implementer would need broad repo rereads to stay safe",
            "the routed Memory bridge is absent and the missing context is blocking",
        ],
    }


def _run_prompt_command(
    *,
    prompt_command: str,
    target_root: Path,
    selected_modules: list[str],
    resolved_preset: str | None,
    descriptors: dict[str, ModuleDescriptor],
    force_adopt: bool,
    non_interactive: bool,
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
            non_interactive=non_interactive,
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
        non_interactive=non_interactive,
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


def _normalize_module_report_startup_paths(report: dict[str, Any], *, config: WorkspaceConfig) -> dict[str, Any]:
    if (
        config.agent_instructions_file == DEFAULT_AGENT_INSTRUCTIONS_FILE
        or DEFAULT_AGENT_INSTRUCTIONS_FILE in config.detected_agent_instructions_files
    ):
        return report

    def _rewrite_path(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        path = Path(value)
        if path.parent == Path(".") and path.name == DEFAULT_AGENT_INSTRUCTIONS_FILE:
            return config.agent_instructions_file
        return value

    return {
        **report,
        "actions": [{**action, "path": _rewrite_path(action.get("path"))} for action in report["actions"]],
        "warnings": [{**warning, "path": _rewrite_path(warning.get("path"))} for warning in report["warnings"]],
    }


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
    agent_instructions_file: str,
) -> list[str]:
    target = target_root.as_posix()
    steps = [f"Run agentic-workspace doctor --target {target} after bootstrap changes settle."]
    if prompt_requirement != "none":
        steps.append(
            f"Use the generated finishing brief at {WORKSPACE_BOOTSTRAP_HANDOFF_PATH.as_posix()} for the next bounded bootstrap action."
        )
    if prompt_requirement == "none":
        steps.append(
            f"Tell your coding agent to use {agent_instructions_file} for normal work and llms.txt for lifecycle/front-door guidance."
        )
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
    agent_instructions_file = str(summary.get("agent_instructions_file", DEFAULT_AGENT_INSTRUCTIONS_FILE))
    workflow_artifact_profile = _workflow_artifact_profile_payload(
        str(summary.get("workflow_artifact_profile", DEFAULT_WORKFLOW_ARTIFACT_PROFILE))
    )
    intent_payload = summary.get("intent")
    lines = [
        f"Finish the Agentic Workspace bootstrap in {summary['target']}.",
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
    if isinstance(intent_payload, dict):
        confirmed_intent = intent_payload.get("confirmed_intent")
        interpreted_intent = intent_payload.get("interpreted_intent")
        if isinstance(confirmed_intent, dict) and isinstance(interpreted_intent, dict):
            lines.extend(
                [
                    "",
                    "Intent:",
                    f"- confirmed: {confirmed_intent.get('summary', intent_payload.get('summary', ''))}",
                    f"- interpreted: {interpreted_intent.get('summary', intent_payload.get('summary', ''))}",
                ]
            )
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
            f"- workflow artifact profile `{workflow_artifact_profile['profile']}`: {workflow_artifact_profile['sync_rule']}",
        ]
    )
    if summary.get("non_interactive"):
        lines.append("- keep the finishing pass non-interactive; do not assume a human can answer prompts or unblock a PTY")
    lines.extend(["", "Validation:"])
    lines.extend(f"- {command}" for command in summary["validation"])
    lines.extend(["", "When done:"])
    if summary["placeholders"]:
        lines.append("- remove or resolve any remaining placeholders before closing the bootstrap task")
    lines.append("- keep llms.txt current as the canonical external-agent handoff surface")
    lines.append("- leave only durable workflow residue; do not keep temporary bootstrap notes around")
    lines.append(f"- keep {agent_instructions_file} as the repo startup entrypoint")
    return "\n".join(lines)


def _build_bootstrap_handoff_record(summary: dict[str, Any]) -> dict[str, Any]:
    agent_instructions_file = str(summary.get("agent_instructions_file", DEFAULT_AGENT_INSTRUCTIONS_FILE))
    workflow_artifact_profile = _workflow_artifact_profile_payload(
        str(summary.get("workflow_artifact_profile", DEFAULT_WORKFLOW_ARTIFACT_PROFILE))
    )
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
            "non_interactive": bool(summary.get("non_interactive")),
            "workflow_artifact_profile": workflow_artifact_profile,
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
            agent_instructions_file,
            "TODO.md",
            "llms.txt",
            "docs/delegated-judgment-contract.md",
            "docs/init-lifecycle.md",
            "agentic-workspace defaults --format json",
            "agentic-workspace config --target ./repo --format json",
        ],
    }


def _reporting_schema_payload() -> dict[str, Any]:
    return report_contract_manifest().copy()


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
    if payload.get("non_interactive"):
        lines.extend(
            [
                "Run this flow with `--non-interactive` and avoid command paths that would wait for human confirmation.",
                "Keep the lifecycle pass prompt-free and safe for unattended Windows/PowerShell execution.",
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
    intent_payload = payload.get("intent")
    if isinstance(intent_payload, dict):
        confirmed_intent = intent_payload.get("confirmed_intent")
        interpreted_intent = intent_payload.get("interpreted_intent")
        if isinstance(confirmed_intent, dict) and isinstance(interpreted_intent, dict):
            lines.extend(
                [
                    "",
                    "Intent:",
                    f"- confirmed: {confirmed_intent.get('summary', intent_payload.get('summary', ''))}",
                    f"- interpreted: {interpreted_intent.get('summary', intent_payload.get('summary', ''))}",
                ]
            )
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
    compact_manifest = compact_contract_manifest()
    proof_manifest = proof_routes_manifest()
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
            "default_canonical_agent_instructions_file": DEFAULT_AGENT_INSTRUCTIONS_FILE,
            "supported_agent_instructions_files": list(SUPPORTED_AGENT_INSTRUCTIONS_FILES),
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
            "canonical_doc": compact_manifest["canonical_doc"],
            "rule": "When one bounded answer is enough, prefer a narrow selector over a whole-surface dump.",
            "answer_shape": list(compact_manifest["answer_shape"]),
            "selectors": {key: value["command"] for key, value in compact_manifest["selectors"].items()},
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
        "setup": {
            "canonical_doc": "docs/jumpstart-contract.md",
            "command": "agentic-workspace setup --target ./repo --format json",
            "rule": "Setup is a bounded post-bootstrap phase that stays separate from init.",
            "phase": "post-bootstrap",
            "scope": [
                "orient from a compact report first",
                "keep follow-through bounded and reviewable",
            ],
            "secondary": [
                "Do not widen init.",
                "Do not collapse setup into the proof backlog.",
                "Do not turn setup into generic analysis.",
            ],
        },
        "setup_findings_promotion": {
            "canonical_doc": "docs/setup-findings-contract.md",
            "command": "agentic-workspace setup --target ./repo --format json",
            "rule": (
                "Setup may accept one optional agent-produced findings artifact, but it should preserve only the classes "
                "that reduce rediscovery and have a clear durable owner."
            ),
            "artifact_path": SETUP_FINDINGS_PATH.as_posix(),
            "schema_path": "src/agentic_workspace/contracts/schemas/setup_findings.schema.json",
            "accepted_kind": SETUP_FINDINGS_KIND,
            "accepted_classes": [_setup_finding_class_payload(finding_class) for finding_class in SUPPORTED_SETUP_FINDING_CLASSES],
            "preserve_rule": (
                "Promote only evidence-backed repo-friction findings or bounded planning candidates; leave everything else transient."
            ),
            "secondary": [
                "Do not build a workspace-owned analyzer.",
                "Do not auto-write planning or memory state from setup input.",
                "Do not preserve findings that have no durable owner or bounded next action.",
            ],
        },
        "intent": _intent_contract_payload(),
        "clarification": _clarification_contract_payload(),
        "prompt_routing": _prompt_routing_contract_payload(),
        "relay": _relay_contract_payload(),
        "config": {
            "path": "agentic-workspace.toml",
            "command": "agentic-workspace config --target ./repo --format json",
            "supported_fields": [
                "workspace.default_preset",
                "workspace.agent_instructions_file",
                "workspace.workflow_artifact_profile",
                "workspace.improvement_latitude",
                "workspace.optimization_bias",
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
        "improvement_latitude": {
            "canonical_doc": "docs/workspace-config-contract.md",
            "command": "agentic-workspace defaults --section improvement_latitude --format json",
            "rule": (
                "Repo-owned improvement latitude may widen means to reduce proven repo friction, "
                "but it must remain subordinate to delegated judgment, proof, and ownership."
            ),
            "owner_surface": "workspace",
            "owner_rule": ("Repo-friction policy and evidence remain workspace-level shared surfaces rather than a separate core module."),
            "policy_target": "repo-directed-improvement",
            "policy_target_rule": (
                "The improvement-latitude modes govern autonomous initiative directed at repo-owned or otherwise external surfaces."
            ),
            "workspace_self_adaptation": _workspace_self_adaptation_payload(),
            "friction_response_order": _friction_response_order_payload(),
            "mode_interpretation": {
                "none": ("Repo-directed initiative stays off, but bounded workspace self-adaptation remains allowed."),
                "reporting": ("Repo-directed follow-through stays reporting-only, but bounded workspace self-adaptation remains allowed."),
                "proactive": (
                    "Prefer workspace adaptation first; use repo-directed action only when the root problem is genuinely external and the work stays bounded."
                ),
            },
            "examples": {
                "workspace_adaptation_first": [
                    "tighten a selector, recovery hint, or report field so the workspace points agents at the right repo surface without asking the repo to restructure itself"
                ],
                "repo_directed_improvement_next": [
                    "after the workspace already routes correctly, repeated shared friction still comes from unclear repo seams, tranche boundaries, or ownership and should be promoted as repo-directed follow-on work",
                    "when validation keeps bouncing across unclear seams or proof expectations, keep that visible as validation-friction evidence instead of treating it as just another one-off failure",
                ],
            },
            "guardrail_test": _workspace_self_adaptation_guardrail_payload(),
            "repo_directed_improvement_threshold": _repo_directed_improvement_evidence_threshold_payload(),
            "default_mode": DEFAULT_IMPROVEMENT_LATITUDE,
            "supported_modes": [_improvement_latitude_payload(mode) for mode in SUPPORTED_IMPROVEMENT_LATITUDES],
            "decision_test": _improvement_boundary_test_payload(),
            "evidence_source": "agentic-workspace report --target ./repo --format json",
            "evidence_classes": [
                "large_file_hotspots",
                "concept_surface_hotspots",
                "planning_friction",
                "validation_friction",
            ],
            "validation_friction": _validation_friction_payload(),
        },
        "optimization_bias": {
            "canonical_doc": "docs/workspace-config-contract.md",
            "command": "agentic-workspace defaults --section optimization_bias --format json",
            "rule": (
                "Repo-owned optimization bias may change output density and residue style, "
                "but it must not change execution method or canonical state semantics."
            ),
            "owner_surface": "workspace",
            "default_mode": DEFAULT_OPTIMIZATION_BIAS,
            "supported_modes": [_optimization_bias_payload(mode) for mode in SUPPORTED_OPTIMIZATION_BIASES],
            "applies_to": [
                "derived report rendering density",
                "rendered human-facing views",
                "durable residue style when canonical state is unchanged",
            ],
            "surface_boundary": _optimization_bias_payload(DEFAULT_OPTIMIZATION_BIAS)["surface_boundary"],
            "must_not_change": [
                "execution method",
                "reasoning depth",
                "delegated-judgment boundaries",
                "proof requirements",
                "canonical state semantics",
            ],
        },
        "workflow_artifact_adapters": {
            "canonical_doc": "docs/workspace-config-contract.md",
            "command": "agentic-workspace defaults --section workflow_artifact_adapters --format json",
            "rule": (
                "Runtime-native planning artifacts may exist, but durable cross-agent state "
                "must project back into TODO.md and docs/execplans before handoff or review."
            ),
            "default_profile": DEFAULT_WORKFLOW_ARTIFACT_PROFILE,
            "supported_profiles": [_workflow_artifact_profile_payload(profile) for profile in SUPPORTED_WORKFLOW_ARTIFACT_PROFILES],
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
                "supported_target_strengths": list(SUPPORTED_DELEGATION_TARGET_STRENGTHS),
                "supported_target_execution_methods": list(SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS),
                "intended_scope": [
                    "machine-specific capability posture",
                    "account- or cost-profile asymmetry",
                    "local execution preferences that do not redefine repo semantics",
                    "available delegation target hints that stay advisory and local-only",
                ],
            },
            "local_outcome_artifact": {
                "path": WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix(),
                "kind": DELEGATION_OUTCOMES_KIND,
                "rule": "local-only delegation outcome evidence used to derive advisory tuning suggestions over time",
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
        "delegation_posture": {
            "canonical_doc": "docs/delegation-posture-contract.md",
            "command": "agentic-workspace defaults --section delegation_posture --format json",
            "rule": (
                "Use the effective mixed-agent posture to decide whether to keep work direct, "
                "split it into planner/implementer/validator subtasks, or escalate to a stronger planner."
            ),
            "preferred_split": [
                "planner",
                "implementer",
                "validator",
            ],
            "config_controls": [
                "agentic-workspace.local.toml runtime.supports_internal_delegation",
                "agentic-workspace.local.toml runtime.strong_planner_available",
                "agentic-workspace.local.toml runtime.cheap_bounded_executor_available",
                "agentic-workspace.local.toml handoff.prefer_internal_delegation_when_available",
                "agentic-workspace.local.toml delegation_targets.<target>.*",
                "agentic-workspace.delegation-outcomes.json",
            ],
            "secondary": [
                "Do not treat config as a scheduler.",
                "Do not delegate when the task stays cheap and direct.",
                "Do not silently rewrite ends.",
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
            "canonical_doc": proof_manifest["canonical_doc"],
            "command": proof_manifest["command"],
            "rule": "Use the narrowest proof lane that answers the current trust question.",
            "default_routes": dict(proof_manifest["default_routes"]),
            "secondary": [
                "Use package-local tests or payload verification only when the trust question is package-specific.",
            ],
        },
        "proof_selection": {
            "canonical_doc": "docs/proof-surfaces-contract.md",
            "command": "agentic-workspace defaults --section proof_selection --format json",
            "rule": "Make proof choice cheap by naming the narrowest lane that still answers the trust question.",
            "recommended_lanes": [
                {
                    "id": "workspace_proof",
                    "use_when": "The question is what proves the workspace contract here.",
                    "enough_proof": "agentic-workspace proof --target ./repo --format json",
                    "broaden_when": "The current workspace proof answer is not specific enough for the trust question.",
                    "escalate_when": "The proof question crosses into package-specific or repo-wide contract changes.",
                },
                {
                    "id": "workspace_current",
                    "use_when": "The question is the current workspace health or installed-module state.",
                    "enough_proof": "agentic-workspace proof --target ./repo --current --format json",
                    "broaden_when": "Current health alone does not answer the trust question.",
                    "escalate_when": "A deeper package or repo-wide proof lane is required.",
                },
                {
                    "id": "validation_lane",
                    "use_when": "The question is whether a touched contract change is proved by narrow validation.",
                    "enough_proof": "Use the narrowest validation lane from `validation` that covers the touched surface.",
                    "broaden_when": "The narrower validation lane stops proving the touched contract or the change crosses boundaries.",
                    "escalate_when": "Validation would be meaningless without broader scope.",
                },
            ],
            "rule_of_thumb": [
                "Prefer the smallest queryable proof answer first.",
                "Broaden only when the narrow lane stops answering the trust question.",
                "Escalate when proof would need broader scope than the current trust question justifies.",
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
            "effective_output_posture": {
                "command": "agentic-workspace config --target ./repo --format json",
                "field": "workspace.optimization_bias",
                "rule": (
                    "When startup or recovery needs the effective repo output posture, inspect it through config "
                    "instead of inferring it from rendered report density alone."
                ),
            },
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
    compact_manifest = compact_contract_manifest()
    payload: dict[str, Any] = {
        "profile": compact_manifest["profile"],
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
    refs = [compact_contract_manifest()["canonical_doc"], command]
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
    print("Setup:")
    print(f"- doc: {payload['setup']['canonical_doc']}")
    print(f"- command: {payload['setup']['command']}")
    print(f"- rule: {payload['setup']['rule']}")
    print(f"- phase: {payload['setup']['phase']}")
    for step in payload["setup"]["scope"]:
        print(f"- scope: {step}")
    print("Intent:")
    print(f"- doc: {payload['intent']['canonical_doc']}")
    print(f"- command: {payload['intent']['command']}")
    print(f"- rule: {payload['intent']['rule']}")
    print(f"- confirmed: {payload['intent']['confirmed_intent']['summary']}")
    print(f"- interpreted: {payload['intent']['interpreted_intent']['summary']}")
    print("Clarification:")
    print(f"- doc: {payload['clarification']['canonical_doc']}")
    print(f"- command: {payload['clarification']['command']}")
    print(f"- rule: {payload['clarification']['rule']}")
    print(f"- mode: {payload['clarification']['mode']}")
    for step in payload["clarification"]["repo_context"]:
        print(f"- repo context: {step}")
    print("Prompt routing:")
    print(f"- doc: {payload['prompt_routing']['canonical_doc']}")
    print(f"- command: {payload['prompt_routing']['command']}")
    print(f"- rule: {payload['prompt_routing']['rule']}")
    for route in payload["prompt_routing"]["route_by_class"]:
        route_text = route["proof_lane"]
        broaden_with = route.get("broaden_with")
        if isinstance(broaden_with, list) and broaden_with:
            route_text = f"{route_text} (broaden with {', '.join(broaden_with)})"
        print(f"- {route['class']}: {route_text} -> {route['owner_surface']}")
    print("Relay:")
    print(f"- doc: {payload['relay']['canonical_doc']}")
    print(f"- command: {payload['relay']['command']}")
    print(f"- rule: {payload['relay']['rule']}")
    print(f"- planner: {payload['relay']['planner_role']['summary']}")
    print(f"- implementer: {payload['relay']['implementer_role']['summary']}")
    print(f"- memory bridge: {payload['relay']['memory_bridge']['summary']}")
    print("Improvement latitude:")
    print(f"- doc: {payload['improvement_latitude']['canonical_doc']}")
    print(f"- command: {payload['improvement_latitude']['command']}")
    print(f"- rule: {payload['improvement_latitude']['rule']}")
    print(f"- owner: {payload['improvement_latitude']['owner_surface']}")
    print(f"- default mode: {payload['improvement_latitude']['default_mode']}")
    for mode in payload["improvement_latitude"]["supported_modes"]:
        print(f"- {mode['mode']}: {mode['summary']}")
    print("Optimization bias:")
    print(f"- doc: {payload['optimization_bias']['canonical_doc']}")
    print(f"- command: {payload['optimization_bias']['command']}")
    print(f"- rule: {payload['optimization_bias']['rule']}")
    print(f"- owner: {payload['optimization_bias']['owner_surface']}")
    print(f"- default mode: {payload['optimization_bias']['default_mode']}")
    for mode in payload["optimization_bias"]["supported_modes"]:
        print(f"- {mode['mode']}: {mode['summary']}")
    print("Compact contract profile:")
    print(f"- doc: {payload['compact_contract_profile']['canonical_doc']}")
    print(f"- rule: {payload['compact_contract_profile']['rule']}")
    print("Config:")
    print(f"- path: {payload['config']['path']}")
    print(f"- inspect: {payload['config']['command']}")
    print("Workflow artifact adapters:")
    print(f"- doc: {payload['workflow_artifact_adapters']['canonical_doc']}")
    print(f"- command: {payload['workflow_artifact_adapters']['command']}")
    print(f"- rule: {payload['workflow_artifact_adapters']['rule']}")
    print("Mixed-agent:")
    print(f"- rule: {payload['mixed_agent']['rule']}")
    print(f"- local override: {payload['mixed_agent']['local_override']['path']} ({payload['mixed_agent']['local_override']['status']})")
    print("Delegation posture:")
    print(f"- doc: {payload['delegation_posture']['canonical_doc']}")
    print(f"- command: {payload['delegation_posture']['command']}")
    print(f"- rule: {payload['delegation_posture']['rule']}")
    print(f"- preferred split: {' -> '.join(payload['delegation_posture']['preferred_split'])}")
    print(f"- config controls: {', '.join(payload['delegation_posture']['config_controls'])}")
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
    print("Proof selection:")
    print(f"- doc: {payload['proof_selection']['canonical_doc']}")
    print(f"- command: {payload['proof_selection']['command']}")
    print(f"- rule: {payload['proof_selection']['rule']}")
    print("Ownership mapping:")
    print(f"- doc: {payload['ownership_mapping']['canonical_doc']}")
    print(f"- command: {payload['ownership_mapping']['command']}")
    print(f"- rule: {payload['ownership_mapping']['rule']}")
    print("Combined install:")
    print(f"- {payload['combined_install']['primary']}")
    print("Recovery:")
    print(f"- doc: {payload['recovery']['canonical_doc']}")
    print(f"- rule: {payload['recovery']['rule']}")
    print(
        "- effective output posture: "
        f"{payload['recovery']['effective_output_posture']['command']} -> "
        f"{payload['recovery']['effective_output_posture']['field']}"
    )
    print("Completion:")
    print(f"- rule: {payload['completion']['rule']}")
    print("Delegated judgment:")
    print(f"- doc: {payload['delegated_judgment']['canonical_doc']}")
    print(f"- rule: {payload['delegated_judgment']['rule']}")
    print("Delegated judgment follow-through:")
    for item in payload["delegated_judgment"]["operational_follow_through"]:
        print(f"- {item}")


def _setup_orientation_surfaces(*, target_root: Path) -> tuple[Path, ...]:
    return (
        target_root / "AGENTS.md",
        target_root / "TODO.md",
        target_root / "tools" / "AGENT_QUICKSTART.md",
        target_root / "tools" / "AGENT_ROUTING.md",
        target_root / "memory" / "index.md",
    )


def _repo_looks_setup_mature(*, target_root: Path) -> bool:
    return all(path.exists() for path in _setup_orientation_surfaces(target_root=target_root))


def _setup_payload(
    *,
    target_root: Path,
    selected_modules: list[str],
    resolved_preset: str | None,
    descriptors: dict[str, ModuleDescriptor],
    config: WorkspaceConfig,
) -> dict[str, Any]:
    status_payload = _run_lifecycle_command(
        command_name="status",
        target_root=target_root,
        selected_modules=selected_modules,
        resolved_preset=resolved_preset,
        descriptors=descriptors,
        dry_run=False,
        non_interactive=False,
        config=config,
    )
    discovery = setup_discovery_payload(
        target_root=target_root,
        status_payload=status_payload,
        active_todo_surface=_active_todo_surface(target_root=target_root),
    )
    findings_input = _setup_findings_input_payload(target_root=target_root)
    mature_repo = _repo_looks_setup_mature(target_root=target_root)
    if mature_repo:
        orientation: dict[str, Any] = {
            "mode": "no-new-seed-surfaces-needed",
            "summary": "No new seed surfaces are needed; the repo already has the core setup orientation surfaces.",
            "reason": "AGENTS.md, TODO.md, tools/AGENT_QUICKSTART.md, tools/AGENT_ROUTING.md, and memory/index.md are already present.",
        }
        next_action = {
            "summary": "No new seed surfaces needed",
            "commands": ["agentic-workspace report --target ./repo --format json"],
        }
    else:
        prioritized = discovery["memory_candidates"] + discovery["planning_candidates"] + discovery["ambiguous"]
        prioritized.sort(key=lambda item: item["confidence"], reverse=True)
        best = prioritized[0] if prioritized else None
        orientation = {
            "mode": "bounded-orientation-needed",
            "summary": "Review the strongest current surface candidates before seeding anything new.",
        }
        if best is not None:
            orientation["surface"] = best["surface"]
            orientation["reason"] = best["reason"]
        next_action = {
            "summary": "Review the compact report surfaces",
            "commands": ["agentic-workspace report --target ./repo --format json"],
        }
    if findings_input.get("status") == "loaded":
        promotable_count = sum(len(items) for items in findings_input["promotable"].values())
        if promotable_count:
            next_action = {
                "summary": "Review promotable setup findings before seeding or promoting anything durable",
                "commands": [
                    "agentic-workspace setup --target ./repo --format json",
                    "agentic-workspace report --target ./repo --format json",
                ],
            }

    return {
        "kind": "workspace-setup/v1",
        "schema": _reporting_schema_payload(),
        "command": "setup",
        "target": target_root.as_posix(),
        "selected_modules": selected_modules,
        "health": status_payload["health"],
        "orientation": orientation,
        "findings_promotion": {
            "canonical_doc": "docs/setup-findings-contract.md",
            "artifact_path": SETUP_FINDINGS_PATH.as_posix(),
            "schema_path": "src/agentic_workspace/contracts/schemas/setup_findings.schema.json",
            "accepted_kind": SETUP_FINDINGS_KIND,
            "accepted_classes": [_setup_finding_class_payload(finding_class) for finding_class in SUPPORTED_SETUP_FINDING_CLASSES],
            "rule": (
                "Accept agent-produced setup findings as optional input, preserve only the classes that reduce rediscovery, "
                "and keep low-value or weakly grounded findings transient."
            ),
        },
        "analysis_input": findings_input,
        "next_action": next_action,
        "discovery": discovery,
        "current": {
            "installed_modules": [entry["name"] for entry in status_payload.get("registry", []) if entry.get("installed")],
            "warnings": list(status_payload.get("warnings", [])),
            "needs_review": list(status_payload.get("needs_review", [])),
            "stale_generated_surfaces": list(status_payload.get("stale_generated_surfaces", [])),
        },
    }


def _emit_setup(
    *,
    format_name: str,
    target_root: Path,
    selected_modules: list[str],
    resolved_preset: str | None,
    descriptors: dict[str, ModuleDescriptor],
    config: WorkspaceConfig,
) -> None:
    payload = _setup_payload(
        target_root=target_root,
        selected_modules=selected_modules,
        resolved_preset=resolved_preset,
        descriptors=descriptors,
        config=config,
    )
    if format_name == "json":
        print(json.dumps(serialise_value(payload), indent=2))
        return
    print(f"Target: {payload['target']}")
    print("Setup:")
    print(f"- command: {payload['command']}")
    print(f"- mode: {payload['orientation']['mode']}")
    print(f"- summary: {payload['orientation']['summary']}")
    if payload["orientation"].get("surface"):
        print(f"- surface: {payload['orientation']['surface']}")
    if payload["orientation"].get("reason"):
        print(f"- reason: {payload['orientation']['reason']}")
    print(f"- next action: {payload['next_action']['summary']}")
    for command in payload["next_action"]["commands"]:
        print(f"  - {command}")
    if payload["current"]["warnings"]:
        print("Current warnings:")
        for warning in payload["current"]["warnings"]:
            print(f"- {warning}")


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
    configured_agent_instructions_file: str | None = None
    workflow_artifact_profile = DEFAULT_WORKFLOW_ARTIFACT_PROFILE
    workflow_artifact_profile_source = "product-default"
    improvement_latitude = DEFAULT_IMPROVEMENT_LATITUDE
    improvement_latitude_source = "product-default"
    optimization_bias = DEFAULT_OPTIMIZATION_BIAS
    optimization_bias_source = "product-default"
    if not config_path.exists():
        agent_instructions_file, agent_instructions_source, detected_agent_instruction_files = _resolve_effective_agent_instructions_file(
            target_root=target_root,
            configured=None,
        )
        return WorkspaceConfig(
            target_root=target_root,
            path=config_path,
            exists=False,
            schema_version=1,
            default_preset=default_preset,
            agent_instructions_file=agent_instructions_file,
            agent_instructions_source=agent_instructions_source,
            workflow_artifact_profile=workflow_artifact_profile,
            workflow_artifact_profile_source=workflow_artifact_profile_source,
            improvement_latitude=improvement_latitude,
            improvement_latitude_source=improvement_latitude_source,
            optimization_bias=optimization_bias,
            optimization_bias_source=optimization_bias_source,
            detected_agent_instructions_files=detected_agent_instruction_files,
            update_modules=defaults,
            local_override=local_override,
        )

    payload = _load_toml_payload(path=config_path, surface_name=WORKSPACE_CONFIG_PATH.as_posix())

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
    raw_agent_instructions_file = raw_workspace.get("agent_instructions_file")
    if raw_agent_instructions_file is not None:
        configured_agent_instructions_file = _validate_agent_instructions_filename(str(raw_agent_instructions_file))
    raw_workflow_artifact_profile = raw_workspace.get("workflow_artifact_profile")
    if raw_workflow_artifact_profile is not None:
        workflow_artifact_profile = _validate_workflow_artifact_profile(str(raw_workflow_artifact_profile))
        workflow_artifact_profile_source = "repo-config"
    raw_improvement_latitude = raw_workspace.get("improvement_latitude")
    if raw_improvement_latitude is not None:
        improvement_latitude = _validate_improvement_latitude(str(raw_improvement_latitude))
        improvement_latitude_source = "repo-config"
    raw_optimization_bias = raw_workspace.get("optimization_bias")
    if raw_optimization_bias is not None:
        optimization_bias = _validate_optimization_bias(str(raw_optimization_bias))
        optimization_bias_source = "repo-config"

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

    agent_instructions_file, agent_instructions_source, detected_agent_instruction_files = _resolve_effective_agent_instructions_file(
        target_root=target_root,
        configured=configured_agent_instructions_file,
    )
    return WorkspaceConfig(
        target_root=target_root,
        path=config_path,
        exists=True,
        schema_version=1,
        default_preset=configured_preset,
        agent_instructions_file=agent_instructions_file,
        agent_instructions_source=agent_instructions_source,
        workflow_artifact_profile=workflow_artifact_profile,
        workflow_artifact_profile_source=workflow_artifact_profile_source,
        improvement_latitude=improvement_latitude,
        improvement_latitude_source=improvement_latitude_source,
        optimization_bias=optimization_bias,
        optimization_bias_source=optimization_bias_source,
        detected_agent_instructions_files=detected_agent_instruction_files,
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
        refs = [compact_contract_manifest()["canonical_doc"], payload["command"], payload["canonical_doc"]]
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
        refs = [compact_contract_manifest()["canonical_doc"], payload["command"], payload["canonical_doc"]]
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
            non_interactive=False,
            config=config,
        )
        doctor_payload = _run_lifecycle_command(
            command_name="doctor",
            target_root=target_root,
            selected_modules=installed_modules,
            resolved_preset=None,
            descriptors=descriptors,
            dry_run=False,
            non_interactive=False,
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
    refs = [compact_contract_manifest()["canonical_doc"], payload["command"], payload["canonical_doc"], payload["ledger_path"]]
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
        payload = _load_toml_payload(path=ledger_path, surface_name=ledger_path.as_posix())
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
        safe_to_auto_run_commands=None,
        requires_human_verification_on_pr=None,
        delegation_targets=(),
    )


def _require_optional_bool(*, payload: dict[str, Any], key: str, config_path: Path) -> bool | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, bool):
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be a boolean.")
    return value


def _load_toml_payload(*, path: Path, surface_name: str) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise WorkspaceUsageError(f"{surface_name} is invalid TOML: {exc}.") from exc


def _load_json_payload(*, path: Path, surface_name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise WorkspaceUsageError(f"{surface_name} is invalid JSON: {exc}.") from exc
    if not isinstance(payload, dict):
        raise WorkspaceUsageError(f"{surface_name} must contain a JSON object.")
    return payload


def _require_optional_confidence(*, payload: dict[str, Any], key: str, config_path: Path) -> float | None:
    if key not in payload:
        return None
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be a number between 0 and 1.")
    normalized = float(value)
    if normalized < 0 or normalized > 1:
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be between 0 and 1.")
    return normalized


def _require_optional_string_list(
    *,
    payload: dict[str, Any],
    key: str,
    config_path: Path,
    allowed: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    if key not in payload:
        return ()
    value = payload[key]
    if not isinstance(value, list):
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be an array of strings.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise WorkspaceUsageError(f"{config_path.as_posix()} {key} entries must be non-empty strings.")
        if allowed is not None and item not in allowed:
            allowed_text = ", ".join(allowed)
            raise WorkspaceUsageError(f"{config_path.as_posix()} {key} entries must be one of: {allowed_text}.")
        if item not in items:
            items.append(item)
    return tuple(items)


def _load_delegation_target_profiles(*, raw_targets: dict[str, Any], config_path: Path) -> tuple[DelegationTargetProfile, ...]:
    profiles: list[DelegationTargetProfile] = []
    for target_name in sorted(raw_targets):
        raw_profile = raw_targets[target_name]
        target_path = Path(f"{config_path.as_posix()} delegation_targets.{target_name}")
        if not isinstance(raw_profile, dict):
            raise WorkspaceUsageError(f"{target_path.as_posix()} must be a table.")
        unknown_fields = sorted(set(raw_profile) - {"strength", "confidence", "task_fit", "execution_methods"})
        if unknown_fields:
            unknown_text = ", ".join(unknown_fields)
            raise WorkspaceUsageError(f"{target_path.as_posix()} contains unsupported field(s): {unknown_text}.")
        strength = raw_profile.get("strength")
        if not isinstance(strength, str) or strength not in SUPPORTED_DELEGATION_TARGET_STRENGTHS:
            allowed_text = ", ".join(SUPPORTED_DELEGATION_TARGET_STRENGTHS)
            raise WorkspaceUsageError(f"{target_path.as_posix()} strength must be one of: {allowed_text}.")
        execution_methods = _require_optional_string_list(
            payload=raw_profile,
            key="execution_methods",
            config_path=target_path,
            allowed=SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS,
        )
        if not execution_methods:
            raise WorkspaceUsageError(f"{target_path.as_posix()} execution_methods must list at least one supported method.")
        profiles.append(
            DelegationTargetProfile(
                name=target_name,
                strength=strength,
                execution_methods=execution_methods,
                confidence=_require_optional_confidence(
                    payload=raw_profile,
                    key="confidence",
                    config_path=target_path,
                ),
                task_fit=_require_optional_string_list(
                    payload=raw_profile,
                    key="task_fit",
                    config_path=target_path,
                ),
            )
        )
    return tuple(profiles)


def _normalize_delegation_outcome_record(raw: Any, *, surface_name: str) -> DelegationOutcomeRecord:
    if not isinstance(raw, dict):
        raise WorkspaceUsageError(f"{surface_name} records entries must be objects.")
    recorded_at = raw.get("recorded_at")
    delegation_target = raw.get("delegation_target")
    task_class = raw.get("task_class")
    outcome = raw.get("outcome")
    handoff_sufficiency = raw.get("handoff_sufficiency")
    review_burden = raw.get("review_burden")
    escalation_required = raw.get("escalation_required")
    if not isinstance(recorded_at, str) or not recorded_at.strip():
        raise WorkspaceUsageError(f"{surface_name} record recorded_at must be a non-empty string.")
    if not isinstance(delegation_target, str) or not delegation_target.strip():
        raise WorkspaceUsageError(f"{surface_name} record delegation_target must be a non-empty string.")
    if not isinstance(task_class, str) or not task_class.strip():
        raise WorkspaceUsageError(f"{surface_name} record task_class must be a non-empty string.")
    if outcome not in SUPPORTED_DELEGATION_OUTCOMES:
        allowed = ", ".join(SUPPORTED_DELEGATION_OUTCOMES)
        raise WorkspaceUsageError(f"{surface_name} record outcome must be one of: {allowed}.")
    if handoff_sufficiency not in SUPPORTED_HANDOFF_SUFFICIENCY:
        allowed = ", ".join(SUPPORTED_HANDOFF_SUFFICIENCY)
        raise WorkspaceUsageError(f"{surface_name} record handoff_sufficiency must be one of: {allowed}.")
    if review_burden not in SUPPORTED_REVIEW_BURDENS:
        allowed = ", ".join(SUPPORTED_REVIEW_BURDENS)
        raise WorkspaceUsageError(f"{surface_name} record review_burden must be one of: {allowed}.")
    if not isinstance(escalation_required, bool):
        raise WorkspaceUsageError(f"{surface_name} record escalation_required must be a boolean.")
    return DelegationOutcomeRecord(
        recorded_at=recorded_at.strip(),
        delegation_target=delegation_target.strip(),
        task_class=task_class.strip(),
        outcome=outcome,
        handoff_sufficiency=handoff_sufficiency,
        review_burden=review_burden,
        escalation_required=escalation_required,
    )


def _load_delegation_outcomes(*, target_root: Path) -> tuple[Path, dict[str, Any], tuple[DelegationOutcomeRecord, ...]]:
    path = target_root / WORKSPACE_DELEGATION_OUTCOMES_PATH
    if not path.exists():
        return path, {"kind": DELEGATION_OUTCOMES_KIND, "records": []}, ()
    payload = _load_json_payload(path=path, surface_name=WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix())
    if payload.get("kind") != DELEGATION_OUTCOMES_KIND:
        raise WorkspaceUsageError(f"{WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix()} must set kind to {DELEGATION_OUTCOMES_KIND}.")
    raw_records = payload.get("records", [])
    if not isinstance(raw_records, list):
        raise WorkspaceUsageError(f"{WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix()} records must be a list.")
    records = tuple(
        _normalize_delegation_outcome_record(raw_record, surface_name=WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix())
        for raw_record in raw_records
    )
    return path, payload, records


def _write_delegation_outcomes(*, path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(serialise_value(payload), indent=2) + "\n", encoding="utf-8")


def _delegation_signal_score(record: DelegationOutcomeRecord) -> float:
    outcome_score = {
        "success": 1.0,
        "mixed": 0.0,
        "failed": -1.0,
    }[record.outcome]
    handoff_score = {
        "sufficient": 0.25,
        "borderline": 0.0,
        "insufficient": -0.25,
    }[record.handoff_sufficiency]
    review_score = {
        "light": 0.25,
        "normal": 0.0,
        "high": -0.25,
    }[record.review_burden]
    escalation_score = -0.5 if record.escalation_required else 0.0
    return outcome_score + handoff_score + review_score + escalation_score


def _default_confidence_for_strength(strength: str) -> float:
    return {
        "strong": 0.8,
        "medium": 0.65,
        "weak": 0.5,
    }[strength]


def _round_confidence(value: float) -> float:
    return round(max(0.0, min(value, 1.0)), 2)


def _task_fit_suggestions(*, current_task_fit: tuple[str, ...], records: tuple[DelegationOutcomeRecord, ...]) -> dict[str, list[str]]:
    by_task: dict[str, list[float]] = {}
    for record in records:
        by_task.setdefault(record.task_class, []).append(_delegation_signal_score(record))
    suggest_add: list[str] = []
    suggest_remove: list[str] = []
    for task_class, scores in sorted(by_task.items()):
        average = sum(scores) / len(scores)
        if len(scores) >= 2 and average >= 0.75 and task_class not in current_task_fit:
            suggest_add.append(task_class)
        if average <= -0.5 and task_class in current_task_fit:
            suggest_remove.append(task_class)
    return {
        "suggest_add": suggest_add,
        "suggest_remove": suggest_remove,
    }


def _delegation_outcome_advisory(
    *,
    profile: DelegationTargetProfile,
    records: tuple[DelegationOutcomeRecord, ...],
) -> dict[str, Any]:
    if not records:
        return {
            "record_count": 0,
            "status": "no-local-evidence",
        }
    scores = [_delegation_signal_score(record) for record in records]
    average_score = sum(scores) / len(scores)
    baseline_confidence = profile.confidence if profile.confidence is not None else _default_confidence_for_strength(profile.strength)
    suggested_confidence = _round_confidence(baseline_confidence + (average_score * 0.1))
    confidence_delta = round(suggested_confidence - baseline_confidence, 2)
    if confidence_delta > 0.03:
        confidence_action = "raise"
    elif confidence_delta < -0.03:
        confidence_action = "lower"
    else:
        confidence_action = "keep"
    task_fit = _task_fit_suggestions(current_task_fit=profile.task_fit, records=records)
    return {
        "record_count": len(records),
        "average_signal": round(average_score, 2),
        "confidence": {
            "current": profile.confidence,
            "suggested": suggested_confidence,
            "action": confidence_action,
            "delta": confidence_delta,
        },
        "task_fit": task_fit,
        "recent_task_classes": sorted({record.task_class for record in records}),
    }


def _load_mixed_agent_local_override(*, target_root: Path) -> MixedAgentLocalOverride:
    local_path = target_root / WORKSPACE_LOCAL_CONFIG_PATH
    if not local_path.exists():
        return _empty_mixed_agent_local_override(path=local_path, exists=False)

    payload = _load_toml_payload(path=local_path, surface_name=WORKSPACE_LOCAL_CONFIG_PATH.as_posix())

    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise WorkspaceUsageError(
            f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} must set schema_version = 1 for the current local mixed-agent override contract."
        )

    unknown_top_level = sorted(set(payload) - {"schema_version", "runtime", "handoff", "safety", "delegation_targets"})
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

    raw_safety = payload.get("safety", {})
    if raw_safety is None:
        raw_safety = {}
    if not isinstance(raw_safety, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [safety] section must be a table.")
    unknown_safety = sorted(set(raw_safety) - {"safe_to_auto_run_commands", "requires_human_verification_on_pr"})
    if unknown_safety:
        unknown_text = ", ".join(unknown_safety)
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [safety] contains unsupported field(s): {unknown_text}.")

    raw_delegation_targets = payload.get("delegation_targets", {})
    if raw_delegation_targets is None:
        raw_delegation_targets = {}
    if not isinstance(raw_delegation_targets, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [delegation_targets] section must be a table.")

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
        safe_to_auto_run_commands=_require_optional_bool(
            payload=raw_safety,
            key="safe_to_auto_run_commands",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        requires_human_verification_on_pr=_require_optional_bool(
            payload=raw_safety,
            key="requires_human_verification_on_pr",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        delegation_targets=_load_delegation_target_profiles(
            raw_targets=raw_delegation_targets,
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
    )


def _sourced_value(value: bool | None, *, source: str) -> dict[str, Any]:
    return {"value": value, "source": source if value is not None else "unset"}


def _delegation_target_advisory(profile: DelegationTargetProfile) -> dict[str, str]:
    confidence = profile.confidence
    if profile.strength == "weak" or (confidence is not None and confidence < 0.6):
        return {
            "handoff_detail": "high",
            "review_burden": "high",
        }
    if profile.strength == "strong" and confidence is not None and confidence >= 0.85:
        return {
            "handoff_detail": "compact",
            "review_burden": "light",
        }
    return {
        "handoff_detail": "standard",
        "review_burden": "normal",
    }


def _record_delegation_outcome(
    *,
    target_root: Path,
    delegation_target: str,
    task_class: str,
    outcome: str,
    handoff_sufficiency: str,
    review_burden: str,
    escalation_required: bool,
) -> dict[str, Any]:
    path, payload, records = _load_delegation_outcomes(target_root=target_root)
    record = DelegationOutcomeRecord(
        recorded_at=date.today().isoformat(),
        delegation_target=delegation_target.strip(),
        task_class=task_class.strip(),
        outcome=outcome,
        handoff_sufficiency=handoff_sufficiency,
        review_burden=review_burden,
        escalation_required=escalation_required,
    )
    updated_payload = {
        "kind": DELEGATION_OUTCOMES_KIND,
        "records": [
            *[
                {
                    "recorded_at": existing.recorded_at,
                    "delegation_target": existing.delegation_target,
                    "task_class": existing.task_class,
                    "outcome": existing.outcome,
                    "handoff_sufficiency": existing.handoff_sufficiency,
                    "review_burden": existing.review_burden,
                    "escalation_required": existing.escalation_required,
                }
                for existing in records
            ],
            {
                "recorded_at": record.recorded_at,
                "delegation_target": record.delegation_target,
                "task_class": record.task_class,
                "outcome": record.outcome,
                "handoff_sufficiency": record.handoff_sufficiency,
                "review_burden": record.review_burden,
                "escalation_required": record.escalation_required,
            },
        ],
    }
    _write_delegation_outcomes(path=path, payload=updated_payload)
    return {
        "kind": DELEGATION_OUTCOMES_KIND,
        "path": WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix(),
        "recorded": updated_payload["records"][-1],
        "record_count": len(updated_payload["records"]),
        "rule": "local-only delegation outcome evidence; advisory input for tuning only",
    }


def _mixed_agent_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    defaults = _defaults_payload()["mixed_agent"]
    local_override = config.local_override
    outcome_records: tuple[DelegationOutcomeRecord, ...] = ()
    outcome_status = "unavailable"
    if config.target_root is not None:
        _, _, outcome_records = _load_delegation_outcomes(target_root=config.target_root)
        outcome_status = "configured" if outcome_records else "available-not-set"
    records_by_target: dict[str, tuple[DelegationOutcomeRecord, ...]] = {}
    for target_name in sorted({record.delegation_target for record in outcome_records}):
        records_by_target[target_name] = tuple(record for record in outcome_records if record.delegation_target == target_name)
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
            "authoritative": config.exists,
            "supported_fields": ["workspace.improvement_latitude"],
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
        "delegation_targets": {
            "supported": True,
            "status": "configured" if local_override.delegation_targets else "available-not-set",
            "rule": (
                "local-only advisory target hints; may guide handoff detail and review burden, but must not turn config into a scheduler"
            ),
            "supported_fields": [
                "delegation_targets.<target>.strength",
                "delegation_targets.<target>.confidence",
                "delegation_targets.<target>.task_fit",
                "delegation_targets.<target>.execution_methods",
            ],
            "supported_strengths": list(SUPPORTED_DELEGATION_TARGET_STRENGTHS),
            "supported_execution_methods": list(SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS),
            "profiles": [
                {
                    "name": profile.name,
                    "strength": profile.strength,
                    "confidence": profile.confidence,
                    "task_fit": list(profile.task_fit),
                    "execution_methods": list(profile.execution_methods),
                    "advisory": _delegation_target_advisory(profile),
                    "outcome_evidence": _delegation_outcome_advisory(
                        profile=profile,
                        records=records_by_target.get(profile.name, ()),
                    ),
                }
                for profile in local_override.delegation_targets
            ],
            "outcome_artifact": {
                "path": WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix(),
                "status": outcome_status,
                "record_count": len(outcome_records),
            },
            "unprofiled_targets_with_evidence": sorted(
                target_name
                for target_name in records_by_target
                if target_name not in {profile.name for profile in local_override.delegation_targets}
            ),
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
            "safe_to_auto_run_commands": _sourced_value(
                local_override.safe_to_auto_run_commands,
                source="local-override",
            ),
            "requires_human_verification_on_pr": _sourced_value(
                local_override.requires_human_verification_on_pr,
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
        "workspace": {
            "default_preset": config.default_preset,
            "agent_instructions_file": config.agent_instructions_file,
            "agent_instructions_file_source": config.agent_instructions_source,
            "workflow_artifact_profile": config.workflow_artifact_profile,
            "workflow_artifact_profile_source": config.workflow_artifact_profile_source,
            "improvement_latitude": config.improvement_latitude,
            "improvement_latitude_source": config.improvement_latitude_source,
            "optimization_bias": config.optimization_bias,
            "optimization_bias_source": config.optimization_bias_source,
            "workflow_artifact_adapter": _workflow_artifact_profile_payload(config.workflow_artifact_profile),
            "detected_agent_instructions_files": list(config.detected_agent_instructions_files),
            "supported_agent_instructions_files": list(SUPPORTED_AGENT_INSTRUCTIONS_FILES),
            "supported_workflow_artifact_profiles": list(SUPPORTED_WORKFLOW_ARTIFACT_PROFILES),
            "supported_improvement_latitudes": list(SUPPORTED_IMPROVEMENT_LATITUDES),
            "supported_optimization_biases": list(SUPPORTED_OPTIMIZATION_BIASES),
        },
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
    print(
        "Agent instructions file: "
        f"{payload['workspace']['agent_instructions_file']} "
        f"({payload['workspace']['agent_instructions_file_source']})"
    )
    print(
        "Workflow artifact profile: "
        f"{payload['workspace']['workflow_artifact_profile']} "
        f"({payload['workspace']['workflow_artifact_profile_source']})"
    )
    print(f"Improvement latitude: {payload['workspace']['improvement_latitude']} ({payload['workspace']['improvement_latitude_source']})")
    print(f"Optimization bias: {payload['workspace']['optimization_bias']} ({payload['workspace']['optimization_bias_source']})")
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
    print(f"- delegation targets: {len(payload['mixed_agent']['delegation_targets']['profiles'])} configured")
    print(
        f"- delegation outcome evidence: {payload['mixed_agent']['delegation_targets']['outcome_artifact']['path']} "
        f"({payload['mixed_agent']['delegation_targets']['outcome_artifact']['status']})"
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
    if "setup" in task_text_lower:
        for skill in skills:
            if skill.skill_id == "planning-reporting":
                return [
                    SkillRecommendation(
                        skill=skill,
                        hint_score=10,
                        score=10,
                        reasons=("setup uses the compact planning reporting surface before any broader discovery",),
                    )
                ]
        return []
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
    if payload.get("command") == "setup":
        _emit_setup_text(payload)
        return
    if payload.get("command") == "report":
        _emit_report_text(payload)
        return
    if "modules" in payload and "reports" not in payload and "command" not in payload:
        for module_data in payload["modules"]:
            print(f"{module_data['name']}: {module_data['description']}")
            print(f"  commands: {', '.join(module_data['commands'])}")
            print(f"  capabilities: {', '.join(module_data['capabilities'])}")
        return
    _emit_lifecycle_text(payload)


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
