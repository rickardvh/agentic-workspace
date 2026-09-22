"""Read the closed human configuration grammar and current owner manifests."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from agentic_workspace.result_adapter import serialise_value


def _validate_current_authoring(payload: dict[str, Any], *, local: bool) -> None:
    from jsonschema import Draft202012Validator

    from aw_maintainer.contracts import contract_schema

    name = "workspace_local_override" if local else "workspace_config"
    errors = list(Draft202012Validator(contract_schema(f"{name}.schema.json")).iter_errors(payload))
    if errors:
        raise WorkspaceUsageError(f"Invalid configuration at {list(errors[0].absolute_path)}")


WORKSPACE_CONFIG_PATH = Path(".agentic-workspace/config.toml")
WORKSPACE_LOCAL_CONFIG_PATH = Path(".agentic-workspace/config.local.toml")
WORKSPACE_DELEGATION_OUTCOMES_PATH = Path(".agentic-workspace/delegation-outcomes.json")
LEGACY_WORKSPACE_DELEGATION_OUTCOMES_PATH = Path("agentic-workspace.delegation-outcomes.json")
WORKSPACE_LOCAL_MEMORY_DEFAULT_PATH = Path(".agentic-workspace/local/memory.toml")
WORKSPACE_LOCAL_TARGET_GUIDANCE_OVERLAY_DEFAULT_PATH = Path(".agentic-workspace/local/target-guidance-overlay.json")
WORKSPACE_LOCAL_CORRECTION_EVENTS_DEFAULT_PATH = Path(".agentic-workspace/local/correction-events.json")
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
SUPPORTED_REPO_REQUIREMENT_CLASSES = (
    "invariant",
    "current-evidence",
    "guideline",
)
SUPPORTED_MEASUREMENT_COMPARATORS = ("lte", "gte", "eq", "ratio-lte", "ratio-gte")
SUPPORTED_MEASUREMENT_AGGREGATIONS = ("single", "median", "percentile", "ratio", "count")
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
SUPPORTED_DELEGATION_DISPATCH_ADAPTER_KINDS = (
    "process",
    "host-native",
)
SUPPORTED_DELEGATION_DISPATCH_OUTPUT_MODES = (
    "stdout",
    "json-file",
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
SUPPORTED_CURRENT_ECONOMIC_EVIDENCE_STATUSES = (
    "available",
    "unavailable",
    "exhausted",
    "contradictory",
    "unknown",
)
SUPPORTED_CURRENT_MARGINAL_COST_CLASSES = (
    "near-zero",
    "lower",
    "equivalent",
    "higher",
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
SUPPORTED_SETUP_PROMPT_DISPOSITIONS = (
    "active",
    "deferred",
    "optional-suppressed",
)
SUPPORTED_TARGET_IDENTITY_STATUSES = (
    "active",
    "retired",
    "superseded",
    "ambiguous",
    "unavailable",
)
SUPPORTED_TARGET_REVISION_POLICIES = (
    "preserve",
    "revalidate",
    "migrate",
    "retire",
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
SUPPORTED_TRANSPORT_AUTHORITIES = (
    "manual",
    "automatic",
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


def workspace_pointer_block(cli_invoke: str = "agentic-workspace") -> str:
    """Render the mixed-agent activation pointer; invocation policy stays source-owned."""
    return (
        f"{WORKSPACE_WORKFLOW_MARKER_START}"
        "\nUse `.agentic-workspace/skills/workspace-startup/SKILL.md` for repository procedure; if native skill discovery is unavailable, read it directly.\n"
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
    "unknown",
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
SUPPORTED_CLI_RESOLUTION_POLICIES = (
    "direct",
    "locked",
    "frozen",
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
    target_id: str | None
    target_revision: str | None
    aliases: tuple[str, ...]
    identity_status: str
    revision_policy: str
    strength: str
    location: str
    execution_methods: tuple[str, ...]
    transports: tuple[dict[str, Any], ...]
    confidence: float | None
    task_fit: tuple[str, ...]
    capability_classes: tuple[str, ...]
    model_family: str | None
    provider: str | None
    dispatch_adapter_kind: str | None
    dispatch_command: tuple[str, ...]
    dispatch_output_mode: str
    dispatch_timeout_seconds: int
    context_capacity: str
    reasoning_profile: str
    cost_class: str
    current_economic_evidence: dict[str, Any] | None
    latency_class: str
    safe_task_classes: tuple[str, ...]
    forbidden_task_classes: tuple[str, ...]
    escalation_target: str | None
    confidence_source: str | None
    last_evaluation: str | None
    human_control_modes: tuple[str, ...]
    execution_guarantees: tuple[str, ...] = ()


@dataclass(frozen=True)
class SessionLoggingConfig:
    enabled: bool | None
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
    transport_authority: str | None
    selection_objective: str | None
    current_target: str | None
    underfit_behavior: str | None
    down_routing_behavior: str | None
    human_override_policy: str | None
    manual_transport_policy: str | None
    clarification_mode: str | None
    setup_prompt_disposition: str | None
    setup_identity: str | None
    setup_context_revision: str | None
    setup_unresolved_concerns: tuple[str, ...]
    setup_required_concerns: tuple[str, ...]
    local_memory_enabled: bool | None
    local_memory_path: Path
    target_guidance_enabled: bool | None
    user_guidance_root: str | None
    target_guidance_overlay_path: Path
    correction_events_path: Path
    session_logging: SessionLoggingConfig
    delegation_targets: tuple[DelegationTargetProfile, ...]
    local_overlay: dict[str, Any]
    high_risk_overlay: dict[str, Any]
    field_sources: dict[str, str]
    assignment_replacement: dict[str, str] | None = None
    required_execution_guarantees: tuple[str, ...] = ()


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
    applicability: dict[str, Any]


@dataclass(frozen=True)
class AssuranceRequirement:
    id: str
    level: str
    applies_to_paths: tuple[str, ...]
    applies_to_task_markers: tuple[str, ...]
    applies_to_semantic_routes: tuple[str, ...]
    applies_to_planning_refs: tuple[str, ...]
    applies_to_proof_profiles: tuple[str, ...]
    applies_to_risk_refs: tuple[str, ...]
    applies_to_invariant_refs: tuple[str, ...]
    authority_refs: tuple[str, ...]
    required_evidence: tuple[str, ...]
    proof_profile: str | None
    review_owner: str | None
    force: str
    blocking_claims: tuple[str, ...]
    waiver: AssuranceRequirementDisposition | None
    dismissal: AssuranceRequirementDisposition | None
    notes: str | None
    requirement_class: str | None
    source_intent_ref: str | None
    source_intent_revision: str | None
    source_intent_current: bool | None
    preference_target: str | None
    evidence_owner: str | None
    detail_route: str | None
    measurement: dict[str, Any] | None
    requirement_refs: tuple[str, ...] = ()
    claim_boundary: str | None = None


@dataclass(frozen=True)
class AssuranceSubsystemProfile:
    id: str
    assurance_level: str
    scope_refs: tuple[str, ...]
    requirement_refs: tuple[str, ...]
    required_evidence: tuple[str, ...]
    proof_profile: str | None
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
    classification_owner: str
    classification_source: str | None
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
    decision_record_revision: str | None
    instruction_revision: str | None
    decision_record_fallback: dict[str, Any] | None
    decision_record_format: str | None
    decision_record_template: str | None
    decision_record_statuses: tuple[str, ...]
    invariant_registry: str | None
    risk_registry: str | None


@dataclass(frozen=True)
class PayloadTargetConfig:
    target_release: str | None
    minimum_capabilities: tuple[str, ...]
    policy: str
    source: str


@dataclass(frozen=True)
class WorkspaceConfig:
    target_root: Path | None
    path: Path | None
    exists: bool
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
    system_intent: SystemIntentDeclaration
    assurance: AssuranceConfig
    payload_target: PayloadTargetConfig
    local_override: MixedAgentLocalOverride
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class DelegationOutcomeRecord:
    recorded_at: str
    delegation_target: str
    task_class: str
    scope_class: str
    outcome: str
    handoff_sufficiency: str
    review_burden: str
    escalation_required: bool
    operation: str = "submit"
    record_id: str = ""
    predecessor_id: str = ""
    authority: str = "local-outcome-ledger"
    confidence: str = "medium"
    admission_state: str = "accepted"
    source_type: str = "local-json-ledger"
    source_ref: str = ""
    producer_class: str = "local-operator"
    route_outcome: str = ""
    assignment_route: str = ""
    proof_observation: str = ""
    review_observation: str = ""
    handoff_burden: str = ""
    repair_burden: str = ""
    retry_burden: str = ""
    restart_burden: str = ""
    expected_burden: str = ""
    observed_burden: str = ""
    context_cost: dict[str, Any] | None = None
    scope_drift: str = "none"
    contradiction_state: str = "none"
    uncertainty_state: str = "unknown"
    idempotency_key: str = ""


def discover_workspace_root(start_path: Path | None = None) -> Path | None:
    """Search upwards for the workspace root containing the checked-in workspace config."""
    current = (start_path or Path.cwd()).resolve()
    while True:
        if (current / WORKSPACE_CONFIG_PATH).exists():
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
    }
    unknown = sorted(set(raw_payload) - supported_fields)
    if unknown:
        warnings.append(f"{config_path.as_posix()} [payload] contains unsupported field(s): {', '.join(unknown)}.")
    target_release = _validate_payload_target_release(value=raw_payload.get("target_release"), config_path=config_path)
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


def _require_measurement_requirement(*, payload: dict[str, Any], config_path: Path) -> dict[str, Any] | None:
    raw = payload.get("measurement")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} measurement must be a table.")
    measurement_path = Path(f"{config_path.as_posix()} measurement")
    required = {
        "kind",
        "evidence_label",
        "metric",
        "unit",
        "comparator",
        "threshold",
        "aggregation",
        "minimum_samples",
        "subject",
        "subject_revision",
        "environment",
        "source_revision",
        "producer_command",
    }
    optional = {"tolerance", "excluded_costs", "control_subject", "control_revision"}
    unknown = sorted(set(raw) - required - optional)
    if unknown:
        raise WorkspaceUsageError(f"{measurement_path.as_posix()} contains unsupported field(s): {', '.join(unknown)}.")
    missing = sorted(required - set(raw))
    if missing:
        raise WorkspaceUsageError(f"{measurement_path.as_posix()} requires: {', '.join(missing)}.")
    kind = require_optional_string(payload=raw, key="kind", config_path=measurement_path)
    if kind != "agentic-workspace/measurement-requirement/v1":
        raise WorkspaceUsageError(f"{measurement_path.as_posix()} kind must be agentic-workspace/measurement-requirement/v1.")
    normalized: dict[str, Any] = {
        "kind": kind,
        "evidence_label": require_optional_string(payload=raw, key="evidence_label", config_path=measurement_path),
        "metric": require_optional_string(payload=raw, key="metric", config_path=measurement_path),
        "unit": require_optional_string(payload=raw, key="unit", config_path=measurement_path),
        "comparator": require_required_enum(
            payload=raw,
            key="comparator",
            config_path=measurement_path,
            allowed=SUPPORTED_MEASUREMENT_COMPARATORS,
        ),
        "aggregation": require_required_enum(
            payload=raw,
            key="aggregation",
            config_path=measurement_path,
            allowed=SUPPORTED_MEASUREMENT_AGGREGATIONS,
        ),
        "subject": require_optional_string(payload=raw, key="subject", config_path=measurement_path),
        "subject_revision": require_optional_string(payload=raw, key="subject_revision", config_path=measurement_path),
        "environment": require_optional_string(payload=raw, key="environment", config_path=measurement_path),
        "source_revision": require_optional_string(payload=raw, key="source_revision", config_path=measurement_path),
        "producer_command": require_optional_string(payload=raw, key="producer_command", config_path=measurement_path),
        "excluded_costs": list(require_optional_string_list(payload=raw, key="excluded_costs", config_path=measurement_path)),
    }
    for field in (
        "evidence_label",
        "metric",
        "unit",
        "subject",
        "subject_revision",
        "environment",
        "source_revision",
        "producer_command",
    ):
        if not normalized[field]:
            raise WorkspaceUsageError(f"{measurement_path.as_posix()} {field} must be a non-empty string.")
    threshold = raw.get("threshold")
    tolerance = raw.get("tolerance", 0)
    minimum_samples = raw.get("minimum_samples")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise WorkspaceUsageError(f"{measurement_path.as_posix()} threshold must be a number.")
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or tolerance < 0:
        raise WorkspaceUsageError(f"{measurement_path.as_posix()} tolerance must be a non-negative number.")
    if isinstance(minimum_samples, bool) or not isinstance(minimum_samples, int) or minimum_samples < 1:
        raise WorkspaceUsageError(f"{measurement_path.as_posix()} minimum_samples must be a positive integer.")
    normalized.update(threshold=threshold, tolerance=tolerance, minimum_samples=minimum_samples)
    for field in ("control_subject", "control_revision"):
        value = require_optional_string(payload=raw, key=field, config_path=measurement_path)
        if value is not None:
            normalized[field] = value
    if normalized["comparator"].startswith("ratio-"):
        if normalized["aggregation"] != "ratio" or not normalized.get("control_subject") or not normalized.get("control_revision"):
            raise WorkspaceUsageError(
                f"{measurement_path.as_posix()} ratio comparators require aggregation=ratio, control_subject, and control_revision."
            )
    elif normalized["aggregation"] == "ratio":
        raise WorkspaceUsageError(f"{measurement_path.as_posix()} ratio aggregation requires a ratio comparator.")
    return normalized


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
    requirement_declarations: dict[str, tuple[str, AssuranceRequirement]] = {}
    supported_fields = {
        "level",
        "applies_to_paths",
        "applies_to_task_markers",
        "applies_to_semantic_routes",
        "applies_to_planning_refs",
        "applies_to_proof_profiles",
        "applies_to_risk_refs",
        "applies_to_invariant_refs",
        "authority_refs",
        "required_evidence",
        "proof_profile",
        "review_owner",
        "force",
        "blocking_claims",
        "notes",
        "requirement_class",
        "source_intent_ref",
        "source_intent_revision",
        "preference_target",
        "evidence_owner",
        "detail_route",
        "measurement",
        "requirement_refs",
        "claim_boundary",
    }
    activation_fields = {
        "applies_to_paths",
        "applies_to_task_markers",
        "applies_to_semantic_routes",
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
            raise WorkspaceUsageError(f"{requirement_path.as_posix()} contains unsupported fields.")
        activation_values = {
            key: require_optional_string_list(payload=raw_requirement, key=key, config_path=requirement_path) for key in activation_fields
        }
        if not any(activation_values.values()):
            allowed = ", ".join(sorted(activation_fields))
            raise WorkspaceUsageError(f"{requirement_path.as_posix()} requires at least one activation signal: {allowed}.")
        requirement_class = (
            require_required_enum(
                payload=raw_requirement,
                key="requirement_class",
                config_path=requirement_path,
                allowed=SUPPORTED_REPO_REQUIREMENT_CLASSES,
            )
            if "requirement_class" in raw_requirement
            else None
        )
        source_intent_ref = require_optional_string(payload=raw_requirement, key="source_intent_ref", config_path=requirement_path)
        source_intent_revision = require_optional_string(
            payload=raw_requirement, key="source_intent_revision", config_path=requirement_path
        )
        preference_target = require_optional_string(payload=raw_requirement, key="preference_target", config_path=requirement_path)
        evidence_owner = require_optional_string(payload=raw_requirement, key="evidence_owner", config_path=requirement_path)
        detail_route = require_optional_string(payload=raw_requirement, key="detail_route", config_path=requirement_path)
        measurement = _require_measurement_requirement(payload=raw_requirement, config_path=requirement_path)
        blocking_claims = require_optional_string_list(
            payload=raw_requirement,
            key="blocking_claims",
            config_path=requirement_path,
            allowed=SUPPORTED_ASSURANCE_REQUIREMENT_BLOCKING_CLAIMS,
        )
        required_evidence = require_optional_string_list(payload=raw_requirement, key="required_evidence", config_path=requirement_path)
        force = require_required_enum(
            payload=raw_requirement,
            key="force",
            config_path=requirement_path,
            allowed=SUPPORTED_WORKFLOW_OBLIGATION_FORCES,
        )
        if requirement_class is not None and not (source_intent_ref and source_intent_revision):
            raise WorkspaceUsageError(
                f"{requirement_path.as_posix()} named repo requirements require source_intent_ref, "
                "and source_intent_revision. Currentness is established by the source owner."
            )
        if requirement_class == "guideline":
            if not preference_target or not preference_target.startswith(("surface:", "skill:", "operation:")):
                raise WorkspaceUsageError(
                    f"{requirement_path.as_posix()} guideline requires a surface:, skill:, or operation: preference_target."
                )
            if blocking_claims or force not in {"informational", "recommended"}:
                raise WorkspaceUsageError(f"{requirement_path.as_posix()} guideline cannot block claims or use enforcing force.")
        elif requirement_class in {"invariant", "current-evidence"}:
            if not required_evidence or not blocking_claims or not evidence_owner or not detail_route:
                raise WorkspaceUsageError(
                    f"{requirement_path.as_posix()} hard named repo requirements require required_evidence, "
                    "blocking_claims, evidence_owner, and detail_route."
                )
            if not evidence_owner.startswith(("assurance:", "verification:", "proof:", "module:")):
                raise WorkspaceUsageError(
                    f"{requirement_path.as_posix()} evidence_owner must name an assurance:, verification:, proof:, or module: owner."
                )
            if force not in {"required-before-closeout", "blocking"}:
                raise WorkspaceUsageError(f"{requirement_path.as_posix()} hard named repo requirements require enforcing force.")
        if measurement is not None:
            if requirement_class not in {"current-evidence", "guideline"}:
                raise WorkspaceUsageError(
                    f"{requirement_path.as_posix()} measurement is supported only for current-evidence or guideline requirements."
                )
            if requirement_class == "current-evidence" and measurement["evidence_label"] not in required_evidence:
                raise WorkspaceUsageError(f"{requirement_path.as_posix()} measurement evidence_label must appear in required_evidence.")
            if not evidence_owner or not detail_route:
                raise WorkspaceUsageError(f"{requirement_path.as_posix()} measurement requires evidence_owner and detail_route.")
        requirement = AssuranceRequirement(
            id=str(requirement_id).strip(),
            level=require_required_enum(
                payload=raw_requirement,
                key="level",
                config_path=requirement_path,
                allowed=SUPPORTED_ASSURANCE_LEVELS,
            ),
            applies_to_paths=activation_values["applies_to_paths"],
            applies_to_task_markers=activation_values["applies_to_task_markers"],
            applies_to_semantic_routes=activation_values["applies_to_semantic_routes"],
            applies_to_planning_refs=activation_values["applies_to_planning_refs"],
            applies_to_proof_profiles=activation_values["applies_to_proof_profiles"],
            applies_to_risk_refs=activation_values["applies_to_risk_refs"],
            applies_to_invariant_refs=activation_values["applies_to_invariant_refs"],
            authority_refs=require_optional_string_list(payload=raw_requirement, key="authority_refs", config_path=requirement_path),
            required_evidence=required_evidence,
            proof_profile=require_optional_string(payload=raw_requirement, key="proof_profile", config_path=requirement_path),
            review_owner=require_optional_string(payload=raw_requirement, key="review_owner", config_path=requirement_path),
            force=force,
            blocking_claims=blocking_claims,
            waiver=None,
            dismissal=None,
            notes=require_optional_string(payload=raw_requirement, key="notes", config_path=requirement_path),
            requirement_class=requirement_class,
            source_intent_ref=source_intent_ref,
            source_intent_revision=source_intent_revision,
            source_intent_current=None,
            preference_target=preference_target,
            evidence_owner=evidence_owner,
            detail_route=detail_route,
            measurement=measurement,
            requirement_refs=require_optional_string_list(payload=raw_requirement, key="requirement_refs", config_path=requirement_path),
            claim_boundary=require_optional_string(payload=raw_requirement, key="claim_boundary", config_path=requirement_path),
        )
        prior_declaration = requirement_declarations.get(requirement.id)
        if prior_declaration is not None:
            prior_id, prior_requirement = prior_declaration
            prior_owner = (
                prior_requirement.source_intent_ref,
                prior_requirement.source_intent_revision,
                prior_requirement.authority_refs,
                prior_requirement.evidence_owner,
            )
            current_owner = (
                requirement.source_intent_ref,
                requirement.source_intent_revision,
                requirement.authority_refs,
                requirement.evidence_owner,
            )
            if current_owner != prior_owner:
                raise WorkspaceUsageError(
                    f"{config_path.as_posix()} assurance.requirements contains conflicting owner declarations "
                    f"for stable requirement id {requirement.id!r}: {prior_id!r} owns "
                    f"source_intent_ref={prior_requirement.source_intent_ref!r}, "
                    f"source_intent_revision={prior_requirement.source_intent_revision!r}, "
                    f"authority_refs={list(prior_requirement.authority_refs)!r}, "
                    f"evidence_owner={prior_requirement.evidence_owner!r}; {str(requirement_id)!r} owns "
                    f"source_intent_ref={requirement.source_intent_ref!r}, "
                    f"source_intent_revision={requirement.source_intent_revision!r}, "
                    f"authority_refs={list(requirement.authority_refs)!r}, "
                    f"evidence_owner={requirement.evidence_owner!r}."
                )
            if requirement != prior_requirement:
                raise WorkspaceUsageError(
                    f"{config_path.as_posix()} assurance.requirements contains divergent declarations "
                    f"for stable requirement id {requirement.id!r} under the same source owner: "
                    f"{prior_id!r} and {str(requirement_id)!r}."
                )
            continue
        requirement_declarations[requirement.id] = (str(requirement_id), requirement)
        requirements.append(requirement)
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
        "scope_refs",
        "requirement_refs",
        "required_evidence",
        "proof_profile",
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
        level_value = raw_profile.get("assurance_level")
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
        "decision_record_target",
        "decision_record_revision",
        "instruction_revision",
        "decision_record_fallback",
    }
    unknown = sorted(set(raw_assurance) - supported_fields)
    if unknown:
        raise WorkspaceUsageError(f"{config_path.as_posix()} assurance contains unsupported fields.")
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
        required_commands = require_optional_string_list(payload=profile_payload, key="required_commands", config_path=config_path)
        optional_commands = require_optional_string_list(payload=profile_payload, key="optional_commands", config_path=config_path)
        disallowed_commands = require_optional_string_list(payload=profile_payload, key="disallowed_commands", config_path=config_path)
        overlapping_roles = sorted(
            (set(required_commands) & set(optional_commands))
            | (set(required_commands) & set(disallowed_commands))
            | (set(optional_commands) & set(disallowed_commands))
        )
        if overlapping_roles:
            raise WorkspaceUsageError(
                f"{config_path.as_posix()} [assurance.proof_profiles.{profile_id}] assigns multiple command roles "
                f"to: {', '.join(overlapping_roles)}. Give each command identity exactly one of required, optional, or disallowed."
            )
        profiles.append(
            AssuranceProofProfile(
                id=str(profile_id).strip(),
                required_commands=required_commands,
                optional_commands=optional_commands,
                review_aids=require_optional_string_list(payload=profile_payload, key="review_aids", config_path=config_path),
                disallowed_commands=disallowed_commands,
            )
        )
    raw_decision_fallback = raw_assurance.get("decision_record_fallback")
    if raw_decision_fallback is not None and not isinstance(raw_decision_fallback, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [assurance.decision_record_fallback] must be a table.")
    decision_record_target = raw_assurance.get("decision_record_target")
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
    return (
        AssuranceConfig(
            default_level=default_level,
            default_level_source=default_level_source,
            classification_owner="config-native",
            classification_source=None,
            agent_may_escalate=_require_bool(payload=raw_assurance, key="agent_may_escalate", default=True, config_path=config_path),
            agent_may_deescalate=_require_bool(payload=raw_assurance, key="agent_may_deescalate", default=False, config_path=config_path),
            strict_closeout=_require_bool(payload=raw_assurance, key="strict_closeout", default=False, config_path=config_path),
            proof_profiles=tuple(profile for profile in profiles if profile.id),
            requirements=requirements,
            subsystem_profiles=subsystem_profiles,
            domain_proof_lanes=domain_proof_lanes,
            closeout_postures=(),
            test_data_policy={},
            decision_record_fallback=dict(raw_decision_fallback) if raw_decision_fallback is not None else None,
            instruction_revision=str(raw_assurance["instruction_revision"]).strip() if raw_assurance.get("instruction_revision") else None,
            decision_record_revision=str(raw_assurance["decision_record_revision"]).strip()
            if raw_assurance.get("decision_record_revision")
            else None,
            decision_record_target=str(decision_record_target).strip() if decision_record_target is not None else None,
            decision_record_format=None,
            decision_record_template=None,
            decision_record_statuses=(),
            invariant_registry=None,
            risk_registry=None,
        ),
        warnings,
    )


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


def normalize_current_economic_evidence(raw: Any, *, config_path: Path) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} must be a table.")
    supported = {"status", "marginal_cost", "resource_domain", "source", "observed_at", "expires_at"}
    unknown = sorted(set(raw) - supported)
    if unknown:
        raise WorkspaceUsageError(f"{config_path.as_posix()} contains unsupported field(s): {', '.join(unknown)}.")
    status = require_optional_enum(
        payload=raw,
        key="status",
        config_path=config_path,
        allowed=SUPPORTED_CURRENT_ECONOMIC_EVIDENCE_STATUSES,
        default="unknown",
    )
    marginal_cost = require_optional_enum(
        payload=raw,
        key="marginal_cost",
        config_path=config_path,
        allowed=SUPPORTED_CURRENT_MARGINAL_COST_CLASSES,
        default="unknown",
    )
    source = require_optional_string(payload=raw, key="source", config_path=config_path)
    observed_at = require_optional_string(payload=raw, key="observed_at", config_path=config_path)
    expires_at = require_optional_string(payload=raw, key="expires_at", config_path=config_path)
    resource_domain = require_optional_string(payload=raw, key="resource_domain", config_path=config_path)
    if status == "available" and not all((source, observed_at, expires_at)):
        raise WorkspaceUsageError(f"{config_path.as_posix()} available evidence requires source, observed_at, and expires_at.")
    return {
        "status": status,
        "marginal_cost": marginal_cost,
        "resource_domain": resource_domain,
        "source": source,
        "observed_at": observed_at,
        "expires_at": expires_at,
    }


def load_delegation_target_profiles(
    *, raw_targets: dict[str, Any], config_path: Path
) -> tuple[tuple[DelegationTargetProfile, ...], list[str]]:
    from aw_maintainer.native_conformance import transport_sources

    _validate_current_authoring({"delegation_targets": raw_targets}, local=True)
    decoded = transport_sources(raw_targets)["sources"] if raw_targets else {}
    profiles = []
    for name, raw in sorted(raw_targets.items()):
        source = decoded[name]
        if "error" in source:
            raise WorkspaceUsageError(f"{config_path} target {name}: {source['error']}")
        transports = tuple(source["transports"])
        adapter = next((item for item in transports if item["method"] in {"cli", "api"} and item["readiness"] == "configured"), None)
        profiles.append(
            DelegationTargetProfile(
                name=name,
                target_id=raw.get("target_id"),
                target_revision=raw.get("target_revision"),
                aliases=tuple(raw.get("aliases", [])),
                identity_status=raw.get("identity_status", "active"),
                revision_policy="revalidate",
                strength="unknown",
                location=raw.get("location", "either"),
                confidence=raw.get("confidence"),
                transports=transports,
                execution_methods=tuple(dict.fromkeys(item["method"] for item in transports)),
                dispatch_adapter_kind="process" if adapter and adapter["kind"] in {"process", "api"} else None,
                dispatch_command=tuple(adapter["command"]) if adapter else (),
                dispatch_output_mode=adapter["output_mode"] if adapter else "stdout",
                dispatch_timeout_seconds=adapter["timeout_seconds"] if adapter else 1800,
                task_fit=(),
                capability_classes=(),
                model_family=None,
                provider=None,
                context_capacity="unknown",
                reasoning_profile="unknown",
                cost_class=raw.get("cost_class", "unknown"),
                latency_class=raw.get("latency_class", "unknown"),
                current_economic_evidence=None,
                safe_task_classes=(),
                forbidden_task_classes=tuple(raw.get("forbidden_task_classes", [])),
                escalation_target=None,
                confidence_source=raw.get("confidence_source"),
                last_evaluation=None,
                human_control_modes=(),
                execution_guarantees=tuple(raw.get("execution_guarantees", [])),
            )
        )
    return tuple(profiles), []


def normalize_delegation_context_cost(raw: Any, *, surface_name: str) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise WorkspaceUsageError(f"{surface_name} record context_cost must be an object when present.")
    if raw.get("kind") != "agentic-workspace/assignment-context-cost/v1":
        raise WorkspaceUsageError(f"{surface_name} record context_cost kind must be agentic-workspace/assignment-context-cost/v1.")
    transport = raw.get("transport")
    if not isinstance(transport, str) or not transport.strip():
        raise WorkspaceUsageError(f"{surface_name} record context_cost transport must be a non-empty string.")
    required_integer_fields = ("assignment_packet_bytes", "rendered_prompt_bytes", "elapsed_ms")
    optional_integer_fields = (
        "effective_input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "orientation_command_count",
        "retry_count",
        "repair_loop_count",
    )
    for field_name in required_integer_fields:
        value = raw.get(field_name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise WorkspaceUsageError(f"{surface_name} record context_cost {field_name} must be a non-negative integer.")
    for field_name in optional_integer_fields:
        value = raw.get(field_name)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            raise WorkspaceUsageError(f"{surface_name} record context_cost {field_name} must be a non-negative integer or null.")
    unknown_fields = raw.get("unknown_fields", [])
    if not isinstance(unknown_fields, list) or any(not isinstance(item, str) for item in unknown_fields):
        raise WorkspaceUsageError(f"{surface_name} record context_cost unknown_fields must be a string list.")
    configuration_context = raw.get("configuration_context")
    if configuration_context is not None and (
        not isinstance(configuration_context, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", configuration_context)
    ):
        raise WorkspaceUsageError(f"{surface_name} record context_cost configuration_context must be a SHA256 identity or null.")
    return {
        "kind": "agentic-workspace/assignment-context-cost/v1",
        "transport": transport.strip(),
        "adapter_revision": str(raw.get("adapter_revision") or "").strip(),
        **({"configuration_context": configuration_context} if configuration_context is not None else {}),
        **{field_name: raw[field_name] for field_name in required_integer_fields},
        **{field_name: raw.get(field_name) for field_name in optional_integer_fields},
        "unknown_fields": list(dict.fromkeys(unknown_fields)),
        "observation_authority": "adapter-sidecar-or-host-measurement",
        "raw_transcript_stored": False,
    }


def normalize_delegation_outcome_record(raw: Any, *, surface_name: str) -> DelegationOutcomeRecord:
    if not isinstance(raw, dict):
        raise WorkspaceUsageError(f"{surface_name} records entries must be objects.")
    recorded_at = raw.get("recorded_at")
    delegation_target = raw.get("delegation_target")
    task_class = raw.get("task_class")
    scope_class = raw.get("scope_class")
    outcome = raw.get("outcome")
    handoff_sufficiency = raw.get("handoff_sufficiency")
    review_burden = raw.get("review_burden")
    escalation_required = raw.get("escalation_required")
    operation = raw.get("operation", "submit")
    record_id = raw.get("record_id", "")
    predecessor_id = raw.get("predecessor_id", "")
    authority = raw.get("authority", "local-outcome-ledger")
    confidence = raw.get("confidence", "medium")
    admission_state = raw.get("admission_state", "accepted-normalized")
    source_type = raw.get("source_type", "local-json-ledger")
    source_ref = raw.get("source_ref", WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix())
    producer_class = raw.get("producer_class", "local-operator")
    route_outcome = raw.get("route_outcome", "")
    assignment_route = raw.get("assignment_route", "")
    proof_observation = raw.get("proof_observation", "")
    review_observation = raw.get("review_observation", "")
    handoff_burden = raw.get("handoff_burden", "")
    repair_burden = raw.get("repair_burden", "")
    retry_burden = raw.get("retry_burden", "")
    restart_burden = raw.get("restart_burden", "")
    expected_burden = raw.get("expected_burden", "")
    observed_burden = raw.get("observed_burden", "")
    context_cost = normalize_delegation_context_cost(raw.get("context_cost"), surface_name=surface_name)
    scope_drift = raw.get("scope_drift", "none")
    contradiction_state = raw.get("contradiction_state", "none")
    uncertainty_state = raw.get("uncertainty_state", "unknown")
    idempotency_key = raw.get("idempotency_key", "")
    if not isinstance(recorded_at, str) or not recorded_at.strip():
        raise WorkspaceUsageError(f"{surface_name} record recorded_at must be a non-empty string.")
    if not isinstance(delegation_target, str) or not delegation_target.strip():
        raise WorkspaceUsageError(f"{surface_name} record delegation_target must be a non-empty string.")
    if not isinstance(task_class, str) or not task_class.strip():
        raise WorkspaceUsageError(f"{surface_name} record task_class must be a non-empty string.")
    if scope_class is not None and (not isinstance(scope_class, str) or not scope_class.strip()):
        raise WorkspaceUsageError(f"{surface_name} record scope_class must be a non-empty string when present.")
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
    if operation not in {"submit", "correct-or-dispute", "supersede", "prune-or-compact"}:
        raise WorkspaceUsageError(
            f"{surface_name} record operation must be one of: submit, correct-or-dispute, supersede, prune-or-compact."
        )
    for field_name, value in {
        "record_id": record_id,
        "predecessor_id": predecessor_id,
        "authority": authority,
        "confidence": confidence,
        "admission_state": admission_state,
        "source_type": source_type,
        "source_ref": source_ref,
        "producer_class": producer_class,
        "route_outcome": route_outcome,
        "assignment_route": assignment_route,
        "proof_observation": proof_observation,
        "review_observation": review_observation,
        "handoff_burden": handoff_burden,
        "repair_burden": repair_burden,
        "retry_burden": retry_burden,
        "restart_burden": restart_burden,
        "expected_burden": expected_burden,
        "observed_burden": observed_burden,
        "scope_drift": scope_drift,
        "contradiction_state": contradiction_state,
        "uncertainty_state": uncertainty_state,
        "idempotency_key": idempotency_key,
    }.items():
        if value is not None and not isinstance(value, str):
            raise WorkspaceUsageError(f"{surface_name} record {field_name} must be a string when present.")
    return DelegationOutcomeRecord(
        recorded_at=recorded_at.strip(),
        delegation_target=delegation_target.strip(),
        task_class=task_class.strip(),
        scope_class=(scope_class.strip() if isinstance(scope_class, str) and scope_class.strip() else task_class.strip()),
        outcome=outcome,
        handoff_sufficiency=handoff_sufficiency,
        review_burden=review_burden,
        escalation_required=escalation_required,
        operation=str(operation).strip(),
        record_id=str(record_id).strip(),
        predecessor_id=str(predecessor_id).strip(),
        authority=str(authority).strip() or "local-outcome-ledger",
        confidence=str(confidence).strip() or "medium",
        admission_state=str(admission_state).strip() or "accepted",
        source_type=str(source_type).strip() or "local-json-ledger",
        source_ref=str(source_ref).strip() or WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix(),
        producer_class=str(producer_class).strip() or "local-operator",
        route_outcome=str(route_outcome).strip(),
        assignment_route=str(assignment_route).strip(),
        proof_observation=str(proof_observation).strip(),
        review_observation=str(review_observation).strip(),
        handoff_burden=str(handoff_burden).strip(),
        repair_burden=str(repair_burden).strip(),
        retry_burden=str(retry_burden).strip(),
        restart_burden=str(restart_burden).strip(),
        expected_burden=str(expected_burden).strip(),
        observed_burden=str(observed_burden).strip(),
        context_cost=context_cost,
        scope_drift=str(scope_drift).strip() or "none",
        contradiction_state=str(contradiction_state).strip() or "none",
        uncertainty_state=str(uncertainty_state).strip() or "unknown",
        idempotency_key=str(idempotency_key).strip(),
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
        transport_authority=None,
        selection_objective=None,
        current_target=None,
        underfit_behavior=None,
        down_routing_behavior=None,
        human_override_policy=None,
        manual_transport_policy=None,
        clarification_mode=None,
        setup_prompt_disposition=None,
        setup_identity=None,
        setup_context_revision=None,
        setup_unresolved_concerns=(),
        setup_required_concerns=(),
        local_memory_enabled=None,
        local_memory_path=WORKSPACE_LOCAL_MEMORY_DEFAULT_PATH,
        target_guidance_enabled=None,
        user_guidance_root=None,
        target_guidance_overlay_path=WORKSPACE_LOCAL_TARGET_GUIDANCE_OVERLAY_DEFAULT_PATH,
        correction_events_path=WORKSPACE_LOCAL_CORRECTION_EVENTS_DEFAULT_PATH,
        session_logging=SessionLoggingConfig(enabled=None, path_mode="absolute", source="unset"),
        delegation_targets=(),
        local_overlay={},
        high_risk_overlay={},
        field_sources={},
    )


def _merge_local_config_payloads(*, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    if not base:
        return dict(override)
    if not override:
        return dict(base)
    from aw_maintainer.native_conformance import local_source_overlay

    return local_source_overlay(base, override)


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
    if not local_path.exists():
        return empty_mixed_agent_local_override(path=local_path, exists=False), []
    local = load_toml_payload(path=local_path, surface_name=WORKSPACE_LOCAL_CONFIG_PATH.as_posix())
    _validate_current_authoring(local, local=True)
    shared_path = _resolve_shared_local_config_path(
        raw_workspace=local.get("workspace", {}), local_path=local_path, target_root=target_root
    )
    shared: dict[str, Any] = {}
    if shared_path is not None:
        if not shared_path.is_file():
            raise WorkspaceUsageError("Configured shared-local source is unavailable.")
        shared = load_toml_payload(path=shared_path, surface_name="Shared-local configuration")
        _validate_current_authoring(shared, local=True)
    payload = _merge_local_config_payloads(base=shared, override=local)
    _validate_current_authoring(payload, local=True)
    values: dict[str, Any] = {}
    sources: dict[str, str] = {}
    for table, keys in {
        "workspace": {"enabled": "enabled", "cli_invoke": "cli_invoke"},
        "safety": {
            "safe_to_auto_run_commands": "safe_to_auto_run_commands",
            "requires_human_verification_on_pr": "requires_human_verification_on_pr",
        },
        "delegation": {
            key: key
            for key in (
                "assignment_policy",
                "transport_authority",
                "current_target",
                "human_override_policy",
                "required_execution_guarantees",
            )
        },
        "clarification": {"mode": "clarification_mode"},
    }.items():
        for key, attribute in keys.items():
            if key in payload.get(table, {}):
                value = payload[table][key]
                values[attribute] = tuple(value) if key == "required_execution_guarantees" else value
                sources[f"{table}.{key}"] = _local_config_field_source(local_payload=local, shared_payload=shared, table=table, key=key)
    logging = payload.get("session_logging", {})
    mode = logging.get("path_mode", "absolute")
    profiles, warnings = load_delegation_target_profiles(
        raw_targets=payload.get("delegation_targets", {}), config_path=WORKSPACE_LOCAL_CONFIG_PATH
    )
    return replace(
        empty_mixed_agent_local_override(path=local_path, exists=True),
        applied=bool(payload),
        shared_config_path=shared_path,
        shared_config_exists=shared_path is not None,
        shared_config_applied=bool(shared),
        field_sources=sources,
        delegation_targets=profiles,
        session_logging=SessionLoggingConfig(
            enabled=logging.get("enabled"),
            path_mode=mode,
            source=_local_config_field_source(local_payload=local, shared_payload=shared, table="session_logging", key="enabled"),
        ),
        **values,
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


def _verification_assurance_source(effective_root: Path, raw_assurance: Any) -> dict[str, Any]:
    if not isinstance(raw_assurance, dict):
        raise WorkspaceUsageError("Workspace assurance must be a table.")
    raw_assurance = dict(raw_assurance)
    strategy_path = effective_root / ".agentic-workspace/verification/manifest.toml"
    if strategy_path.exists():
        for path in (strategy_path, *strategy_path.parents):
            if path == effective_root:
                break
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                raise WorkspaceUsageError("Verification strategy source cannot traverse links.")
        if strategy_path.stat().st_size > 1_048_576:
            raise WorkspaceUsageError("Verification strategy source exceeds bounded read.")
        strategy = load_toml_payload(path=strategy_path, surface_name="Verification manifest")
        if "assurance" in strategy:
            if strategy.get("schema_version") != "agentic-workspace/verification-manifest/v1":
                raise WorkspaceUsageError("Invalid Verification strategy source version.")
            owned = strategy["assurance"]
            from importlib.resources import files

            from jsonschema import Draft202012Validator

            schema = json.loads(
                files("repo_verification_bootstrap").joinpath("contracts/assurance.schema.json").read_text(encoding="utf-8")
            )
            if not Draft202012Validator(schema).is_valid(owned):
                raise WorkspaceUsageError("Invalid Verification assurance source.")
            for field, value in owned.items():
                raw_assurance[field] = value
    return raw_assurance


def load_workspace_config(*, target_root: Path, valid_presets: set[str] | None = None) -> WorkspaceConfig:
    effective_root = discover_workspace_root(target_root) or target_root
    path = effective_root / WORKSPACE_CONFIG_PATH
    payload = load_toml_payload(path=path, surface_name=WORKSPACE_CONFIG_PATH.as_posix()) if path.exists() else {}
    _validate_current_authoring(payload, local=False)
    local, warnings = load_mixed_agent_local_override(target_root=effective_root)
    workspace = payload.get("workspace", {})

    def selected(key: str, default: Any) -> tuple[Any, str]:
        override = getattr(local, key, None)
        if override is not None:
            return override, local.field_sources.get(f"workspace.{key}", "local-override")
        return workspace.get(key, default), "repo-config" if key in workspace else "product-default"

    enabled, enabled_source = selected("enabled", True)
    invoke, invoke_source = selected("cli_invoke", DEFAULT_CLI_INVOKE)
    profile, profile_source = selected("workflow_artifact_profile", DEFAULT_WORKFLOW_ARTIFACT_PROFILE)
    latitude, latitude_source = selected("improvement_latitude", DEFAULT_IMPROVEMENT_LATITUDE)
    instruction, instruction_source, detected = resolve_effective_agent_instructions_file(
        target_root=effective_root, configured=workspace.get("agent_instructions_file")
    )
    intent, intent_warnings = resolve_system_intent_declaration(
        target_root=effective_root, raw_system_intent=payload.get("system_intent", {}), config_path=WORKSPACE_CONFIG_PATH
    )
    assurance, assurance_warnings = _load_assurance_config(
        raw_assurance=_verification_assurance_source(effective_root, payload.get("assurance", {})), config_path=WORKSPACE_CONFIG_PATH
    )
    payload_target, payload_warnings = _load_payload_target_config(
        raw_payload=payload.get("payload", {}), config_path=WORKSPACE_CONFIG_PATH
    )
    return WorkspaceConfig(
        target_root=effective_root,
        path=path,
        exists=path.exists(),
        enabled=enabled,
        enabled_source=enabled_source,
        enabled_modules=tuple(payload.get("modules", {}).get("enabled", DEFAULT_ENABLED_MODULES)),
        agent_instructions_file=instruction,
        agent_instructions_source=instruction_source,
        detected_agent_instructions_files=detected,
        workflow_artifact_profile=profile,
        workflow_artifact_profile_source=profile_source,
        improvement_latitude=latitude,
        improvement_latitude_source=latitude_source,
        cli_invoke=invoke,
        cli_invoke_source=invoke_source,
        optimization_bias=DEFAULT_OPTIMIZATION_BIAS,
        optimization_bias_source="product-default",
        advanced_features=(),
        advanced_features_source="product-default",
        maintainer_mode=False,
        maintainer_mode_source="product-default",
        update_modules=default_module_update_policies(),
        system_intent=intent,
        assurance=assurance,
        payload_target=payload_target,
        local_override=local,
        warnings=tuple(warnings + intent_warnings + assurance_warnings + payload_warnings),
    )
