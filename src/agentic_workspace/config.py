from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_workspace.result_adapter import serialise_value

WORKSPACE_CONFIG_PATH = Path(".agentic-workspace/config.toml")
LEGACY_WORKSPACE_CONFIG_PATH = Path("agentic-workspace.toml")
WORKSPACE_LOCAL_CONFIG_PATH = Path(".agentic-workspace/config.local.toml")
LEGACY_WORKSPACE_LOCAL_CONFIG_PATH = Path("agentic-workspace.local.toml")
WORKSPACE_DELEGATION_OUTCOMES_PATH = Path(".agentic-workspace/delegation-outcomes.json")
LEGACY_WORKSPACE_DELEGATION_OUTCOMES_PATH = Path("agentic-workspace.delegation-outcomes.json")
WORKSPACE_LOCAL_MEMORY_DEFAULT_PATH = Path(".agentic-workspace/local/memory.toml")
WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH = Path(".agentic-workspace/local/integrations")
WORKSPACE_LOCAL_INTEGRATION_SUBFOLDER_CONVENTION = "<vendor-or-runtime>/"
WORKSPACE_LOCAL_SCRATCH_ROOT_PATH = Path(".agentic-workspace/local/scratch")
WORKSPACE_LOCAL_BOOTSTRAP_HANDOFF_PATH = WORKSPACE_LOCAL_SCRATCH_ROOT_PATH / "bootstrap-handoff.md"
WORKSPACE_LOCAL_BOOTSTRAP_HANDOFF_RECORD_PATH = WORKSPACE_LOCAL_SCRATCH_ROOT_PATH / "bootstrap-handoff.json"
WORKSPACE_AGENT_AID_ROOT_PATH = Path(".agentic-workspace/agent-aids")
WORKSPACE_AGENT_AID_SUBDIRS = (
    "scripts",
    "skills",
    "runbooks",
    "prompts",
    "checks",
    "templates",
    "module-components",
)
WORKSPACE_LOCAL_INTEGRATION_ALLOWED_AID_KINDS = (
    "prompt helpers",
    "export/import shims",
    "local wrappers",
    "native-workflow adapters",
    "resumable handoff helpers",
    "runtime scratch files",
)
WORKSPACE_LOCAL_INTEGRATION_BOUNDARY_RULES = (
    "local-only and ignored by git",
    "optional for ordinary workspace commands",
    "non-authoritative for planning, memory, startup, review, and workflow state",
    "safe to delete without changing repo-owned shared behavior",
    "not a plugin registry or shared compatibility framework",
)
WORKSPACE_SYSTEM_INTENT_ROOT = Path(".agentic-workspace/system-intent")
WORKSPACE_SYSTEM_INTENT_MIRROR_PATH = WORKSPACE_SYSTEM_INTENT_ROOT / "intent.toml"
WORKSPACE_SUBSYSTEM_INTENT_PATH = WORKSPACE_SYSTEM_INTENT_ROOT / "subsystems.toml"
WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH = WORKSPACE_SYSTEM_INTENT_ROOT / "WORKFLOW.md"
SYSTEM_INTENT_SOURCE_DISCOVERY_CANDIDATES = (
    Path("SYSTEM_INTENT.md"),
    Path("README.md"),
    Path("AGENTS.md"),
    Path("docs/system-intent.md"),
    Path("docs/product-direction.md"),
)
WORKSPACE_BOOTSTRAP_HANDOFF_PATH = Path(".agentic-workspace/bootstrap-handoff.md")
WORKSPACE_BOOTSTRAP_HANDOFF_RECORD_PATH = Path(".agentic-workspace/bootstrap-handoff.json")
WORKSPACE_ADOPTION_RECEIPT_PATH = Path(".agentic-workspace/adoption-receipt.json")
DEFAULT_BOOTSTRAP_FOOTPRINT_PROFILE = "necessary-surfaces"
SUPPORTED_BOOTSTRAP_FOOTPRINT_PROFILES = (
    "necessary-surfaces",
    "full-payload-mirror",
)
DEFAULT_AGENT_INSTRUCTIONS_FILE = "AGENTS.md"
SUPPORTED_AGENT_INSTRUCTIONS_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".cursorrules",
)
DEFAULT_WORKFLOW_ARTIFACT_PROFILE = "repo-owned"
SUPPORTED_WORKFLOW_ARTIFACT_PROFILES = (
    "repo-owned",
    "gemini",
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
DEFAULT_ENABLED_MODULES = ("planning", "memory")
SUPPORTED_CORE_MODULES = ("planning", "memory", "verification")
SUPPORTED_OPTIMIZATION_BIASES = (
    "agent-efficiency",
    "balanced",
    "human-legibility",
)
SUPPORTED_ADVANCED_FEATURES = (
    "review_artifacts",
    "external_adapters",
)
DEFAULT_MAINTAINER_MODE = False
DEFAULT_CLI_INVOKE = "agentic-workspace"
DEFAULT_ASSURANCE_LEVEL = "low"
SUPPORTED_ASSURANCE_LEVELS = ("low", "medium", "high", "critical")
SUPPORTED_WORKFLOW_OBLIGATION_STAGES = (
    "pre-work",
    "before-claiming-completion",
    "before-commit",
    "review",
    "closeout",
)
SUPPORTED_WORKFLOW_OBLIGATION_FORCES = (
    "informational",
    "recommended",
    "required-before-closeout",
    "blocking",
)
SUPPORTED_ASSURANCE_REQUIREMENT_BLOCKING_CLAIMS = (
    "claim-slice-complete",
    "claim-work-complete",
    "close-parent-lane",
)
SUPPORTED_DELEGATION_TARGET_STRENGTHS = (
    "strong",
    "medium",
    "weak",
)
SUPPORTED_CAPABILITY_EXECUTION_CLASSES = (
    "boundary-shaping",
    "reasoning-heavy",
    "mixed",
    "mechanical-follow-through",
)
SUPPORTED_CAPABILITY_LOCATIONS = (
    "local",
    "external",
    "either",
)
SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS = (
    "internal",
    "cli",
    "api",
    "manual",
)
SUPPORTED_DELEGATION_TARGET_CONTEXT_CAPACITIES = (
    "small",
    "medium",
    "large",
    "unknown",
)
SUPPORTED_DELEGATION_TARGET_REASONING_PROFILES = (
    "weak",
    "balanced",
    "strong",
    "unknown",
)
SUPPORTED_DELEGATION_TARGET_COST_CLASSES = (
    "cheap",
    "standard",
    "premium",
    "unknown",
)
SUPPORTED_DELEGATION_TARGET_LATENCY_CLASSES = (
    "fast",
    "standard",
    "slow",
    "unknown",
)
SUPPORTED_DELEGATION_CONTROL_MODES = (
    "off",
    "manual",
    "suggest",
    "auto",
)
SUPPORTED_ORCHESTRATION_EXECUTION_ROLES = (
    "ordinary-executor",
    "orchestrator",
    "bounded-worker",
)
SUPPORTED_ASSIGNMENT_POLICIES = (
    "local-preferred",
    "best-fit-advisory",
    "required-best-fit",
)
SUPPORTED_UNDERFIT_BEHAVIORS = (
    "stay-when-safe",
    "prepare-manual-escalation",
    "require-delegation",
)
SUPPORTED_DOWN_ROUTING_BEHAVIORS = (
    "never",
    "bounded-mechanical-work",
    "when-cheaper-safe-target-exists",
)
SUPPORTED_HUMAN_OVERRIDE_POLICIES = (
    "explicit-only",
    "allowed-with-recorded-reason",
    "disallowed",
)
SUPPORTED_MANUAL_TRANSPORT_POLICIES = (
    "disabled",
    "allowed",
    "required-when-no-automatic-method",
)
SUPPORTED_CLARIFICATION_CONTROL_MODES = (
    "ask-first",
    "suggest",
    "auto-continue",
)
SUPPORTED_SESSION_LOGGING_PATH_MODES = (
    "absolute",
    "repo-relative",
    "redacted",
)
WORKSPACE_WORKFLOW_MARKER_START = "<!-- agentic-workspace:workflow:start -->"
WORKSPACE_WORKFLOW_MARKER_END = "<!-- agentic-workspace:workflow:end -->"


def workspace_pointer_block(*, cli_invoke: str = DEFAULT_CLI_INVOKE) -> str:
    return (
        f"{WORKSPACE_WORKFLOW_MARKER_START}\n"
        "Use the main Agentic Workspace operating skill: `.agentic-workspace/skills/workspace-startup/SKILL.md`.\n"
        "\n"
        "Invocation rule:\n"
        "1. Use `.agentic-workspace/config.local.toml` `[workspace].cli_invoke` when present.\n"
        "2. Otherwise use `.agentic-workspace/config.toml` `[workspace].cli_invoke`.\n"
        "3. Otherwise use the package default `agentic-workspace`.\n"
        "4. If no CLI invocation works, read `.agentic-workspace/WORKFLOW.md` before other workspace files.\n"
        "\n"
        "Ordinary route:\n"
        '1. Run `<configured AW invocation> start --target . --task "<task>" --format json` before non-trivial answers, edits, read-only workflow, config, delegation, or action-safety decisions.\n'
        '2. Run `<configured AW invocation> implement --target . --changed <paths> --task "<task>" --format json` when changed paths are already known.\n'
        "3. Follow `next_safe_action`, `action_signals`, and `skills` before opening raw `.agentic-workspace` files or running drill-down commands.\n"
        "4. Use the returned `communication_contract` for decision-first, evidence-backed, compact output; expand only for its safety/proof/detail triggers.\n"
        "5. When implementing an issue, satisfy the intended end state in the ordinary path; ask for clarification instead of closing with a partial path when the full outcome appears larger than the issue safely permits.\n"
        "\n"
        "Boundaries:\n"
        "- Known dedicated Agentic Workspace commands are allowed only when the request maps directly to that command and no takeover, recovery, active-planning, or ambiguous safety decision is needed first.\n"
        "- Do not bake machine-local AW invocation paths into checked-in generic guidance; concrete commands come from the configured invocation or live router output.\n"
        "- Treat checked-in `.agentic-workspace/skills` and module skill trees as required operating surfaces, not optional payload mirror content.\n"
        "- Treat `preflight`, `config`, `defaults`, `skills`, `modules`, `ownership`, and `report` as routed drill-down or recovery surfaces, not the ordinary startup loop.\n"
        "- Report repo-relative paths, not local absolute paths.\n"
        f"{WORKSPACE_WORKFLOW_MARKER_END}"
    )


WORKSPACE_POINTER_BLOCK = workspace_pointer_block()
MEMORY_WORKFLOW_MARKER_START = "<!-- agentic-memory:workflow:start -->"
MEMORY_WORKFLOW_MARKER_END = "<!-- agentic-memory:workflow:end -->"
MEMORY_POINTER_BLOCK = (
    f"{MEMORY_WORKFLOW_MARKER_START}\nRead `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules.\n{MEMORY_WORKFLOW_MARKER_END}"
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
SUPPORTED_CLI_COMPATIBILITY_ENFORCEMENT = (
    "off",
    "advisory",
    "blocking",
)
SUPPORTED_CLI_SOURCE_CLASSES = (
    "source-checkout",
    "installed-package",
    "editable-dev",
    "unknown",
)
SUPPORTED_CLI_TARGET_RELATIONS = (
    "inside-target",
    "outside-target",
    "no-target",
)
SUPPORTED_PAYLOAD_TARGET_POLICIES = (
    "advisory",
    "required-before-claim",
    "required-before-work",
)
SUPPORTED_LOCAL_HIGH_RISK_IMPACTS = (
    "advisory",
    "blocking",
    "human-review-only",
    "claim-limiting",
)
SUPPORTED_LOCAL_HIGH_RISK_VALIDATION_STATES = (
    "ci_failed",
    "ci_pending",
    "ci_skipped",
    "ci_not_run",
    "ci_unavailable",
    "quota_exhausted",
    "logs_unavailable",
    "local_substitute",
)
SUPPORTED_LOCAL_HIGH_RISK_SUBSTITUTE_POLICIES = (
    "advisory",
    "sufficient-for-bounded-claim",
    "insufficient",
    "human-review-only",
)
SUPPORTED_LOCAL_HIGH_RISK_UNRESOLVED_CLASSES = (
    "merge-blocker",
    "release-blocker",
    "human-review-required",
    "safe-follow-up",
    "intentionally-deferred",
)


class WorkspaceUsageError(ValueError):
    """Raised when workspace CLI preconditions are not met."""


@dataclass(frozen=True)
class ModuleUpdatePolicy:
    module: str
    source_type: str
    source_ref: str
    source_label: str
    recommended_upgrade_after_days: int
    source: str


@dataclass(frozen=True)
class DelegationTargetProfile:
    name: str
    strength: str
    location: str
    execution_methods: tuple[str, ...]
    confidence: float | None
    task_fit: tuple[str, ...]
    capability_classes: tuple[str, ...]
    model_family: str | None
    provider: str | None
    context_capacity: str
    reasoning_profile: str
    cost_class: str
    latency_class: str
    safe_task_classes: tuple[str, ...]
    forbidden_task_classes: tuple[str, ...]
    escalation_target: str | None
    confidence_source: str | None
    last_evaluation: str | None
    human_control_modes: tuple[str, ...]


@dataclass(frozen=True)
class SessionLoggingConfig:
    enabled: bool | None
    redact_local_paths: bool
    path_mode: str
    source: str


@dataclass(frozen=True)
class MixedAgentLocalOverride:
    path: Path | None
    exists: bool
    applied: bool
    shared_config_path: Path | None
    shared_config_exists: bool
    shared_config_applied: bool
    enabled: bool | None
    cli_invoke: str | None
    maintainer_mode: bool | None
    supports_internal_delegation: bool | None
    strong_planner_available: bool | None
    cheap_bounded_executor_available: bool | None
    prefer_internal_delegation_when_available: bool | None
    safe_to_auto_run_commands: bool | None
    requires_human_verification_on_pr: bool | None
    delegation_mode: str | None
    execution_role: str | None
    assignment_policy: str | None
    selection_objective: str | None
    current_target: str | None
    underfit_behavior: str | None
    down_routing_behavior: str | None
    human_override_policy: str | None
    manual_transport_policy: str | None
    clarification_mode: str | None
    local_memory_enabled: bool | None
    local_memory_path: Path
    session_logging: SessionLoggingConfig
    delegation_targets: tuple[DelegationTargetProfile, ...]
    local_overlay: dict[str, Any]
    high_risk_overlay: dict[str, Any]
    field_sources: dict[str, str]


@dataclass(frozen=True)
class WorkflowObligation:
    name: str
    summary: str
    stage: str
    force: str
    scope_tags: tuple[str, ...]
    commands: tuple[str, ...]
    review_hint: str | None


@dataclass(frozen=True)
class SystemIntentDeclaration:
    sources: tuple[str, ...]
    sources_source: str
    preferred_source: str | None
    preferred_source_source: str


@dataclass(frozen=True)
class AssuranceProofProfile:
    id: str
    required_commands: tuple[str, ...]
    optional_commands: tuple[str, ...]
    review_aids: tuple[str, ...]
    disallowed_commands: tuple[str, ...]


@dataclass(frozen=True)
class AssuranceRequirementDisposition:
    reason: str
    owner: str


@dataclass(frozen=True)
class AssuranceRequirement:
    id: str
    level: str
    applies_to_paths: tuple[str, ...]
    applies_to_task_markers: tuple[str, ...]
    applies_to_planning_refs: tuple[str, ...]
    applies_to_proof_profiles: tuple[str, ...]
    applies_to_risk_refs: tuple[str, ...]
    applies_to_invariant_refs: tuple[str, ...]
    authority_refs: tuple[str, ...]
    required_evidence: tuple[str, ...]
    proof_profile: str | None
    workflow_obligation_refs: tuple[str, ...]
    review_owner: str | None
    force: str
    blocking_claims: tuple[str, ...]
    waiver: AssuranceRequirementDisposition | None
    dismissal: AssuranceRequirementDisposition | None
    notes: str | None


@dataclass(frozen=True)
class AssuranceSubsystemProfile:
    id: str
    assurance_level: str
    scope_refs: tuple[str, ...]
    requirement_refs: tuple[str, ...]
    required_evidence: tuple[str, ...]
    proof_profile: str | None
    workflow_obligation_refs: tuple[str, ...]
    review_owner: str | None
    force: str
    blocked_without_evidence: tuple[str, ...]
    claim_boundary: str | None
    notes: str | None


@dataclass(frozen=True)
class AssuranceDomainProofLane:
    id: str
    purpose: str
    applies_to_paths: tuple[str, ...]
    applies_to_task_markers: tuple[str, ...]
    commands: tuple[str, ...]
    manual_evidence: tuple[str, ...]
    review_aids: tuple[str, ...]
    evidence_concepts: tuple[str, ...]
    assurance_requirement_refs: tuple[str, ...]
    proof_profiles: tuple[str, ...]
    authority_refs: tuple[str, ...]
    escalation: tuple[str, ...]
    escalation_conditions: tuple[str, ...]
    claim_boundary: str | None
    owner: str | None
    route_role: str | None
    precedence: str | None
    allowed_composition: tuple[str, ...]
    notes: str | None


@dataclass(frozen=True)
class AssuranceCloseoutPosture:
    id: str
    purpose: str
    applies_to_paths: tuple[str, ...]
    applies_to_task_markers: tuple[str, ...]
    assurance_requirement_refs: tuple[str, ...]
    proof_profiles: tuple[str, ...]
    required_evidence: tuple[str, ...]
    review_owner: str | None
    authority_refs: tuple[str, ...]
    claim_boundary: str | None
    uncertainty: str | None
    human_waiver_refs: tuple[str, ...]
    certification_limits: tuple[str, ...]
    notes: str | None


@dataclass(frozen=True)
class AssuranceConfig:
    default_level: str
    default_level_source: str
    agent_may_escalate: bool
    agent_may_deescalate: bool
    strict_closeout: bool
    proof_profiles: tuple[AssuranceProofProfile, ...]
    requirements: tuple[AssuranceRequirement, ...]
    subsystem_profiles: tuple[AssuranceSubsystemProfile, ...]
    domain_proof_lanes: tuple[AssuranceDomainProofLane, ...]
    closeout_postures: tuple[AssuranceCloseoutPosture, ...]
    test_data_policy: dict[str, Any]
    decision_record_target: str | None
    decision_record_format: str | None
    decision_record_template: str | None
    decision_record_statuses: tuple[str, ...]
    invariant_registry: str | None
    risk_registry: str | None


@dataclass(frozen=True)
class CLICompatibilityExpectation:
    enforcement: str
    enforcement_source: str
    minimum_version: str | None
    exact_version: str | None
    source_classes: tuple[str, ...]
    target_relations: tuple[str, ...]
    command: str | None
    source: str


@dataclass(frozen=True)
class PayloadTargetConfig:
    target_release: str | None
    minimum_capabilities: tuple[str, ...]
    policy: str
    dogfood_latest: bool
    source: str


@dataclass(frozen=True)
class WorkspaceConfig:
    target_root: Path | None
    path: Path | None
    exists: bool
    schema_version: int
    enabled: bool
    enabled_source: str
    enabled_modules: tuple[str, ...]
    agent_instructions_file: str
    agent_instructions_source: str
    workflow_artifact_profile: str
    workflow_artifact_profile_source: str
    improvement_latitude: str
    improvement_latitude_source: str
    optimization_bias: str
    optimization_bias_source: str
    advanced_features: tuple[str, ...]
    advanced_features_source: str
    maintainer_mode: bool
    maintainer_mode_source: str
    cli_invoke: str
    cli_invoke_source: str
    detected_agent_instructions_files: tuple[str, ...]
    update_modules: dict[str, ModuleUpdatePolicy]
    workflow_obligations: tuple[WorkflowObligation, ...]
    system_intent: SystemIntentDeclaration
    assurance: AssuranceConfig
    cli_compatibility: CLICompatibilityExpectation
    payload_target: PayloadTargetConfig
    local_override: MixedAgentLocalOverride
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class DelegationOutcomeRecord:
    recorded_at: str
    delegation_target: str
    task_class: str
    outcome: str
    handoff_sufficiency: str
    review_burden: str
    escalation_required: bool


def discover_workspace_root(start_path: Path | None = None) -> Path | None:
    """Search upwards for the workspace root containing the checked-in workspace config."""
    current = (start_path or Path.cwd()).resolve()
    while True:
        if (current / WORKSPACE_CONFIG_PATH).exists() or (current / LEGACY_WORKSPACE_CONFIG_PATH).exists():
            return current
        if (current / ".git").exists() or current.parent == current:
            break
        current = current.parent
    return None


def load_toml_payload(*, path: Path, surface_name: str) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError as exc:
        raise WorkspaceUsageError(f"{surface_name} is invalid TOML: {exc}.") from exc


def load_json_payload(*, path: Path, surface_name: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise WorkspaceUsageError(f"{surface_name} is invalid JSON: {exc}.") from exc
    if not isinstance(payload, dict):
        raise WorkspaceUsageError(f"{surface_name} must contain a JSON object.")
    return payload


def require_optional_bool(*, payload: dict[str, Any], key: str, config_path: Path) -> bool | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, bool):
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be a boolean.")
    return value


def require_optional_relative_path(*, payload: dict[str, Any], key: str, config_path: Path, default: Path) -> Path:
    if key not in payload:
        return default
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be a non-empty relative path string.")
    path = Path(value.strip())
    if path.is_absolute() or ".." in path.parts:
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must stay inside the target repository.")
    return path


def require_optional_confidence(*, payload: dict[str, Any], key: str, config_path: Path) -> float | None:
    if key not in payload:
        return None
    value = payload[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be a number between 0 and 1.")
    normalized = float(value)
    if normalized < 0 or normalized > 1:
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be between 0 and 1.")
    return normalized


def require_optional_string_list(
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


def require_optional_string(*, payload: dict[str, Any], key: str, config_path: Path) -> str | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be a non-empty string when present.")
    return value.strip()


def require_optional_enum(
    *,
    payload: dict[str, Any],
    key: str,
    config_path: Path,
    allowed: tuple[str, ...],
    default: str,
) -> str:
    if key not in payload:
        return default
    value = payload[key]
    if not isinstance(value, str) or value not in allowed:
        allowed_text = ", ".join(allowed)
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be one of: {allowed_text}.")
    return value


def require_optional_enum_or_none(
    *,
    payload: dict[str, Any],
    key: str,
    config_path: Path,
    allowed: tuple[str, ...],
) -> str | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, str) or value not in allowed:
        allowed_text = ", ".join(allowed)
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be one of: {allowed_text}.")
    return value


def require_required_enum(*, payload: dict[str, Any], key: str, config_path: Path, allowed: tuple[str, ...]) -> str:
    if key not in payload:
        allowed_text = ", ".join(allowed)
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} is required and must be one of: {allowed_text}.")
    value = payload[key]
    if not isinstance(value, str) or value not in allowed:
        allowed_text = ", ".join(allowed)
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be one of: {allowed_text}.")
    return value


def validate_agent_instructions_filename(filename: str) -> str:
    normalized = filename.strip()
    if not normalized:
        raise WorkspaceUsageError("agent instructions filename must be a non-empty relative path.")
    path = Path(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise WorkspaceUsageError("agent instructions filename must be a non-empty relative path inside the target repo.")
    return normalized


def validate_workflow_artifact_profile(profile: str) -> str:
    normalized = profile.strip() or DEFAULT_WORKFLOW_ARTIFACT_PROFILE
    if normalized not in SUPPORTED_WORKFLOW_ARTIFACT_PROFILES:
        supported = ", ".join(SUPPORTED_WORKFLOW_ARTIFACT_PROFILES)
        raise WorkspaceUsageError(f"workflow artifact profile must be one of: {supported}.")
    return normalized


def validate_improvement_latitude(latitude: str) -> str:
    normalized = latitude.strip() or DEFAULT_IMPROVEMENT_LATITUDE
    if normalized not in SUPPORTED_IMPROVEMENT_LATITUDES:
        supported = ", ".join(SUPPORTED_IMPROVEMENT_LATITUDES)
        raise WorkspaceUsageError(f"workspace.improvement_latitude must be one of: {supported}.")
    return normalized


def validate_optimization_bias(bias: str) -> str:
    normalized = bias.strip() or DEFAULT_OPTIMIZATION_BIAS
    if normalized not in SUPPORTED_OPTIMIZATION_BIASES:
        supported = ", ".join(SUPPORTED_OPTIMIZATION_BIASES)
        raise WorkspaceUsageError(f"workspace.optimization_bias must be one of: {supported}.")
    return normalized


def validate_assurance_level(level: str) -> str:
    normalized = level.strip() or DEFAULT_ASSURANCE_LEVEL
    if normalized not in SUPPORTED_ASSURANCE_LEVELS:
        supported = ", ".join(SUPPORTED_ASSURANCE_LEVELS)
        raise WorkspaceUsageError(f"assurance.default_level must be one of: {supported}.")
    return normalized


def validate_cli_compatibility_enforcement(enforcement: str) -> str:
    normalized = enforcement.strip() or "off"
    if normalized not in SUPPORTED_CLI_COMPATIBILITY_ENFORCEMENT:
        supported = ", ".join(SUPPORTED_CLI_COMPATIBILITY_ENFORCEMENT)
        raise WorkspaceUsageError(f"cli_compatibility.enforcement must be one of: {supported}.")
    return normalized


def _validate_version_string(*, value: Any, field: str, config_path: Path) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceUsageError(f"{config_path.as_posix()} cli_compatibility.{field} must be a non-empty string.")
    normalized = value.strip()
    if not re.match(r"^\d+(?:\.\d+){0,3}(?:[-+][A-Za-z0-9.-]+)?$", normalized):
        raise WorkspaceUsageError(f"{config_path.as_posix()} cli_compatibility.{field} must be a simple version string like 1.2.3.")
    return normalized


def _validate_payload_target_release(*, value: Any, config_path: Path) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceUsageError(f"{config_path.as_posix()} payload.target_release must be a non-empty string.")
    normalized = value.strip()
    if normalized == "source-current":
        return normalized
    if not re.match(r"^\d+(?:\.\d+){0,3}(?:[-+][A-Za-z0-9.-]+)?$", normalized):
        raise WorkspaceUsageError(
            f"{config_path.as_posix()} payload.target_release must be `source-current` or a simple version string like 1.2.3."
        )
    return normalized


def _load_cli_compatibility_expectation(*, raw_cli_compatibility: Any, config_path: Path) -> tuple[CLICompatibilityExpectation, list[str]]:
    warnings: list[str] = []
    if raw_cli_compatibility is None:
        raw_cli_compatibility = {}
    if not isinstance(raw_cli_compatibility, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [cli_compatibility] section must be a table.")
    supported_fields = {
        "enforcement",
        "minimum_version",
        "exact_version",
        "source_classes",
        "target_relations",
        "command",
    }
    unknown = sorted(set(raw_cli_compatibility) - supported_fields)
    if unknown:
        warnings.append(f"{config_path.as_posix()} [cli_compatibility] contains unsupported field(s): {', '.join(unknown)}.")
    enforcement = validate_cli_compatibility_enforcement(str(raw_cli_compatibility.get("enforcement", "off")))
    source_classes = require_optional_string_list(
        payload=raw_cli_compatibility,
        key="source_classes",
        config_path=config_path,
        allowed=SUPPORTED_CLI_SOURCE_CLASSES,
    )
    target_relations = require_optional_string_list(
        payload=raw_cli_compatibility,
        key="target_relations",
        config_path=config_path,
        allowed=SUPPORTED_CLI_TARGET_RELATIONS,
    )
    command = raw_cli_compatibility.get("command")
    if command is not None and (not isinstance(command, str) or not command.strip()):
        raise WorkspaceUsageError(f"{config_path.as_posix()} cli_compatibility.command must be a non-empty string when present.")
    return (
        CLICompatibilityExpectation(
            enforcement=enforcement,
            enforcement_source="repo-config" if "enforcement" in raw_cli_compatibility else "product-default",
            minimum_version=_validate_version_string(
                value=raw_cli_compatibility.get("minimum_version"),
                field="minimum_version",
                config_path=config_path,
            ),
            exact_version=_validate_version_string(
                value=raw_cli_compatibility.get("exact_version"),
                field="exact_version",
                config_path=config_path,
            ),
            source_classes=source_classes,
            target_relations=target_relations,
            command=command.strip() if isinstance(command, str) else None,
            source="repo-config" if raw_cli_compatibility else "product-default",
        ),
        warnings,
    )


def _load_payload_target_config(*, raw_payload: Any, config_path: Path) -> tuple[PayloadTargetConfig, list[str]]:
    warnings: list[str] = []
    if raw_payload is None:
        raw_payload = {}
    if not isinstance(raw_payload, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [payload] section must be a table.")
    supported_fields = {
        "target_release",
        "minimum_capabilities",
        "policy",
        "dogfood_latest",
    }
    unknown = sorted(set(raw_payload) - supported_fields)
    if unknown:
        warnings.append(f"{config_path.as_posix()} [payload] contains unsupported field(s): {', '.join(unknown)}.")
    dogfood_latest = _require_bool(payload=raw_payload, key="dogfood_latest", default=False, config_path=config_path)
    target_release = _validate_payload_target_release(value=raw_payload.get("target_release"), config_path=config_path)
    if dogfood_latest and target_release is None:
        target_release = "source-current"
    return (
        PayloadTargetConfig(
            target_release=target_release,
            minimum_capabilities=require_optional_string_list(
                payload=raw_payload,
                key="minimum_capabilities",
                config_path=config_path,
            ),
            policy=require_optional_enum(
                payload=raw_payload,
                key="policy",
                config_path=config_path,
                allowed=SUPPORTED_PAYLOAD_TARGET_POLICIES,
                default="advisory",
            ),
            dogfood_latest=dogfood_latest,
            source="repo-config" if raw_payload else "product-default",
        ),
        warnings,
    )


def _require_bool(*, payload: dict[str, Any], key: str, default: bool, config_path: Path) -> bool:
    if key not in payload:
        return default
    value = payload[key]
    if not isinstance(value, bool):
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be true or false.")
    return value


def _require_disposition(
    *,
    payload: dict[str, Any],
    key: str,
    config_path: Path,
) -> AssuranceRequirementDisposition | None:
    if key not in payload:
        return None
    value = payload[key]
    if not isinstance(value, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be a table with reason and owner.")
    unknown = sorted(set(value) - {"reason", "owner"})
    if unknown:
        allowed = ", ".join(("reason", "owner"))
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} contains unsupported field(s): {', '.join(unknown)}; use {allowed}.")
    reason = require_optional_string(payload=value, key="reason", config_path=Path(f"{config_path.as_posix()} {key}"))
    owner = require_optional_string(payload=value, key="owner", config_path=Path(f"{config_path.as_posix()} {key}"))
    if reason is None or owner is None:
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} requires non-empty reason and owner.")
    return AssuranceRequirementDisposition(reason=reason, owner=owner)


def _load_assurance_requirements(
    *,
    raw_requirements: Any,
    config_path: Path,
) -> tuple[tuple[AssuranceRequirement, ...], list[str]]:
    warnings: list[str] = []
    if raw_requirements is None:
        raw_requirements = {}
    if not isinstance(raw_requirements, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [assurance.requirements] section must be a table.")
    requirements: list[AssuranceRequirement] = []
    supported_fields = {
        "level",
        "applies_to_paths",
        "applies_to_task_markers",
        "applies_to_planning_refs",
        "applies_to_proof_profiles",
        "applies_to_risk_refs",
        "applies_to_invariant_refs",
        "authority_refs",
        "required_evidence",
        "proof_profile",
        "workflow_obligation_refs",
        "review_owner",
        "force",
        "blocking_claims",
        "waiver",
        "dismissal",
        "notes",
    }
    activation_fields = {
        "applies_to_paths",
        "applies_to_task_markers",
        "applies_to_planning_refs",
        "applies_to_proof_profiles",
        "applies_to_risk_refs",
        "applies_to_invariant_refs",
    }
    for requirement_id, raw_requirement in sorted(raw_requirements.items()):
        requirement_path = Path(f"{config_path.as_posix()} assurance.requirements.{requirement_id}")
        if not isinstance(raw_requirement, dict):
            raise WorkspaceUsageError(f"{requirement_path.as_posix()} must be a table.")
        unknown_requirement = sorted(set(raw_requirement) - supported_fields)
        if unknown_requirement:
            warnings.append(f"{requirement_path.as_posix()} contains unsupported field(s): {', '.join(unknown_requirement)}.")
        activation_values = {
            key: require_optional_string_list(payload=raw_requirement, key=key, config_path=requirement_path) for key in activation_fields
        }
        if not any(activation_values.values()):
            allowed = ", ".join(sorted(activation_fields))
            raise WorkspaceUsageError(f"{requirement_path.as_posix()} requires at least one activation signal: {allowed}.")
        requirements.append(
            AssuranceRequirement(
                id=str(requirement_id).strip(),
                level=require_required_enum(
                    payload=raw_requirement,
                    key="level",
                    config_path=requirement_path,
                    allowed=SUPPORTED_ASSURANCE_LEVELS,
                ),
                applies_to_paths=activation_values["applies_to_paths"],
                applies_to_task_markers=activation_values["applies_to_task_markers"],
                applies_to_planning_refs=activation_values["applies_to_planning_refs"],
                applies_to_proof_profiles=activation_values["applies_to_proof_profiles"],
                applies_to_risk_refs=activation_values["applies_to_risk_refs"],
                applies_to_invariant_refs=activation_values["applies_to_invariant_refs"],
                authority_refs=require_optional_string_list(payload=raw_requirement, key="authority_refs", config_path=requirement_path),
                required_evidence=require_optional_string_list(
                    payload=raw_requirement, key="required_evidence", config_path=requirement_path
                ),
                proof_profile=require_optional_string(payload=raw_requirement, key="proof_profile", config_path=requirement_path),
                workflow_obligation_refs=require_optional_string_list(
                    payload=raw_requirement, key="workflow_obligation_refs", config_path=requirement_path
                ),
                review_owner=require_optional_string(payload=raw_requirement, key="review_owner", config_path=requirement_path),
                force=require_required_enum(
                    payload=raw_requirement,
                    key="force",
                    config_path=requirement_path,
                    allowed=SUPPORTED_WORKFLOW_OBLIGATION_FORCES,
                ),
                blocking_claims=require_optional_string_list(
                    payload=raw_requirement,
                    key="blocking_claims",
                    config_path=requirement_path,
                    allowed=SUPPORTED_ASSURANCE_REQUIREMENT_BLOCKING_CLAIMS,
                ),
                waiver=_require_disposition(payload=raw_requirement, key="waiver", config_path=requirement_path),
                dismissal=_require_disposition(payload=raw_requirement, key="dismissal", config_path=requirement_path),
                notes=require_optional_string(payload=raw_requirement, key="notes", config_path=requirement_path),
            )
        )
    return (tuple(requirement for requirement in requirements if requirement.id), warnings)


def _load_assurance_subsystem_profiles(
    *,
    raw_profiles: Any,
    config_path: Path,
) -> tuple[tuple[AssuranceSubsystemProfile, ...], list[str]]:
    warnings: list[str] = []
    if raw_profiles is None:
        raw_profiles = {}
    if not isinstance(raw_profiles, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [assurance.subsystem_profiles] section must be a table.")
    profiles: list[AssuranceSubsystemProfile] = []
    supported_fields = {
        "assurance_level",
        "level",
        "scope_refs",
        "requirement_refs",
        "required_evidence",
        "proof_profile",
        "workflow_obligation_refs",
        "review_owner",
        "force",
        "blocked_without_evidence",
        "claim_boundary",
        "notes",
    }
    for profile_id, raw_profile in sorted(raw_profiles.items()):
        profile_path = Path(f"{config_path.as_posix()} assurance.subsystem_profiles.{profile_id}")
        if not isinstance(raw_profile, dict):
            raise WorkspaceUsageError(f"{profile_path.as_posix()} must be a table.")
        unknown_profile = sorted(set(raw_profile) - supported_fields)
        if unknown_profile:
            warnings.append(f"{profile_path.as_posix()} contains unsupported field(s): {', '.join(unknown_profile)}.")
        level_value = raw_profile.get("assurance_level", raw_profile.get("level"))
        profiles.append(
            AssuranceSubsystemProfile(
                id=str(profile_id).strip(),
                assurance_level=require_required_enum(
                    payload={**raw_profile, "assurance_level": level_value},
                    key="assurance_level",
                    config_path=profile_path,
                    allowed=SUPPORTED_ASSURANCE_LEVELS,
                ),
                scope_refs=require_optional_string_list(payload=raw_profile, key="scope_refs", config_path=profile_path),
                requirement_refs=require_optional_string_list(payload=raw_profile, key="requirement_refs", config_path=profile_path),
                required_evidence=require_optional_string_list(payload=raw_profile, key="required_evidence", config_path=profile_path),
                proof_profile=require_optional_string(payload=raw_profile, key="proof_profile", config_path=profile_path),
                workflow_obligation_refs=require_optional_string_list(
                    payload=raw_profile, key="workflow_obligation_refs", config_path=profile_path
                ),
                review_owner=require_optional_string(payload=raw_profile, key="review_owner", config_path=profile_path),
                force=require_required_enum(
                    payload=raw_profile,
                    key="force",
                    config_path=profile_path,
                    allowed=SUPPORTED_WORKFLOW_OBLIGATION_FORCES,
                ),
                blocked_without_evidence=require_optional_string_list(
                    payload=raw_profile, key="blocked_without_evidence", config_path=profile_path
                ),
                claim_boundary=require_optional_string(payload=raw_profile, key="claim_boundary", config_path=profile_path),
                notes=require_optional_string(payload=raw_profile, key="notes", config_path=profile_path),
            )
        )
    return (tuple(profile for profile in profiles if profile.id), warnings)


def _load_assurance_domain_proof_lanes(
    *,
    raw_lanes: Any,
    config_path: Path,
) -> tuple[tuple[AssuranceDomainProofLane, ...], list[str]]:
    warnings: list[str] = []
    if raw_lanes is None:
        raw_lanes = {}
    if not isinstance(raw_lanes, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [assurance.domain_proof_lanes] section must be a table.")
    supported_fields = {
        "purpose",
        "applies_to_paths",
        "applies_to_task_markers",
        "commands",
        "manual_evidence",
        "review_aids",
        "evidence_concepts",
        "assurance_requirement_refs",
        "proof_profiles",
        "authority_refs",
        "escalation",
        "escalation_conditions",
        "claim_boundary",
        "owner",
        "route_role",
        "precedence",
        "allowed_composition",
        "notes",
    }
    lanes: list[AssuranceDomainProofLane] = []
    for lane_id, raw_lane in sorted(raw_lanes.items()):
        lane_path = Path(f"{config_path.as_posix()} assurance.domain_proof_lanes.{lane_id}")
        if not isinstance(raw_lane, dict):
            raise WorkspaceUsageError(f"{lane_path.as_posix()} must be a table.")
        unknown_lane = sorted(set(raw_lane) - supported_fields)
        if unknown_lane:
            warnings.append(f"{lane_path.as_posix()} contains unsupported field(s): {', '.join(unknown_lane)}.")
        applies_to_paths = require_optional_string_list(payload=raw_lane, key="applies_to_paths", config_path=lane_path)
        applies_to_task_markers = require_optional_string_list(payload=raw_lane, key="applies_to_task_markers", config_path=lane_path)
        if not (applies_to_paths or applies_to_task_markers):
            raise WorkspaceUsageError(
                f"{lane_path.as_posix()} requires applies_to_paths or applies_to_task_markers so matching is explicit."
            )
        commands = require_optional_string_list(payload=raw_lane, key="commands", config_path=lane_path)
        manual_evidence = require_optional_string_list(payload=raw_lane, key="manual_evidence", config_path=lane_path)
        review_aids = require_optional_string_list(payload=raw_lane, key="review_aids", config_path=lane_path)
        if not (commands or manual_evidence or review_aids):
            raise WorkspaceUsageError(f"{lane_path.as_posix()} requires commands, manual_evidence, or review_aids.")
        purpose = require_optional_string(payload=raw_lane, key="purpose", config_path=lane_path)
        if purpose is None:
            raise WorkspaceUsageError(f"{lane_path.as_posix()} purpose is required.")
        lanes.append(
            AssuranceDomainProofLane(
                id=str(lane_id).strip(),
                purpose=purpose,
                applies_to_paths=applies_to_paths,
                applies_to_task_markers=applies_to_task_markers,
                commands=commands,
                manual_evidence=manual_evidence,
                review_aids=review_aids,
                evidence_concepts=require_optional_string_list(payload=raw_lane, key="evidence_concepts", config_path=lane_path),
                assurance_requirement_refs=require_optional_string_list(
                    payload=raw_lane, key="assurance_requirement_refs", config_path=lane_path
                ),
                proof_profiles=require_optional_string_list(payload=raw_lane, key="proof_profiles", config_path=lane_path),
                authority_refs=require_optional_string_list(payload=raw_lane, key="authority_refs", config_path=lane_path),
                escalation=require_optional_string_list(payload=raw_lane, key="escalation", config_path=lane_path),
                escalation_conditions=require_optional_string_list(payload=raw_lane, key="escalation_conditions", config_path=lane_path),
                claim_boundary=require_optional_string(payload=raw_lane, key="claim_boundary", config_path=lane_path),
                owner=require_optional_string(payload=raw_lane, key="owner", config_path=lane_path),
                route_role=require_optional_string(payload=raw_lane, key="route_role", config_path=lane_path),
                precedence=require_optional_string(payload=raw_lane, key="precedence", config_path=lane_path),
                allowed_composition=require_optional_string_list(payload=raw_lane, key="allowed_composition", config_path=lane_path),
                notes=require_optional_string(payload=raw_lane, key="notes", config_path=lane_path),
            )
        )
    return (tuple(lane for lane in lanes if lane.id), warnings)


def _load_assurance_closeout_postures(
    *,
    raw_postures: Any,
    config_path: Path,
) -> tuple[tuple[AssuranceCloseoutPosture, ...], list[str]]:
    warnings: list[str] = []
    if raw_postures is None:
        raw_postures = {}
    if not isinstance(raw_postures, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [assurance.closeout_postures] section must be a table.")
    supported_fields = {
        "purpose",
        "applies_to_paths",
        "applies_to_task_markers",
        "assurance_requirement_refs",
        "proof_profiles",
        "required_evidence",
        "review_owner",
        "authority_refs",
        "claim_boundary",
        "uncertainty",
        "human_waiver_refs",
        "certification_limits",
        "notes",
    }
    activation_fields = {"applies_to_paths", "applies_to_task_markers", "assurance_requirement_refs", "proof_profiles"}
    postures: list[AssuranceCloseoutPosture] = []
    for posture_id, raw_posture in sorted(raw_postures.items()):
        posture_path = Path(f"{config_path.as_posix()} assurance.closeout_postures.{posture_id}")
        if not isinstance(raw_posture, dict):
            raise WorkspaceUsageError(f"{posture_path.as_posix()} must be a table.")
        unknown_posture = sorted(set(raw_posture) - supported_fields)
        if unknown_posture:
            warnings.append(f"{posture_path.as_posix()} contains unsupported field(s): {', '.join(unknown_posture)}.")
        activation_values = {
            key: require_optional_string_list(payload=raw_posture, key=key, config_path=posture_path) for key in activation_fields
        }
        if not any(activation_values.values()):
            allowed = ", ".join(sorted(activation_fields))
            raise WorkspaceUsageError(f"{posture_path.as_posix()} requires at least one activation signal: {allowed}.")
        purpose = require_optional_string(payload=raw_posture, key="purpose", config_path=posture_path)
        if purpose is None:
            raise WorkspaceUsageError(f"{posture_path.as_posix()} purpose is required.")
        postures.append(
            AssuranceCloseoutPosture(
                id=str(posture_id).strip(),
                purpose=purpose,
                applies_to_paths=activation_values["applies_to_paths"],
                applies_to_task_markers=activation_values["applies_to_task_markers"],
                assurance_requirement_refs=activation_values["assurance_requirement_refs"],
                proof_profiles=activation_values["proof_profiles"],
                required_evidence=require_optional_string_list(payload=raw_posture, key="required_evidence", config_path=posture_path),
                review_owner=require_optional_string(payload=raw_posture, key="review_owner", config_path=posture_path),
                authority_refs=require_optional_string_list(payload=raw_posture, key="authority_refs", config_path=posture_path),
                claim_boundary=require_optional_string(payload=raw_posture, key="claim_boundary", config_path=posture_path),
                uncertainty=require_optional_string(payload=raw_posture, key="uncertainty", config_path=posture_path),
                human_waiver_refs=require_optional_string_list(payload=raw_posture, key="human_waiver_refs", config_path=posture_path),
                certification_limits=require_optional_string_list(
                    payload=raw_posture, key="certification_limits", config_path=posture_path
                ),
                notes=require_optional_string(payload=raw_posture, key="notes", config_path=posture_path),
            )
        )
    return (tuple(posture for posture in postures if posture.id), warnings)


def _load_assurance_config(*, raw_assurance: Any, config_path: Path) -> tuple[AssuranceConfig, list[str]]:
    warnings: list[str] = []
    if raw_assurance is None:
        raw_assurance = {}
    if not isinstance(raw_assurance, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [assurance] section must be a table.")
    supported_fields = {
        "default_level",
        "agent_may_escalate",
        "agent_may_deescalate",
        "strict_closeout",
        "proof_profiles",
        "requirements",
        "subsystem_profiles",
        "domain_proof_lanes",
        "closeout_postures",
        "test_data_policy",
        "decision_record_target",
        "decision_record_format",
        "decision_record_template",
        "decision_record_statuses",
        "invariant_registry",
        "risk_registry",
    }
    unknown = sorted(set(raw_assurance) - supported_fields)
    if unknown:
        warnings.append(f"{config_path.as_posix()} [assurance] contains unsupported field(s): {', '.join(unknown)}.")
    default_level_source = "repo-config" if "default_level" in raw_assurance else "product-default"
    default_level = validate_assurance_level(str(raw_assurance.get("default_level", DEFAULT_ASSURANCE_LEVEL)))
    raw_profiles = raw_assurance.get("proof_profiles", {})
    if raw_profiles is None:
        raw_profiles = {}
    if not isinstance(raw_profiles, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [assurance.proof_profiles] section must be a table.")
    profiles: list[AssuranceProofProfile] = []
    for profile_id, profile_payload in sorted(raw_profiles.items()):
        if not isinstance(profile_payload, dict):
            raise WorkspaceUsageError(f"{config_path.as_posix()} [assurance.proof_profiles.{profile_id}] must be a table.")
        unknown_profile = sorted(set(profile_payload) - {"required_commands", "optional_commands", "review_aids", "disallowed_commands"})
        if unknown_profile:
            warnings.append(
                f"{config_path.as_posix()} [assurance.proof_profiles.{profile_id}] contains unsupported field(s): {', '.join(unknown_profile)}."
            )
        profiles.append(
            AssuranceProofProfile(
                id=str(profile_id).strip(),
                required_commands=require_optional_string_list(payload=profile_payload, key="required_commands", config_path=config_path),
                optional_commands=require_optional_string_list(payload=profile_payload, key="optional_commands", config_path=config_path),
                review_aids=require_optional_string_list(payload=profile_payload, key="review_aids", config_path=config_path),
                disallowed_commands=require_optional_string_list(
                    payload=profile_payload, key="disallowed_commands", config_path=config_path
                ),
            )
        )
    raw_test_data_policy = raw_assurance.get("test_data_policy", {})
    if raw_test_data_policy is None:
        raw_test_data_policy = {}
    if not isinstance(raw_test_data_policy, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [assurance.test_data_policy] section must be a table.")
    decision_record_target = raw_assurance.get("decision_record_target")
    decision_record_format = raw_assurance.get("decision_record_format")
    decision_record_template = raw_assurance.get("decision_record_template")
    invariant_registry = raw_assurance.get("invariant_registry")
    risk_registry = raw_assurance.get("risk_registry")
    requirements, requirement_warnings = _load_assurance_requirements(
        raw_requirements=raw_assurance.get("requirements", {}),
        config_path=config_path,
    )
    warnings.extend(requirement_warnings)
    subsystem_profiles, subsystem_profile_warnings = _load_assurance_subsystem_profiles(
        raw_profiles=raw_assurance.get("subsystem_profiles", {}),
        config_path=config_path,
    )
    warnings.extend(subsystem_profile_warnings)
    domain_proof_lanes, domain_lane_warnings = _load_assurance_domain_proof_lanes(
        raw_lanes=raw_assurance.get("domain_proof_lanes", {}),
        config_path=config_path,
    )
    warnings.extend(domain_lane_warnings)
    closeout_postures, closeout_posture_warnings = _load_assurance_closeout_postures(
        raw_postures=raw_assurance.get("closeout_postures", {}),
        config_path=config_path,
    )
    warnings.extend(closeout_posture_warnings)
    return (
        AssuranceConfig(
            default_level=default_level,
            default_level_source=default_level_source,
            agent_may_escalate=_require_bool(payload=raw_assurance, key="agent_may_escalate", default=True, config_path=config_path),
            agent_may_deescalate=_require_bool(payload=raw_assurance, key="agent_may_deescalate", default=False, config_path=config_path),
            strict_closeout=_require_bool(payload=raw_assurance, key="strict_closeout", default=False, config_path=config_path),
            proof_profiles=tuple(profile for profile in profiles if profile.id),
            requirements=requirements,
            subsystem_profiles=subsystem_profiles,
            domain_proof_lanes=domain_proof_lanes,
            closeout_postures=closeout_postures,
            test_data_policy={str(key): value for key, value in raw_test_data_policy.items()},
            decision_record_target=str(decision_record_target).strip() if decision_record_target is not None else None,
            decision_record_format=str(decision_record_format).strip() if decision_record_format is not None else None,
            decision_record_template=str(decision_record_template).strip() if decision_record_template is not None else None,
            decision_record_statuses=require_optional_string_list(
                payload=raw_assurance, key="decision_record_statuses", config_path=config_path
            ),
            invariant_registry=str(invariant_registry).strip() if invariant_registry is not None else None,
            risk_registry=str(risk_registry).strip() if risk_registry is not None else None,
        ),
        warnings,
    )


def load_workflow_obligations(
    *,
    raw_obligations: dict[str, Any],
    config_path: Path,
) -> tuple[tuple[WorkflowObligation, ...], list[str]]:
    obligations: list[WorkflowObligation] = []
    warnings: list[str] = []
    for obligation_name in sorted(raw_obligations):
        raw_obligation = raw_obligations[obligation_name]
        obligation_path = Path(f"{config_path.as_posix()} workflow_obligations.{obligation_name}")
        if not isinstance(raw_obligation, dict):
            raise WorkspaceUsageError(f"{obligation_path.as_posix()} must be a table.")
        unknown_fields = sorted(set(raw_obligation) - {"summary", "stage", "force", "scope_tags", "commands", "review_hint"})
        if unknown_fields:
            unknown_text = ", ".join(unknown_fields)
            warnings.append(f"{obligation_path.as_posix()} contains unsupported field(s): {unknown_text}.")
        summary = raw_obligation.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            raise WorkspaceUsageError(f"{obligation_path.as_posix()} summary must be a non-empty string.")
        stage = raw_obligation.get("stage")
        if not isinstance(stage, str) or stage not in SUPPORTED_WORKFLOW_OBLIGATION_STAGES:
            allowed_text = ", ".join(SUPPORTED_WORKFLOW_OBLIGATION_STAGES)
            raise WorkspaceUsageError(f"{obligation_path.as_posix()} stage must be one of: {allowed_text}.")
        force = raw_obligation.get("force")
        if force is None:
            force = "required-before-closeout" if stage in {"before-claiming-completion", "closeout"} else "recommended"
        if not isinstance(force, str) or force not in SUPPORTED_WORKFLOW_OBLIGATION_FORCES:
            allowed_text = ", ".join(SUPPORTED_WORKFLOW_OBLIGATION_FORCES)
            raise WorkspaceUsageError(f"{obligation_path.as_posix()} force must be one of: {allowed_text}.")
        scope_tags = require_optional_string_list(
            payload=raw_obligation,
            key="scope_tags",
            config_path=obligation_path,
        )
        if not scope_tags:
            raise WorkspaceUsageError(f"{obligation_path.as_posix()} scope_tags must list at least one non-empty string.")
        commands = require_optional_string_list(
            payload=raw_obligation,
            key="commands",
            config_path=obligation_path,
        )
        if not commands:
            raise WorkspaceUsageError(f"{obligation_path.as_posix()} commands must list at least one non-empty string.")
        review_hint = raw_obligation.get("review_hint")
        if review_hint is not None and (not isinstance(review_hint, str) or not review_hint.strip()):
            raise WorkspaceUsageError(f"{obligation_path.as_posix()} review_hint must be a non-empty string when present.")
        obligations.append(
            WorkflowObligation(
                name=obligation_name,
                summary=summary.strip(),
                stage=stage,
                force=force,
                scope_tags=scope_tags,
                commands=commands,
                review_hint=review_hint.strip() if isinstance(review_hint, str) else None,
            )
        )
    return tuple(obligations), warnings


def resolve_system_intent_declaration(
    *,
    target_root: Path,
    raw_system_intent: dict[str, Any] | None,
    config_path: Path,
) -> tuple[SystemIntentDeclaration, list[str]]:
    warnings: list[str] = []
    payload = raw_system_intent or {}
    if not isinstance(payload, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [system_intent] section must be a table.")

    unknown_fields = sorted(set(payload) - {"sources", "preferred_source"})
    if unknown_fields:
        unknown_text = ", ".join(unknown_fields)
        warnings.append(f"{config_path.as_posix()} [system_intent] contains unsupported field(s): {unknown_text}.")

    configured_sources = require_optional_string_list(
        payload=payload,
        key="sources",
        config_path=config_path,
    )
    if configured_sources:
        sources = configured_sources
        sources_source = "repo-config"
    else:
        detected_sources = tuple(path.as_posix() for path in SYSTEM_INTENT_SOURCE_DISCOVERY_CANDIDATES if (target_root / path).exists())
        sources = detected_sources
        sources_source = "autodetected-existing" if detected_sources else "product-default"

    raw_preferred_source = payload.get("preferred_source")
    if raw_preferred_source is not None:
        if not isinstance(raw_preferred_source, str) or not raw_preferred_source.strip():
            raise WorkspaceUsageError(f"{config_path.as_posix()} system_intent.preferred_source must be a non-empty string.")
        preferred_source = raw_preferred_source.strip()
        preferred_source_source = "repo-config"
    else:
        preferred_source = sources[0] if sources else None
        preferred_source_source = sources_source

    if preferred_source and sources and preferred_source not in sources:
        raise WorkspaceUsageError(
            f"{config_path.as_posix()} system_intent.preferred_source must be one of the declared system_intent.sources."
        )

    return (
        SystemIntentDeclaration(
            sources=sources,
            sources_source=sources_source,
            preferred_source=preferred_source,
            preferred_source_source=preferred_source_source,
        ),
        warnings,
    )


def resolve_effective_agent_instructions_file(*, target_root: Path, configured: str | None) -> tuple[str, str, tuple[str, ...]]:
    detected = tuple(filename for filename in SUPPORTED_AGENT_INSTRUCTIONS_FILES if (target_root / filename).exists())
    if configured:
        return configured, "repo-config", detected
    if detected:
        return detected[0], "autodetected-existing", detected
    return DEFAULT_AGENT_INSTRUCTIONS_FILE, "product-default", detected


def load_delegation_target_profiles(
    *, raw_targets: dict[str, Any], config_path: Path
) -> tuple[tuple[DelegationTargetProfile, ...], list[str]]:
    profiles: list[DelegationTargetProfile] = []
    warnings: list[str] = []
    for target_name in sorted(raw_targets):
        raw_profile = raw_targets[target_name]
        target_path = Path(f"{config_path.as_posix()} delegation_targets.{target_name}")
        if not isinstance(raw_profile, dict):
            raise WorkspaceUsageError(f"{target_path.as_posix()} must be a table.")
        supported_fields = {
            "strength",
            "location",
            "confidence",
            "task_fit",
            "capability_classes",
            "execution_methods",
            "model_family",
            "provider",
            "context_capacity",
            "reasoning_profile",
            "cost_class",
            "latency_class",
            "safe_task_classes",
            "forbidden_task_classes",
            "escalation_target",
            "confidence_source",
            "last_evaluation",
            "human_control_modes",
        }
        unknown_fields = sorted(set(raw_profile) - supported_fields)
        if unknown_fields:
            unknown_text = ", ".join(unknown_fields)
            warnings.append(f"{target_path.as_posix()} contains unsupported field(s): {unknown_text}.")

        strength = raw_profile.get("strength")
        if not isinstance(strength, str) or strength not in SUPPORTED_DELEGATION_TARGET_STRENGTHS:
            allowed_text = ", ".join(SUPPORTED_DELEGATION_TARGET_STRENGTHS)
            raise WorkspaceUsageError(f"{target_path.as_posix()} strength must be one of: {allowed_text}.")
        raw_location = str(raw_profile.get("location", "either")).strip() or "either"
        if raw_location not in SUPPORTED_CAPABILITY_LOCATIONS:
            allowed_text = ", ".join(SUPPORTED_CAPABILITY_LOCATIONS)
            raise WorkspaceUsageError(f"{target_path.as_posix()} location must be one of: {allowed_text}.")
        execution_methods = require_optional_string_list(
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
                location=raw_location,
                execution_methods=execution_methods,
                confidence=require_optional_confidence(
                    payload=raw_profile,
                    key="confidence",
                    config_path=target_path,
                ),
                task_fit=require_optional_string_list(
                    payload=raw_profile,
                    key="task_fit",
                    config_path=target_path,
                ),
                capability_classes=require_optional_string_list(
                    payload=raw_profile,
                    key="capability_classes",
                    config_path=target_path,
                    allowed=SUPPORTED_CAPABILITY_EXECUTION_CLASSES,
                ),
                model_family=require_optional_string(payload=raw_profile, key="model_family", config_path=target_path),
                provider=require_optional_string(payload=raw_profile, key="provider", config_path=target_path),
                context_capacity=require_optional_enum(
                    payload=raw_profile,
                    key="context_capacity",
                    config_path=target_path,
                    allowed=SUPPORTED_DELEGATION_TARGET_CONTEXT_CAPACITIES,
                    default="unknown",
                ),
                reasoning_profile=require_optional_enum(
                    payload=raw_profile,
                    key="reasoning_profile",
                    config_path=target_path,
                    allowed=SUPPORTED_DELEGATION_TARGET_REASONING_PROFILES,
                    default="unknown",
                ),
                cost_class=require_optional_enum(
                    payload=raw_profile,
                    key="cost_class",
                    config_path=target_path,
                    allowed=SUPPORTED_DELEGATION_TARGET_COST_CLASSES,
                    default="unknown",
                ),
                latency_class=require_optional_enum(
                    payload=raw_profile,
                    key="latency_class",
                    config_path=target_path,
                    allowed=SUPPORTED_DELEGATION_TARGET_LATENCY_CLASSES,
                    default="unknown",
                ),
                safe_task_classes=require_optional_string_list(
                    payload=raw_profile,
                    key="safe_task_classes",
                    config_path=target_path,
                    allowed=SUPPORTED_CAPABILITY_EXECUTION_CLASSES,
                ),
                forbidden_task_classes=require_optional_string_list(
                    payload=raw_profile,
                    key="forbidden_task_classes",
                    config_path=target_path,
                    allowed=SUPPORTED_CAPABILITY_EXECUTION_CLASSES,
                ),
                escalation_target=require_optional_string(payload=raw_profile, key="escalation_target", config_path=target_path),
                confidence_source=require_optional_string(payload=raw_profile, key="confidence_source", config_path=target_path),
                last_evaluation=require_optional_string(payload=raw_profile, key="last_evaluation", config_path=target_path),
                human_control_modes=require_optional_string_list(
                    payload=raw_profile,
                    key="human_control_modes",
                    config_path=target_path,
                    allowed=SUPPORTED_DELEGATION_CONTROL_MODES,
                ),
            )
        )
    return tuple(profiles), warnings


def normalize_delegation_outcome_record(raw: Any, *, surface_name: str) -> DelegationOutcomeRecord:
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


def load_delegation_outcomes(*, target_root: Path) -> tuple[Path, dict[str, Any], tuple[DelegationOutcomeRecord, ...]]:
    path = target_root / WORKSPACE_DELEGATION_OUTCOMES_PATH
    if not path.exists():
        legacy_path = target_root / LEGACY_WORKSPACE_DELEGATION_OUTCOMES_PATH
        if legacy_path.exists():
            path = legacy_path
    if not path.exists():
        return path, {"kind": DELEGATION_OUTCOMES_KIND, "records": []}, ()
    payload = load_json_payload(path=path, surface_name=WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix())
    if payload.get("kind") != DELEGATION_OUTCOMES_KIND:
        raise WorkspaceUsageError(f"{WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix()} must set kind to {DELEGATION_OUTCOMES_KIND}.")
    raw_records = payload.get("records", [])
    if not isinstance(raw_records, list):
        raise WorkspaceUsageError(f"{WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix()} records must be a list.")
    records = tuple(
        normalize_delegation_outcome_record(raw_record, surface_name=WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix())
        for raw_record in raw_records
    )
    return path, payload, records


def write_delegation_outcomes(*, path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(serialise_value(payload), indent=2) + "\n", encoding="utf-8")


def empty_mixed_agent_local_override(*, path: Path | None, exists: bool) -> MixedAgentLocalOverride:
    return MixedAgentLocalOverride(
        path=path,
        exists=exists,
        applied=False,
        shared_config_path=None,
        shared_config_exists=False,
        shared_config_applied=False,
        enabled=None,
        cli_invoke=None,
        maintainer_mode=None,
        supports_internal_delegation=None,
        strong_planner_available=None,
        cheap_bounded_executor_available=None,
        prefer_internal_delegation_when_available=None,
        safe_to_auto_run_commands=None,
        requires_human_verification_on_pr=None,
        delegation_mode=None,
        execution_role=None,
        assignment_policy=None,
        selection_objective=None,
        current_target=None,
        underfit_behavior=None,
        down_routing_behavior=None,
        human_override_policy=None,
        manual_transport_policy=None,
        clarification_mode=None,
        local_memory_enabled=None,
        local_memory_path=WORKSPACE_LOCAL_MEMORY_DEFAULT_PATH,
        session_logging=SessionLoggingConfig(enabled=None, redact_local_paths=False, path_mode="absolute", source="unset"),
        delegation_targets=(),
        local_overlay={},
        high_risk_overlay={},
        field_sources={},
    )


def _merge_local_config_payloads(*, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_local_config_payloads(base=merged[key], override=value)
        else:
            merged[key] = value
    return merged


def _local_config_table(payload: dict[str, Any] | None, table: str) -> dict[str, Any]:
    if not payload:
        return {}
    value = payload.get(table, {})
    return value if isinstance(value, dict) else {}


def _local_config_field_source(
    *,
    local_payload: dict[str, Any],
    shared_payload: dict[str, Any] | None,
    table: str,
    key: str,
) -> str:
    if key in _local_config_table(local_payload, table):
        return "local-override"
    if key in _local_config_table(shared_payload, table):
        return "shared-local-config"
    return "unset"


def _local_config_nested_source(
    *,
    local_payload: dict[str, Any],
    shared_payload: dict[str, Any] | None,
    table: str,
    section: str,
    item_id: str,
) -> str:
    if item_id in _local_config_table(_local_config_table(local_payload, table), section):
        return "repo-local-override"
    if item_id in _local_config_table(_local_config_table(shared_payload, table), section):
        return "shared-local-config"
    return "merged-local-config"


def _local_overlay_high_risk_source(
    *, local_payload: dict[str, Any], shared_payload: dict[str, Any] | None, section: str, item_id: str
) -> str:
    local_overlay = _local_config_table(local_payload, "local_overlay")
    shared_overlay = _local_config_table(shared_payload, "local_overlay")
    if item_id in _local_config_table(_local_config_table(local_overlay, "high_risk"), section):
        return "repo-local-override"
    if item_id in _local_config_table(_local_config_table(shared_overlay, "high_risk"), section):
        return "shared-local-config"
    return "merged-local-config"


def _optional_overlay_string_list(*, payload: dict[str, Any], key: str, item_path: Path, warnings: list[str]) -> tuple[str, ...]:
    try:
        return require_optional_string_list(payload=payload, key=key, config_path=item_path)
    except WorkspaceUsageError as exc:
        warnings.append(str(exc))
        return ()


def _optional_overlay_string(*, payload: dict[str, Any], key: str, item_path: Path, warnings: list[str]) -> str | None:
    try:
        return require_optional_string(payload=payload, key=key, config_path=item_path)
    except WorkspaceUsageError as exc:
        warnings.append(str(exc))
        return None


def _optional_overlay_enum(
    *, payload: dict[str, Any], key: str, item_path: Path, allowed: tuple[str, ...], default: str, warnings: list[str]
) -> str:
    try:
        return require_optional_enum(payload=payload, key=key, config_path=item_path, allowed=allowed, default=default)
    except WorkspaceUsageError as exc:
        warnings.append(str(exc))
        return default


def _normalize_local_guidance_overlay(
    *,
    raw_guidance: Any,
    local_payload: dict[str, Any],
    shared_payload: dict[str, Any] | None,
    warnings: list[str],
) -> dict[str, Any]:
    allowed_fields = {
        "applies_to_paths",
        "applies_to_task_markers",
        "signal",
        "category",
        "guidance",
        "authority_refs",
        "required_commands",
        "optional_commands",
        "unavailable_routes",
        "review_owner",
        "claim_boundary",
        "impact",
        "notes",
    }
    if raw_guidance in (None, {}):
        return {"status": "absent", "items": [], "warnings": []}
    if not isinstance(raw_guidance, dict):
        message = f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} local_overlay.guidance must be a table of named items."
        warnings.append(message)
        return {"status": "invalid", "items": [], "warnings": [message]}
    guidance_warnings: list[str] = []
    items: list[dict[str, Any]] = []
    for item_id, raw_item in sorted(raw_guidance.items()):
        item_path = Path(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} local_overlay.guidance.{item_id}")
        if not isinstance(raw_item, dict):
            message = f"{item_path.as_posix()} must be a table."
            warnings.append(message)
            guidance_warnings.append(message)
            continue
        raw_item = dict(raw_item)
        unknown_fields = sorted(set(raw_item) - allowed_fields)
        if unknown_fields:
            message = f"{item_path.as_posix()} contains unsupported field(s): {', '.join(unknown_fields)}."
            warnings.append(message)
            guidance_warnings.append(message)
        items.append(
            {
                "id": str(item_id).strip(),
                "section": "guidance",
                "source_layer": _local_config_nested_source(
                    local_payload=local_payload,
                    shared_payload=shared_payload,
                    table="local_overlay",
                    section="guidance",
                    item_id=str(item_id),
                ),
                "surface": f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [local_overlay.guidance.{item_id}]",
                "applies_to_paths": list(
                    _optional_overlay_string_list(payload=raw_item, key="applies_to_paths", item_path=item_path, warnings=guidance_warnings)
                ),
                "applies_to_task_markers": list(
                    _optional_overlay_string_list(
                        payload=raw_item, key="applies_to_task_markers", item_path=item_path, warnings=guidance_warnings
                    )
                ),
                "signal": _optional_overlay_string(payload=raw_item, key="signal", item_path=item_path, warnings=guidance_warnings),
                "category": _optional_overlay_string(payload=raw_item, key="category", item_path=item_path, warnings=guidance_warnings),
                "guidance": _optional_overlay_string(payload=raw_item, key="guidance", item_path=item_path, warnings=guidance_warnings),
                "authority_refs": list(
                    _optional_overlay_string_list(payload=raw_item, key="authority_refs", item_path=item_path, warnings=guidance_warnings)
                ),
                "required_commands": list(
                    _optional_overlay_string_list(
                        payload=raw_item, key="required_commands", item_path=item_path, warnings=guidance_warnings
                    )
                ),
                "optional_commands": list(
                    _optional_overlay_string_list(
                        payload=raw_item, key="optional_commands", item_path=item_path, warnings=guidance_warnings
                    )
                ),
                "unavailable_routes": list(
                    _optional_overlay_string_list(
                        payload=raw_item, key="unavailable_routes", item_path=item_path, warnings=guidance_warnings
                    )
                ),
                "review_owner": _optional_overlay_string(
                    payload=raw_item, key="review_owner", item_path=item_path, warnings=guidance_warnings
                ),
                "claim_boundary": _optional_overlay_string(
                    payload=raw_item, key="claim_boundary", item_path=item_path, warnings=guidance_warnings
                ),
                "impact": _optional_overlay_enum(
                    payload=raw_item,
                    key="impact",
                    item_path=item_path,
                    allowed=SUPPORTED_LOCAL_HIGH_RISK_IMPACTS,
                    default="advisory",
                    warnings=guidance_warnings,
                ),
                "notes": _optional_overlay_string(payload=raw_item, key="notes", item_path=item_path, warnings=guidance_warnings),
            }
        )
    return {"status": "configured" if items else "absent", "items": items, "warnings": guidance_warnings}


def _normalize_local_high_risk_overlay(
    *,
    raw_overlay: Any,
    local_payload: dict[str, Any],
    shared_payload: dict[str, Any] | None,
    warnings: list[str],
    surface_prefix: str = "high_risk_overlay",
) -> dict[str, Any]:
    if raw_overlay in (None, {}):
        return {
            "kind": "agentic-workspace/local-high-risk-overlay-config/v1",
            "status": "absent",
            "sections": {},
            "warnings": [],
        }
    if not isinstance(raw_overlay, dict):
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [{surface_prefix}] section must be a table.")
        return {
            "kind": "agentic-workspace/local-high-risk-overlay-config/v1",
            "status": "invalid",
            "sections": {},
            "warnings": [f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [{surface_prefix}] section must be a table."],
        }
    section_fields = {
        "source_maps": {
            "applies_to_paths",
            "applies_to_task_markers",
            "authority_refs",
            "required_sources",
            "review_owner",
            "review_aids",
            "proof_profiles",
            "required_commands",
            "manual_evidence",
            "claim_boundary",
            "drift_state",
            "impact",
            "notes",
        },
        "validation_profiles": {
            "category",
            "applies_to_paths",
            "applies_to_task_markers",
            "required_commands",
            "optional_commands",
            "manual_checks",
            "unavailable_routes",
            "claim_boundary",
            "proof_profiles",
            "authority_refs",
            "impact",
            "notes",
        },
        "ci_validation": {
            "applies_to_paths",
            "applies_to_task_markers",
            "validation_state",
            "local_substitute_commands",
            "local_substitute_policy",
            "authority_refs",
            "claim_boundary",
            "impact",
            "notes",
        },
        "templates": {
            "applies_to_task_markers",
            "host",
            "kind",
            "paths",
            "headings",
            "required_fields",
            "state",
            "impact",
            "notes",
        },
        "guardrails": {
            "applies_to_paths",
            "applies_to_task_markers",
            "sensitive_data",
            "synthetic_fixture_guidance",
            "safe_examples",
            "authority_refs",
            "claim_boundary",
            "impact",
            "notes",
        },
        "unresolved_questions": {
            "applies_to_paths",
            "applies_to_task_markers",
            "category",
            "question",
            "owner",
            "residue_route",
            "reason",
            "authority_refs",
            "claim_boundary",
            "impact",
            "notes",
        },
    }
    unknown_sections = sorted(set(raw_overlay) - set(section_fields))
    if unknown_sections:
        warnings.append(
            f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [{surface_prefix}] contains unsupported section(s): {', '.join(unknown_sections)}."
        )
    overlay_warnings: list[str] = []
    sections: dict[str, list[dict[str, Any]]] = {}
    for section, allowed_fields in section_fields.items():
        raw_section = raw_overlay.get(section, {})
        if raw_section in (None, {}):
            sections[section] = []
            continue
        if not isinstance(raw_section, dict):
            message = f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} {surface_prefix}.{section} must be a table of named items."
            warnings.append(message)
            overlay_warnings.append(message)
            sections[section] = []
            continue
        items: list[dict[str, Any]] = []
        for item_id, raw_item in sorted(raw_section.items()):
            item_path = Path(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} {surface_prefix}.{section}.{item_id}")
            if not isinstance(raw_item, dict):
                message = f"{item_path.as_posix()} must be a table."
                warnings.append(message)
                overlay_warnings.append(message)
                continue
            raw_item = dict(raw_item)
            unknown_fields = sorted(set(raw_item) - allowed_fields)
            if unknown_fields:
                message = f"{item_path.as_posix()} contains unsupported field(s): {', '.join(unknown_fields)}."
                warnings.append(message)
                overlay_warnings.append(message)
            item: dict[str, Any] = {
                "id": str(item_id).strip(),
                "section": section,
                "source_layer": _local_config_nested_source(
                    local_payload=local_payload,
                    shared_payload=shared_payload,
                    table="high_risk_overlay",
                    section=section,
                    item_id=str(item_id),
                )
                if surface_prefix == "high_risk_overlay"
                else _local_overlay_high_risk_source(
                    local_payload=local_payload,
                    shared_payload=shared_payload,
                    section=section,
                    item_id=str(item_id),
                ),
                "surface": f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [{surface_prefix}.{section}.{item_id}]",
                "applies_to_paths": list(
                    _optional_overlay_string_list(payload=raw_item, key="applies_to_paths", item_path=item_path, warnings=overlay_warnings)
                ),
                "applies_to_task_markers": list(
                    _optional_overlay_string_list(
                        payload=raw_item, key="applies_to_task_markers", item_path=item_path, warnings=overlay_warnings
                    )
                ),
                "authority_refs": list(
                    _optional_overlay_string_list(payload=raw_item, key="authority_refs", item_path=item_path, warnings=overlay_warnings)
                ),
                "claim_boundary": _optional_overlay_string(
                    payload=raw_item, key="claim_boundary", item_path=item_path, warnings=overlay_warnings
                ),
                "impact": _optional_overlay_enum(
                    payload=raw_item,
                    key="impact",
                    item_path=item_path,
                    allowed=SUPPORTED_LOCAL_HIGH_RISK_IMPACTS,
                    default="advisory",
                    warnings=overlay_warnings,
                ),
                "notes": _optional_overlay_string(payload=raw_item, key="notes", item_path=item_path, warnings=overlay_warnings),
            }
            for key in (
                "required_sources",
                "review_aids",
                "proof_profiles",
                "required_commands",
                "manual_evidence",
                "optional_commands",
                "manual_checks",
                "unavailable_routes",
                "local_substitute_commands",
                "paths",
                "headings",
                "required_fields",
                "sensitive_data",
                "synthetic_fixture_guidance",
                "safe_examples",
            ):
                if key in allowed_fields:
                    item[key] = list(
                        _optional_overlay_string_list(payload=raw_item, key=key, item_path=item_path, warnings=overlay_warnings)
                    )
            for key in (
                "review_owner",
                "drift_state",
                "category",
                "validation_state",
                "local_substitute_policy",
                "host",
                "kind",
                "state",
                "question",
                "owner",
                "residue_route",
                "reason",
            ):
                if key in allowed_fields:
                    item[key] = _optional_overlay_string(payload=raw_item, key=key, item_path=item_path, warnings=overlay_warnings)
            if section == "ci_validation" and item.get("validation_state") not in (None, ""):
                item["validation_state"] = _optional_overlay_enum(
                    payload=raw_item,
                    key="validation_state",
                    item_path=item_path,
                    allowed=SUPPORTED_LOCAL_HIGH_RISK_VALIDATION_STATES,
                    default="ci_unavailable",
                    warnings=overlay_warnings,
                )
            if section == "ci_validation" and item.get("local_substitute_policy") not in (None, ""):
                item["local_substitute_policy"] = _optional_overlay_enum(
                    payload=raw_item,
                    key="local_substitute_policy",
                    item_path=item_path,
                    allowed=SUPPORTED_LOCAL_HIGH_RISK_SUBSTITUTE_POLICIES,
                    default="insufficient",
                    warnings=overlay_warnings,
                )
            if section == "unresolved_questions" and item.get("category") not in (None, ""):
                item["category"] = _optional_overlay_enum(
                    payload=raw_item,
                    key="category",
                    item_path=item_path,
                    allowed=SUPPORTED_LOCAL_HIGH_RISK_UNRESOLVED_CLASSES,
                    default="safe-follow-up",
                    warnings=overlay_warnings,
                )
            items.append(item)
        sections[section] = items
    item_count = sum(len(items) for items in sections.values())
    return {
        "kind": "agentic-workspace/local-high-risk-overlay-config/v1",
        "status": "configured" if item_count else "absent",
        "item_count": item_count,
        "sections": sections,
        "warnings": overlay_warnings,
        "authority_boundary": {
            "source": "local-only-overlay",
            "rule": "Local high-risk overlay guidance may shape the acting checkout workflow, but it is not checked-in host policy.",
        },
    }


def _normalize_local_overlay(
    *,
    raw_overlay: Any,
    legacy_high_risk_overlay: Any,
    local_payload: dict[str, Any],
    shared_payload: dict[str, Any] | None,
    warnings: list[str],
) -> dict[str, Any]:
    overlay_warnings: list[str] = []
    if raw_overlay in (None, {}):
        raw_overlay = {}
    if not isinstance(raw_overlay, dict):
        message = f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [local_overlay] section must be a table."
        warnings.append(message)
        overlay_warnings.append(message)
        raw_overlay = {}
    unknown_sections = sorted(set(raw_overlay) - {"guidance", "high_risk"})
    if unknown_sections:
        message = (
            f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [local_overlay] contains unsupported section(s): {', '.join(unknown_sections)}."
        )
        warnings.append(message)
        overlay_warnings.append(message)
    if legacy_high_risk_overlay not in (None, {}):
        message = (
            f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [high_risk_overlay] is deprecated; "
            "use [local_overlay.high_risk] so high-risk workflow guidance consumes the general local overlay substrate."
        )
        warnings.append(message)
        overlay_warnings.append(message)
    guidance = _normalize_local_guidance_overlay(
        raw_guidance=raw_overlay.get("guidance", {}),
        local_payload=local_payload,
        shared_payload=shared_payload,
        warnings=warnings,
    )
    raw_high_risk = raw_overlay.get("high_risk", {})
    if raw_high_risk in (None, {}) and legacy_high_risk_overlay not in (None, {}):
        raw_high_risk = legacy_high_risk_overlay
    high_risk = _normalize_local_high_risk_overlay(
        raw_overlay=raw_high_risk,
        local_payload=local_payload,
        shared_payload=shared_payload,
        warnings=warnings,
        surface_prefix="local_overlay.high_risk",
    )
    overlay_warnings.extend(guidance.get("warnings", []))
    overlay_warnings.extend(high_risk.get("warnings", []))
    guidance_count = len(guidance.get("items", [])) if isinstance(guidance.get("items"), list) else 0
    high_risk_count = int(high_risk.get("item_count", 0) or 0) if isinstance(high_risk, dict) else 0
    return {
        "kind": "agentic-workspace/local-overlay-config/v1",
        "status": "configured" if guidance_count or high_risk_count else "absent",
        "item_count": guidance_count + high_risk_count,
        "ordinary_guidance_count": guidance_count,
        "high_risk_profile_count": high_risk_count,
        "sections": {
            "guidance": guidance.get("items", []),
            "high_risk": high_risk.get("sections", {}),
        },
        "high_risk_profile": high_risk,
        "warnings": overlay_warnings,
        "authority_boundary": {
            "source": "local-overlay",
            "rule": "Local overlay guidance may shape the acting checkout workflow, but it is not checked-in host policy.",
        },
    }


def _local_config_display_path(*, path: Path, target_root: Path) -> str:
    try:
        return path.relative_to(target_root).as_posix()
    except ValueError:
        return path.as_posix()


def _resolve_shared_local_config_path(
    *,
    raw_workspace: dict[str, Any],
    local_path: Path,
    target_root: Path,
) -> Path | None:
    raw_path = raw_workspace.get("shared_config_path")
    if raw_path is None:
        return None
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} workspace.shared_config_path must be a non-empty string.")
    configured = Path(raw_path.strip())
    if configured.is_absolute():
        return configured
    return (target_root / configured).resolve()


def load_mixed_agent_local_override(*, target_root: Path) -> tuple[MixedAgentLocalOverride, list[str]]:
    local_path = target_root / WORKSPACE_LOCAL_CONFIG_PATH
    warnings: list[str] = []
    if not local_path.exists():
        legacy_path = target_root / LEGACY_WORKSPACE_LOCAL_CONFIG_PATH
        if legacy_path.exists():
            local_path = legacy_path
        else:
            return empty_mixed_agent_local_override(path=local_path, exists=False), warnings

    local_payload = load_toml_payload(path=local_path, surface_name=WORKSPACE_LOCAL_CONFIG_PATH.as_posix())

    schema_version = local_payload.get("schema_version")
    if schema_version != 1:
        raise WorkspaceUsageError(
            f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} must set schema_version = 1 for the current local mixed-agent override contract."
        )
    local_workspace_for_shared = _local_config_table(local_payload, "workspace")
    shared_config_path = _resolve_shared_local_config_path(
        raw_workspace=local_workspace_for_shared,
        local_path=local_path,
        target_root=target_root,
    )
    shared_payload: dict[str, Any] | None = None
    shared_config_exists = False
    shared_config_applied = False
    if shared_config_path is not None:
        shared_config_exists = shared_config_path.exists()
        shared_display = _local_config_display_path(path=shared_config_path, target_root=target_root)
        if shared_config_exists:
            shared_payload = load_toml_payload(path=shared_config_path, surface_name=shared_display)
            shared_schema_version = shared_payload.get("schema_version")
            if shared_schema_version != 1:
                raise WorkspaceUsageError(
                    f"{shared_display} must set schema_version = 1 for the current local mixed-agent override contract."
                )
            shared_config_applied = True
        else:
            warnings.append(
                f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} workspace.shared_config_path points to missing file: {shared_display}."
            )

    payload = _merge_local_config_payloads(base=shared_payload or {}, override=local_payload)
    field_sources: dict[str, str] = {}

    unknown_top_level = sorted(
        set(payload)
        - {
            "schema_version",
            "workspace",
            "runtime",
            "handoff",
            "safety",
            "delegation",
            "clarification",
            "local_scratch_retention",
            "local_memory",
            "session_logging",
            "local_overlay",
            "high_risk_overlay",
            "delegation_targets",
        }
    )
    if unknown_top_level:
        unknown_text = ", ".join(unknown_top_level)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} contains unsupported top-level field(s): {unknown_text}.")

    raw_workspace = payload.get("workspace", {})
    if raw_workspace is None:
        raw_workspace = {}
    if not isinstance(raw_workspace, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [workspace] section must be a table.")
    unknown_workspace = sorted(set(raw_workspace) - {"enabled", "cli_invoke", "shared_config_path", "maintainer_mode"})
    if unknown_workspace:
        unknown_text = ", ".join(unknown_workspace)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [workspace] contains unsupported field(s): {unknown_text}.")
    enabled = require_optional_bool(
        payload=raw_workspace,
        key="enabled",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
    )
    if enabled is not None:
        field_sources["workspace.enabled"] = _local_config_field_source(
            local_payload=local_payload,
            shared_payload=shared_payload,
            table="workspace",
            key="enabled",
        )
    raw_cli_invoke = raw_workspace.get("cli_invoke")
    cli_invoke = None
    if raw_cli_invoke is not None:
        if not isinstance(raw_cli_invoke, str) or not raw_cli_invoke.strip():
            raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} workspace.cli_invoke must be a non-empty string.")
        cli_invoke = raw_cli_invoke.strip()
        field_sources["workspace.cli_invoke"] = _local_config_field_source(
            local_payload=local_payload,
            shared_payload=shared_payload,
            table="workspace",
            key="cli_invoke",
        )
    maintainer_mode = require_optional_bool(
        payload=raw_workspace,
        key="maintainer_mode",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
    )
    if maintainer_mode is not None:
        field_sources["workspace.maintainer_mode"] = _local_config_field_source(
            local_payload=local_payload,
            shared_payload=shared_payload,
            table="workspace",
            key="maintainer_mode",
        )

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
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [runtime] contains unsupported field(s): {unknown_text}.")

    raw_handoff = payload.get("handoff", {})
    if raw_handoff is None:
        raw_handoff = {}
    if not isinstance(raw_handoff, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [handoff] section must be a table.")
    unknown_handoff = sorted(set(raw_handoff) - {"prefer_internal_delegation_when_available"})
    if unknown_handoff:
        unknown_text = ", ".join(unknown_handoff)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [handoff] contains unsupported field(s): {unknown_text}.")

    raw_safety = payload.get("safety", {})
    if raw_safety is None:
        raw_safety = {}
    if not isinstance(raw_safety, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [safety] section must be a table.")
    unknown_safety = sorted(set(raw_safety) - {"safe_to_auto_run_commands", "requires_human_verification_on_pr"})
    if unknown_safety:
        unknown_text = ", ".join(unknown_safety)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [safety] contains unsupported field(s): {unknown_text}.")

    raw_delegation = payload.get("delegation", {})
    if raw_delegation is None:
        raw_delegation = {}
    if not isinstance(raw_delegation, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [delegation] section must be a table.")
    unknown_delegation = sorted(
        set(raw_delegation)
        - {
            "mode",
            "execution_role",
            "assignment_policy",
            "selection_objective",
            "current_target",
            "underfit_behavior",
            "down_routing_behavior",
            "human_override_policy",
            "manual_transport_policy",
        }
    )
    if unknown_delegation:
        unknown_text = ", ".join(unknown_delegation)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [delegation] contains unsupported field(s): {unknown_text}.")
    delegation_mode = raw_delegation.get("mode")
    if delegation_mode is not None:
        if not isinstance(delegation_mode, str) or delegation_mode not in SUPPORTED_DELEGATION_CONTROL_MODES:
            allowed_text = ", ".join(SUPPORTED_DELEGATION_CONTROL_MODES)
            raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} delegation.mode must be one of: {allowed_text}.")
        field_sources["delegation.mode"] = _local_config_field_source(
            local_payload=local_payload,
            shared_payload=shared_payload,
            table="delegation",
            key="mode",
        )
    execution_role = require_optional_enum_or_none(
        payload=raw_delegation,
        key="execution_role",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        allowed=SUPPORTED_ORCHESTRATION_EXECUTION_ROLES,
    )
    assignment_policy = require_optional_enum_or_none(
        payload=raw_delegation,
        key="assignment_policy",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        allowed=SUPPORTED_ASSIGNMENT_POLICIES,
    )
    selection_objective = require_optional_string(
        payload=raw_delegation,
        key="selection_objective",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
    )
    current_target = require_optional_string(
        payload=raw_delegation,
        key="current_target",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
    )
    underfit_behavior = require_optional_enum_or_none(
        payload=raw_delegation,
        key="underfit_behavior",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        allowed=SUPPORTED_UNDERFIT_BEHAVIORS,
    )
    down_routing_behavior = require_optional_enum_or_none(
        payload=raw_delegation,
        key="down_routing_behavior",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        allowed=SUPPORTED_DOWN_ROUTING_BEHAVIORS,
    )
    human_override_policy = require_optional_enum_or_none(
        payload=raw_delegation,
        key="human_override_policy",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        allowed=SUPPORTED_HUMAN_OVERRIDE_POLICIES,
    )
    manual_transport_policy = require_optional_enum_or_none(
        payload=raw_delegation,
        key="manual_transport_policy",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        allowed=SUPPORTED_MANUAL_TRANSPORT_POLICIES,
    )

    raw_clarification = payload.get("clarification", {})
    if raw_clarification is None:
        raw_clarification = {}
    if not isinstance(raw_clarification, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [clarification] section must be a table.")
    unknown_clarification = sorted(set(raw_clarification) - {"mode"})
    if unknown_clarification:
        unknown_text = ", ".join(unknown_clarification)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [clarification] contains unsupported field(s): {unknown_text}.")
    clarification_mode = raw_clarification.get("mode")
    if clarification_mode is not None:
        if not isinstance(clarification_mode, str) or clarification_mode not in SUPPORTED_CLARIFICATION_CONTROL_MODES:
            allowed_text = ", ".join(SUPPORTED_CLARIFICATION_CONTROL_MODES)
            raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} clarification.mode must be one of: {allowed_text}.")
        field_sources["clarification.mode"] = _local_config_field_source(
            local_payload=local_payload,
            shared_payload=shared_payload,
            table="clarification",
            key="mode",
        )

    raw_local_memory = payload.get("local_memory", {})
    if raw_local_memory is None:
        raw_local_memory = {}
    if not isinstance(raw_local_memory, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [local_memory] section must be a table.")
    unknown_local_memory = sorted(set(raw_local_memory) - {"enabled", "path"})
    if unknown_local_memory:
        unknown_text = ", ".join(unknown_local_memory)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [local_memory] contains unsupported field(s): {unknown_text}.")

    raw_session_logging = payload.get("session_logging", {})
    if raw_session_logging is None:
        raw_session_logging = {}
    if not isinstance(raw_session_logging, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [session_logging] section must be a table.")
    unknown_session_logging = sorted(set(raw_session_logging) - {"enabled", "redact_local_paths", "path_mode"})
    if unknown_session_logging:
        unknown_text = ", ".join(unknown_session_logging)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [session_logging] contains unsupported field(s): {unknown_text}.")
    session_logging_enabled = require_optional_bool(
        payload=raw_session_logging,
        key="enabled",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
    )
    session_logging_redact_local_paths = require_optional_bool(
        payload=raw_session_logging,
        key="redact_local_paths",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
    )
    session_logging_path_mode = require_optional_enum(
        payload=raw_session_logging,
        key="path_mode",
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        allowed=SUPPORTED_SESSION_LOGGING_PATH_MODES,
        default="redacted" if session_logging_redact_local_paths else "absolute",
    )

    raw_delegation_targets = payload.get("delegation_targets", {})
    if raw_delegation_targets is None:
        raw_delegation_targets = {}
    if not isinstance(raw_delegation_targets, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [delegation_targets] section must be a table.")
    delegation_targets, delegation_target_warnings = load_delegation_target_profiles(
        raw_targets=raw_delegation_targets,
        config_path=WORKSPACE_LOCAL_CONFIG_PATH,
    )
    warnings.extend(delegation_target_warnings)
    local_overlay = _normalize_local_overlay(
        raw_overlay=payload.get("local_overlay", {}),
        legacy_high_risk_overlay=payload.get("high_risk_overlay", {}),
        local_payload=local_payload,
        shared_payload=shared_payload,
        warnings=warnings,
    )
    high_risk_overlay = local_overlay.get("high_risk_profile", {}) if isinstance(local_overlay, dict) else {}

    return MixedAgentLocalOverride(
        path=local_path,
        exists=True,
        applied=True,
        shared_config_path=shared_config_path,
        shared_config_exists=shared_config_exists,
        shared_config_applied=shared_config_applied,
        enabled=enabled,
        cli_invoke=cli_invoke,
        maintainer_mode=maintainer_mode,
        supports_internal_delegation=require_optional_bool(
            payload=raw_runtime,
            key="supports_internal_delegation",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        strong_planner_available=require_optional_bool(
            payload=raw_runtime,
            key="strong_planner_available",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        cheap_bounded_executor_available=require_optional_bool(
            payload=raw_runtime,
            key="cheap_bounded_executor_available",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        prefer_internal_delegation_when_available=require_optional_bool(
            payload=raw_handoff,
            key="prefer_internal_delegation_when_available",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        safe_to_auto_run_commands=require_optional_bool(
            payload=raw_safety,
            key="safe_to_auto_run_commands",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        requires_human_verification_on_pr=require_optional_bool(
            payload=raw_safety,
            key="requires_human_verification_on_pr",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        delegation_mode=delegation_mode,
        execution_role=execution_role,
        assignment_policy=assignment_policy,
        selection_objective=selection_objective,
        current_target=current_target,
        underfit_behavior=underfit_behavior,
        down_routing_behavior=down_routing_behavior,
        human_override_policy=human_override_policy,
        manual_transport_policy=manual_transport_policy,
        clarification_mode=clarification_mode,
        local_memory_enabled=require_optional_bool(
            payload=raw_local_memory,
            key="enabled",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
        ),
        local_memory_path=require_optional_relative_path(
            payload=raw_local_memory,
            key="path",
            config_path=WORKSPACE_LOCAL_CONFIG_PATH,
            default=WORKSPACE_LOCAL_MEMORY_DEFAULT_PATH,
        ),
        session_logging=SessionLoggingConfig(
            enabled=session_logging_enabled,
            redact_local_paths=session_logging_path_mode == "redacted",
            path_mode=session_logging_path_mode,
            source=_local_config_field_source(
                local_payload=local_payload,
                shared_payload=shared_payload,
                table="session_logging",
                key="enabled",
            )
            if session_logging_enabled is not None
            else "unset",
        ),
        delegation_targets=delegation_targets,
        local_overlay=local_overlay,
        high_risk_overlay=high_risk_overlay,
        field_sources=field_sources
        | {
            field_path: _local_config_field_source(
                local_payload=local_payload,
                shared_payload=shared_payload,
                table=table,
                key=key,
            )
            for field_path, table, key, configured in (
                (
                    "runtime.supports_internal_delegation",
                    "runtime",
                    "supports_internal_delegation",
                    raw_runtime.get("supports_internal_delegation"),
                ),
                (
                    "runtime.strong_planner_available",
                    "runtime",
                    "strong_planner_available",
                    raw_runtime.get("strong_planner_available"),
                ),
                (
                    "runtime.cheap_bounded_executor_available",
                    "runtime",
                    "cheap_bounded_executor_available",
                    raw_runtime.get("cheap_bounded_executor_available"),
                ),
                (
                    "handoff.prefer_internal_delegation_when_available",
                    "handoff",
                    "prefer_internal_delegation_when_available",
                    raw_handoff.get("prefer_internal_delegation_when_available"),
                ),
                (
                    "safety.safe_to_auto_run_commands",
                    "safety",
                    "safe_to_auto_run_commands",
                    raw_safety.get("safe_to_auto_run_commands"),
                ),
                (
                    "safety.requires_human_verification_on_pr",
                    "safety",
                    "requires_human_verification_on_pr",
                    raw_safety.get("requires_human_verification_on_pr"),
                ),
                ("delegation.execution_role", "delegation", "execution_role", raw_delegation.get("execution_role")),
                ("delegation.assignment_policy", "delegation", "assignment_policy", raw_delegation.get("assignment_policy")),
                ("delegation.selection_objective", "delegation", "selection_objective", raw_delegation.get("selection_objective")),
                ("delegation.current_target", "delegation", "current_target", raw_delegation.get("current_target")),
                ("delegation.underfit_behavior", "delegation", "underfit_behavior", raw_delegation.get("underfit_behavior")),
                ("delegation.down_routing_behavior", "delegation", "down_routing_behavior", raw_delegation.get("down_routing_behavior")),
                ("delegation.human_override_policy", "delegation", "human_override_policy", raw_delegation.get("human_override_policy")),
                (
                    "delegation.manual_transport_policy",
                    "delegation",
                    "manual_transport_policy",
                    raw_delegation.get("manual_transport_policy"),
                ),
                ("local_memory.enabled", "local_memory", "enabled", raw_local_memory.get("enabled")),
                ("local_memory.path", "local_memory", "path", raw_local_memory.get("path")),
                ("session_logging.enabled", "session_logging", "enabled", raw_session_logging.get("enabled")),
                (
                    "session_logging.redact_local_paths",
                    "session_logging",
                    "redact_local_paths",
                    raw_session_logging.get("redact_local_paths"),
                ),
                ("session_logging.path_mode", "session_logging", "path_mode", raw_session_logging.get("path_mode")),
            )
            if configured is not None
        },
    ), warnings


def default_module_update_policies() -> dict[str, ModuleUpdatePolicy]:
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
            recommended_upgrade_after_days=int(memory_default["recommended_upgrade_after_days"])
            if isinstance(memory_default["recommended_upgrade_after_days"], (int, str))
            else 0,
            source="product-default",
        ),
    }


def validate_enabled_modules(value: Any, *, config_path: Path, known_modules: tuple[str, ...] = SUPPORTED_CORE_MODULES) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise WorkspaceUsageError(f"{config_path.as_posix()} modules.enabled must be an array of module ids.")
    enabled: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise WorkspaceUsageError(f"{config_path.as_posix()} modules.enabled entries must be non-empty strings.")
        module_name = item.strip()
        if module_name == "none":
            raise WorkspaceUsageError(f"{config_path.as_posix()} modules.enabled uses [] for no enabled modules, not 'none'.")
        if module_name not in known_modules:
            supported = ", ".join(known_modules)
            raise WorkspaceUsageError(
                f"{config_path.as_posix()} modules.enabled contains unknown module '{module_name}'. Supported modules: {supported}."
            )
        if module_name not in enabled:
            enabled.append(module_name)
    return tuple(enabled)


def load_workspace_config(*, target_root: Path, valid_presets: set[str] | None = None) -> WorkspaceConfig:
    defaults = default_module_update_policies()

    # Discovery logic
    discovered_root = discover_workspace_root(target_root)
    effective_root = discovered_root or target_root

    config_path = effective_root / WORKSPACE_CONFIG_PATH
    if not config_path.exists():
        legacy_config_path = effective_root / LEGACY_WORKSPACE_CONFIG_PATH
        if legacy_config_path.exists():
            config_path = legacy_config_path
    local_override, local_warnings = load_mixed_agent_local_override(target_root=effective_root)
    warnings = list(local_warnings)

    enabled_modules = DEFAULT_ENABLED_MODULES
    configured_agent_instructions_file: str | None = None
    workflow_artifact_profile = DEFAULT_WORKFLOW_ARTIFACT_PROFILE
    workflow_artifact_profile_source = "product-default"
    enabled = True
    enabled_source = "product-default"
    improvement_latitude = DEFAULT_IMPROVEMENT_LATITUDE
    improvement_latitude_source = "product-default"
    optimization_bias = DEFAULT_OPTIMIZATION_BIAS
    optimization_bias_source = "product-default"
    advanced_features: tuple[str, ...] = ()
    advanced_features_source = "product-default"
    maintainer_mode = DEFAULT_MAINTAINER_MODE
    maintainer_mode_source = "product-default"
    cli_invoke = DEFAULT_CLI_INVOKE
    cli_invoke_source = "product-default"
    assurance, assurance_warnings = _load_assurance_config(raw_assurance={}, config_path=WORKSPACE_CONFIG_PATH)
    warnings.extend(assurance_warnings)
    cli_compatibility, cli_compatibility_warnings = _load_cli_compatibility_expectation(
        raw_cli_compatibility={},
        config_path=WORKSPACE_CONFIG_PATH,
    )
    warnings.extend(cli_compatibility_warnings)
    payload_target, payload_target_warnings = _load_payload_target_config(
        raw_payload={},
        config_path=WORKSPACE_CONFIG_PATH,
    )
    warnings.extend(payload_target_warnings)
    if local_override.enabled is not None:
        enabled = local_override.enabled
        enabled_source = local_override.field_sources.get("workspace.enabled", "local-override")
    if local_override.cli_invoke is not None:
        cli_invoke = local_override.cli_invoke
        cli_invoke_source = local_override.field_sources.get("workspace.cli_invoke", "local-override")
    if local_override.maintainer_mode is not None:
        maintainer_mode = local_override.maintainer_mode
        maintainer_mode_source = local_override.field_sources.get("workspace.maintainer_mode", "local-override")

    if not config_path.exists():
        agent_instructions_file, agent_instructions_source, detected_agent_instruction_files = resolve_effective_agent_instructions_file(
            target_root=effective_root,
            configured=None,
        )
        return WorkspaceConfig(
            target_root=effective_root,
            path=config_path,
            exists=False,
            schema_version=1,
            enabled=enabled,
            enabled_source=enabled_source,
            enabled_modules=enabled_modules,
            agent_instructions_file=agent_instructions_file,
            agent_instructions_source=agent_instructions_source,
            workflow_artifact_profile=workflow_artifact_profile,
            workflow_artifact_profile_source=workflow_artifact_profile_source,
            improvement_latitude=improvement_latitude,
            improvement_latitude_source=improvement_latitude_source,
            optimization_bias=optimization_bias,
            optimization_bias_source=optimization_bias_source,
            advanced_features=advanced_features,
            advanced_features_source=advanced_features_source,
            maintainer_mode=maintainer_mode,
            maintainer_mode_source=maintainer_mode_source,
            cli_invoke=cli_invoke,
            cli_invoke_source=cli_invoke_source,
            detected_agent_instructions_files=detected_agent_instruction_files,
            update_modules=defaults,
            workflow_obligations=(),
            system_intent=SystemIntentDeclaration(
                sources=tuple(path.as_posix() for path in SYSTEM_INTENT_SOURCE_DISCOVERY_CANDIDATES if (effective_root / path).exists()),
                sources_source=(
                    "autodetected-existing"
                    if any((effective_root / path).exists() for path in SYSTEM_INTENT_SOURCE_DISCOVERY_CANDIDATES)
                    else "product-default"
                ),
                preferred_source=next(
                    (path.as_posix() for path in SYSTEM_INTENT_SOURCE_DISCOVERY_CANDIDATES if (effective_root / path).exists()),
                    None,
                ),
                preferred_source_source=(
                    "autodetected-existing"
                    if any((effective_root / path).exists() for path in SYSTEM_INTENT_SOURCE_DISCOVERY_CANDIDATES)
                    else "product-default"
                ),
            ),
            assurance=assurance,
            cli_compatibility=cli_compatibility,
            payload_target=payload_target,
            local_override=local_override,
            warnings=tuple(warnings),
        )

    try:
        payload = load_toml_payload(path=config_path, surface_name=WORKSPACE_CONFIG_PATH.as_posix())
    except WorkspaceUsageError:
        text = config_path.read_text(encoding="utf-8-sig", errors="replace")
        if not any(marker in text for marker in ("<<<<<<< ", "=======", ">>>>>>> ")):
            raise
        warnings.append(
            f"{WORKSPACE_CONFIG_PATH.as_posix()} contains git merge conflict markers; "
            "using product defaults only so doctor/report can route semantic recovery."
        )
        payload: dict[str, Any] = {"schema_version": 1}

    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise WorkspaceUsageError(
            f"{WORKSPACE_CONFIG_PATH.as_posix()} must set schema_version = 1 for the current workspace config contract."
        )

    unknown_top_level = sorted(
        set(payload)
        - {
            "schema_version",
            "workspace",
            "modules",
            "update",
            "workflow_obligations",
            "system_intent",
            "assurance",
            "cli_compatibility",
            "payload",
        }
    )
    if unknown_top_level:
        unknown_text = ", ".join(unknown_top_level)
        warnings.append(f"{WORKSPACE_CONFIG_PATH.as_posix()} contains unsupported top-level field(s): {unknown_text}.")

    raw_workspace = payload.get("workspace", {})
    if raw_workspace is None:
        raw_workspace = {}
    if not isinstance(raw_workspace, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} [workspace] section must be a table.")

    # Relaxed: Warn about unknown workspace fields
    unknown_workspace = sorted(
        set(raw_workspace)
        - {
            "agent_instructions_file",
            "enabled",
            "workflow_artifact_profile",
            "improvement_latitude",
            "optimization_bias",
            "advanced_features",
            "maintainer_mode",
            "cli_invoke",
        }
    )
    if unknown_workspace:
        unknown_text = ", ".join(unknown_workspace)
        warnings.append(f"{WORKSPACE_CONFIG_PATH.as_posix()} [workspace] contains unsupported field(s): {unknown_text}.")

    if "default_preset" in raw_workspace:
        raise WorkspaceUsageError(
            f"{WORKSPACE_CONFIG_PATH.as_posix()} workspace.default_preset is no longer supported; use [modules] enabled = [...] instead."
        )
    raw_enabled_modules_section = payload.get("modules", {})
    if raw_enabled_modules_section is None:
        raw_enabled_modules_section = {}
    if not isinstance(raw_enabled_modules_section, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} [modules] section must be a table.")
    unknown_enabled_module_fields = sorted(set(raw_enabled_modules_section) - {"enabled"})
    if unknown_enabled_module_fields:
        unknown_text = ", ".join(unknown_enabled_module_fields)
        warnings.append(f"{WORKSPACE_CONFIG_PATH.as_posix()} [modules] contains unsupported field(s): {unknown_text}.")
    if "enabled" in raw_enabled_modules_section:
        enabled_modules = validate_enabled_modules(
            raw_enabled_modules_section["enabled"],
            config_path=WORKSPACE_CONFIG_PATH,
            known_modules=tuple(sorted(valid_presets)) if valid_presets else SUPPORTED_CORE_MODULES,
        )

    raw_agent_instructions_file = raw_workspace.get("agent_instructions_file")
    if raw_agent_instructions_file is not None:
        configured_agent_instructions_file = validate_agent_instructions_filename(str(raw_agent_instructions_file))
    raw_enabled = raw_workspace.get("enabled")
    if raw_enabled is not None:
        if not isinstance(raw_enabled, bool):
            raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} workspace.enabled must be true or false.")
        enabled = raw_enabled
        enabled_source = "repo-config"
    raw_workflow_artifact_profile = raw_workspace.get("workflow_artifact_profile")
    if raw_workflow_artifact_profile is not None:
        workflow_artifact_profile = validate_workflow_artifact_profile(str(raw_workflow_artifact_profile))
        workflow_artifact_profile_source = "repo-config"
    raw_improvement_latitude = raw_workspace.get("improvement_latitude")
    if raw_improvement_latitude is not None:
        improvement_latitude = validate_improvement_latitude(str(raw_improvement_latitude))
        improvement_latitude_source = "repo-config"
    raw_optimization_bias = raw_workspace.get("optimization_bias")
    if raw_optimization_bias is not None:
        optimization_bias = validate_optimization_bias(str(raw_optimization_bias))
        optimization_bias_source = "repo-config"
    configured_advanced_features = require_optional_string_list(
        payload=raw_workspace,
        key="advanced_features",
        config_path=WORKSPACE_CONFIG_PATH,
        allowed=SUPPORTED_ADVANCED_FEATURES,
    )
    if configured_advanced_features:
        advanced_features = configured_advanced_features
        advanced_features_source = "repo-config"
    raw_maintainer_mode = raw_workspace.get("maintainer_mode")
    if raw_maintainer_mode is not None:
        if not isinstance(raw_maintainer_mode, bool):
            raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} workspace.maintainer_mode must be true or false.")
        maintainer_mode = raw_maintainer_mode
        maintainer_mode_source = "repo-config"
    raw_cli_invoke = raw_workspace.get("cli_invoke")
    if raw_cli_invoke is not None:
        if not isinstance(raw_cli_invoke, str) or not raw_cli_invoke.strip():
            raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} workspace.cli_invoke must be a non-empty string.")
        cli_invoke = raw_cli_invoke.strip()
        cli_invoke_source = "repo-config"
    if local_override.cli_invoke is not None:
        cli_invoke = local_override.cli_invoke
        cli_invoke_source = local_override.field_sources.get("workspace.cli_invoke", "local-override")
    if local_override.enabled is not None:
        enabled = local_override.enabled
        enabled_source = local_override.field_sources.get("workspace.enabled", "local-override")
    if local_override.maintainer_mode is not None:
        maintainer_mode = local_override.maintainer_mode
        maintainer_mode_source = local_override.field_sources.get("workspace.maintainer_mode", "local-override")

    update_modules = dict(defaults)
    raw_update = payload.get("update", {})
    if raw_update is None:
        raw_update = {}
    if not isinstance(raw_update, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} [update] section must be a table.")

    # Relaxed: Warn about unknown update fields
    unknown_update = sorted(set(raw_update) - {"modules"})
    if unknown_update:
        unknown_text = ", ".join(unknown_update)
        warnings.append(f"{WORKSPACE_CONFIG_PATH.as_posix()} [update] contains unsupported field(s): {unknown_text}.")

    raw_modules = raw_update.get("modules", {})
    if raw_modules is None:
        raw_modules = {}
    if not isinstance(raw_modules, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} [update.modules] section must be a table.")

    unknown_modules = [module_name for module_name in raw_modules if module_name not in defaults]
    if unknown_modules:
        supported = ", ".join(sorted(defaults))
        unknown = ", ".join(sorted(unknown_modules))
        raise WorkspaceUsageError(
            f"{WORKSPACE_CONFIG_PATH.as_posix()} update.modules contains unknown module(s): {unknown}. Supported modules: {supported}."
        )

    for module_name, module_payload in raw_modules.items():
        if not isinstance(module_payload, dict):
            raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} [update.modules.{module_name}] must be a table.")

        # Relaxed: Warn about unknown module update fields
        unknown_module_fields = sorted(
            set(module_payload) - {"source_type", "source_ref", "source_label", "recommended_upgrade_after_days"}
        )
        if unknown_module_fields:
            unknown_text = ", ".join(unknown_module_fields)
            warnings.append(
                f"{WORKSPACE_CONFIG_PATH.as_posix()} [update.modules.{module_name}] contains unsupported field(s): {unknown_text}."
            )

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

    raw_workflow_obligations = payload.get("workflow_obligations", {})
    if raw_workflow_obligations is None:
        raw_workflow_obligations = {}
    if not isinstance(raw_workflow_obligations, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} [workflow_obligations] section must be a table.")
    workflow_obligations, workflow_obligation_warnings = load_workflow_obligations(
        raw_obligations=raw_workflow_obligations,
        config_path=WORKSPACE_CONFIG_PATH,
    )
    warnings.extend(workflow_obligation_warnings)
    system_intent, system_intent_warnings = resolve_system_intent_declaration(
        target_root=effective_root,
        raw_system_intent=payload.get("system_intent", {}),
        config_path=WORKSPACE_CONFIG_PATH,
    )
    warnings.extend(system_intent_warnings)
    assurance, assurance_warnings = _load_assurance_config(
        raw_assurance=payload.get("assurance", {}),
        config_path=WORKSPACE_CONFIG_PATH,
    )
    warnings.extend(assurance_warnings)
    cli_compatibility, cli_compatibility_warnings = _load_cli_compatibility_expectation(
        raw_cli_compatibility=payload.get("cli_compatibility", {}),
        config_path=WORKSPACE_CONFIG_PATH,
    )
    warnings.extend(cli_compatibility_warnings)
    payload_target, payload_target_warnings = _load_payload_target_config(
        raw_payload=payload.get("payload", {}),
        config_path=WORKSPACE_CONFIG_PATH,
    )
    warnings.extend(payload_target_warnings)

    agent_instructions_file, agent_instructions_source, detected_agent_instruction_files = resolve_effective_agent_instructions_file(
        target_root=effective_root,
        configured=configured_agent_instructions_file,
    )
    return WorkspaceConfig(
        target_root=effective_root,
        path=config_path,
        exists=True,
        schema_version=1,
        enabled=enabled,
        enabled_source=enabled_source,
        enabled_modules=enabled_modules,
        agent_instructions_file=agent_instructions_file,
        agent_instructions_source=agent_instructions_source,
        workflow_artifact_profile=workflow_artifact_profile,
        workflow_artifact_profile_source=workflow_artifact_profile_source,
        improvement_latitude=improvement_latitude,
        improvement_latitude_source=improvement_latitude_source,
        optimization_bias=optimization_bias,
        optimization_bias_source=optimization_bias_source,
        advanced_features=advanced_features,
        advanced_features_source=advanced_features_source,
        maintainer_mode=maintainer_mode,
        maintainer_mode_source=maintainer_mode_source,
        cli_invoke=cli_invoke,
        cli_invoke_source=cli_invoke_source,
        detected_agent_instructions_files=detected_agent_instruction_files,
        update_modules=update_modules,
        workflow_obligations=workflow_obligations,
        system_intent=system_intent,
        assurance=assurance,
        cli_compatibility=cli_compatibility,
        payload_target=payload_target,
        local_override=local_override,
        warnings=tuple(warnings),
    )
