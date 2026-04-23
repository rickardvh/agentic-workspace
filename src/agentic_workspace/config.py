from __future__ import annotations

import json
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
WORKSPACE_SYSTEM_INTENT_ROOT = Path(".agentic-workspace/system-intent")
WORKSPACE_SYSTEM_INTENT_MIRROR_PATH = WORKSPACE_SYSTEM_INTENT_ROOT / "intent.toml"
WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH = WORKSPACE_SYSTEM_INTENT_ROOT / "WORKFLOW.md"
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
SUPPORTED_WORKFLOW_OBLIGATION_STAGES = (
    "pre-work",
    "before-claiming-completion",
    "before-commit",
    "review",
    "closeout",
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
    delegation_targets: tuple[DelegationTargetProfile, ...]


@dataclass(frozen=True)
class WorkflowObligation:
    name: str
    summary: str
    stage: str
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
    workflow_obligations: tuple[WorkflowObligation, ...]
    system_intent: SystemIntentDeclaration
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


def validate_agent_instructions_filename(filename: str) -> str:
    normalized = filename.strip()
    if normalized not in SUPPORTED_AGENT_INSTRUCTIONS_FILES:
        supported = ", ".join(SUPPORTED_AGENT_INSTRUCTIONS_FILES)
        raise WorkspaceUsageError(f"agent instructions filename must be one of: {supported}.")
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
        unknown_fields = sorted(set(raw_obligation) - {"summary", "stage", "scope_tags", "commands", "review_hint"})
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
        detected_sources = tuple(
            path.as_posix()
            for path in (
                Path("SYSTEM_INTENT.md"),
                Path("docs/system-intent.md"),
                Path("docs/product-direction.md"),
            )
            if (target_root / path).exists()
        )
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
        unknown_fields = sorted(
            set(raw_profile) - {"strength", "location", "confidence", "task_fit", "capability_classes", "execution_methods"}
        )
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
        supports_internal_delegation=None,
        strong_planner_available=None,
        cheap_bounded_executor_available=None,
        prefer_internal_delegation_when_available=None,
        safe_to_auto_run_commands=None,
        requires_human_verification_on_pr=None,
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

    unknown_top_level = sorted(set(payload) - {"schema_version", "runtime", "handoff", "safety", "delegation_targets"})
    if unknown_top_level:
        unknown_text = ", ".join(unknown_top_level)
        warnings.append(f"{WORKSPACE_LOCAL_CONFIG_PATH.as_posix()} contains unsupported top-level field(s): {unknown_text}.")

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
            detected_agent_instructions_files=detected_agent_instruction_files,
            update_modules=defaults,
            workflow_obligations=(),
            system_intent=SystemIntentDeclaration(
                sources=tuple(path.as_posix() for path in (Path("SYSTEM_INTENT.md"),) if (effective_root / path).exists()),
                sources_source="autodetected-existing" if (effective_root / "SYSTEM_INTENT.md").exists() else "product-default",
                preferred_source="SYSTEM_INTENT.md" if (effective_root / "SYSTEM_INTENT.md").exists() else None,
                preferred_source_source="autodetected-existing" if (effective_root / "SYSTEM_INTENT.md").exists() else "product-default",
            ),
            local_override=local_override,
            warnings=tuple(warnings),
        )

    payload = load_toml_payload(path=config_path, surface_name=WORKSPACE_CONFIG_PATH.as_posix())

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

    # Relaxed: Warn about unknown workspace fields
    unknown_workspace = sorted(
        set(raw_workspace)
        - {"default_preset", "agent_instructions_file", "workflow_artifact_profile", "improvement_latitude", "optimization_bias"}
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
        detected_agent_instructions_files=detected_agent_instruction_files,
        update_modules=update_modules,
        workflow_obligations=workflow_obligations,
        system_intent=system_intent,
        local_override=local_override,
        warnings=tuple(warnings),
    )
