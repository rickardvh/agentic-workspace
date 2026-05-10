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
    Path("llms.txt"),
    Path("docs/system-intent.md"),
    Path("docs/product-direction.md"),
)
WORKSPACE_EXTERNAL_AGENT_PATH = Path("llms.txt")
WORKSPACE_BOOTSTRAP_HANDOFF_PATH = Path(".agentic-workspace/bootstrap-handoff.md")
WORKSPACE_BOOTSTRAP_HANDOFF_RECORD_PATH = Path(".agentic-workspace/bootstrap-handoff.json")
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
SUPPORTED_OPTIMIZATION_BIASES = (
    "agent-efficiency",
    "balanced",
    "human-legibility",
)
SUPPORTED_ADVANCED_FEATURES = (
    "review_artifacts",
    "external_adapters",
)
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
SUPPORTED_CLARIFICATION_CONTROL_MODES = (
    "ask-first",
    "suggest",
    "auto-continue",
)
WORKSPACE_WORKFLOW_MARKER_START = "<!-- agentic-workspace:workflow:start -->"
WORKSPACE_WORKFLOW_MARKER_END = "<!-- agentic-workspace:workflow:end -->"
WORKSPACE_POINTER_BLOCK = (
    f"{WORKSPACE_WORKFLOW_MARKER_START}\n"
    'Before answering or editing non-trivial requests, including read-only workflow, config, delegation, or action-safety decisions, use the effective CLI invocation from `agentic-workspace start --format json` / `.agentic-workspace/config.local.toml` `[workspace].cli_invoke` when present. Run `<effective-cli> implement --changed <paths> --format json` when changed paths are known; otherwise run `<effective-cli> start --task "<task>" --format json` using the user\'s request as `<task>`. Do not substitute a bare `agentic-workspace` command when local config names a repo-local invocation; PATH may resolve a stale installed selector. Do not open raw `.agentic-workspace` files before this command; follow `immediate_next_allowed_action` and `skill_routing` first. Use `preflight` for takeover or recovery. Report repo-relative paths, not local absolute paths. If the CLI is unavailable, immediately read `.agentic-workspace/WORKFLOW.md` before any other files.\n'
    f"{WORKSPACE_WORKFLOW_MARKER_END}"
)
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
    "unknown",
)
SUPPORTED_CLI_TARGET_RELATIONS = (
    "inside-target",
    "outside-target",
    "no-target",
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
class MixedAgentLocalOverride:
    path: Path | None
    exists: bool
    applied: bool
    cli_invoke: str | None
    supports_internal_delegation: bool | None
    strong_planner_available: bool | None
    cheap_bounded_executor_available: bool | None
    prefer_internal_delegation_when_available: bool | None
    safe_to_auto_run_commands: bool | None
    requires_human_verification_on_pr: bool | None
    delegation_mode: str | None
    clarification_mode: str | None
    local_memory_enabled: bool | None
    local_memory_path: Path
    delegation_targets: tuple[DelegationTargetProfile, ...]


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


@dataclass(frozen=True)
class AssuranceConfig:
    default_level: str
    default_level_source: str
    agent_may_escalate: bool
    agent_may_deescalate: bool
    strict_closeout: bool
    proof_profiles: tuple[AssuranceProofProfile, ...]
    test_data_policy: dict[str, Any]
    decision_record_target: str | None
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
    advanced_features: tuple[str, ...]
    advanced_features_source: str
    cli_invoke: str
    cli_invoke_source: str
    detected_agent_instructions_files: tuple[str, ...]
    update_modules: dict[str, ModuleUpdatePolicy]
    workflow_obligations: tuple[WorkflowObligation, ...]
    system_intent: SystemIntentDeclaration
    assurance: AssuranceConfig
    cli_compatibility: CLICompatibilityExpectation
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


def _require_bool(*, payload: dict[str, Any], key: str, default: bool, config_path: Path) -> bool:
    if key not in payload:
        return default
    value = payload[key]
    if not isinstance(value, bool):
        raise WorkspaceUsageError(f"{config_path.as_posix()} {key} must be true or false.")
    return value


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
        "test_data_policy",
        "decision_record_target",
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
        unknown_profile = sorted(set(profile_payload) - {"required_commands", "optional_commands", "review_aids"})
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
            )
        )
    raw_test_data_policy = raw_assurance.get("test_data_policy", {})
    if raw_test_data_policy is None:
        raw_test_data_policy = {}
    if not isinstance(raw_test_data_policy, dict):
        raise WorkspaceUsageError(f"{config_path.as_posix()} [assurance.test_data_policy] section must be a table.")
    decision_record_target = raw_assurance.get("decision_record_target")
    invariant_registry = raw_assurance.get("invariant_registry")
    risk_registry = raw_assurance.get("risk_registry")
    return (
        AssuranceConfig(
            default_level=default_level,
            default_level_source=default_level_source,
            agent_may_escalate=_require_bool(payload=raw_assurance, key="agent_may_escalate", default=True, config_path=config_path),
            agent_may_deescalate=_require_bool(payload=raw_assurance, key="agent_may_deescalate", default=False, config_path=config_path),
            strict_closeout=_require_bool(payload=raw_assurance, key="strict_closeout", default=False, config_path=config_path),
            proof_profiles=tuple(profile for profile in profiles if profile.id),
            test_data_policy={str(key): value for key, value in raw_test_data_policy.items()},
            decision_record_target=str(decision_record_target).strip() if decision_record_target is not None else None,
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
    path.write_text(json.dumps(serialise_value(payload), indent=2) + "\n", encoding="utf-8")


def empty_mixed_agent_local_override(*, path: Path | None, exists: bool) -> MixedAgentLocalOverride:
    return MixedAgentLocalOverride(
        path=path,
        exists=exists,
        applied=False,
        cli_invoke=None,
        supports_internal_delegation=None,
        strong_planner_available=None,
        cheap_bounded_executor_available=None,
        prefer_internal_delegation_when_available=None,
        safe_to_auto_run_commands=None,
        requires_human_verification_on_pr=None,
        delegation_mode=None,
        clarification_mode=None,
        local_memory_enabled=None,
        local_memory_path=WORKSPACE_LOCAL_MEMORY_DEFAULT_PATH,
        delegation_targets=(),
    )


def load_mixed_agent_local_override(*, target_root: Path) -> tuple[MixedAgentLocalOverride, list[str]]:
    local_path = target_root / WORKSPACE_LOCAL_CONFIG_PATH
    warnings: list[str] = []
    if not local_path.exists():
        legacy_path = target_root / LEGACY_WORKSPACE_LOCAL_CONFIG_PATH
        if legacy_path.exists():
            local_path = legacy_path
        else:
            return empty_mixed_agent_local_override(path=local_path, exists=False), warnings

    payload = load_toml_payload(path=local_path, surface_name=WORKSPACE_LOCAL_CONFIG_PATH.as_posix())

    schema_version = payload.get("schema_version")
    if schema_version != 1:
        raise WorkspaceUsageError(
            f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} must set schema_version = 1 for the current local mixed-agent override contract."
        )

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
            "local_memory",
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
    unknown_workspace = sorted(set(raw_workspace) - {"cli_invoke"})
    if unknown_workspace:
        unknown_text = ", ".join(unknown_workspace)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [workspace] contains unsupported field(s): {unknown_text}.")
    raw_cli_invoke = raw_workspace.get("cli_invoke")
    cli_invoke = None
    if raw_cli_invoke is not None:
        if not isinstance(raw_cli_invoke, str) or not raw_cli_invoke.strip():
            raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} workspace.cli_invoke must be a non-empty string.")
        cli_invoke = raw_cli_invoke.strip()

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
    unknown_delegation = sorted(set(raw_delegation) - {"mode"})
    if unknown_delegation:
        unknown_text = ", ".join(unknown_delegation)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [delegation] contains unsupported field(s): {unknown_text}.")
    delegation_mode = raw_delegation.get("mode")
    if delegation_mode is not None:
        if not isinstance(delegation_mode, str) or delegation_mode not in SUPPORTED_DELEGATION_CONTROL_MODES:
            allowed_text = ", ".join(SUPPORTED_DELEGATION_CONTROL_MODES)
            raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} delegation.mode must be one of: {allowed_text}.")

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

    raw_local_memory = payload.get("local_memory", {})
    if raw_local_memory is None:
        raw_local_memory = {}
    if not isinstance(raw_local_memory, dict):
        raise WorkspaceUsageError(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [local_memory] section must be a table.")
    unknown_local_memory = sorted(set(raw_local_memory) - {"enabled", "path"})
    if unknown_local_memory:
        unknown_text = ", ".join(unknown_local_memory)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} [local_memory] contains unsupported field(s): {unknown_text}.")

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

    return MixedAgentLocalOverride(
        path=local_path,
        exists=True,
        applied=True,
        cli_invoke=cli_invoke,
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
        delegation_targets=delegation_targets,
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

    default_preset = "full"
    configured_agent_instructions_file: str | None = None
    workflow_artifact_profile = DEFAULT_WORKFLOW_ARTIFACT_PROFILE
    workflow_artifact_profile_source = "product-default"
    improvement_latitude = DEFAULT_IMPROVEMENT_LATITUDE
    improvement_latitude_source = "product-default"
    optimization_bias = DEFAULT_OPTIMIZATION_BIAS
    optimization_bias_source = "product-default"
    advanced_features: tuple[str, ...] = ()
    advanced_features_source = "product-default"
    cli_invoke = DEFAULT_CLI_INVOKE
    cli_invoke_source = "product-default"
    assurance, assurance_warnings = _load_assurance_config(raw_assurance={}, config_path=WORKSPACE_CONFIG_PATH)
    warnings.extend(assurance_warnings)
    cli_compatibility, cli_compatibility_warnings = _load_cli_compatibility_expectation(
        raw_cli_compatibility={},
        config_path=WORKSPACE_CONFIG_PATH,
    )
    warnings.extend(cli_compatibility_warnings)
    if local_override.cli_invoke is not None:
        cli_invoke = local_override.cli_invoke
        cli_invoke_source = "local-override"

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
            default_preset=default_preset,
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
        set(payload) - {"schema_version", "workspace", "update", "workflow_obligations", "system_intent", "assurance", "cli_compatibility"}
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
            "default_preset",
            "agent_instructions_file",
            "workflow_artifact_profile",
            "improvement_latitude",
            "optimization_bias",
            "advanced_features",
        }
    )
    if unknown_workspace:
        unknown_text = ", ".join(unknown_workspace)
        warnings.append(f"{WORKSPACE_CONFIG_PATH.as_posix()} [workspace] contains unsupported field(s): {unknown_text}.")

    configured_preset = str(raw_workspace.get("default_preset", default_preset)).strip() or default_preset
    if valid_presets and configured_preset not in valid_presets:
        supported = ", ".join(sorted(valid_presets))
        raise WorkspaceUsageError(f"{WORKSPACE_CONFIG_PATH.as_posix()} workspace.default_preset must be one of: {supported}.")

    raw_agent_instructions_file = raw_workspace.get("agent_instructions_file")
    if raw_agent_instructions_file is not None:
        configured_agent_instructions_file = validate_agent_instructions_filename(str(raw_agent_instructions_file))
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
    if local_override.cli_invoke is not None:
        cli_invoke = local_override.cli_invoke
        cli_invoke_source = "local-override"

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

    agent_instructions_file, agent_instructions_source, detected_agent_instruction_files = resolve_effective_agent_instructions_file(
        target_root=effective_root,
        configured=configured_agent_instructions_file,
    )
    return WorkspaceConfig(
        target_root=effective_root,
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
        advanced_features=advanced_features,
        advanced_features_source=advanced_features_source,
        cli_invoke=cli_invoke,
        cli_invoke_source=cli_invoke_source,
        detected_agent_instructions_files=detected_agent_instruction_files,
        update_modules=update_modules,
        workflow_obligations=workflow_obligations,
        system_intent=system_intent,
        assurance=assurance,
        cli_compatibility=cli_compatibility,
        local_override=local_override,
        warnings=tuple(warnings),
    )
