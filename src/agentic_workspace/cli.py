from __future__ import annotations

import argparse
import copy
import difflib
import fnmatch
import hashlib
import json
import re
import shutil
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, NoReturn, cast

from agentic_workspace import __version__, doctor
from agentic_workspace import config as config_lib
from agentic_workspace._schema import (
    ModuleDescriptor,
    ModuleResultContract,
    RootAgentsCleanupBlock,
)
from agentic_workspace.config import (
    DEFAULT_AGENT_INSTRUCTIONS_FILE,
    DEFAULT_CLI_INVOKE,
    DEFAULT_IMPROVEMENT_LATITUDE,
    DEFAULT_OPTIMIZATION_BIAS,
    DEFAULT_WORKFLOW_ARTIFACT_PROFILE,
    DELEGATION_OUTCOMES_KIND,
    MEMORY_POINTER_BLOCK,
    MEMORY_WORKFLOW_MARKER_END,
    MEMORY_WORKFLOW_MARKER_START,
    SUPPORTED_AGENT_INSTRUCTIONS_FILES,
    SUPPORTED_CAPABILITY_EXECUTION_CLASSES,
    SUPPORTED_CAPABILITY_LOCATIONS,
    SUPPORTED_DELEGATION_OUTCOMES,
    SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS,
    SUPPORTED_DELEGATION_TARGET_STRENGTHS,
    SUPPORTED_HANDOFF_SUFFICIENCY,
    SUPPORTED_IMPROVEMENT_LATITUDES,
    SUPPORTED_OPTIMIZATION_BIASES,
    SUPPORTED_REVIEW_BURDENS,
    SUPPORTED_WORKFLOW_ARTIFACT_PROFILES,
    SUPPORTED_WORKFLOW_OBLIGATION_STAGES,
    WORKSPACE_BOOTSTRAP_HANDOFF_PATH,
    WORKSPACE_BOOTSTRAP_HANDOFF_RECORD_PATH,
    WORKSPACE_CONFIG_PATH,
    WORKSPACE_DELEGATION_OUTCOMES_PATH,
    WORKSPACE_EXTERNAL_AGENT_PATH,
    WORKSPACE_LOCAL_CONFIG_PATH,
    WORKSPACE_LOCAL_INTEGRATION_ALLOWED_AID_KINDS,
    WORKSPACE_LOCAL_INTEGRATION_BOUNDARY_RULES,
    WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH,
    WORKSPACE_LOCAL_INTEGRATION_SUBFOLDER_CONVENTION,
    WORKSPACE_LOCAL_MEMORY_DEFAULT_PATH,
    WORKSPACE_POINTER_BLOCK,
    WORKSPACE_SYSTEM_INTENT_MIRROR_PATH,
    WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH,
    WORKSPACE_WORKFLOW_MARKER_END,
    WORKSPACE_WORKFLOW_MARKER_START,
    DelegationOutcomeRecord,
    DelegationTargetProfile,
    ModuleUpdatePolicy,
    WorkspaceConfig,
    WorkspaceUsageError,
)
from agentic_workspace.contract_tooling import (
    authority_markers_manifest,
    cli_commands_manifest,
    cli_option_groups_manifest,
    compact_contract_manifest,
    context_templates_manifest,
    contract_inventory_manifest,
    improvement_latitude_policy_manifest,
    module_registry_manifest,
    optimization_bias_policy_manifest,
    preflight_policy_manifest,
    proof_routes_manifest,
    proof_selection_rules_manifest,
    repo_friction_policy_manifest,
    report_contract_manifest,
    setup_findings_policy_manifest,
    workflow_artifact_profiles_manifest,
    workflow_definition_format_manifest,
    workspace_surfaces_manifest,
)
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

_CLI_COMMANDS_MANIFEST = cli_commands_manifest()
_CLI_OPTION_GROUPS_MANIFEST = cli_option_groups_manifest()
_MODULE_REGISTRY_MANIFEST = module_registry_manifest()
_WORKSPACE_SURFACES_MANIFEST = workspace_surfaces_manifest()
_WORKFLOW_ARTIFACT_PROFILES_MANIFEST = workflow_artifact_profiles_manifest()
_WORKFLOW_DEFINITION_FORMAT = workflow_definition_format_manifest()
_IMPROVEMENT_LATITUDE_POLICY = improvement_latitude_policy_manifest()
_OPTIMIZATION_BIAS_POLICY = optimization_bias_policy_manifest()
_REPO_FRICTION_POLICY = repo_friction_policy_manifest()
_PREFLIGHT_POLICY = preflight_policy_manifest()
_PROOF_SELECTION_RULES = proof_selection_rules_manifest()
_CONTEXT_TEMPLATES = context_templates_manifest()
HIGH_RISK_COMMANDS = frozenset(str(command) for command in _PREFLIGHT_POLICY["high_risk_commands"])
PREFLIGHT_TOKEN_PREFIX = str(_PREFLIGHT_POLICY["token"]["prefix"])
DEFAULT_PREFLIGHT_MAX_AGE_SECONDS = int(_PREFLIGHT_POLICY["default_max_age_seconds"])
_PREFLIGHT_STRICT_GATE_POLICY = _PREFLIGHT_POLICY["strict_gate"]
PLACEHOLDER_RE = re.compile(r"<[A-Z][A-Z0-9_]+>")
MODULE_COMMAND_ARGS = {command_name: tuple(args) for command_name, args in _MODULE_REGISTRY_MANIFEST["module_command_args"].items()}
MIXED_AGENT_LOCAL_OVERRIDE_FIELDS = tuple(_WORKSPACE_SURFACES_MANIFEST["mixed_agent_local_override_fields"])
WORKSPACE_PAYLOAD_FILES = tuple(Path(relative) for relative in _WORKSPACE_SURFACES_MANIFEST["payload_files"])
SYSTEM_INTENT_MIRROR_KIND = str(_WORKSPACE_SURFACES_MANIFEST["system_intent_mirror_kind"])
WORKSPACE_AGENTS_PATH = Path(_WORKSPACE_SURFACES_MANIFEST["default_agents_path"])
WORKSPACE_HANDOFF_SURFACES = tuple(Path(relative) for relative in _WORKSPACE_SURFACES_MANIFEST["handoff_surfaces"])
MODULE_UPGRADE_SOURCE_PATHS = {
    module_name: Path(relative) for module_name, relative in _WORKSPACE_SURFACES_MANIFEST["module_upgrade_source_paths"].items()
}


def _load_workspace_config(*, target_root: Path, descriptors: dict[str, "ModuleDescriptor"] | None = None, **kwargs):
    """Backward-compatible alias for tests and local helpers."""
    if descriptors is not None and "valid_presets" not in kwargs:
        kwargs["valid_presets"] = set(_preset_modules(descriptors))
    return config_lib.load_workspace_config(target_root=target_root, **kwargs)


def _load_toml_payload(*args, **kwargs):
    """Alias for tests."""
    return config_lib.load_toml_payload(*args, **kwargs)


SETUP_FINDINGS_PATH = Path(_WORKSPACE_SURFACES_MANIFEST["setup_findings_path"])
_SETUP_FINDINGS_POLICY = setup_findings_policy_manifest()
SETUP_FINDINGS_KIND = str(_SETUP_FINDINGS_POLICY["accepted_kind"])
SUPPORTED_SETUP_FINDING_CLASSES = tuple(item["class"] for item in _SETUP_FINDINGS_POLICY["accepted_classes"])
SETUP_FINDING_PROMOTION_THRESHOLD = float(_SETUP_FINDINGS_POLICY["promotion_confidence_threshold"])
_WORKFLOW_ARTIFACT_PROFILE_PAYLOADS = {
    str(item["profile"]): copy.deepcopy(item) for item in _WORKFLOW_ARTIFACT_PROFILES_MANIFEST["profiles"]
}
_IMPROVEMENT_LATITUDE_PAYLOADS = {str(item["mode"]): copy.deepcopy(item) for item in _IMPROVEMENT_LATITUDE_POLICY["modes"]}
_OPTIMIZATION_BIAS_PAYLOADS = {str(item["mode"]): copy.deepcopy(item) for item in _OPTIMIZATION_BIAS_POLICY["modes"]}
_MODULE_REGISTRY_ENTRIES = {str(item["name"]): copy.deepcopy(item) for item in _MODULE_REGISTRY_MANIFEST["modules"]}
_CLI_COMMAND_MANIFESTS = {str(item["name"]): copy.deepcopy(item) for item in _CLI_COMMANDS_MANIFEST["commands"]}
_SETUP_FINDING_CLASS_PAYLOADS = {str(item["class"]): copy.deepcopy(item) for item in _SETUP_FINDINGS_POLICY["accepted_classes"]}
if str(_WORKFLOW_ARTIFACT_PROFILES_MANIFEST["default_profile"]) != DEFAULT_WORKFLOW_ARTIFACT_PROFILE:
    raise RuntimeError("workflow_artifact_profiles.json drifted from config defaults")
if str(_IMPROVEMENT_LATITUDE_POLICY["default_mode"]) != DEFAULT_IMPROVEMENT_LATITUDE:
    raise RuntimeError("improvement_latitude_policy.json drifted from config defaults")
if str(_OPTIMIZATION_BIAS_POLICY["default_mode"]) != DEFAULT_OPTIMIZATION_BIAS:
    raise RuntimeError("optimization_bias_policy.json drifted from config defaults")


def _local_integration_area_payload(*, target_root: Path | None = None) -> dict[str, Any]:
    exists = False
    if target_root is not None:
        exists = (target_root / WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH).exists()
    return {
        "root": WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH.as_posix(),
        "subfolder_convention": WORKSPACE_LOCAL_INTEGRATION_SUBFOLDER_CONVENTION,
        "example_subfolder": (WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH / "codex").as_posix(),
        "status": "available-local-only",
        "exists": exists,
        "authoritative": False,
        "git_ignored": True,
        "canonical_doc": ".agentic-workspace/docs/local-integration-area.md",
        "allowed_aid_kinds": list(WORKSPACE_LOCAL_INTEGRATION_ALLOWED_AID_KINDS),
        "boundary_rules": list(WORKSPACE_LOCAL_INTEGRATION_BOUNDARY_RULES),
    }


def _local_memory_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    local_override = config.local_override
    enabled = bool(local_override.local_memory_enabled)
    relative_path = local_override.local_memory_path or WORKSPACE_LOCAL_MEMORY_DEFAULT_PATH
    exists = False
    if config.target_root is not None:
        exists = (config.target_root / relative_path).exists()
    return {
        "status": "enabled" if enabled else "disabled",
        "enabled": enabled,
        "configured": local_override.local_memory_enabled is not None,
        "path": relative_path.as_posix(),
        "exists": exists,
        "controlled_by": WORKSPACE_LOCAL_CONFIG_PATH.as_posix(),
        "authoritative": False,
        "advisory_only": True,
        "git_ignored": True,
        "safe_to_delete": True,
        "record_shape": {
            "kind": "agentic-workspace/local-memory/v1",
            "fields": ["id", "summary", "scope", "source", "confidence", "promotion_candidate"],
        },
        "promotion_guidance": (
            "Promote manually into checked-in Memory only when the knowledge is durable, shareable, non-private, "
            "and useful beyond this machine."
        ),
        "boundary_rules": [
            "machine-local and repo-scoped",
            "not shared repo authority",
            "not a secret store",
            "does not override checked-in Memory, planning, config, or docs",
            "safe to disable or delete without changing shared behavior",
        ],
    }


_memory_cleanup_blocks = _MODULE_REGISTRY_ENTRIES["memory"]["root_agents_cleanup_blocks"]
if _memory_cleanup_blocks:
    first_memory_cleanup_block = _memory_cleanup_blocks[0]
    if str(first_memory_cleanup_block["block"]) != MEMORY_POINTER_BLOCK:
        raise RuntimeError("module_registry.json drifted from memory pointer block")
    if str(first_memory_cleanup_block["start_marker"]) != MEMORY_WORKFLOW_MARKER_START:
        raise RuntimeError("module_registry.json drifted from memory workflow start marker")
    if str(first_memory_cleanup_block["end_marker"]) != MEMORY_WORKFLOW_MARKER_END:
        raise RuntimeError("module_registry.json drifted from memory workflow end marker")


# Types moved to _schema.py


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


class ModuleSelectionError(ValueError):
    """Raised when the orchestrator cannot resolve a safe module set."""


class WorkspaceArgumentParser(argparse.ArgumentParser):
    """Parser with startup-oriented fallback guidance for invalid commands."""

    def error(self, message: str) -> NoReturn:
        if "invalid choice" in message and "command" in message:
            unknown_command = _extract_unknown_command(message)
            suggestions = _command_suggestions(unknown_command)
            if suggestions:
                suggestion_text = ", ".join(suggestions)
                message = f"{message}\nDid you mean: {suggestion_text}?"
            message = f"{message}\nStartup tip: run 'agentic-workspace preflight --format json' to recover a compact takeover context."
        super().error(message)


def _extract_unknown_command(message: str) -> str:
    match = re.search(r"invalid choice: '([^']+)'", message)
    if not match:
        return ""
    return match.group(1)


def _command_suggestions(unknown_command: str) -> list[str]:
    if not unknown_command:
        return []
    known_commands = [item["name"] for item in _CLI_COMMANDS_MANIFEST["commands"]]
    return difflib.get_close_matches(unknown_command, known_commands, n=2, cutoff=0.55)


def _build_preflight_token(*, issued_at_epoch: int) -> str:
    return f"{PREFLIGHT_TOKEN_PREFIX}{issued_at_epoch}"


def _parse_preflight_token(token: str) -> int | None:
    if not token.startswith(PREFLIGHT_TOKEN_PREFIX):
        return None
    epoch_text = token[len(PREFLIGHT_TOKEN_PREFIX) :]
    if not epoch_text.isdigit():
        return None
    return int(epoch_text)


def _enforce_preflight_gate(*, parser: argparse.ArgumentParser, args: argparse.Namespace, command_name: str) -> None:
    if command_name not in HIGH_RISK_COMMANDS:
        return
    if not bool(getattr(args, "strict_preflight", False)):
        return

    token = str(getattr(args, "preflight_token", "") or "")
    if not token:
        parser.error(str(_PREFLIGHT_STRICT_GATE_POLICY["missing_token_error"]))

    issued_at_epoch = _parse_preflight_token(token)
    if issued_at_epoch is None:
        parser.error(str(_PREFLIGHT_STRICT_GATE_POLICY["invalid_token_error"]))

    max_age_seconds = int(getattr(args, "preflight_max_age_seconds", DEFAULT_PREFLIGHT_MAX_AGE_SECONDS))
    if max_age_seconds <= 0:
        parser.error(str(_PREFLIGHT_STRICT_GATE_POLICY["non_positive_max_age_error"]))
    now_epoch = int(time.time())
    age_seconds = now_epoch - issued_at_epoch
    if age_seconds < 0:
        parser.error(str(_PREFLIGHT_STRICT_GATE_POLICY["future_token_error"]))
    if age_seconds > max_age_seconds:
        parser.error(
            str(_PREFLIGHT_STRICT_GATE_POLICY["stale_token_error_template"]).format(
                age_seconds=age_seconds,
                max_age_seconds=max_age_seconds,
            )
        )


def build_parser() -> argparse.ArgumentParser:
    parser = WorkspaceArgumentParser(
        prog=str(_CLI_COMMANDS_MANIFEST["program"]),
        description=str(_CLI_COMMANDS_MANIFEST["description"]),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command_spec in _CLI_COMMANDS_MANIFEST["commands"]:
        _add_manifest_command(subparsers, command_spec)

    return parser


def _add_selection_arguments(parser: argparse.ArgumentParser) -> None:
    _apply_option_group(parser, "selection")


def _add_init_arguments(parser: argparse.ArgumentParser) -> None:
    _apply_option_group(parser, "init")


def _add_preflight_gate_arguments(parser: argparse.ArgumentParser) -> None:
    _apply_option_group(parser, "preflight_gate")


def _add_format_argument(parser: argparse.ArgumentParser) -> None:
    _apply_option_group(parser, "format")


def _resolve_option_choices(option_spec: dict[str, Any]) -> tuple[Any, ...] | None:
    if "choices" in option_spec:
        return tuple(option_spec["choices"])
    ref = option_spec.get("choices_ref")
    if ref == "SUPPORTED_DELEGATION_OUTCOMES":
        return SUPPORTED_DELEGATION_OUTCOMES
    if ref == "SUPPORTED_HANDOFF_SUFFICIENCY":
        return SUPPORTED_HANDOFF_SUFFICIENCY
    if ref == "SUPPORTED_REVIEW_BURDENS":
        return SUPPORTED_REVIEW_BURDENS
    return None


def _resolve_option_default(option_spec: dict[str, Any]) -> Any:
    if "default" in option_spec:
        return option_spec["default"]
    ref = option_spec.get("default_ref")
    if ref == "preflight_policy.default_max_age_seconds":
        return DEFAULT_PREFLIGHT_MAX_AGE_SECONDS
    return None


def _resolve_option_type(option_spec: dict[str, Any]) -> Any:
    if option_spec.get("type") == "integer":
        return int
    return None


def _resolved_option_help(option_spec: dict[str, Any]) -> str | None:
    help_text = option_spec.get("help")
    if isinstance(help_text, str):
        return help_text
    help_template = option_spec.get("help_template")
    if isinstance(help_template, str):
        return help_template.format(default=_resolve_option_default(option_spec))
    return None


def _add_manifest_option(parser: argparse.ArgumentParser, option_spec: dict[str, Any]) -> None:
    kwargs: dict[str, Any] = {}
    action = option_spec.get("action")
    if isinstance(action, str):
        kwargs["action"] = action
    choices = _resolve_option_choices(option_spec)
    if choices is not None:
        kwargs["choices"] = choices
    if "default" in option_spec or "default_ref" in option_spec:
        kwargs["default"] = _resolve_option_default(option_spec)
    if "nargs" in option_spec:
        kwargs["nargs"] = option_spec["nargs"]
    option_type = _resolve_option_type(option_spec)
    if option_type is not None:
        kwargs["type"] = option_type
    if option_spec.get("required") is True:
        kwargs["required"] = True
    help_text = _resolved_option_help(option_spec)
    if help_text is not None:
        kwargs["help"] = help_text
    parser.add_argument(*option_spec["flags"], **kwargs)


def _apply_option_group(parser: argparse.ArgumentParser, group_name: str) -> None:
    group_spec = _CLI_OPTION_GROUPS_MANIFEST["option_groups"][group_name]
    for parent_group in group_spec.get("uses", []):
        _apply_option_group(parser, str(parent_group))
    for option_spec in group_spec.get("options", []):
        _add_manifest_option(parser, option_spec)


def _add_manifest_command(subparsers, command_spec: dict[str, Any]) -> None:
    command_parser = subparsers.add_parser(
        str(command_spec["name"]),
        help=str(command_spec["help"]),
        description=str(command_spec["help"]),
    )
    for group_name in command_spec.get("uses_option_groups", []):
        _apply_option_group(command_parser, str(group_name))
    for option_spec in command_spec.get("options", []):
        _add_manifest_option(command_parser, option_spec)
    subcommands = command_spec.get("subcommands", [])
    if isinstance(subcommands, list) and subcommands:
        child_subparsers = command_parser.add_subparsers(dest=str(command_spec.get("subcommand_dest", "subcommand")), required=True)
        for subcommand_spec in subcommands:
            _add_manifest_command(child_subparsers, subcommand_spec)


def _workflow_artifact_profile_payload(profile: str) -> dict[str, Any]:
    return copy.deepcopy(_WORKFLOW_ARTIFACT_PROFILE_PAYLOADS[profile])


def _improvement_latitude_payload(mode: str) -> dict[str, Any]:
    return copy.deepcopy(_IMPROVEMENT_LATITUDE_PAYLOADS[mode])


def _workspace_self_adaptation_payload() -> dict[str, Any]:
    return copy.deepcopy(_REPO_FRICTION_POLICY["workspace_self_adaptation"])


def _friction_response_order_payload() -> list[dict[str, Any]]:
    return copy.deepcopy(_REPO_FRICTION_POLICY["friction_response_order"])


def _workspace_self_adaptation_guardrail_payload() -> dict[str, Any]:
    return copy.deepcopy(_REPO_FRICTION_POLICY["workspace_self_adaptation_guardrail"])


def _repo_directed_improvement_evidence_threshold_payload() -> dict[str, Any]:
    return copy.deepcopy(_REPO_FRICTION_POLICY["repo_directed_improvement_threshold"])


def _validation_friction_payload() -> dict[str, Any]:
    return copy.deepcopy(_REPO_FRICTION_POLICY["validation_friction"])


def _improvement_boundary_test_payload() -> dict[str, Any]:
    return copy.deepcopy(_REPO_FRICTION_POLICY["improvement_boundary_test"])


def _optimization_bias_payload(mode: str) -> dict[str, Any]:
    return copy.deepcopy(_OPTIMIZATION_BIAS_PAYLOADS[mode])


def _setup_finding_class_payload(finding_class: str) -> dict[str, Any]:
    return copy.deepcopy(_SETUP_FINDING_CLASS_PAYLOADS[finding_class])


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
    if confidence < SETUP_FINDING_PROMOTION_THRESHOLD:
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

    if args.command == "summary":
        target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
        _validate_target_root(command_name="summary", target_root=target_root)
        try:
            from repo_planning_bootstrap.cli import _print_summary
            from repo_planning_bootstrap.installer import format_summary_json, planning_summary

            summary_profile = args.profile if args.format == "json" else "full"
            summary = planning_summary(target=target_root.as_posix(), profile=summary_profile)
            if args.format == "json":
                print(format_summary_json(summary))
            else:
                _print_summary(summary)
            return 0
        except ImportError:
            parser.error("The planning module must be installed to use the summary command.")

    if args.command == "start":
        target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
        _validate_target_root(command_name="start", target_root=target_root)
        payload = _start_payload(
            target_root=target_root,
            changed_paths=list(getattr(args, "changed", []) or []),
        )
        _emit_payload(payload=payload, format_name=args.format)
        return 0

    if args.command == "implement":
        target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
        _validate_target_root(command_name="implement", target_root=target_root)
        payload = _implement_payload(
            target_root=target_root,
            changed_paths=list(getattr(args, "changed", []) or []),
        )
        _emit_payload(payload=payload, format_name=args.format)
        return 0

    if args.command == "preflight":
        target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
        _validate_target_root(command_name="preflight", target_root=target_root)
        payload = _run_preflight_command(
            target_root=target_root,
            active_only=getattr(args, "active_only", False),
        )
        _emit_payload(payload=payload, format_name=args.format)
        return 0

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
                    changed_paths=list(getattr(args, "changed", []) or []),
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
                _emit_config(
                    format_name=args.format,
                    config=config_lib.load_workspace_config(target_root=target_root, valid_presets=set(_preset_modules(descriptors))),
                )
            return 0
        except WorkspaceUsageError as exc:
            parser.error(str(exc))

    if args.command == "setup":
        try:
            target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
            _validate_target_root(command_name="setup", target_root=target_root)
            config = config_lib.load_workspace_config(target_root=target_root, valid_presets=set(_preset_modules(descriptors)))
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

    if args.command == "system-intent":
        try:
            target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
            _validate_target_root(command_name="system-intent", target_root=target_root)
            config = config_lib.load_workspace_config(target_root=target_root, valid_presets=set(_preset_modules(descriptors)))
            _emit_system_intent(format_name=args.format, target_root=target_root, config=config, sync=bool(args.sync))
            return 0
        except (ModuleSelectionError, WorkspaceUsageError) as exc:
            parser.error(str(exc))

    if args.command in {"install", "init"}:
        try:
            repo_root = _resolve_target_root(args.target)
            _validate_target_root(command_name=args.command, target_root=repo_root, local_only=bool(args.local_only))
            _enforce_preflight_gate(parser=parser, args=args, command_name=args.command)
            target_root = repo_root / LOCAL_ONLY_INSTALL_ROOT if args.local_only else repo_root
            config = config_lib.load_workspace_config(target_root=target_root, valid_presets=set(_preset_modules(descriptors)))
            explicit_agent_instructions_file = getattr(args, "agent_instructions_file", None)
            if explicit_agent_instructions_file:
                config = _with_agent_instructions_file(
                    config,
                    filename=config_lib.validate_agent_instructions_filename(explicit_agent_instructions_file),
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

        payload = _run_init(
            target_root=target_root,
            local_only_repo_root=repo_root if args.local_only else None,
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
        payload["command"] = args.command
        _emit_payload(payload=payload, format_name=args.format)
        return 0

    if args.command == "reconcile":
        try:
            target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
            _validate_target_root(command_name="reconcile", target_root=target_root)
            from repo_planning_bootstrap.cli import _print_reconcile
            from repo_planning_bootstrap.installer import planning_reconcile
        except ImportError:
            parser.error("The planning module must be installed to use the reconcile command.")
        except WorkspaceUsageError as exc:
            parser.error(str(exc))
        payload = planning_reconcile(target=target_root)
        if args.format == "json":
            _emit_payload(payload=payload, format_name=args.format)
        else:
            _print_reconcile(payload)
        return 0

    local_only_repo_root: Path | None = None
    try:
        if args.command == "uninstall" and bool(getattr(args, "local_only", False)):
            local_only_repo_root = _resolve_target_root(args.target)
            _validate_target_root(command_name=args.command, target_root=local_only_repo_root, local_only=True)
            target_root = local_only_repo_root / LOCAL_ONLY_INSTALL_ROOT
        else:
            target_root = _resolve_target_root(args.target)
            _validate_target_root(command_name=args.command, target_root=target_root)
        _enforce_preflight_gate(parser=parser, args=args, command_name=args.command)
        config = config_lib.load_workspace_config(target_root=target_root, valid_presets=set(_preset_modules(descriptors)))
        explicit_agent_instructions_file = getattr(args, "agent_instructions_file", None)
        if explicit_agent_instructions_file:
            config = _with_agent_instructions_file(
                config,
                filename=config_lib.validate_agent_instructions_filename(explicit_agent_instructions_file),
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
        if getattr(args, "startup", False):
            try:
                _emit_startup_report(format_name=args.format, target_root=target_root, descriptors=descriptors, config=config)
                return 0
            except WorkspaceUsageError as exc:
                parser.error(str(exc))
        payload = _run_report_command(
            target_root=target_root,
            selected_modules=selected_modules,
            resolved_preset=resolved_preset,
            descriptors=descriptors,
            config=config,
        )
        try:
            payload = _select_report_payload(
                payload,
                profile=str(getattr(args, "profile", "router")),
                section=getattr(args, "section", None),
            )
        except WorkspaceUsageError as exc:
            parser.error(str(exc))
        if payload.get("health") != "healthy" and args.format == "json":
            import sys

            print(f"DEBUG findings: {payload.get('findings')}", file=sys.stderr)
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
        local_only_repo_root=local_only_repo_root,
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

    handlers = {
        "planning": {
            "install_handler": planning_install_bootstrap,
            "adopt_handler": planning_adopt_bootstrap,
            "upgrade_handler": planning_upgrade_bootstrap,
            "uninstall_handler": planning_uninstall_bootstrap,
            "doctor_handler": planning_doctor_bootstrap,
            "status_handler": planning_collect_status,
            "detector": lambda target_root: (
                (target_root / ".agentic-workspace" / "planning" / "state.toml").exists()
                and (target_root / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
            ),
        },
        "memory": {
            "install_handler": memory_install_bootstrap,
            "adopt_handler": memory_adopt_bootstrap,
            "upgrade_handler": memory_upgrade_bootstrap,
            "uninstall_handler": memory_uninstall_bootstrap,
            "doctor_handler": memory_doctor_bootstrap,
            "status_handler": memory_collect_status,
            "detector": lambda target_root: (
                (target_root / ".agentic-workspace" / "memory" / "repo" / "index.md").exists()
                and (target_root / ".agentic-workspace" / "memory").exists()
            ),
        },
    }
    return {
        module_name: _build_module_descriptor(
            name=module_name,
            metadata=_MODULE_REGISTRY_ENTRIES[module_name],
            install_handler=cast(Callable[..., Any], handler_bundle["install_handler"]),
            adopt_handler=cast(Callable[..., Any], handler_bundle["adopt_handler"]),
            upgrade_handler=cast(Callable[..., Any], handler_bundle["upgrade_handler"]),
            uninstall_handler=cast(Callable[..., Any], handler_bundle["uninstall_handler"]),
            doctor_handler=cast(Callable[..., Any], handler_bundle["doctor_handler"]),
            status_handler=cast(Callable[..., Any], handler_bundle["status_handler"]),
            detector=cast(Callable[[Path], bool], handler_bundle["detector"]),
        )
        for module_name, handler_bundle in handlers.items()
    }


def _build_module_descriptor(
    *,
    name: str,
    metadata: dict[str, Any],
    install_handler: Callable[..., Any],
    adopt_handler: Callable[..., Any],
    upgrade_handler: Callable[..., Any],
    uninstall_handler: Callable[..., Any],
    doctor_handler: Callable[..., Any],
    status_handler: Callable[..., Any],
    detector: Callable[[Path], bool],
) -> ModuleDescriptor:
    result_contract = ModuleResultContract(
        schema_version=str(metadata["result_contract"]["schema_version"]),
        guaranteed_fields=tuple(metadata["result_contract"]["guaranteed_fields"]),
        action_fields=tuple(metadata["result_contract"]["action_fields"]),
        warning_fields=tuple(metadata["result_contract"]["warning_fields"]),
    )
    root_agents_cleanup_blocks = tuple(
        RootAgentsCleanupBlock(
            block=str(block["block"]),
            start_marker=str(block["start_marker"]),
            end_marker=str(block["end_marker"]),
            label=str(block["label"]),
        )
        for block in metadata["root_agents_cleanup_blocks"]
    )
    return ModuleDescriptor(
        name=name,
        description=str(metadata["description"]),
        commands={
            "install": lambda *, target, dry_run, force: install_handler(target=target, dry_run=dry_run, force=force),
            "adopt": lambda *, target, dry_run: adopt_handler(target=target, dry_run=dry_run),
            "upgrade": lambda *, target, dry_run: upgrade_handler(target=target, dry_run=dry_run),
            "uninstall": lambda *, target, dry_run: uninstall_handler(target=target, dry_run=dry_run),
            "doctor": lambda *, target: doctor_handler(target=target),
            "status": lambda *, target: status_handler(target=target),
        },
        detector=detector,
        selection_rank=int(metadata["selection_rank"]),
        include_in_full_preset=bool(metadata["include_in_full_preset"]),
        install_signals=tuple(Path(path) for path in metadata["install_signals"]),
        workflow_surfaces=tuple(Path(path) for path in metadata["workflow_surfaces"]),
        generated_artifacts=tuple(Path(path) for path in metadata["generated_artifacts"]),
        command_args=MODULE_COMMAND_ARGS,
        startup_steps=tuple(metadata["startup_steps"]),
        sources_of_truth=tuple(metadata["sources_of_truth"]),
        root_agents_cleanup_blocks=root_agents_cleanup_blocks,
        capabilities=tuple(metadata["capabilities"]),
        dependencies=tuple(metadata["dependencies"]),
        conflicts=tuple(metadata["conflicts"]),
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
    cli_invoke: str = DEFAULT_CLI_INVOKE,
) -> str:
    _ = workflow_artifact_profile
    _ = selected_modules
    _ = descriptors

    lines = [
        "# Agent Instructions",
        "",
        "Authority marker:",
        "",
        "- authority: adapter",
        "- canonical_source: `.agentic-workspace/config.toml` and `agentic-workspace start --target . --format json`",
        "- safe_to_edit: true",
        "- refresh_command: null",
        "",
        WORKSPACE_POINTER_BLOCK,
        "",
        "Keep this file thin. Treat it as the repo-owned startup adapter over the structured workspace surfaces under `.agentic-workspace/`.",
        "",
        "## Startup",
        "",
        f"- Use `{cli_invoke} preflight --format json` when you want startup guidance, resolved config, and active state in one compact answer.",
        f"- Use `{cli_invoke} defaults --section startup --format json` when startup order or first-contact routing is the question.",
        f"- Use `{cli_invoke} config --target . --format json` when the configured entrypoint, posture, or workflow obligations matter.",
        f"- Use `{cli_invoke} summary --format json` when only active planning or ownership state is the question.",
        "- Open module, planning, memory, or deeper routing files only when the compact answers point there.",
        "- Read package-local `AGENTS.md` only for the package being edited.",
    ]
    lines.extend(
        [
            "",
            "## Repo Rules",
            "",
            "Do not start coding from chat context alone when the same information exists in checked-in files.",
            "Do not bulk-read all planning surfaces.",
            "Keep package boundaries explicit.",
            "Preserve independent package versioning and CLI entry points.",
            "Keep repo-custom workflow obligations in `.agentic-workspace/config.toml`; let `AGENTS.md` stay a compact router.",
        ]
    )
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
    installed_modules = [
        module_name for module_name in _ordered_module_names(descriptors) if descriptors[module_name].detector(target_root)
    ]
    expected_handoff = _external_agent_handoff_text(
        selected_modules=installed_modules or selected_modules,
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

    for config_warning in config.warnings:
        warnings.append({"path": config.path.as_posix() if config.path else ".agentic-workspace/config.toml", "message": config_warning})

    if command_name == "doctor":
        abs_paths = doctor.check_absolute_paths(target_root)
        for finding in abs_paths:
            actions.append(
                {
                    "kind": "warning",
                    "path": finding.path.as_posix(),
                    "detail": f"absolute path found at {finding.line}:{finding.column}: {finding.value}",
                }
            )
            warnings.append({"path": finding.path.as_posix(), "message": f"absolute path found: {finding.value}"})

        integrity_errors = doctor.check_contract_integrity()
        for error in integrity_errors:
            warnings.append({"path": "src/agentic_workspace/contracts/", "message": f"contract drift: {error}"})

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
        "# Agent Entrypoint Router",
        "",
        "Authority marker:",
        "",
        "- authority: generated-adapter",
        "- canonical_source: `src/agentic_workspace/cli.py:_external_agent_handoff_text`",
        "- safe_to_edit: false",
        "- refresh_command: `make maintainer-surfaces`",
        "",
        "This file is the agent entrypoint router.",
        "Treat it as a lightweight compatibility adapter over the structured workspace config, not as the primary authority.",
        "",
        "Use Agentic Workspace as the lifecycle front door for the repository that contains this file.",
        "",
        "Target repository:",
        "- the repository containing this llms.txt file",
        "",
        "Default startup path:",
        f"- Read `{agent_instructions_file}` first.",
        "- Then run `agentic-workspace preflight --format json` when you want startup guidance, resolved config, and active state in one compact answer.",
        "- Then run `agentic-workspace defaults --section startup --format json` for the ordered compact startup route.",
        "- Run `agentic-workspace config --target ./repo --format json` when the configured startup entrypoint, posture, or workflow obligations matter.",
        "- Run `agentic-workspace summary --format json` when active planning or ownership state matters.",
        "- Do not assume agentic-workspace is already installed; follow the checked-in lifecycle instructions in this repository.",
        "- For lifecycle work, use agentic-workspace rather than package-specific CLIs unless package-local debugging is required.",
        "",
        "When needed:",
        "- Read `.agentic-workspace/docs/routing-contract.md` only when lifecycle or install/adopt routing is still ambiguous after the compact startup path.",
        "- For compact configuration queries beyond startup order, prefer `agentic-workspace defaults --section agent_configuration_queries --format json` before broader prose.",
        "- Open `.agentic-workspace/planning/state.toml` and the active execplan only when `agentic-workspace summary --format json` points there.",
        "",
        "Preferred lifecycle commands:",
    ]
    if selected_modules == ["planning"]:
        lines.append("- `agentic-workspace install --target ./repo --preset planning`")
    elif selected_modules == ["memory"]:
        lines.append("- `agentic-workspace install --target ./repo --preset memory`")
    else:
        lines.append("- `agentic-workspace install --target ./repo --preset full`")
    lines.extend(
        [
            "- `agentic-workspace config --target ./repo --format json`",
            "- `agentic-workspace summary --format json`",
            "- `agentic-workspace report --target ./repo --format json`",
            "",
            "Quick state check:",
            "- If `.agentic-workspace/config.local.toml` is present, use the config report to see local capability/cost posture without treating it as checked-in repo policy.",
            "",
            "Rules:",
            "- Keep this file lightweight.",
            "- Keep planning and memory ownership boundaries explicit.",
            f"- Workflow artifact profile: {artifact_profile['profile']}.",
            f"- {artifact_profile['sync_rule']}",
            "",
            "Success means:",
            f"- `{agent_instructions_file}` remains the repo startup entrypoint",
            "- `llms.txt` stays aligned with the installed workspace contract",
            "",
        ]
    )
    return "\n".join(lines)


def _external_agent_handoff_text_for_target(*, target_root: Path) -> str:
    descriptors = _module_operations()
    config = _load_workspace_config(target_root=target_root, descriptors=descriptors)
    selected_modules, _resolved_preset = _selected_modules(
        command_name="report",
        preset_name=None,
        module_arg=None,
        target_root=target_root,
        descriptors=descriptors,
        config=config,
    )
    return _external_agent_handoff_text(
        selected_modules=selected_modules,
        agent_instructions_file=config.agent_instructions_file,
        workflow_artifact_profile=config.workflow_artifact_profile,
    )


def _write_generated_text(*, destination: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


LOCAL_ONLY_INSTALL_ROOT = Path(".agentic-workspace") / "local-only"
LOCAL_ONLY_IGNORE_BLOCK = "# Agentic Workspace local-only storage\n.agentic-workspace/\n"
LOCAL_ONLY_STATE_FILE = Path("LOCAL-ONLY.toml")


def _repo_git_dir(repo_root: Path) -> Path:
    git_path = repo_root / ".git"
    if git_path.is_dir():
        return git_path
    if git_path.is_file():
        gitdir_text = git_path.read_text(encoding="utf-8").strip()
        if gitdir_text.lower().startswith("gitdir:"):
            gitdir_value = gitdir_text.split(":", 1)[1].strip()
            gitdir_path = Path(gitdir_value)
            return gitdir_path if gitdir_path.is_absolute() else (repo_root / gitdir_path).resolve()
    raise WorkspaceUsageError("Could not resolve the repository git directory for local-only residue management.")


def _local_only_exclude_path(*, repo_root: Path) -> Path:
    return _repo_git_dir(repo_root) / "info" / "exclude"


def _local_only_state_text() -> str:
    return "\n".join(
        (
            "schema_version = 1",
            'mode = "local-only"',
            'repo_hook = ".git/info/exclude"',
            "",
        )
    )


def _local_only_state_path(*, target_root: Path) -> Path:
    return target_root / LOCAL_ONLY_STATE_FILE


def _write_local_only_state(*, target_root: Path, dry_run: bool) -> dict[str, str]:
    state_path = _local_only_state_path(target_root=target_root)
    rendered_text = _local_only_state_text()
    existing_text = state_path.read_text(encoding="utf-8") if state_path.exists() else None
    if existing_text == rendered_text:
        return {
            "kind": "current",
            "path": LOCAL_ONLY_STATE_FILE.as_posix(),
            "detail": "local-only package-owned state already current",
        }
    if not dry_run:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(rendered_text, encoding="utf-8")
    return {
        "kind": "would create" if dry_run and existing_text is None else "would update" if dry_run else "created",
        "path": LOCAL_ONLY_STATE_FILE.as_posix(),
        "detail": "record local-only package-owned state inside the package install tree",
    }


def _remove_local_only_state(*, target_root: Path, dry_run: bool) -> dict[str, str]:
    state_path = _local_only_state_path(target_root=target_root)
    if not state_path.exists():
        return {
            "kind": "skipped",
            "path": LOCAL_ONLY_STATE_FILE.as_posix(),
            "detail": "no local-only package-owned state to remove",
        }
    if not dry_run:
        state_path.unlink()
    return {
        "kind": "would remove" if dry_run else "removed",
        "path": LOCAL_ONLY_STATE_FILE.as_posix(),
        "detail": "remove the local-only package-owned state file",
    }


def _append_local_only_git_exclude(*, repo_root: Path, dry_run: bool) -> dict[str, str]:
    exclude_path = _local_only_exclude_path(repo_root=repo_root)
    existing_text = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    if LOCAL_ONLY_IGNORE_BLOCK in existing_text:
        return {
            "kind": "current",
            "path": ".git/info/exclude",
            "detail": "local-only workspace storage already ignored",
        }

    updated_text = existing_text.rstrip()
    addition = "\n" + LOCAL_ONLY_IGNORE_BLOCK
    rendered_text = (updated_text + addition) if updated_text else addition.lstrip("\n")
    if not dry_run:
        exclude_path.parent.mkdir(parents=True, exist_ok=True)
        exclude_path.write_text(rendered_text, encoding="utf-8")
    return {
        "kind": "would create" if dry_run and not exclude_path.exists() else "would update" if dry_run else "created",
        "path": ".git/info/exclude",
        "detail": "record .agentic-workspace/ in git-local exclude metadata for local-only workspace storage",
    }


def _remove_local_only_git_exclude(*, repo_root: Path, dry_run: bool) -> dict[str, str]:
    exclude_path = _local_only_exclude_path(repo_root=repo_root)
    existing_text = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    if LOCAL_ONLY_IGNORE_BLOCK not in existing_text:
        return {
            "kind": "skipped",
            "path": ".git/info/exclude",
            "detail": "no local-only workspace ignore block to remove",
        }

    rendered_text = existing_text.replace(LOCAL_ONLY_IGNORE_BLOCK, "")
    if not rendered_text.strip():
        if not dry_run:
            exclude_path.write_text("", encoding="utf-8")
        return {
            "kind": "would remove" if dry_run else "removed",
            "path": ".git/info/exclude",
            "detail": "remove the local-only workspace ignore block and leave the git-local exclude file empty",
        }

    if not dry_run:
        exclude_path.write_text(rendered_text, encoding="utf-8")
    return {
        "kind": "would update" if dry_run else "updated",
        "path": ".git/info/exclude",
        "detail": "remove the local-only workspace ignore block",
    }


def _remove_legacy_local_only_gitignore(*, repo_root: Path, dry_run: bool) -> dict[str, str]:
    gitignore_path = repo_root / ".gitignore"
    existing_text = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    if LOCAL_ONLY_IGNORE_BLOCK not in existing_text:
        return {
            "kind": "skipped",
            "path": ".gitignore",
            "detail": "no legacy local-only workspace ignore block to remove",
        }

    rendered_text = existing_text.replace(LOCAL_ONLY_IGNORE_BLOCK, "")
    if not rendered_text.strip():
        if not dry_run and gitignore_path.exists():
            gitignore_path.unlink()
        return {
            "kind": "would remove" if dry_run else "removed",
            "path": ".gitignore",
            "detail": "remove the legacy local-only workspace ignore block and the empty .gitignore file",
        }

    if not dry_run:
        gitignore_path.write_text(rendered_text, encoding="utf-8")
    return {
        "kind": "would update" if dry_run else "updated",
        "path": ".gitignore",
        "detail": "remove the legacy local-only workspace ignore block",
    }


def _workspace_init_or_upgrade_report(
    *,
    target_root: Path,
    local_only_repo_root: Path | None,
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
        cli_invoke=config.cli_invoke,
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

    if local_only_repo_root is not None:
        actions.append(_write_local_only_state(target_root=target_root, dry_run=dry_run))
        actions.append(_remove_legacy_local_only_gitignore(repo_root=local_only_repo_root, dry_run=dry_run))
        actions.append(_append_local_only_git_exclude(repo_root=local_only_repo_root, dry_run=dry_run))

    return _workspace_report(
        target_root=target_root,
        message=f"{command_name.title()} report",
        dry_run=dry_run,
        actions=actions,
        warnings=warnings,
    )


def _workspace_uninstall_report(*, target_root: Path, dry_run: bool, local_only_repo_root: Path | None = None) -> dict[str, Any]:
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
        if local_only_repo_root is not None and target_root.exists():
            actions.append(_remove_local_only_state(target_root=target_root, dry_run=dry_run))
            shutil.rmtree(target_root)
    if local_only_repo_root is not None:
        if dry_run and target_root.exists():
            actions.append(
                {
                    "kind": "would remove",
                    "path": target_root.as_posix(),
                    "detail": "remove the entire local-only workspace install tree",
                }
            )
        actions.append(_remove_local_only_git_exclude(repo_root=local_only_repo_root, dry_run=dry_run))
        actions.append(_remove_legacy_local_only_gitignore(repo_root=local_only_repo_root, dry_run=dry_run))

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


def _validate_target_root(*, command_name: str, target_root: Path, local_only: bool = False) -> None:
    if not target_root.exists():
        raise WorkspaceUsageError(f"Target path does not exist: {target_root}")
    if not target_root.is_dir():
        raise WorkspaceUsageError(f"Target path is not a directory: {target_root}")
    if (
        command_name in {"init", "install", "status", "doctor", "upgrade", "uninstall"}
        and not local_only
        and not _is_git_repo_root(target_root)
    ):
        raise WorkspaceUsageError("Target must be a git repository root with a .git directory or file.")


def _is_git_repo_root(target_root: Path) -> bool:
    return (target_root / ".git").exists()


def _run_init(
    *,
    target_root: Path,
    local_only_repo_root: Path | None,
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
            local_only_repo_root=local_only_repo_root,
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
    local_only_repo_root: Path | None,
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
                local_only_repo_root=None,
                selected_modules=selected_modules,
                descriptors=descriptors,
                dry_run=dry_run,
                inspection_mode="upgrade",
                command_name=command_name,
                config=config,
            )
        )
    elif command_name == "uninstall":
        reports.append(
            _workspace_uninstall_report(
                target_root=target_root,
                dry_run=dry_run,
                local_only_repo_root=local_only_repo_root,
            )
        )
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
        local_only_repo_root=None,
        selected_modules=selected_modules,
        resolved_preset=resolved_preset,
        descriptors=descriptors,
        dry_run=False,
        non_interactive=False,
        config=config,
    )
    warnings = list(status_payload.get("warnings", []))
    aggregated_findings: list[dict[str, Any]] = []
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
        aggregated_findings.append(finding)

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
        module_findings = cast(Any, module_report.get("findings"))
        if isinstance(module_findings, list):
            for finding in module_findings:
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
    branch_workflow_posture = _branch_workflow_posture_payload(target_root=target_root)
    local_memory = _local_memory_payload(config=config)
    closeout_trust = _report_closeout_trust_payload(module_reports=module_reports)
    surface_value_guardrail = _surface_value_guardrail_payload()
    payload = {
        "kind": "workspace-report/v1",
        "schema": _reporting_schema_payload(),
        "command": "report",
        "target": target_root.as_posix(),
        "selected_modules": selected_modules,
        "installed_modules": installed_modules,
        "health": status_payload["health"],
        "report_profile": _report_profile_payload(),
        "output_contract": output_contract_payload(
            optimization_bias=config.optimization_bias,
            optimization_bias_source=config.optimization_bias_source,
            bias_payload=_optimization_bias_payload(config.optimization_bias),
            surface="report",
        ),
        "branch_workflow_posture": branch_workflow_posture,
        "local_memory": local_memory,
        "execution_shape": execution_shape,
        "agent_configuration_system": _agent_configuration_report_payload(
            config=config,
            installed_modules=installed_modules,
        ),
        "agent_configuration_queries": _agent_configuration_queries_report_payload(
            installed_modules=installed_modules,
            active_direction=_effective_active_direction_payload(module_reports=module_reports),
        ),
        "system_intent_mirror": _system_intent_report_payload(
            target_root=target_root,
            config=config,
        ),
        "workflow_obligations": _workflow_obligations_report_payload(
            config=config,
            active_planning_record=_active_planning_record(module_reports=module_reports),
        ),
        "surface_value_guardrail": surface_value_guardrail,
        "effective_authority": _effective_authority_payload(
            target_root=target_root,
            config=config,
            installed_modules=installed_modules,
            module_reports=module_reports,
        ),
        "findings": aggregated_findings,
        "closeout_trust": closeout_trust,
        "next_action": next_action,
        "discovery": discovery,
        "standing_intent": standing_intent,
        "repo_friction": repo_friction,
        "registry": status_payload["registry"],
        "config": status_payload["config"],
        "reports": status_payload["reports"],
        "module_reports": module_reports,
    }
    payload["operational_compression"] = _operational_compression_payload(
        report_payload=payload,
        module_reports=module_reports,
        findings=aggregated_findings,
        surface_value_guardrail=surface_value_guardrail,
    )
    return payload


def _operational_compression_payload(
    *,
    report_payload: dict[str, Any],
    module_reports: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    surface_value_guardrail: dict[str, Any],
) -> dict[str, Any]:
    planning_report = next(
        (report for report in module_reports if isinstance(report, dict) and report.get("module") == "planning"),
        {},
    )
    memory_report = next(
        (report for report in module_reports if isinstance(report, dict) and report.get("module") == "memory"),
        {},
    )
    planning_report = planning_report if isinstance(planning_report, dict) else {}
    memory_report = memory_report if isinstance(memory_report, dict) else {}

    report_profile = report_payload.get("report_profile", {})
    schema = report_payload.get("schema", {})
    decision_grade_fields = _list_payload(report_profile.get("decision_grade_fields") if isinstance(report_profile, dict) else [])
    high_volume_sections = _list_payload(report_profile.get("high_volume_sections") if isinstance(report_profile, dict) else [])
    shared_fields = _list_payload(schema.get("shared_fields") if isinstance(schema, dict) else [])
    section_hints = _report_section_hints({**report_payload, "operational_compression": {}})

    memory_habitual_pull = memory_report.get("habitual_pull", {}) if isinstance(memory_report, dict) else {}
    memory_evidence = memory_habitual_pull.get("evidence", {}) if isinstance(memory_habitual_pull, dict) else {}
    durable_facts = memory_report.get("durable_facts", {}) if isinstance(memory_report, dict) else {}
    durable_fact_records = _list_payload(durable_facts.get("records") if isinstance(durable_facts, dict) else [])

    ownership_review = planning_report.get("ownership_review", {}) if isinstance(planning_report, dict) else {}
    authority_surfaces = _list_payload(ownership_review.get("authority_surfaces") if isinstance(ownership_review, dict) else [])
    managed_fences = _list_payload(ownership_review.get("managed_fences") if isinstance(ownership_review, dict) else [])

    closeout_distillation = planning_report.get("closeout_distillation", {}) if isinstance(planning_report, dict) else {}
    closeout_counts = closeout_distillation.get("counts", {}) if isinstance(closeout_distillation, dict) else {}
    archived_distillation = _archived_plan_distillation_measure(target=report_payload.get("target"))
    intent_validation = planning_report.get("intent_validation", {}) if isinstance(planning_report, dict) else {}
    intent_counts = intent_validation.get("counts", {}) if isinstance(intent_validation, dict) else {}
    current_external_work = intent_validation.get("current_external_work", {}) if isinstance(intent_validation, dict) else {}

    durable_metadata_records = authority_surfaces + durable_fact_records
    missing_metadata = [
        {
            "surface": str(record.get("surface") or record.get("id") or record.get("path") or ""),
            "missing": _missing_metadata_fields(record, required=("owner", "authority", "summary")),
        }
        for record in durable_metadata_records
        if isinstance(record, dict) and _missing_metadata_fields(record, required=("owner", "authority", "summary"))
    ]
    adapter_missing_removal_paths = [
        str(record.get("file") or record.get("surface") or record.get("name") or "")
        for record in managed_fences
        if isinstance(record, dict) and not str(record.get("uninstall_policy", "")).strip()
    ]

    measures = {
        "first_line_startup_read_surface_count": {
            "status": "measured",
            "count": len(_list_payload(report_payload.get("selected_modules"))) + 1,
            "sources": [
                "AGENTS.md workflow pointer",
                "installed module routing from report.selected_modules",
            ],
            "advisory": "New first-line startup surfaces should replace, merge, or background an existing route.",
        },
        "default_report_size_or_warning_count": {
            "status": "measured",
            "shared_field_count": len(shared_fields),
            "decision_grade_field_count": len(decision_grade_fields),
            "section_hint_count": len(section_hints),
            "high_volume_section_count": len(high_volume_sections),
            "warning_count": len(findings),
            "sources": ["report.schema.shared_fields", "report.report_profile", "report.findings"],
        },
        "routed_memory_pull_size": {
            "status": "measured" if memory_evidence else "unavailable",
            "average_routed_note_count": memory_evidence.get("average_routed_note_count"),
            "average_routed_line_count": memory_evidence.get("average_routed_line_count"),
            "durable_fact_count": memory_evidence.get("durable_fact_count", len(durable_fact_records)),
            "durable_fact_matched_case_count": memory_evidence.get("durable_fact_matched_case_count"),
            "durable_facts_smaller_or_more_precise": memory_evidence.get("durable_facts_smaller_or_more_precise"),
            "sources": ["memory.habitual_pull.evidence", "memory.durable_facts.routing_measure"],
        },
        "durable_surface_metadata": {
            "status": "measured",
            "record_count": len(durable_metadata_records),
            "missing_metadata_count": len(missing_metadata),
            "sample_missing_metadata": missing_metadata[:5],
            "required_metadata": ["owner", "authority", "summary"],
            "sources": ["planning.ownership_review.authority_surfaces", "memory.durable_facts.records"],
        },
        "additive_surface_replacement_pressure": {
            "status": "available-advisory-gate",
            "preference_count": len(_list_payload(surface_value_guardrail.get("preference_order"))),
            "value_question_count": len(_list_payload(surface_value_guardrail.get("value_questions"))),
            "review_gate": surface_value_guardrail.get("review_gate", {}),
            "sources": ["surface_value_guardrail"],
        },
        "archived_plan_distillation": {
            "status": "measured",
            "active_closeout_status": (
                closeout_distillation.get("status", "unavailable") if isinstance(closeout_distillation, dict) else "unavailable"
            ),
            "promoted_or_routed_count": closeout_counts.get("promoted_or_routed_count"),
            "intentionally_discarded_count": closeout_counts.get("intentionally_discarded_count"),
            **archived_distillation,
            "sources": ["planning.closeout_distillation.counts", ".agentic-workspace/planning/execplans/archive/*.plan.json"],
        },
        "unresolved_external_work_routing": {
            "status": current_external_work.get("status", "unavailable") if isinstance(current_external_work, dict) else "unavailable",
            "tracked_open_count": intent_counts.get("tracked_external_open_count"),
            "untracked_open_count": intent_counts.get("untracked_external_open_count"),
            "provider_rule": current_external_work.get("provider_rule", "") if isinstance(current_external_work, dict) else "",
            "sources": ["planning.intent_validation"],
        },
        "adapter_surface_lifecycle": {
            "status": "measured",
            "adapter_count": len(managed_fences),
            "missing_removal_path_count": len(adapter_missing_removal_paths),
            "sample_missing_removal_paths": adapter_missing_removal_paths[:5],
            "sources": ["planning.ownership_review.managed_fences"],
        },
    }

    advisory_signals: list[dict[str, Any]] = []
    if len(findings) > 0:
        advisory_signals.append(
            {
                "severity": "advisory",
                "measure": "default_report_size_or_warning_count",
                "message": "Report findings are present; inspect warning_summary before declaring the workspace quiet.",
                "count": len(findings),
            }
        )
    if missing_metadata:
        advisory_signals.append(
            {
                "severity": "advisory",
                "measure": "durable_surface_metadata",
                "message": "Some durable records do not expose owner, authority, and summary metadata.",
                "count": len(missing_metadata),
            }
        )
    if adapter_missing_removal_paths:
        advisory_signals.append(
            {
                "severity": "advisory",
                "measure": "adapter_surface_lifecycle",
                "message": "Some adapter surfaces do not expose a removal path.",
                "count": len(adapter_missing_removal_paths),
            }
        )
    post_contract_missing = _as_int(archived_distillation.get("post_contract_missing_distillation_count"))
    if post_contract_missing:
        advisory_signals.append(
            {
                "severity": "advisory",
                "measure": "archived_plan_distillation",
                "message": "Some post-contract archived execplans do not expose closeout distillation buckets.",
                "count": post_contract_missing,
            }
        )
    if _as_int(intent_counts.get("untracked_external_open_count")):
        advisory_signals.append(
            {
                "severity": "advisory",
                "measure": "unresolved_external_work_routing",
                "message": "External work evidence has open items not tracked by active planning.",
                "count": _as_int(intent_counts.get("untracked_external_open_count")),
            }
        )

    return {
        "kind": "workspace-operational-compression/v1",
        "status": "attention" if advisory_signals else "measured",
        "advisory_only": True,
        "rule": ("These measures make surface cost inspectable. They are not a score, workflow engine, dashboard, or host-tracker policy."),
        "measures": measures,
        "signals": advisory_signals,
        "hard_failures": [],
        "review_question": "Did this change remove, merge, compress, route, or background more repeated work than it added?",
        "section_command": "agentic-workspace report --target ./repo --section operational_compression --format json",
    }


def _missing_metadata_fields(record: dict[str, Any], *, required: tuple[str, ...]) -> list[str]:
    missing: list[str] = []
    for field in required:
        if field == "authority":
            value = record.get("authority") or record.get("authority_class")
        else:
            value = record.get(field)
        if not str(value or "").strip():
            missing.append(field)
    return missing


def _archived_plan_distillation_measure(*, target: Any) -> dict[str, Any]:
    target_text = str(target or "").strip()
    if not target_text:
        return {
            "archived_plan_count": 0,
            "with_distillation_count": 0,
            "missing_distillation_count": 0,
            "legacy_missing_distillation_count": 0,
            "post_contract_missing_distillation_count": 0,
            "distillation_contract_anchor": "",
            "sample_missing_distillation": [],
            "sample_post_contract_missing_distillation": [],
        }
    archive_dir = Path(target_text) / ".agentic-workspace" / "planning" / "execplans" / "archive"
    if not archive_dir.exists():
        return {
            "archived_plan_count": 0,
            "with_distillation_count": 0,
            "missing_distillation_count": 0,
            "legacy_missing_distillation_count": 0,
            "post_contract_missing_distillation_count": 0,
            "distillation_contract_anchor": "",
            "sample_missing_distillation": [],
            "sample_post_contract_missing_distillation": [],
        }
    archived_plans = [path for path in sorted(archive_dir.glob("*.plan.json")) if path.is_file()]
    missing: list[str] = []
    missing_with_mtime: list[tuple[str, float]] = []
    distillation_anchors: list[tuple[str, float]] = []
    with_distillation = 0
    for path in archived_plans:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            missing.append(path.name)
            continue
        distillation = payload.get("closeout_distillation") if isinstance(payload, dict) else None
        buckets = distillation.get("buckets", {}) if isinstance(distillation, dict) else {}
        if isinstance(buckets, dict) and any(_list_payload(buckets.get(bucket)) for bucket in buckets):
            with_distillation += 1
            distillation_anchors.append((path.name, path.stat().st_mtime))
        else:
            missing.append(path.name)
            missing_with_mtime.append((path.name, path.stat().st_mtime))
    anchor_name = ""
    anchor_mtime: float | None = None
    if distillation_anchors:
        anchor_name, anchor_mtime = min(distillation_anchors, key=lambda item: item[1])
    legacy_missing = [name for name, mtime in missing_with_mtime if anchor_mtime is None or mtime < anchor_mtime]
    post_contract_missing = [name for name, mtime in missing_with_mtime if anchor_mtime is not None and mtime >= anchor_mtime]
    return {
        "archived_plan_count": len(archived_plans),
        "with_distillation_count": with_distillation,
        "missing_distillation_count": len(missing),
        "legacy_missing_distillation_count": len(legacy_missing),
        "post_contract_missing_distillation_count": len(post_contract_missing),
        "distillation_contract_anchor": anchor_name,
        "sample_missing_distillation": missing[:5],
        "sample_post_contract_missing_distillation": post_contract_missing[:5],
    }


def _list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _report_profile_payload() -> dict[str, Any]:
    return {
        "default_profile": "router",
        "full_profile": "full",
        "section_selector": "--section <top-level-field>",
        "default_command": "agentic-workspace report --target ./repo --format json",
        "full_profile_command": "agentic-workspace report --target ./repo --profile full --format json",
        "section_command": "agentic-workspace report --target ./repo --section <section> --format json",
        "rule": (
            "Default report output should route to decision-grade current state before exposing high-volume "
            "module detail. Use --profile full or --section when deeper data is needed."
        ),
        "high_volume_sections": [
            {
                "section": "module_reports",
                "reason": "deep module state can be large; inspect only after the router points there",
            },
            {
                "section": "reports",
                "reason": "lifecycle report detail is useful for diagnosis but not needed for first-contact routing",
            },
            {
                "section": "registry",
                "reason": "module registry metadata is stable lookup detail rather than current-action routing",
            },
            {
                "section": "config",
                "reason": "resolved config is authoritative, but current work usually needs only routed policy highlights first",
            },
        ],
        "decision_grade_fields": [
            "health",
            "current_work",
            "next_action",
            "warning_summary",
            "section_hints",
            "effective_authority",
            "execution_shape",
            "operational_compression",
        ],
    }


def _select_report_payload(payload: dict[str, Any], *, profile: str, section: str | None) -> dict[str, Any]:
    if section:
        if profile != "router":
            raise WorkspaceUsageError("report selectors are mutually exclusive; use either --profile or --section.")
        if section not in payload:
            available = ", ".join(sorted(str(key) for key in payload.keys()))
            raise WorkspaceUsageError(f"Unknown report section {section!r}. Available sections: {available}")
        return _compact_contract_answer(
            surface="report",
            selector={"section": section},
            answer=payload[section],
            refs=[
                ".agentic-workspace/docs/reporting-contract.md",
                "agentic-workspace report --target ./repo --profile full --format json",
            ],
        )
    if profile == "full":
        return payload
    if profile == "router":
        return _report_router_payload(payload)
    raise WorkspaceUsageError("report --profile must be one of: router, full")


def _report_router_payload(payload: dict[str, Any]) -> dict[str, Any]:
    findings = [finding for finding in payload.get("findings", []) if isinstance(finding, dict)]
    findings_by_severity: dict[str, int] = {}
    findings_by_module: dict[str, int] = {}
    for finding in findings:
        severity = str(finding.get("severity", "info"))
        module = str(finding.get("module", "workspace") or "workspace")
        findings_by_severity[severity] = findings_by_severity.get(severity, 0) + 1
        findings_by_module[module] = findings_by_module.get(module, 0) + 1
    effective_authority = payload.get("effective_authority", {})
    current_work = {}
    if isinstance(effective_authority, dict):
        current_work = dict(effective_authority.get("current_work", {}) or {})
    execution_shape = payload.get("execution_shape", {})
    if not current_work and isinstance(execution_shape, dict):
        task_shape = execution_shape.get("task_shape", {})
        if isinstance(task_shape, dict):
            current_work = {
                "status": str(task_shape.get("id", "unknown")),
                "summary": str(task_shape.get("summary", "")),
                "source": "execution_shape",
            }
    section_hints = _report_section_hints(payload)
    profile_payload = payload.get("report_profile", _report_profile_payload())
    return {
        "kind": "workspace-report-router/v1",
        "schema": {
            "schema_version": "workspace-report-router-schema/v1",
            "full_profile_command": "agentic-workspace report --target ./repo --profile full --format json",
            "section_command": "agentic-workspace report --target ./repo --section <section> --format json",
            "principle": "route first, inspect deep sections only when needed",
        },
        "command": "report",
        "target": payload.get("target", ""),
        "selected_modules": payload.get("selected_modules", []),
        "installed_modules": payload.get("installed_modules", []),
        "health": payload.get("health", "unknown"),
        "output_contract": payload.get("output_contract", {}),
        "report_profile": profile_payload,
        "current_work": current_work,
        "next_action": payload.get("next_action", {}),
        "warning_summary": {
            "total_count": len(findings),
            "by_severity": findings_by_severity,
            "by_module": findings_by_module,
            "sample": findings[:5],
            "raw_section": "findings",
        },
        "section_hints": section_hints,
        "effective_authority": _report_router_effective_authority(payload.get("effective_authority", {})),
        "execution_shape": _report_router_execution_shape(payload.get("execution_shape", {})),
        "closeout_trust": payload.get("closeout_trust", {}),
        "operational_compression": _report_router_operational_compression(payload.get("operational_compression", {})),
        "surface_value_guardrail": {
            "command": "agentic-workspace defaults --section surface_value_guardrail --format json",
            "prefer": payload.get("surface_value_guardrail", {}).get("preference_order", [])[:3],
        },
        "deeper_detail": {
            "full_profile_command": "agentic-workspace report --target ./repo --profile full --format json",
            "section_command": "agentic-workspace report --target ./repo --section <section> --format json",
            "high_volume_sections": profile_payload.get("high_volume_sections", []),
        },
    }


def _report_router_effective_authority(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    return {
        "status": value.get("status", "unknown"),
        "current_work": value.get("current_work", {}),
        "unresolved_gap_count": len(value.get("unresolved_gaps", []) or []),
        "authority_concerns": [
            entry.get("concern") for entry in value.get("authority_map", []) if isinstance(entry, dict) and entry.get("concern")
        ],
    }


def _report_router_execution_shape(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    recommendation = value.get("recommendation", {})
    task_shape = value.get("task_shape", {})
    return {
        "status": value.get("status", "unknown"),
        "task_shape": task_shape if isinstance(task_shape, dict) else {},
        "recommendation": recommendation if isinstance(recommendation, dict) else {},
        "deviation_rule": value.get("deviation_rule", ""),
    }


def _report_router_operational_compression(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    signals = _list_payload(value.get("signals"))
    hard_failures = _list_payload(value.get("hard_failures"))
    return {
        "status": value.get("status", "unknown"),
        "advisory_only": value.get("advisory_only", True),
        "signal_count": len(signals),
        "hard_failure_count": len(hard_failures),
        "section_command": value.get(
            "section_command",
            "agentic-workspace report --target ./repo --section operational_compression --format json",
        ),
    }


def _report_section_hints(payload: dict[str, Any]) -> list[dict[str, Any]]:
    section_purposes = {
        "effective_authority": "authority, current work, system-intent pressure, and unresolved gaps",
        "execution_shape": "default execution posture and planning-backed work guidance",
        "operational_compression": "falsifiable advisory measures for whether surfaces reduce total operational cost",
        "findings": "raw warnings and attention signals grouped in router warning_summary",
        "module_reports": "deep planning and memory module reports",
        "reports": "workspace lifecycle report detail",
        "surface_value_guardrail": "surface growth review pressure",
        "closeout_trust": "closeout trust and lower-trust residue signals",
        "discovery": "setup discovery and candidate surfaces",
        "standing_intent": "effective standing intent and stronger-home guidance",
        "repo_friction": "repo-friction and improvement pressure evidence",
        "config": "resolved workspace config and local posture",
        "registry": "module registry and lifecycle metadata",
    }
    hints: list[dict[str, Any]] = []
    for section, purpose in section_purposes.items():
        if section in payload:
            hints.append(
                {
                    "section": section,
                    "purpose": purpose,
                    "command": f"agentic-workspace report --target ./repo --section {section} --format json",
                    "volume": "high" if section in {"module_reports", "reports", "registry", "config"} else "normal",
                }
            )
    return hints


def _report_closeout_trust_payload(*, module_reports: list[dict[str, Any]]) -> dict[str, Any]:
    planning_report = next(
        (report for report in module_reports if isinstance(report, dict) and report.get("module") == "planning"),
        None,
    )
    if not isinstance(planning_report, dict):
        return {
            "status": "unavailable",
            "reason": "planning module is not installed",
            "package_workflow_evidence": _package_workflow_evidence_payload(planning_report={}),
        }

    intent_validation = planning_report.get("intent_validation", {})
    if not isinstance(intent_validation, dict):
        return {
            "status": "unavailable",
            "reason": "planning intent validation is unavailable",
            "package_workflow_evidence": _package_workflow_evidence_payload(planning_report=planning_report),
        }

    counts = intent_validation.get("counts", {})
    signals = intent_validation.get("signals", [])
    lower_trust_closeout_count = 0
    if isinstance(counts, dict):
        lower_trust_closeout_count = int(counts.get("lower_trust_closeout_count", 0) or 0)
    sample_signals = [
        str(signal.get("message", "")).strip()
        for signal in signals
        if isinstance(signal, dict) and signal.get("kind") == "closed_without_planning_residue"
    ]
    sample_signals = [message for message in sample_signals if message][:3]
    trust = "lower-trust" if lower_trust_closeout_count > 0 else "normal"
    if trust == "lower-trust":
        summary = (
            f"{lower_trust_closeout_count} closeout signal(s) suggest package bypass or missing planning residue; "
            "treat closeout trust as lower until checked-in residue is visible."
        )
        recommended_next_action = str(
            intent_validation.get("recommended_next_action")
            or "Review the lower-trust closeout signals before treating planning closeout as normal."
        )
    else:
        summary = "No lower-trust closeout signals are currently detected from planning evidence."
        recommended_next_action = "No extra closeout trust review is needed beyond normal report inspection."
    return {
        "status": "present",
        "trust": trust,
        "lower_trust_closeout_count": lower_trust_closeout_count,
        "summary": summary,
        "sample_signals": sample_signals,
        "package_workflow_evidence": _package_workflow_evidence_payload(planning_report=planning_report),
        "recommended_next_action": recommended_next_action,
    }


def _package_workflow_evidence_payload(*, planning_report: dict[str, Any]) -> dict[str, Any]:
    active = planning_report.get("active", {}) if isinstance(planning_report, dict) else {}
    planning_record = active.get("planning_record", {}) if isinstance(active, dict) else {}
    execution_run_contract = active.get("execution_run_contract", {}) if isinstance(active, dict) else {}
    if not isinstance(planning_record, dict) or planning_record.get("status") != "present":
        return {
            "status": "unavailable",
            "reason": "no active planning record exposes package-use evidence",
            "required_for_broad_work": True,
        }
    proof_expectations = [str(item) for item in _list_payload(planning_record.get("proof_expectations"))]
    execution_run = planning_record.get("execution_run", {})
    if not isinstance(execution_run, dict):
        execution_run = {}
    evidence_text_parts = [
        " ".join(proof_expectations),
        str(execution_run.get("handoff source", "")),
        str(execution_run.get("validations run", "")),
        str(execution_run.get("what happened", "")),
    ]
    if isinstance(execution_run_contract, dict):
        evidence_text_parts.extend(
            [
                str(execution_run_contract.get("handoff_source", "")),
                str(execution_run_contract.get("validations_run", "")),
                str(execution_run_contract.get("what_happened", "")),
            ]
        )
    evidence_text = "\n".join(evidence_text_parts).lower()
    used_surfaces = [
        surface
        for surface in ["preflight", "summary", "report", "proof", "reconcile", "doctor"]
        if f"agentic-workspace {surface}" in evidence_text
    ]
    skipped_text = str(execution_run.get("package workflow skipped", "") or execution_run.get("package_workflow_skipped", "")).strip()
    trust = "normal" if used_surfaces and not skipped_text else "lower-trust"
    if trust == "normal":
        recommended_next_action = "Package workflow use is visible in the active planning record."
    elif skipped_text:
        recommended_next_action = "Review the declared package workflow skip before trusting broad-work closeout."
    else:
        recommended_next_action = "Record package workflow surfaces used or intentionally skipped before broad-work closeout."
    return {
        "status": "present",
        "required_for_broad_work": True,
        "trust": trust,
        "used_surfaces": used_surfaces,
        "skipped": skipped_text,
        "evidence_sources": [
            "planning.active.planning_record.proof_expectations",
            "planning.active.planning_record.execution_run",
        ],
        "recommended_next_action": recommended_next_action,
    }


def _run_preflight_command(
    *,
    target_root: Path,
    active_only: bool = False,
) -> dict[str, Any]:
    """Get compact takeover-safe context: startup + config + active state.

    If active_only=True, returns only active planning state without startup/config.
    This supports two use cases:
    1. First-contact preflight: bundle startup guidance + config + active state
    2. Active state polling: query current state without startup overhead
    """
    config = _load_workspace_config(target_root=target_root)
    issued_epoch = int(time.time())
    issued_at = datetime.fromtimestamp(issued_epoch, tz=timezone.utc).replace(microsecond=0).isoformat()
    preflight_token = _build_preflight_token(issued_at_epoch=issued_epoch)

    active_state = _preflight_active_state_payload(target_root=target_root)
    planning_record = active_state.get("planning_record", {"status": "unavailable"})
    branch_workflow_posture = _branch_workflow_posture_payload(target_root=target_root)
    local_memory = _local_memory_payload(config=config)

    if active_only:
        # Return only compact active state for polling/monitoring.
        # This remains useful even when the repo has active TODO state but no active execplan.

        return {
            "kind": "preflight-response/v1",
            "mode": "active-state-only",
            "target": target_root.as_posix(),
            "issued_at": issued_at,
            "preflight_token": preflight_token,
            "timestamp_hint": "Run this periodically to poll current active state without startup overhead.",
            "branch_workflow_posture": branch_workflow_posture,
            "local_memory": local_memory,
            "active_planning_state": active_state,
            "planning_record": planning_record if isinstance(planning_record, dict) else {"status": "unavailable"},
        }

    # Full preflight: startup + config + active state for takeover recovery
    # Get startup guidance
    startup_payload = _defaults_payload().get("startup", {})

    # Get config
    config_payload = _config_payload(config=config)

    return {
        "kind": "preflight-response/v1",
        "mode": "full-takeover-context",
        "target": target_root.as_posix(),
        "issued_at": issued_at,
        "preflight_token": preflight_token,
        "timestamp_hint": "Use this to bootstrap into an interrupted or takeover recovery.",
        "startup_guidance": {
            "entrypoint": startup_payload.get("default_canonical_agent_instructions_file", "AGENTS.md"),
            "first_compact_queries": startup_payload.get("tiny_safe_model", {}).get("first_compact_queries", []),
            "escalation_rules": startup_payload.get("escalation_cues", [])[:2],  # Top 2 most common
        },
        "resolved_config": {
            "workspace_config": config_payload.get("workspace", {}),
            "optimization_bias": config_payload.get("optimization_bias"),
            "agent_instructions_file": config_payload.get("workspace", {}).get("agent_instructions_file", "AGENTS.md"),
        },
        "branch_workflow_posture": branch_workflow_posture,
        "local_memory": local_memory,
        "active_planning_state": active_state,
    }


def _branch_workflow_posture_payload(*, target_root: Path) -> dict[str, Any]:
    rule = (
        "Staying on the current branch is separate from being safe to implement, commit, or push there; "
        "surface default-branch posture before broad implementation or push."
    )
    git_dir = _git_metadata_dir(target_root=target_root)
    if git_dir is None:
        return {
            "status": "unavailable",
            "reason": "target is not a git worktree or git metadata is unavailable",
            "advisory_only": True,
            "rule": rule,
        }

    current_branch = _read_symbolic_ref(git_dir=git_dir, ref_name="HEAD", prefix="refs/heads/")
    default_branch = _read_symbolic_ref(git_dir=git_dir, ref_name="refs/remotes/origin/HEAD", prefix="refs/remotes/origin/")
    sources = [".git/HEAD"]
    if default_branch:
        sources.append(".git/refs/remotes/origin/HEAD")

    if not current_branch:
        return {
            "status": "detached-or-unknown",
            "current_branch": "",
            "default_branch": default_branch or "",
            "on_default_branch": False,
            "risk": "unknown",
            "advisory_only": True,
            "rule": rule,
            "sources": sources,
            "recommended_next_action": "Inspect git branch state before implementation, commit, or push.",
        }

    default_branch_known = bool(default_branch)
    on_default_branch = default_branch_known and current_branch == default_branch
    likely_default_name = current_branch in {"main", "master", "trunk"}
    risk = "default-branch-commit-risk" if on_default_branch or (not default_branch_known and likely_default_name) else "normal"
    if risk == "default-branch-commit-risk":
        recommended_next_action = "Make the default-branch posture explicit before implementation, commit, or push; do not switch branches unless the user decides."
    else:
        recommended_next_action = "Continue normal branch-aware workflow; keep commit and push posture explicit before closeout."
    branch_mutation_policy = {
        "status": "present",
        "advisory_only": True,
        "rule": "Branch switching, cross-branch merging, and pushing from a different branch than startup require explicit user intent.",
        "guarded_actions": [
            "switch-branch",
            "create-branch",
            "merge-from-other-branch",
            "rebase-onto-other-branch",
            "push-different-branch",
        ],
        "current_branch_is_execution_branch": bool(current_branch),
        "requires_user_intent_before": [
            "changing the execution branch",
            "merging another branch into the execution branch",
            "pushing work from a branch other than the execution branch",
        ],
    }

    return {
        "status": "present",
        "current_branch": current_branch,
        "default_branch": default_branch or "",
        "default_branch_known": default_branch_known,
        "on_default_branch": on_default_branch,
        "risk": risk,
        "advisory_only": True,
        "rule": rule,
        "branch_mutation_policy": branch_mutation_policy,
        "sources": sources,
        "recommended_next_action": recommended_next_action,
    }


def _git_metadata_dir(*, target_root: Path) -> Path | None:
    git_path = target_root / ".git"
    if git_path.is_dir():
        return git_path
    if not git_path.is_file():
        return None
    text = git_path.read_text(encoding="utf-8", errors="replace").strip()
    if not text.startswith("gitdir:"):
        return None
    raw_path = text.split(":", 1)[1].strip()
    git_dir = Path(raw_path)
    if not git_dir.is_absolute():
        git_dir = (target_root / git_dir).resolve()
    return git_dir if git_dir.exists() else None


def _read_symbolic_ref(*, git_dir: Path, ref_name: str, prefix: str) -> str:
    ref_path = git_dir / ref_name
    if not ref_path.exists():
        return ""
    text = ref_path.read_text(encoding="utf-8", errors="replace").strip()
    if not text.startswith("ref:"):
        return ""
    ref_target = text.split(":", 1)[1].strip()
    if not ref_target.startswith(prefix):
        return ""
    return ref_target[len(prefix) :].strip()


def _package_boundary_payload(*, target_root: Path) -> dict[str, Any]:
    cwd = Path.cwd().resolve()
    try:
        relative_cwd = cwd.relative_to(target_root)
    except ValueError:
        return {
            "status": "outside-target",
            "cwd": cwd.as_posix(),
            "warning": "Current working directory is outside the target root.",
        }
    parts = relative_cwd.parts
    if len(parts) >= 2 and parts[0] == "packages":
        package_root = Path(parts[0]) / parts[1]
        return {
            "status": "inside-package",
            "cwd": relative_cwd.as_posix() or ".",
            "package_root": package_root.as_posix(),
            "warning": "Read package-local AGENTS.md before editing inside this package boundary.",
        }
    return {
        "status": "repo-root-or-subdir",
        "cwd": relative_cwd.as_posix() or ".",
        "warning": None,
    }


def _authority_marker_for_path(path_text: str) -> dict[str, Any]:
    normalized = _normalize_changed_paths([path_text])[0] if _normalize_changed_paths([path_text]) else path_text
    if normalized == "AGENTS.md":
        return _authority_marker_payload(marker_id="root-agent-instructions", normalized=normalized)
    if normalized == "llms.txt":
        return _authority_marker_payload(marker_id="external-agent-handoff", normalized=normalized)
    if normalized.startswith(".agentic-workspace/planning/"):
        return _authority_marker_payload(marker_id="planning-surface", normalized=normalized)
    if normalized.startswith(".agentic-workspace/memory/"):
        return _authority_marker_payload(marker_id="memory-surface", normalized=normalized)
    if "/bootstrap/" in normalized or normalized.endswith("/bootstrap"):
        return _authority_marker_payload(marker_id="package-bootstrap-payload", normalized=normalized)
    if normalized.startswith("src/agentic_workspace/") or normalized.startswith("packages/"):
        return _authority_marker_payload(marker_id="source", normalized=normalized)
    if normalized.startswith(".agentic-workspace/"):
        return _authority_marker_payload(marker_id="managed-workspace-surface", normalized=normalized)
    return _authority_marker_payload(marker_id="repo-owned", normalized=normalized)


def _authority_marker_payload(*, marker_id: str, normalized: str) -> dict[str, Any]:
    marker = _authority_marker_policy_by_id()[marker_id]
    return {
        "path": normalized,
        "authority": marker["authority"],
        "canonical_source": _authority_marker_canonical_source(marker=marker, normalized=normalized),
        "safe_to_edit": marker["safe_to_edit"],
        "refresh_command": marker["refresh_command"],
    }


def _authority_marker_policy_by_id() -> dict[str, dict[str, Any]]:
    return {marker["id"]: marker for marker in authority_markers_manifest()["markers"]}


def _authority_marker_canonical_source(*, marker: dict[str, Any], normalized: str) -> str:
    canonical_source = marker["canonical_source"]
    kind = canonical_source["kind"]
    if kind == "fixed":
        return str(canonical_source["value"])
    if kind == "path":
        return normalized
    if kind == "package-root-source":
        package_root = "/".join(normalized.split("/")[:2]) if normalized.startswith("packages/") else "package"
        return f"{package_root}/src/"
    raise WorkspaceUsageError(f"Unsupported authority marker canonical source kind: {kind}")


def _boundary_warning_for_path(path_text: str) -> dict[str, Any]:
    marker = _authority_marker_for_path(path_text)
    normalized = str(marker["path"])
    warning: str | None = None
    if marker["authority"] == "payload":
        warning = (
            "Package bootstrap payload is not live authority; reflect durable behavior in package source and sync payload before closeout."
        )
    elif normalized.startswith(".agentic-workspace/") and marker["authority"] not in {"canonical", "managed"}:
        warning = "Installed workspace surfaces are shared operational state; verify ownership before editing."
    elif normalized.startswith("packages/") and "/src/" in normalized:
        warning = "Package source edits may need matching payload or installed-surface proof before closeout."
    elif marker["authority"] == "generated-adapter":
        warning = "Generated adapter content should be refreshed from its canonical source rather than hand-edited."
    return {
        "path": normalized,
        "authority": marker["authority"],
        "warning": warning,
        "requires_attention": warning is not None,
    }


def _authority_markers_for_startup(*, active_execplan: str | None = None) -> list[dict[str, Any]]:
    paths = ["AGENTS.md", "llms.txt", ".agentic-workspace/WORKFLOW.md", ".agentic-workspace/OWNERSHIP.toml"]
    if active_execplan:
        paths.append(active_execplan)
    return [_authority_marker_for_path(path) for path in paths]


def _start_payload(*, target_root: Path, changed_paths: list[str]) -> dict[str, Any]:
    startup_template = _CONTEXT_TEMPLATES["startup_context"]
    preflight = _run_preflight_command(target_root=target_root)
    active_state = preflight.get("active_planning_state", {})
    planning_record = active_state.get("planning_record", {})
    active_contract = active_state.get("active_contract", {})
    active_execplans = active_state.get("execplans", {}).get("active_execplans", [])
    active_execplan = active_execplans[0].get("path") if active_execplans else None
    next_action = ""
    if isinstance(planning_record, dict):
        next_action = str(planning_record.get("next_action", "") or "")
    if not next_action and isinstance(active_contract, dict):
        next_action = str(active_contract.get("todo_item", {}).get("why_now", "") or "")
    if not next_action:
        active_items = active_state.get("todo", {}).get("active_items", [])
        if active_items:
            next_action = str(active_items[0].get("next_action", "") or active_items[0].get("why_now", "") or "")
    if not next_action:
        next_action = str(startup_template["fallback_next_action"])
    startup_sequence = copy.deepcopy(startup_template["startup_sequence"])
    for step in startup_sequence:
        if step["id"] == "entrypoint":
            step["surface"] = str(step["surface"]).format(
                agent_instructions_file=preflight.get("resolved_config", {}).get("agent_instructions_file", "AGENTS.md")
            )

    payload: dict[str, Any] = {
        "kind": "startup-context/v1",
        "target": target_root.as_posix(),
        "startup_sequence": startup_sequence,
        "active_state_summary": {
            "todo_active_count": active_state.get("todo", {}).get("active_count", 0),
            "active_execplan": active_execplan,
            "planning_status": planning_record.get("status", "unavailable") if isinstance(planning_record, dict) else "unavailable",
        },
        "package_boundary": _package_boundary_payload(target_root=target_root),
        "authority_markers": _authority_markers_for_startup(active_execplan=active_execplan),
        "immediate_next_allowed_action": {
            "summary": next_action,
            "read_first": preflight.get("startup_guidance", {}).get("first_compact_queries", []),
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
        },
    }
    normalized_paths = _normalize_changed_paths(changed_paths)
    if normalized_paths:
        payload["proof"] = _proof_selection_for_changed_paths(changed_paths=normalized_paths)
        payload["path_boundaries"] = [_boundary_warning_for_path(path) for path in normalized_paths]
    return payload


def _implement_payload(*, target_root: Path, changed_paths: list[str]) -> dict[str, Any]:
    implementer_template = _CONTEXT_TEMPLATES["implementer_context"]
    normalized_paths = _normalize_changed_paths(changed_paths)
    proof = (
        _proof_selection_for_changed_paths(changed_paths=normalized_paths)
        if normalized_paths
        else copy.deepcopy(implementer_template["unknown_scope_proof"])
    )
    path_boundaries = [_boundary_warning_for_path(path) for path in normalized_paths]
    attention_paths = [item["path"] for item in path_boundaries if item["requires_attention"]]
    inspect_files = normalized_paths or list(implementer_template["default_inspect_files"])
    return {
        "kind": "implementer-context/v1",
        "target": target_root.as_posix(),
        "changed_paths": normalized_paths,
        "inspect_files": inspect_files,
        "files_to_avoid": list(implementer_template["files_to_avoid"]),
        "package_boundary": _package_boundary_payload(target_root=target_root),
        "path_boundaries": path_boundaries,
        "authority_markers": [_authority_marker_for_path(path) for path in (normalized_paths or ["AGENTS.md", "llms.txt"])],
        "proof": proof,
        "required_validation_commands": proof["required_commands"],
        "handoff_requirements": copy.deepcopy(implementer_template["handoff_requirements"]),
        "next_allowed_action": (
            implementer_template["next_allowed_action"]["attention"]
            if attention_paths
            else implementer_template["next_allowed_action"]["default"]
        ),
    }


def _preflight_active_state_payload(*, target_root: Path) -> dict[str, Any]:
    from repo_planning_bootstrap.installer import planning_summary

    summary = planning_summary(target=target_root, profile="compact")
    warnings = summary.get("warnings", [])
    return {
        "todo": summary.get("todo", {}),
        "execplans": summary.get("execplans", {}),
        "planning_surface_health": summary.get("planning_surface_health", {}),
        "planning_record": summary.get("planning_record", {"status": "unavailable"}),
        "active_contract": summary.get("active_contract", {"status": "unavailable"}),
        "resumable_contract": summary.get("resumable_contract", {"status": "unavailable"}),
        "handoff_contract": summary.get("handoff_contract", {"status": "unavailable"}),
        "warnings": warnings if isinstance(warnings, list) else [],
        "warning_count": int(summary.get("warning_count", 0) or 0),
    }


def _effective_active_direction_payload(*, module_reports: list[dict[str, Any]]) -> dict[str, Any] | None:
    planning_record = _active_planning_record(module_reports=module_reports)
    if not isinstance(planning_record, dict):
        return None
    task = planning_record.get("task", {})
    refs = planning_record.get("minimal_refs", [])
    owner_surface = ""
    if isinstance(task, dict):
        owner_surface = str(task.get("surface") or "")
    return {
        "owner_surface": owner_surface or ".agentic-workspace/planning/state.toml",
        "summary": str(planning_record.get("next_action") or "Active planning carries the current bounded direction."),
        "requested_outcome": str(planning_record.get("requested_outcome") or ""),
        "refs": refs if isinstance(refs, list) else [],
    }


def _active_planning_record(*, module_reports: list[dict[str, Any]]) -> dict[str, Any] | None:
    planning_report = next(
        (report for report in module_reports if isinstance(report, dict) and report.get("module") == "planning"),
        None,
    )
    if not isinstance(planning_report, dict):
        return None
    planning_record = planning_report.get("active", {}).get("planning_record", {})
    if not isinstance(planning_record, dict) or planning_record.get("status") != "present":
        return None
    return planning_record


def _agent_configuration_report_payload(*, config: WorkspaceConfig, installed_modules: list[str]) -> dict[str, Any]:
    substrate = _agent_configuration_system_payload()
    return {
        "canonical_doc": substrate["canonical_doc"],
        "rule": substrate["rule"],
        "startup_entrypoint": config.agent_instructions_file,
        "workflow_artifact_profile": config.workflow_artifact_profile,
        "workspace_policy_surface": ".agentic-workspace/config.toml",
        "ownership_surface": ".agentic-workspace/OWNERSHIP.toml",
        "module_attachment_status": [
            {
                "module": "planning",
                "installed": "planning" in installed_modules,
                "owner_surface": ".agentic-workspace/planning/state.toml",
            },
            {
                "module": "memory",
                "installed": "memory" in installed_modules,
                "owner_surface": ".agentic-workspace/memory/repo/",
            },
        ],
        "adapter_surfaces": substrate["adapter_surfaces"],
        "selective_loading": substrate["selective_loading"],
        "current_system_intent_role": "workspace-owned compiled intent declaration consumed operationally, with repo-owned prose remaining unconstrained directional evidence",
    }


def _agent_configuration_queries_report_payload(
    *,
    installed_modules: list[str],
    active_direction: dict[str, Any] | None,
) -> dict[str, Any]:
    query_catalog = _agent_configuration_queries_payload()
    current_queries = []
    for item in query_catalog["query_classes"]:
        current_item = {
            "id": item["id"],
            "question": item["question"],
            "ask_first": item["ask_first"],
        }
        if item["id"] == "repo_local_current_work":
            current_item["status"] = "active-planning-present" if active_direction else "no-active-planning-direction"
            current_item["current_owner"] = (
                active_direction.get("owner_surface", ".agentic-workspace/planning/state.toml")
                if isinstance(active_direction, dict)
                else ".agentic-workspace/planning/state.toml"
            )
            current_item["then_if_needed"] = (
                active_direction.get("refs", ["agentic-workspace report --target ./repo --format json"])
                if isinstance(active_direction, dict)
                else item["then_if_needed"]
            )
        elif item["id"] == "relevant_subinstructions":
            current_item["status"] = "planning-and-memory-installed"
            current_item["modules_in_scope"] = [module for module in ("planning", "memory") if module in installed_modules]
            current_item["then_if_needed"] = item["then_if_needed"]
        else:
            current_item["status"] = "available"
            current_item["then_if_needed"] = item["then_if_needed"]
        current_queries.append(current_item)
    return {
        "canonical_doc": query_catalog["canonical_doc"],
        "rule": query_catalog["rule"],
        "default_query_surface": query_catalog["command"],
        "current_work_status": "planning-backed" if active_direction else "no-active-direction",
        "current_queries": current_queries,
        "stop_rule": query_catalog["stop_rule"],
    }


def _workflow_obligation_payloads(config: WorkspaceConfig) -> list[dict[str, Any]]:
    return [
        {
            "id": obligation.name,
            "summary": obligation.summary,
            "stage": obligation.stage,
            "scope_tags": list(obligation.scope_tags),
            "commands": list(obligation.commands),
            "review_hint": obligation.review_hint,
        }
        for obligation in config.workflow_obligations
    ]


def _scope_tags_for_current_work(*, active_planning_record: dict[str, Any] | None) -> list[str]:
    tags: set[str] = set()
    touched_scope = active_planning_record.get("touched_scope", []) if isinstance(active_planning_record, dict) else []
    if isinstance(touched_scope, list):
        for raw_item in touched_scope:
            item = str(raw_item)
            normalized = item.lower()
            if any(token in normalized for token in ("src/agentic_workspace", ".agentic-workspace/docs", "readme.md")):
                tags.add("workspace")
            if any(token in normalized for token in (".agentic-workspace/planning", "packages/planning")):
                tags.add("planning")
            if any(token in normalized for token in (".agentic-workspace/memory", "packages/memory")):
                tags.add("memory")
            if any(token in normalized for token in ("agents.md", "llms.txt", "tools/agent_quickstart", "tools/agent_routing")):
                tags.add("adapter-surfaces")
    if active_planning_record:
        tags.add("planning")
    return sorted(tags)


def _workflow_obligations_report_payload(
    *,
    config: WorkspaceConfig,
    active_planning_record: dict[str, Any] | None,
) -> dict[str, Any]:
    configured = _workflow_obligation_payloads(config)
    current_tags = _scope_tags_for_current_work(active_planning_record=active_planning_record)
    relevant = [obligation for obligation in configured if set(obligation["scope_tags"]) & set(current_tags)]
    return {
        "canonical_doc": ".agentic-workspace/docs/workspace-config-contract.md",
        "rule": (
            "Repo-custom workflow obligations live in workspace config so planning can consume them when relevant "
            "without becoming the owner of workflow extension machinery."
        ),
        "configured_count": len(configured),
        "current_scope_tags": current_tags,
        "configured": configured,
        "relevant_to_current_work": relevant,
    }


def _system_intent_source_payload(config: WorkspaceConfig) -> dict[str, Any]:
    return {
        "sources": list(config.system_intent.sources),
        "sources_source": config.system_intent.sources_source,
        "preferred_source": config.system_intent.preferred_source,
        "preferred_source_source": config.system_intent.preferred_source_source,
    }


def _system_intent_record_from_path(*, target_root: Path, relative: str) -> dict[str, Any]:
    path = target_root / relative
    if not path.exists():
        return {"path": relative, "present": False}
    text = path.read_text(encoding="utf-8")
    first_heading = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            first_heading = line.lstrip("#").strip()
            break
    return {
        "path": relative,
        "present": True,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "first_heading": first_heading,
        "line_count": len(text.splitlines()),
    }


def _empty_system_intent_interpretation(*, config: WorkspaceConfig) -> dict[str, Any]:
    return {
        "summary": "",
        "governing_intents": [],
        "anti_intents": [],
        "decision_tests": [],
        "open_questions": [],
        "interpretation_notes": "",
        "confidence": "low",
        "needs_review": True,
        "preferred_source": config.system_intent.preferred_source or "",
    }


def _load_system_intent_mirror(*, target_root: Path, config: WorkspaceConfig) -> dict[str, Any]:
    mirror_path = target_root / WORKSPACE_SYSTEM_INTENT_MIRROR_PATH
    if not mirror_path.exists():
        return {
            "status": "missing",
            "path": WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix(),
            "kind": SYSTEM_INTENT_MIRROR_KIND,
            "source_declaration": _system_intent_source_payload(config),
            "workflow_surface": WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH.as_posix(),
            "sync_command": "agentic-workspace system-intent --target ./repo --sync --format json",
        }
    payload = config_lib.load_toml_payload(path=mirror_path, surface_name=WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix())
    source_records = payload.get("source_records", [])
    if not isinstance(source_records, list):
        raise WorkspaceUsageError(f"{WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix()} source_records must be an array of tables.")
    normalized_records: list[dict[str, Any]] = []
    for item in source_records:
        if not isinstance(item, dict):
            raise WorkspaceUsageError(f"{WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix()} source_records entries must be tables.")
        normalized_records.append(
            {
                "path": str(item.get("path", "")),
                "present": bool(item.get("present", False)),
                "sha256": str(item.get("sha256", "")),
                "first_heading": str(item.get("first_heading", "")),
                "line_count": int(item.get("line_count", 0)) if str(item.get("line_count", "0")).strip() else 0,
            }
        )
    summary = str(payload.get("summary", ""))
    governing_intents = payload.get("governing_intents", [])
    anti_intents = payload.get("anti_intents", [])
    decision_tests = payload.get("decision_tests", [])
    open_questions = payload.get("open_questions", [])
    return {
        "status": "present",
        "path": WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix(),
        "kind": str(payload.get("kind", SYSTEM_INTENT_MIRROR_KIND)),
        "schema_version": int(payload.get("schema_version", 1)),
        "summary": summary,
        "governing_intents": list(governing_intents) if isinstance(governing_intents, list) else [],
        "anti_intents": list(anti_intents) if isinstance(anti_intents, list) else [],
        "decision_tests": list(decision_tests) if isinstance(decision_tests, list) else [],
        "open_questions": list(open_questions) if isinstance(open_questions, list) else [],
        "interpretation_notes": str(payload.get("interpretation_notes", "")),
        "confidence": str(payload.get("confidence", "low")),
        "needs_review": bool(payload.get("needs_review", True)),
        "preferred_source": str(payload.get("preferred_source", "")),
        "last_synced_at": str(payload.get("last_synced_at", "")),
        "source_records": normalized_records,
        "source_declaration": _system_intent_source_payload(config),
        "workflow_surface": WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH.as_posix(),
        "sync_command": "agentic-workspace system-intent --target ./repo --sync --format json",
    }


def _render_system_intent_mirror_text(*, interpretation: dict[str, Any], source_records: list[dict[str, Any]]) -> str:
    lines = [
        "schema_version = 1",
        f'kind = "{SYSTEM_INTENT_MIRROR_KIND}"',
        f"summary = {json.dumps(str(interpretation.get('summary', '')))}",
        f"governing_intents = {json.dumps(list(interpretation.get('governing_intents', [])))}",
        f"anti_intents = {json.dumps(list(interpretation.get('anti_intents', [])))}",
        f"decision_tests = {json.dumps(list(interpretation.get('decision_tests', [])))}",
        f"open_questions = {json.dumps(list(interpretation.get('open_questions', [])))}",
        f"interpretation_notes = {json.dumps(str(interpretation.get('interpretation_notes', '')))}",
        f"confidence = {json.dumps(str(interpretation.get('confidence', 'low')))}",
        f"needs_review = {'true' if bool(interpretation.get('needs_review', True)) else 'false'}",
        f"preferred_source = {json.dumps(str(interpretation.get('preferred_source', '')))}",
        f"last_synced_at = {json.dumps(date.today().isoformat())}",
    ]
    for record in source_records:
        lines.extend(
            [
                "",
                "[[source_records]]",
                f"path = {json.dumps(str(record.get('path', '')))}",
                f"present = {'true' if bool(record.get('present', False)) else 'false'}",
                f"sha256 = {json.dumps(str(record.get('sha256', '')))}",
                f"first_heading = {json.dumps(str(record.get('first_heading', '')))}",
                f"line_count = {int(record.get('line_count', 0))}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def _sync_system_intent_mirror(*, target_root: Path, config: WorkspaceConfig, dry_run: bool) -> tuple[list[dict[str, str]], dict[str, Any]]:
    actions: list[dict[str, str]] = []
    workflow_destination = target_root / WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH
    workflow_bytes = _workspace_payload_bytes(WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH)
    existing_workflow = workflow_destination.exists()
    if not existing_workflow or workflow_destination.read_bytes() != workflow_bytes:
        if not dry_run:
            workflow_destination.parent.mkdir(parents=True, exist_ok=True)
            workflow_destination.write_bytes(workflow_bytes)
        actions.append(
            {
                "kind": _write_action_kind(
                    dry_run=dry_run, existing=workflow_destination.read_text(encoding="utf-8") if existing_workflow else None
                ),
                "path": WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH.as_posix(),
                "detail": "refresh system-intent extraction workflow guidance",
            }
        )
    else:
        actions.append(
            {
                "kind": "current",
                "path": WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH.as_posix(),
                "detail": "system-intent workflow guidance already current",
            }
        )

    existing = _load_system_intent_mirror(target_root=target_root, config=config)
    interpretation = (
        {
            "summary": existing.get("summary", ""),
            "governing_intents": existing.get("governing_intents", []),
            "anti_intents": existing.get("anti_intents", []),
            "decision_tests": existing.get("decision_tests", []),
            "open_questions": existing.get("open_questions", []),
            "interpretation_notes": existing.get("interpretation_notes", ""),
            "confidence": existing.get("confidence", "low"),
            "needs_review": existing.get("needs_review", True),
            "preferred_source": config.system_intent.preferred_source or existing.get("preferred_source", ""),
        }
        if existing.get("status") == "present"
        else _empty_system_intent_interpretation(config=config)
    )
    source_records = [
        _system_intent_record_from_path(target_root=target_root, relative=relative) for relative in config.system_intent.sources
    ]
    mirror_text = _render_system_intent_mirror_text(interpretation=interpretation, source_records=source_records)
    mirror_path = target_root / WORKSPACE_SYSTEM_INTENT_MIRROR_PATH
    existing_text = mirror_path.read_text(encoding="utf-8") if mirror_path.exists() else None
    if existing_text != mirror_text:
        if not dry_run:
            mirror_path.parent.mkdir(parents=True, exist_ok=True)
            mirror_path.write_text(mirror_text, encoding="utf-8")
        actions.append(
            {
                "kind": _write_action_kind(dry_run=dry_run, existing=existing_text),
                "path": WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix(),
                "detail": "refresh system-intent source metadata while preserving the interpreted declaration fields",
            }
        )
    else:
        actions.append(
            {
                "kind": "current",
                "path": WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix(),
                "detail": "system-intent declaration metadata already current for the declared sources",
            }
        )
    return actions, _load_system_intent_mirror(target_root=target_root, config=config)


def _system_intent_report_payload(*, target_root: Path, config: WorkspaceConfig) -> dict[str, Any]:
    mirror = _load_system_intent_mirror(target_root=target_root, config=config)
    return {
        "canonical_doc": ".agentic-workspace/docs/system-intent-contract.md",
        "rule": (
            "Keep a workspace-owned compiled intent declaration inside `.agentic-workspace/` so package operations can consume "
            "normalized system intent without imposing a host-repo source-file format or pretending source prose maps mechanically into schema."
        ),
        "source_declaration_surface": ".agentic-workspace/config.toml [system_intent]",
        "mirror_surface": WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix(),
        "workflow_surface": WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH.as_posix(),
        "source_declaration": _system_intent_source_payload(config),
        "mirror": mirror,
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
                "agentic-workspace summary --format json",
            ],
        }

    planning_status = planning_module_report.get("status", {})
    active = planning_module_report.get("active", {})
    planning_record = active.get("planning_record", {})
    handoff_contract = active.get("handoff_contract", {})
    has_active_execplan = bool(planning_status.get("active_execplan_count"))
    roadmap_candidate_count = int(planning_status.get("roadmap_candidate_count") or 0)
    roadmap_lane_count = int(planning_status.get("roadmap_lane_count") or 0)
    strong_planner = bool(mixed_agent["effective_posture"]["strong_planner_available"]["value"])
    cheap_executor = bool(mixed_agent["effective_posture"]["cheap_bounded_executor_available"]["value"])
    internal_delegation = bool(mixed_agent["effective_posture"]["supports_internal_delegation"]["value"])
    prefer_internal = bool(mixed_agent["effective_posture"]["prefer_internal_delegation_when_available"]["value"])
    sources = [
        "agentic-workspace config --target ./repo --format json",
        "agentic-workspace summary --format json",
    ]
    if isinstance(handoff_contract, dict) and handoff_contract.get("status") == "present":
        sources.append("agentic-workspace prompt --format json")

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
                ".agentic-workspace/config.toml",
                ".agentic-workspace/config.local.toml",
            ],
        },
    }

    if isinstance(planning_record, dict) and planning_record.get("status") == "present" and has_active_execplan:
        capability_posture = planning_record.get("capability_posture", {}) if isinstance(planning_record, dict) else {}
        target_profiles = mixed_agent.get("delegation_targets", {}).get("profiles", [])
        resolution = []
        if isinstance(capability_posture, dict) and capability_posture:
            for profile_payload in target_profiles:
                profile_name = str(profile_payload.get("name", "")).strip()
                profile = next((item for item in config.local_override.delegation_targets if item.name == profile_name), None)
                if profile is None:
                    continue
                resolution.append(
                    {
                        "name": profile.name,
                        "strength": profile.strength,
                        "location": profile.location,
                        "capability_classes": list(profile.capability_classes),
                        **_capability_resolution_for_profile(profile=profile, capability_posture=capability_posture),
                    }
                )
            resolution.sort(key=lambda item: (-int(item["score"]), str(item["name"])))
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
        if isinstance(capability_posture, dict) and capability_posture:
            payload["capability_posture"] = capability_posture
            payload["resolved_targets"] = resolution
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
                "best_target_fits": [target["name"] for target in resolution if target.get("status") == "recommended"][:3],
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
                "consult": ["agentic-workspace summary --format json"],
                "allowed_execution_methods": ["single-agent fallback"],
                "deviation_visibility": (
                    "If you later delegate anyway, derive the handoff from checked-in planning and note why the exception beat the direct default."
                ),
            }
        payload["deviation_rule"] = (
            "Local judgment may still choose another execution method, but the deviation should stay explainable in checked-in planning residue."
        )
        return payload

    if roadmap_candidate_count or roadmap_lane_count:
        payload["task_shape"] = {
            "id": "roadmap-backed-no-active-plan",
            "summary": "Roadmap candidates exist, but no active planning-backed slice is present.",
            "why": (
                "Roadmap candidates are not execution authority. Broad planned or autopilot work needs an active "
                "TODO item plus execplan before implementation; narrow direct tasks may still proceed."
            ),
        }
        payload["recommendation"] = {
            "id": "promote-before-broad-work",
            "summary": "Promote the selected roadmap lane into active planning before broad implementation.",
            "why": [
                "The repo has roadmap candidates but no active execplan.",
                "Broad planned work needs checked-in milestone, proof, and continuation state before code changes.",
                "Direct execution remains appropriate only for narrow tasks that do not claim roadmap lane progress.",
            ],
            "consult": ["agentic-workspace summary --format json"],
            "allowed_execution_methods": ["single-agent fallback for narrow work", "planning-backed execution after promotion"],
            "deviation_visibility": (
                "If broad work proceeds without promotion, record that as a workflow violation and treat closeout as lower trust."
            ),
        }
        payload["deviation_rule"] = (
            "Do not implement roadmap or autopilot lanes from chat or issue context alone; promote active planning first."
        )
        return payload

    payload["task_shape"] = {
        "id": "direct-or-no-active-plan",
        "summary": "No planning-backed broad slice is active right now.",
        "why": "Without roadmap-backed planned work or an active execplan, the cheapest honest default is direct execution.",
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
    todo_path = target_root / ".agentic-workspace" / "planning" / "state.toml"
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
        "canonical_doc": ".agentic-workspace/docs/compact-contract-profile.md",
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


def _system_intent_payload() -> dict[str, Any]:
    return {
        "canonical_doc": ".agentic-workspace/docs/system-intent-contract.md",
        "command": "agentic-workspace defaults --section system_intent --format json",
        "rule": (
            "Keep the larger requested outcome explicit even when the active slice is narrower, and make closure decisions name that difference honestly."
        ),
        "source_declaration_surface": ".agentic-workspace/config.toml [system_intent]",
        "mirror_surface": WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix(),
        "workflow_surface": WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH.as_posix(),
        "sync_command": "agentic-workspace system-intent --target ./repo --sync --format json",
        "sync_behavior": "Refresh source hints and source-record metadata only; interpreted intent fields remain agent-owned and human-correctable.",
        "mirror_fields": [
            "summary",
            "governing_intents",
            "anti_intents",
            "decision_tests",
            "open_questions",
            "interpretation_notes",
            "confidence",
            "needs_review",
            "source_records",
        ],
        "authority_ladder": [
            {
                "layer": "confirmed request or live issue cluster",
                "owns": "the larger user or product outcome",
            },
            {
                "layer": "delegated judgment and intent continuity",
                "owns": "the bounded slice and its mapping back to the larger outcome",
            },
            {
                "layer": "closure check and required continuation",
                "owns": "whether the slice archives, whether the larger outcome is still open, and where continuation now lives",
            },
        ],
        "reinterpretation_boundary": {
            "allowed": [
                "tighten means and validation",
                "choose a smaller first slice",
                "route required continuation into one checked-in owner",
            ],
            "must_not": [
                "treat a bounded slice as if it closed the larger outcome without explicit evidence",
                "leave required continuation only in drift prose or chat",
                "replace the confirmed outcome with a cheaper substitute silently",
            ],
        },
        "recoverability": {
            "ask_first": [
                "agentic-workspace defaults --section system_intent --format json",
                "agentic-workspace summary --format json",
                "agentic-workspace report --target ./repo --format json",
            ],
            "must_answer": [
                "what larger outcome the active slice serves",
                "whether the larger outcome is actually closed",
                "where required continuation lives now",
                "what evidence justified the closure decision",
            ],
        },
        "checked_in_execplan_rule": (
            "Use a checked-in execplan whenever later proof, intent validation, or follow-through would be expensive or ambiguous to reconstruct from chat alone."
        ),
    }


def _clarification_contract_payload() -> dict[str, Any]:
    return {
        "canonical_doc": ".agentic-workspace/docs/compact-contract-profile.md",
        "command": "agentic-workspace defaults --section clarification --format json",
        "rule": "When a prompt is vague, ask the smallest repo-context question that removes the ambiguity.",
        "mode": "minimal-interruption",
        "repo_context": [
            "Use .agentic-workspace/planning/state.toml or the active execplan when the prompt seems planning-shaped.",
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
        "canonical_doc": ".agentic-workspace/docs/compact-contract-profile.md",
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
                "owner_surface": ".agentic-workspace/planning/execplans/ or .agentic-workspace/planning/state.toml",
            },
            {
                "class": "durable repo knowledge change",
                "proof_lane": "memory_payload",
                "owner_surface": ".agentic-workspace/memory/repo/",
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
            "Use planning_surfaces when the prompt changes .agentic-workspace/planning/state.toml or execplans.",
            "Use memory_payload when the prompt changes durable repo knowledge or routing notes.",
        ],
        "owner_inference": [
            ".agentic-workspace/planning/state.toml or an active execplan implies planning ownership.",
            ".agentic-workspace/memory/repo/index.md or a runbook implies memory ownership.",
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
        "canonical_doc": ".agentic-workspace/docs/delegation-posture-contract.md",
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
                ".agentic-workspace/memory/repo/index.md",
                ".agentic-workspace/memory/repo/current/",
                ".agentic-workspace/memory/repo/runbooks/",
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
            local_only_repo_root=None,
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
        local_only_repo_root=None,
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

    def _is_review_only_issue(issue: str) -> bool:
        return "target is inside parent repository" in issue and "--target is being treated as authoritative" in issue

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
                if kind in {"missing", "warning"} and not _is_review_only_issue(issue):
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
            if not _is_review_only_issue(issue):
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
                "- Treat .agentic-workspace/config.toml as the repo-owned source of lifecycle defaults and update intent.",
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
            ".agentic-workspace/planning/state.toml",
            "llms.txt",
            "docs/delegated-judgment-contract.md",
            "docs/init-lifecycle.md",
            "agentic-workspace defaults --format json",
            "agentic-workspace config --target ./repo --format json",
        ],
    }


def _reporting_schema_payload() -> dict[str, Any]:
    return report_contract_manifest().copy()


def _surface_value_guardrail_payload() -> dict[str, Any]:
    return {
        "canonical_doc": ".agentic-workspace/docs/system-intent-contract.md",
        "command": "agentic-workspace defaults --section surface_value_guardrail --format json",
        "owner_surface": "workspace",
        "rule": (
            "New durable contract, memory, report, workflow, adapter, or local-only surfaces must show that they lower "
            "repeated future cost more than they increase product feel."
        ),
        "applies_to": [
            "checked-in contract or schema surfaces",
            "memory and local-only memory surfaces",
            "workspace or module report surfaces",
            "workflow, adapter, and generated startup surfaces",
        ],
        "value_questions": [
            "what repeated cost does this remove?",
            "which existing surface does it replace, compress, merge, or make cheaper?",
            "who owns it and is it authoritative, derived, adapter, or procedural-owned?",
            "how does an agent discover it without broad rereading?",
            "how does it remain removable, low-residue, or backgrounded?",
            "what drift or review check keeps it trustworthy?",
        ],
        "preference_order": [
            "remove an unnecessary surface",
            "replace or merge with an existing compact surface",
            "compress or background an existing surface",
            "add a new durable surface only when the repeated cost and owner are explicit",
        ],
        "authority_classes": [
            {"class": "authoritative", "test": "other surfaces should defer to it for this concern"},
            {"class": "derived", "test": "it can be regenerated or reconstructed from a stronger source"},
            {"class": "adapter", "test": "it routes a specific tool or audience into stronger structured surfaces"},
            {"class": "procedural-owned", "test": "runtime code owns behavior until it is extracted into a contract"},
        ],
        "review_result": {
            "accept_when": [
                "the repeated cost is real and likely to recur",
                "ownership and authority class are explicit",
                "discovery starts from an existing compact query or selector",
                "validation or drift checks are named",
            ],
            "reject_when": [
                "the surface mainly makes a concept feel cleaner locally",
                "agents would need another first-line thing to remember",
                "the same result can be achieved by compressing, replacing, or backgrounding an existing surface",
            ],
        },
        "review_gate": {
            "ordinary_path": "agentic-workspace proof --target ./repo --changed <paths> --format json",
            "answer_field": "surface_value_review",
            "rule": "Durable-surface changes should carry an inspectable answer during ordinary proof selection.",
            "flags_additive_only_when": [
                "the changed durable path does not currently exist under the target",
                "the change appears to add a new first-line docs, contract, schema, workflow, adapter, report, memory, or planning surface",
                "no repeated-cost, ownership, discovery, and validation answer is visible",
            ],
        },
    }


def _effective_authority_payload(
    *,
    target_root: Path | None = None,
    config: WorkspaceConfig | None = None,
    installed_modules: list[str] | None = None,
    module_reports: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    active_direction = _effective_active_direction_payload(module_reports=module_reports or [])
    active_status = "present" if active_direction else "absent"
    active_surface = ""
    if isinstance(active_direction, dict):
        active_surface = str(active_direction.get("surface", "") or active_direction.get("task", {}).get("surface", ""))
    installed = set(installed_modules or [])
    contract_inventory = contract_inventory_manifest()
    contract_areas = contract_inventory.get("areas", [])
    config_payload = _system_intent_source_payload(config) if config is not None else {}
    unresolved_gaps: list[dict[str, str]] = []
    if active_status == "absent":
        unresolved_gaps.append(
            {
                "id": "no-active-planning-record",
                "summary": "No active planning record is present, so current-work alignment cannot be judged from an active execplan.",
                "recommended_query": "agentic-workspace summary --format json",
            }
        )
    if "memory" not in installed:
        unresolved_gaps.append(
            {
                "id": "memory-not-installed",
                "summary": "Durable Memory authority is absent; reusable learning has no shared module surface.",
                "recommended_query": "agentic-workspace modules --format json",
            }
        )
    return {
        "canonical_doc": ".agentic-workspace/docs/system-intent-contract.md",
        "command": "agentic-workspace report --target ./repo --format json",
        "defaults_command": "agentic-workspace defaults --section effective_authority --format json",
        "rule": (
            "Use this compact view to identify the current authority for intent, policy, active work, durable knowledge, "
            "checks, contracts, and runtime behavior before claiming system-intent alignment or closure."
        ),
        "status": "needs-review" if unresolved_gaps else "ready",
        "current_work": {
            "status": active_status,
            "surface": active_surface,
            "source": "planning module report" if active_status == "present" else "none",
        },
        "authority_map": [
            {
                "concern": "confirmed intent",
                "authority_class": "authoritative",
                "owner": "human or live issue cluster",
                "surface": "current request and checked external-work evidence",
                "status": "runtime",
            },
            {
                "concern": "compiled system intent",
                "authority_class": "authoritative",
                "owner": "workspace",
                "surface": ".agentic-workspace/system-intent/intent.toml",
                "status": "present",
            },
            {
                "concern": "workspace policy",
                "authority_class": "authoritative",
                "owner": "repo",
                "surface": ".agentic-workspace/config.toml",
                "status": "present" if config is not None else "unknown",
            },
            {
                "concern": "active plan and continuation",
                "authority_class": "authoritative",
                "owner": "planning",
                "surface": active_surface or ".agentic-workspace/planning/state.toml",
                "status": active_status,
            },
            {
                "concern": "durable repo knowledge",
                "authority_class": "authoritative",
                "owner": "memory",
                "surface": ".agentic-workspace/memory/repo/",
                "status": "present" if "memory" in installed else "absent",
            },
            {
                "concern": "surface ownership",
                "authority_class": "authoritative",
                "owner": "workspace",
                "surface": ".agentic-workspace/OWNERSHIP.toml",
                "status": "present",
            },
            {
                "concern": "contract extraction and schema coverage",
                "authority_class": "derived",
                "owner": "workspace",
                "surface": "src/agentic_workspace/contracts/contract_inventory.json",
                "status": "present",
            },
            {
                "concern": "runtime implementation",
                "authority_class": "procedural-owned",
                "owner": "workspace",
                "surface": "src/agentic_workspace/cli.py",
                "status": "present",
            },
        ],
        "system_intent_embodiment": {
            "status": "needs-review" if unresolved_gaps else "inspectable",
            "must_answer_before_closure": [
                "Did the slice preserve the larger intended outcome, not only land a local implementation?",
                "Where does unresolved continuation belong?",
                "Did new durable surfaces pass the surface-value guardrail?",
                "Which authoritative surfaces changed and which should remain untouched?",
            ],
            "anti_framework_pressure": _surface_value_guardrail_payload()["preference_order"],
        },
        "provenance": {
            "system_intent_sources": config_payload.get("sources", []),
            "system_intent_preferred_source": config_payload.get("preferred_source", ""),
            "contract_inventory": "src/agentic_workspace/contracts/contract_inventory.json",
            "contract_area_count": len(contract_areas) if isinstance(contract_areas, list) else 0,
            "report": "agentic-workspace report --target ./repo --format json",
            "summary": "agentic-workspace summary --format json",
            "ownership": "agentic-workspace ownership --target ./repo --format json",
        },
        "unresolved_gaps": unresolved_gaps,
    }


def _agent_configuration_system_payload() -> dict[str, Any]:
    canonical_doc = ".agentic-workspace/docs/workspace-config-contract.md"
    return {
        "canonical_doc": canonical_doc,
        "command": "agentic-workspace defaults --section agent_configuration_system --format json",
        "rule": (
            "Treat Agentic Workspace as the repo-owned structured agent configuration substrate: "
            "workspace hosts the substrate, planning and memory attach as modules, and prose startup surfaces act as adapters."
        ),
        "owner_surface": ".agentic-workspace/config.toml",
        "owner_rule": "Repo-owned config selects workspace policy; workspace-owned contract docs, ownership, and descriptors define the substrate shape.",
        "configuration_classes": [
            {
                "id": "startup_and_adapter_policy",
                "summary": "startup entrypoint, prose-adapter role, and workflow-artifact profile",
                "primary_owner": "workspace config plus workspace contract docs",
                "ask_first": "agentic-workspace defaults --section startup --format json",
            },
            {
                "id": "workspace_policy",
                "summary": "repo-owned preset, update intent, improvement latitude, and optimization bias",
                "primary_owner": ".agentic-workspace/config.toml",
                "ask_first": "agentic-workspace config --target ./repo --format json",
            },
            {
                "id": "module_attachment",
                "summary": "which modules exist, what they own, and how they compose",
                "primary_owner": "module descriptors plus .agentic-workspace/OWNERSHIP.toml",
                "ask_first": "agentic-workspace ownership --target ./repo --format json",
            },
            {
                "id": "module_state",
                "summary": "active planning state and durable memory state that consume the substrate without moving ownership to workspace",
                "primary_owner": "planning and memory surfaces",
                "ask_first": "agentic-workspace report --target ./repo --format json",
            },
        ],
        "authority_map": [
            {"concern": "workspace policy", "surface": ".agentic-workspace/config.toml", "owner": "repo"},
            {"concern": "shared substrate contract", "surface": canonical_doc, "owner": "workspace"},
            {"concern": "ownership and authority lookup", "surface": ".agentic-workspace/OWNERSHIP.toml", "owner": "workspace"},
            {"concern": "module attachment metadata", "surface": "workspace module descriptors", "owner": "workspace"},
            {"concern": "active execution state", "surface": ".agentic-workspace/planning/state.toml", "owner": "planning"},
            {"concern": "durable understanding", "surface": ".agentic-workspace/memory/repo/", "owner": "memory"},
        ],
        "module_attachment_points": [
            "descriptor lifecycle commands and install detection",
            "workflow surfaces and generated artifacts",
            "startup steps and sources of truth",
            "capabilities, dependencies, and conflicts",
            "module result-contract shape",
        ],
        "adapter_surfaces": [
            {"surface": "AGENTS.md", "role": "ordinary startup adapter over structured substrate"},
            {"surface": "llms.txt", "role": "external install/adopt adapter over structured substrate"},
            {
                "surface": ".agentic-workspace/planning/agent-manifest.json",
                "role": "planning package-owned generation source over structured substrate",
            },
        ],
        "selective_loading": {
            "rule": "Prefer the smallest compact query that answers the current configuration question before opening broader prose.",
            "first_queries": [
                "agentic-workspace defaults --section agent_configuration_system --format json",
                "agentic-workspace config --target ./repo --format json",
                "agentic-workspace ownership --target ./repo --format json",
                "agentic-workspace modules --format json",
                "agentic-workspace report --target ./repo --format json",
            ],
        },
        "must_not": [
            "treat planning as the owner of general workflow extension machinery",
            "turn the workspace substrate into a scheduler or full workflow engine",
            "let prose startup files become the primary authority again once the substrate can answer the question directly",
        ],
    }


def _agent_configuration_queries_payload() -> dict[str, Any]:
    canonical_doc = ".agentic-workspace/docs/workspace-config-contract.md"
    return {
        "canonical_doc": canonical_doc,
        "command": "agentic-workspace defaults --section agent_configuration_queries --format json",
        "rule": (
            "Treat selective loading as a first-class design constraint: ask one compact configuration question first, "
            "then route to deeper module or doc surfaces only when the compact answer is insufficient."
        ),
        "query_classes": [
            {
                "id": "startup_path",
                "question": "What is the startup path?",
                "ask_first": "agentic-workspace defaults --section startup --format json",
                "then_if_needed": [
                    "agentic-workspace config --target ./repo --format json",
                    "AGENTS.md",
                ],
            },
            {
                "id": "active_behavior_modules",
                "question": "What behavior modules are active?",
                "ask_first": "agentic-workspace ownership --target ./repo --format json",
                "then_if_needed": [
                    "agentic-workspace modules --format json",
                    "agentic-workspace report --target ./repo --format json",
                ],
            },
            {
                "id": "proof_and_ownership_rules",
                "question": "What proof and ownership rules apply here?",
                "ask_first": "agentic-workspace ownership --target ./repo --format json",
                "then_if_needed": [
                    "agentic-workspace defaults --section validation --format json",
                    "agentic-workspace report --target ./repo --format json",
                ],
            },
            {
                "id": "repo_local_current_work",
                "question": "What repo-local behavior is relevant to the current lane or surface?",
                "ask_first": "agentic-workspace summary --format json",
                "then_if_needed": [
                    "agentic-workspace report --target ./repo --format json",
                    ".agentic-workspace/planning/execplans/<active>.md",
                ],
            },
            {
                "id": "relevant_subinstructions",
                "question": "Which subinstructions are relevant right now, and which can remain unloaded?",
                "ask_first": "agentic-workspace defaults --section agent_configuration_queries --format json",
                "then_if_needed": [
                    "agentic-workspace report --target ./repo --format json",
                    "module-local docs or runbooks only for the modules and surfaces already in scope",
                ],
            },
        ],
        "loading_rules": [
            "prefer one compact answer over broad prose rereads",
            "route from workspace defaults/config/ownership/report before opening module-local prose",
            "load planning or memory details only when the compact answer points at active work or durable module-owned state",
            "leave unrelated modules and subinstructions unloaded unless the current surface, proof lane, or active planning state makes them relevant",
        ],
        "stop_rule": "Stop after the first compact answer that settles the question; deeper reads are justified only when the compact answer points at a specific owner or active surface.",
    }


def _agent_configuration_workflow_extensions_payload() -> dict[str, Any]:
    canonical_doc = ".agentic-workspace/docs/workspace-config-contract.md"
    return {
        "canonical_doc": canonical_doc,
        "command": "agentic-workspace defaults --section agent_configuration_workflow_extensions --format json",
        "rule": (
            "Declare small repo-custom workflow obligations in `.agentic-workspace/config.toml` so workspace owns the "
            "extension mechanism and planning only consumes relevant obligations."
        ),
        "definition_format": copy.deepcopy(_WORKFLOW_DEFINITION_FORMAT),
        "owner_surface": ".agentic-workspace/config.toml [workflow_obligations]",
        "fields": [
            {"field": "summary", "purpose": "bounded repo-local expectation worth surfacing into active work"},
            {"field": "stage", "purpose": "when the obligation matters"},
            {"field": "scope_tags", "purpose": "which slices or surfaces should consider the obligation relevant"},
            {"field": "commands", "purpose": "bounded commands or checks the repo expects before the stage completes"},
            {"field": "review_hint", "purpose": "compact reminder for review or closure surfaces"},
        ],
        "supported_stages": list(SUPPORTED_WORKFLOW_OBLIGATION_STAGES),
        "consumption_rule": [
            "workspace owns declaration and reporting of repo-custom workflow obligations",
            "planning consumes only the obligations relevant to the current touched scope",
            "adapter surfaces may mention the mechanism but should not become the primary declaration home",
        ],
        "must_not": [
            "turn workflow obligations into a general scheduler",
            "move planning ownership into workspace config",
            "encode every minor preference as a workflow obligation",
        ],
    }


def _emit_startup_report(
    *,
    format_name: str,
    target_root: Path,
    descriptors: dict[str, ModuleDescriptor],
    config: WorkspaceConfig,
) -> None:
    from repo_planning_bootstrap.installer import planning_report

    plan_report = planning_report(target=target_root)
    active_record = plan_report.get("active", {}).get("planning_record", {})

    manifest_path = target_root / ".agentic-workspace" / "planning" / "agent-manifest.json"
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    tiny_safe_model = _defaults_payload()["startup"]["tiny_safe_model"].copy()
    tiny_safe_model["cli_invoke"] = config.cli_invoke
    tiny_safe_model["first_compact_queries"] = [
        query.replace("agentic-workspace", config.cli_invoke) for query in tiny_safe_model["first_compact_queries"]
    ]

    payload = {
        "kind": "startup-report/v1",
        "active_intent": active_record.get("requested_outcome") or "No active intent",
        "immediate_next_action": active_record.get("next_action") or "No next action",
        "tiny_safe_model": tiny_safe_model,
        "module_boundaries": _defaults_payload()["startup"]["top_level_capabilities"],
        "critical_invariants": manifest.get("invariants") or [],
        "escalation_boundaries": active_record.get("escalate_when") or [],
        "relevant_handoff_context": plan_report.get("active", {}).get("handoff_contract") or {},
    }

    _emit_payload(payload=payload, format_name=format_name)


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
                ".agentic-workspace/planning/state.toml or execplans change without broader code changes",
                "the trust question is planning-surface shape or drift only",
            ],
            "enough_proof": [
                "agentic-workspace doctor --target ./repo --modules planning --format json",
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
            "default_cli_invoke": DEFAULT_CLI_INVOKE,
            "canonical_doc": ".agentic-workspace/docs/minimum-operating-model.md",
            "primary": [
                "For one-call takeover context, run `agentic-workspace preflight --format json`.",
                "Read the configured root startup file from `agentic-workspace config --target ./repo --format json` (default `AGENTS.md`).",
                "Read `.agentic-workspace/planning/state.toml` via `agentic-workspace summary`.",
                "Read the active execplan only when `state.toml` points to one.",
            ],
            "tiny_safe_model": {
                "summary": "Start from one repo entrypoint, one cheap takeover query, and conditional deeper reads.",
                "entrypoint": "AGENTS.md",
                "first_compact_queries": [
                    "agentic-workspace preflight --format json",
                    "agentic-workspace defaults --section startup --format json",
                    "agentic-workspace config --target ./repo --format json",
                    "agentic-workspace summary --format json",
                ],
                "deeper_reads_become_valid_when": [
                    "the active summary points at an execplan or raw planning detail is still needed",
                    "startup or routing ambiguity survives the compact startup answer",
                    "the task crosses a planning, memory, or lifecycle boundary that the small model cannot settle safely",
                ],
            },
            "default_canonical_agent_instructions_file": DEFAULT_AGENT_INSTRUCTIONS_FILE,
            "supported_agent_instructions_files": list(SUPPORTED_AGENT_INSTRUCTIONS_FILES),
            "first_queries": [
                {
                    "question": "What is the cheapest one-call takeover path?",
                    "command": "agentic-workspace preflight --format json",
                    "field": "startup_guidance",
                    "why": "preflight bundles startup guidance, resolved config, and active state into one compact answer",
                },
                {
                    "question": "What is the ordinary repo startup path?",
                    "command": "agentic-workspace defaults --section startup --format json",
                    "why": "startup defaults carry the compact ordered route without reopening broader prose first",
                },
                {
                    "question": "Which startup file is canonical here?",
                    "command": "agentic-workspace config --target ./repo --format json",
                    "field": "workspace.agent_instructions_file",
                    "why": "repo config is authoritative when the startup filename differs from the default `AGENTS.md`",
                },
                {
                    "question": "What is active right now?",
                    "command": "agentic-workspace summary --format json",
                    "field": "planning_record",
                    "why": "active-state recovery should come from the compact planning summary before raw planning prose",
                },
            ],
            "surface_roles": [
                {
                    "surface": "AGENTS.md",
                    "role": "canonical ordinary repo startup entrypoint",
                    "owner": "repo",
                    "kind": "canonical",
                    "edit_rule": "edit directly when repo startup policy changes",
                },
                {
                    "surface": ".agentic-workspace/planning/state.toml",
                    "role": "canonical active queue after startup",
                    "owner": "repo",
                    "kind": "canonical",
                    "edit_rule": "edit directly as the active queue surface",
                },
                {
                    "surface": "llms.txt",
                    "role": "external install/adopt handoff only",
                    "owner": "repo",
                    "kind": "canonical",
                    "edit_rule": "keep bounded to external bootstrap and adopt flow",
                },
                {
                    "surface": ".agentic-workspace/planning/agent-manifest.json",
                    "role": "planning package-owned generation source",
                    "owner": "planning package",
                    "kind": "managed",
                    "edit_rule": "update through the common CLI and package-managed installers",
                },
            ],
            "external_handoff": {
                "surface": "llms.txt",
                "when": "external install or adopt first contact",
                "rule": "Use `llms.txt` only to bootstrap or adopt the workspace, then return to the configured startup entrypoint for ordinary repo work.",
            },
            "secondary": [
                "Check the roadmap in `state.toml` (authoritative) only when promoting work.",
                "Read package-local `AGENTS.md` only for the package being edited.",
                "Read memory only when installed and the task needs durable context.",
            ],
            "escalation_cues": [
                {
                    "boundary": "workspace",
                    "cue": "The question is startup order, lifecycle behavior, config, ownership, or combined workspace state.",
                    "load_next": [
                        "agentic-workspace defaults --section startup --format json",
                        "agentic-workspace config --target ./repo --format json",
                        "agentic-workspace report --target ./repo --format json",
                    ],
                    "why": "Workspace-level surfaces own routing, lifecycle orchestration, and cross-module coordination.",
                },
                {
                    "boundary": "planning",
                    "cue": "The task needs active sequencing, blockers, proof expectations, promotion decisions, or cross-session continuation.",
                    "load_next": [
                        "agentic-workspace summary --format json",
                        ".agentic-workspace/planning/state.toml",
                        ".agentic-workspace/planning/execplans/",
                    ],
                    "why": "Planning owns active execution state and near-term follow-through.",
                },
                {
                    "boundary": "memory",
                    "cue": "The work keeps rediscovering repo facts, prior decisions, failure modes, or domain context that should survive the current slice.",
                    "load_next": [
                        ".agentic-workspace/memory/repo/",
                        ".agentic-workspace/memory/WORKFLOW.md",
                    ],
                    "why": "Memory owns durable anti-rediscovery knowledge instead of active execution state.",
                },
            ],
            "top_level_capabilities": [
                {
                    "module": "workspace",
                    "owns": "startup, lifecycle, routing, and combined workspace reporting",
                    "escalate_when": "the task crosses config, install/adopt, ownership, or cross-module coordination boundaries",
                    "capability_unlocked": "compact defaults/config/report guidance plus authoritative workspace contracts",
                },
                {
                    "module": "planning",
                    "owns": "active execution state, sequencing, proof expectations, and promotion-ready follow-through",
                    "escalate_when": "the task needs milestones, blockers, queue updates, or explicit continuation semantics",
                    "capability_unlocked": "summary, active queue state, execplans, and planning validation surfaces",
                },
                {
                    "module": "memory",
                    "owns": "durable repo knowledge, routed decisions, failure modes, and anti-rediscovery context",
                    "escalate_when": "relevant repo understanding should persist beyond the current chat or implementation slice",
                    "capability_unlocked": "routed memory notes and memory workflow guidance",
                },
            ],
            "fallbacks": [
                (
                    "If the current agent does not natively look for `AGENTS.md`, inspect "
                    "`agentic-workspace config --target ./repo --format json` and follow "
                    "the configured startup file; if the CLI is unavailable, fall back to "
                    "`AGENTS.md` or another supported startup file already present."
                ),
                (
                    "If you need startup guidance plus live state together, prefer "
                    "`agentic-workspace preflight --format json` before running multiple compact queries or rereading repo prose."
                ),
                (
                    "If the question is active planning recovery rather than startup order, "
                    "prefer `agentic-workspace summary --format json` before raw "
                    "planning state or execplan prose."
                ),
            ],
            "workflow_recovery": [
                (
                    "When startup, first-contact routing, or recovery is unclear, prefer "
                    "`agentic-workspace preflight --format json`, "
                    "`agentic-workspace defaults --section startup --format json`, "
                    "`agentic-workspace config --target ./repo --format json`, and "
                    "`agentic-workspace summary --format json` before broader "
                    "prose or repo-local workaround guidance."
                ),
            ],
        },
        "compact_contract_profile": {
            "canonical_doc": compact_manifest["canonical_doc"],
            "rule": "When one bounded answer is enough, prefer a narrow selector over a whole-surface dump.",
            "answer_shape": list(compact_manifest["answer_shape"]),
            "selectors": {key: value["command"] for key, value in compact_manifest["selectors"].items()},
        },
        "operating_questions": {
            "canonical_doc": "docs/which-package.md",
            "command": "agentic-workspace defaults --section operating_questions --format json",
            "rule": "For routine operational lookup, ask the smallest question first and stop at the first compact surface that answers it.",
            "questions": [
                {
                    "id": "startup_or_lifecycle_path",
                    "question": "How do I start, or which lifecycle path applies?",
                    "ask_first": "agentic-workspace defaults --section startup --format json",
                    "then_if_needed": [
                        "agentic-workspace config --target ./repo --format json",
                        ".agentic-workspace/docs/lifecycle-and-config-contract.md",
                    ],
                },
                {
                    "id": "active_state",
                    "question": "What is active right now?",
                    "ask_first": "agentic-workspace summary --format json",
                    "then_if_needed": [
                        ".agentic-workspace/planning/state.toml",
                        ".agentic-workspace/planning/execplans/",
                    ],
                },
                {
                    "id": "combined_workspace_state",
                    "question": "What does the combined workspace state look like?",
                    "ask_first": "agentic-workspace preflight --target ./repo --format json",
                    "then_if_needed": [
                        "agentic-workspace report --target ./repo --format json",
                        ".agentic-workspace/docs/reporting-contract.md",
                        "raw module files only when the report is insufficient",
                    ],
                },
                {
                    "id": "proof_or_ownership_answer",
                    "question": "Which proof or ownership answer is enough?",
                    "ask_first": "agentic-workspace defaults --section proof_selection --format json",
                    "then_if_needed": [
                        "agentic-workspace proof --target ./repo --format json",
                        "agentic-workspace ownership --target ./repo --format json",
                        ".agentic-workspace/docs/compact-contract-profile.md",
                    ],
                },
                {
                    "id": "setup_or_handoff_home",
                    "question": "Where does setup or external handoff work live?",
                    "ask_first": "agentic-workspace setup --target ./repo --format json",
                    "then_if_needed": [
                        "llms.txt",
                        ".agentic-workspace/bootstrap-handoff.md",
                        ".agentic-workspace/bootstrap-handoff.json",
                    ],
                },
                {
                    "id": "mixed_agent_posture",
                    "question": "What mixed-agent posture is in effect here?",
                    "ask_first": "agentic-workspace config --target ./repo --format json",
                    "then_if_needed": [
                        ".agentic-workspace/docs/delegation-posture-contract.md",
                    ],
                },
            ],
            "stop_rule": "Do not reopen broader docs once one compact surface has answered the routine question.",
        },
        "install_profiles": {
            "canonical_doc": "docs/which-package.md",
            "command": "agentic-workspace defaults --section install_profiles --format json",
            "rule": "Use the public workspace entrypoint and choose the preset that matches the repo's main operating problem.",
            "default_entrypoint": "agentic-workspace",
            "default_answer": "Use `agentic-workspace` and choose the preset that matches the repo problem.",
            "profiles": [
                {
                    "preset": "memory",
                    "main_problem": "Stable repo knowledge keeps getting rediscovered.",
                    "why": "Memory is the smallest useful operational profile for durable context and quiet routing.",
                    "good_fit": [
                        "subsystem knowledge is expensive to rediscover",
                        "recurring traps or operator sequences should be shared",
                        "the repo already has task tracking but lacks durable shared knowledge",
                    ],
                },
                {
                    "preset": "planning",
                    "main_problem": "Active work keeps drifting or fragmenting.",
                    "why": "Planning gives a checked-in active queue and bounded execplans.",
                    "good_fit": [
                        "work spans many short sessions",
                        "active execution drifts without a checked-in queue",
                        "backlog tools exist, but active implementation still fragments",
                    ],
                },
                {
                    "preset": "full",
                    "main_problem": "You want both durable knowledge and checked-in execution.",
                    "why": "The workspace layer composes both modules through one lifecycle entrypoint.",
                    "good_fit": [
                        "the repo wants both restartable execution and lower rediscovery cost",
                        "agents are regular maintainers and need both active state and durable context",
                    ],
                },
            ],
            "partial_adoption": [
                {
                    "combination": "memory only",
                    "supported": True,
                    "primary_writable_surfaces": [
                        ".agentic-workspace/memory/repo/",
                        ".agentic-workspace/memory/repo/current/ (weak authority)",
                    ],
                },
                {
                    "combination": "planning only",
                    "supported": True,
                    "primary_writable_surfaces": [
                        ".agentic-workspace/planning/state.toml",
                        ".agentic-workspace/planning/execplans/",
                    ],
                },
                {
                    "combination": "memory + planning",
                    "supported": True,
                    "primary_writable_surfaces": [
                        "Planning for active-now state",
                        "memory for durable knowledge",
                    ],
                },
            ],
            "lightweight_profile": {
                "preset": "memory",
                "summary": "Choose `memory` when you want the smallest useful core.",
                "why": "It keeps the visible surface smaller than `planning` or `full` while still giving the repo durable knowledge and compact routing.",
            },
        },
        "lifecycle": {
            "primary_entrypoint": "agentic-workspace",
            "default_install_command": "agentic-workspace install --target ./repo --preset <memory|planning|full>",
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
            "secondary": list(_SETUP_FINDINGS_POLICY["secondary"]),
        },
        "agent_configuration_system": _agent_configuration_system_payload(),
        "agent_configuration_queries": _agent_configuration_queries_payload(),
        "agent_configuration_workflow_extensions": _agent_configuration_workflow_extensions_payload(),
        "system_intent": _system_intent_payload(),
        "surface_value_guardrail": _surface_value_guardrail_payload(),
        "effective_authority": _effective_authority_payload(),
        "intent": _intent_contract_payload(),
        "clarification": _clarification_contract_payload(),
        "prompt_routing": _prompt_routing_contract_payload(),
        "relay": _relay_contract_payload(),
        "config": {
            "path": ".agentic-workspace/config.toml",
            "command": "agentic-workspace config --target ./repo --format json",
            "supported_fields": [
                "workspace.default_preset",
                "workspace.agent_instructions_file",
                "workspace.workflow_artifact_profile",
                "workspace.improvement_latitude",
                "workspace.optimization_bias",
                "system_intent.sources",
                "system_intent.preferred_source",
                "workflow_obligations.<name>.summary",
                "workflow_obligations.<name>.stage",
                "workflow_obligations.<name>.scope_tags",
                "workflow_obligations.<name>.commands",
                "workflow_obligations.<name>.review_hint",
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
            "canonical_doc": ".agentic-workspace/docs/workspace-config-contract.md",
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
            "mode_interpretation": copy.deepcopy(_IMPROVEMENT_LATITUDE_POLICY["mode_interpretation"]),
            "examples": copy.deepcopy(_IMPROVEMENT_LATITUDE_POLICY["examples"]),
            "guardrail_test": _workspace_self_adaptation_guardrail_payload(),
            "repo_directed_improvement_threshold": _repo_directed_improvement_evidence_threshold_payload(),
            "default_mode": str(_IMPROVEMENT_LATITUDE_POLICY["default_mode"]),
            "supported_modes": [_improvement_latitude_payload(mode) for mode in SUPPORTED_IMPROVEMENT_LATITUDES],
            "decision_test": _improvement_boundary_test_payload(),
            "evidence_source": str(_IMPROVEMENT_LATITUDE_POLICY["evidence_source"]),
            "evidence_classes": list(_IMPROVEMENT_LATITUDE_POLICY["evidence_classes"]),
            "validation_friction": _validation_friction_payload(),
        },
        "optimization_bias": {
            "canonical_doc": ".agentic-workspace/docs/workspace-config-contract.md",
            "command": "agentic-workspace defaults --section optimization_bias --format json",
            "rule": (
                "Repo-owned optimization bias may change output density and residue style, "
                "but it must not change execution method or canonical state semantics."
            ),
            "owner_surface": "workspace",
            "default_mode": str(_OPTIMIZATION_BIAS_POLICY["default_mode"]),
            "supported_modes": [_optimization_bias_payload(mode) for mode in SUPPORTED_OPTIMIZATION_BIASES],
            "applies_to": [
                "derived report rendering density",
                "rendered human-facing views",
                "durable residue style when canonical state is unchanged",
            ],
            "surface_boundary": copy.deepcopy(_OPTIMIZATION_BIAS_POLICY["surface_boundary"]),
            "must_not_change": list(_OPTIMIZATION_BIAS_POLICY["must_not_change"]),
        },
        "workflow_artifact_adapters": {
            "canonical_doc": ".agentic-workspace/docs/workspace-config-contract.md",
            "command": "agentic-workspace defaults --section workflow_artifact_adapters --format json",
            "rule": (
                "Runtime-native planning artifacts may exist, but durable cross-agent state "
                "must project back into .agentic-workspace/planning/state.toml and .agentic-workspace/planning/execplans before handoff or review."
            ),
            "default_profile": str(_WORKFLOW_ARTIFACT_PROFILES_MANIFEST["default_profile"]),
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
                "supported_target_locations": list(SUPPORTED_CAPABILITY_LOCATIONS),
                "supported_capability_classes": list(SUPPORTED_CAPABILITY_EXECUTION_CLASSES),
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
            "local_integration_area": {
                **_local_integration_area_payload(),
                "rule": (
                    "Vendor/runtime integration aids may live here to make local compliance cheaper, "
                    "but shared workflow truth must stay in repo-owned workspace, planning, and memory surfaces."
                ),
            },
            "local_memory": {
                "path": WORKSPACE_LOCAL_MEMORY_DEFAULT_PATH.as_posix(),
                "controlled_by": WORKSPACE_LOCAL_CONFIG_PATH.as_posix(),
                "status": "available-local-only",
                "authoritative": False,
                "advisory_only": True,
                "git_ignored": True,
                "rule": (
                    "Machine-local repo memory may support same-machine continuity when explicitly enabled, "
                    "but checked-in Memory remains the shared durable authority."
                ),
                "promotion_guidance": (
                    "Promote manually into checked-in Memory only when the knowledge is durable, shareable, non-private, "
                    "and useful beyond this machine."
                ),
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
            "delegated_run_guardrail": {
                "rule": (
                    "Before delegating bounded implementation, emit one compact preflight answer "
                    "and set closeout trust to lower-trust when weak-target signals are present."
                ),
                "required_preflight_checks": [
                    "recover handoff-quality must_recover fields from checked-in state",
                    "confirm bounded owned-write scope and stop conditions are explicit",
                    "select a local delegation target profile or stay direct",
                    "declare whether closeout starts as normal or lower-trust",
                ],
                "closeout_gate": {
                    "default_trust": "normal",
                    "lower_trust_when": [
                        "target advisory review burden is high",
                        "target strength is weak",
                        "delegation outcome evidence trends negative",
                    ],
                    "required_when_lower_trust": [
                        "human review before closeout",
                        "explicit execution residue proving bounded scope and validations",
                    ],
                },
            },
            "success_measures": [
                "lower long-run token cost",
                "lower restart and handoff cost",
                "cheap switching across agents and subscriptions",
                "persisted shared knowledge beats rediscovery",
            ],
            "runtime_resolution": {
                "rule": (
                    "Query runtime_resolution before delegating or escalating to get a compact answer "
                    "that combines work semantics with local execution posture."
                ),
                "resolution_categories": list(_RUNTIME_RESOLUTION_CATEGORIES),
                "posture_source_fields": [
                    "execution class",
                    "recommended strength",
                    "preferred location",
                    "delegation friendly",
                    "strong external reasoning",
                ],
                "resolution_algorithm": [
                    "strong_external_reasoning='preferred' → external-delegation if external targets exist, else stronger-reasoning, else manual-handoff",
                    "execution_class in (boundary-shaping, reasoning-heavy) or recommended_strength=strong → stronger-reasoning if available, else external-delegation, else manual-handoff",
                    "execution_class=mixed → stay-local if local profiles acceptable, else stronger-reasoning",
                    "execution_class=mechanical-follow-through or recommended_strength in (weak, medium) → stay-local",
                    "no posture → stay-local with confidence derived from cheap_bounded_executor_available",
                ],
                "confidence_levels": ["high", "medium", "low"],
            },
            "strong_handoff_packet": {
                "rule": (
                    "Use the strong_handoff_packet template when manual-handoff is the runtime recommendation "
                    "or when a bounded high-judgment question should be escalated to a strong general-purpose reasoning model. "
                    "Keep the packet compact: one question, bounded constraints, no full context dump."
                ),
                "required_fields": [
                    "context: one-paragraph summary of the current work and its bounded scope",
                    "question: the specific high-judgment question the strong model should answer",
                    "constraints: the hard constraints the answer must satisfy",
                    "expected_output: what a useful answer looks like (format and scope)",
                    "return_to: what the current executor should do with the answer once received",
                ],
                "optional_fields": [
                    "background: additional context that would materially help the strong model but is not strictly required",
                    "avoid: specific patterns or approaches the answer must not use",
                ],
                "size_guidance": "Target under 500 tokens for the full packet. Escalate one question at a time.",
                "after_receiving_answer": [
                    "Apply the answer to the current bounded task.",
                    "Do not reopen the full execplan or lane scope based on the answer alone.",
                    "Record the answer as a checked-in decision residue if it changes durable state.",
                ],
                "when_to_use": [
                    "runtime_resolution recommendation is 'manual-handoff'",
                    "a boundary decision requires judgment beyond the current executor's reliable range",
                    "an architectural or domain question would benefit from a strong external perspective",
                    "review uncertainty is high enough that stronger reasoning would change the closeout decision",
                ],
            },
        },
        "delegation_posture": {
            "canonical_doc": ".agentic-workspace/docs/delegation-posture-contract.md",
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
                ".agentic-workspace/config.local.toml runtime.supports_internal_delegation",
                ".agentic-workspace/config.local.toml runtime.strong_planner_available",
                ".agentic-workspace/config.local.toml runtime.cheap_bounded_executor_available",
                ".agentic-workspace/config.local.toml handoff.prefer_internal_delegation_when_available",
                ".agentic-workspace/config.local.toml delegation_targets.<target>.*",
                ".agentic-workspace/delegation-outcomes.json",
            ],
            "secondary": [
                "Do not treat config as a scheduler.",
                "Do not delegate when the task stays cheap and direct.",
                "Do not silently rewrite ends.",
            ],
            "capability_posture_fields": [
                "execution class",
                "recommended strength",
                "preferred location",
                "delegation friendly",
                "strong external reasoning",
                "why",
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
            "canonical_doc": ".agentic-workspace/docs/proof-surfaces-contract.md",
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
            "canonical_doc": ".agentic-workspace/docs/ownership-authority-contract.md",
            "command": "agentic-workspace ownership --target ./repo --format json",
            "rule": "Resolve the owner and authoritative surface before changing or trusting a contract.",
            "ledger": ".agentic-workspace/OWNERSHIP.toml",
            "default_routes": {
                "workspace_ownership": "agentic-workspace ownership --target ./repo --format json",
                "workflow_contract": ".agentic-workspace/WORKFLOW.md",
                "ownership_ledger": ".agentic-workspace/OWNERSHIP.toml",
                "compatibility_policy": ".agentic-workspace/docs/compatibility-policy.md",
                "generated_surface_trust": ".agentic-workspace/docs/generated-surface-trust.md",
            },
            "secondary": [
                "Read package-local docs only after the ownership map identifies the package as the primary owner.",
            ],
        },
        "combined_install": {
            "primary": "agentic-workspace install --target ./repo --preset full",
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
            "rule": "When a completed slice came from state.toml, clear the matched queue residue in the same pass.",
            "prefer_surfaces": [
                ".agentic-workspace/planning/state.toml",
                ".agentic-workspace/planning/execplans/README.md",
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
    for query in payload["startup"].get("first_queries", []):
        print(f"- first query: {query['command']}")
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
    print("Surface value guardrail:")
    print(f"- command: {payload['surface_value_guardrail']['command']}")
    print(f"- rule: {payload['surface_value_guardrail']['rule']}")
    print(f"- prefer: {payload['surface_value_guardrail']['preference_order'][0]}")
    print("Effective authority:")
    print(f"- command: {payload['effective_authority']['command']}")
    print(f"- rule: {payload['effective_authority']['rule']}")
    print(f"- status: {payload['effective_authority']['status']}")
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
    print("Agent configuration system:")
    print(f"- doc: {payload['agent_configuration_system']['canonical_doc']}")
    print(f"- command: {payload['agent_configuration_system']['command']}")
    print(f"- rule: {payload['agent_configuration_system']['rule']}")
    print(f"- owner surface: {payload['agent_configuration_system']['owner_surface']}")
    print("Agent configuration queries:")
    print(f"- doc: {payload['agent_configuration_queries']['canonical_doc']}")
    print(f"- command: {payload['agent_configuration_queries']['command']}")
    print(f"- rule: {payload['agent_configuration_queries']['rule']}")
    print("Agent configuration workflow extensions:")
    print(f"- doc: {payload['agent_configuration_workflow_extensions']['canonical_doc']}")
    print(f"- command: {payload['agent_configuration_workflow_extensions']['command']}")
    print(f"- rule: {payload['agent_configuration_workflow_extensions']['rule']}")
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
    print(f"- local integration area: {payload['mixed_agent']['local_integration_area']['root']}")
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
        target_root / ".agentic-workspace/planning/state.toml",
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
        local_only_repo_root=None,
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
            "reason": "AGENTS.md, .agentic-workspace/planning/state.toml, .agentic-workspace/planning/agent-manifest.json, and .agentic-workspace/memory/repo/index.md are already present.",
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


def _select_proof_payload(
    payload: dict[str, Any],
    *,
    target_root: Path,
    route: str | None,
    current_only: bool,
    changed_paths: list[str] | None = None,
) -> dict[str, Any]:
    normalized_paths = _normalize_changed_paths(changed_paths or [])
    selector_count = sum(1 for selected in (bool(route), current_only, bool(normalized_paths)) if selected)
    if selector_count > 1:
        raise WorkspaceUsageError("proof selectors are mutually exclusive; use only one of --route, --current, or --changed.")
    if normalized_paths:
        answer = _proof_selection_for_changed_paths(changed_paths=normalized_paths, target_root=target_root)
        refs = [compact_contract_manifest()["canonical_doc"], payload["command"], payload["canonical_doc"]]
        return _compact_contract_answer(
            surface="proof",
            selector={"changed": normalized_paths},
            answer=answer,
            refs=refs,
            target=payload["target"],
        )
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
    changed_paths: list[str] | None = None,
) -> None:
    payload = _proof_payload(target_root=target_root, descriptors=descriptors)
    payload = _select_proof_payload(
        payload,
        target_root=target_root,
        route=route,
        current_only=current_only,
        changed_paths=changed_paths,
    )
    if format_name == "json":
        print(json.dumps(serialise_value(payload), indent=2))
        return
    if route or current_only or changed_paths:
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
        config = config_lib.load_workspace_config(target_root=target_root, valid_presets=set(_preset_modules(descriptors)))
        status_payload = _run_lifecycle_command(
            command_name="status",
            target_root=target_root,
            local_only_repo_root=None,
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
            local_only_repo_root=None,
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


def _normalize_changed_paths(paths: list[str]) -> list[str]:
    normalized: list[str] = []
    for path_text in paths:
        stripped = str(path_text).strip()
        if not stripped:
            continue
        path = Path(stripped)
        try:
            if path.is_absolute():
                stripped = path.resolve().as_posix()
            else:
                stripped = path.as_posix()
        except OSError:
            stripped = path.as_posix()
        while stripped.startswith("./"):
            stripped = stripped[2:]
        stripped = stripped.rstrip("/")
        if stripped and stripped not in normalized:
            normalized.append(stripped)
    return normalized


def _proof_selection_for_changed_paths(*, changed_paths: list[str], target_root: Path | None = None) -> dict[str, Any]:
    defaults = _defaults_payload()
    validation_lanes = defaults["validation"]["lanes"]

    def _lane(lane_id: str) -> dict[str, Any]:
        return next(lane for lane in validation_lanes if lane["id"] == lane_id)

    selected_ids: list[str] = []

    def _select(lane_id: str) -> None:
        if lane_id not in selected_ids:
            selected_ids.append(lane_id)

    for changed_path in changed_paths:
        matched_rule = False
        for rule in _PROOF_SELECTION_RULES["rules"]:
            exact_matches = set(rule.get("exact", []))
            prefixes = tuple(rule.get("prefixes", []))
            if changed_path in exact_matches or changed_path.startswith(prefixes):
                _select(str(rule["lane"]))
                matched_rule = True
                break
        if not matched_rule:
            _select(str(_PROOF_SELECTION_RULES["fallback_lane"]))

    selected_lanes = [_lane(lane_id) for lane_id in selected_ids]
    required_commands: list[str] = []
    broaden_when: list[str] = []
    escalate_when: list[str] = []
    for lane in selected_lanes:
        for command in lane.get("enough_proof", []):
            if command not in required_commands:
                required_commands.append(command)
        for condition in lane.get("broaden_when", []):
            if condition not in broaden_when:
                broaden_when.append(condition)
        for condition in lane.get("escalate_when", []):
            if condition not in escalate_when:
                escalate_when.append(condition)

    if len(selected_lanes) > 1:
        escalate_when.insert(0, str(_PROOF_SELECTION_RULES["cross_lane_escalation"]))

    proof_selection = {
        "kind": "proof-selection/v1",
        "changed_paths": changed_paths,
        "selected_lanes": [
            {
                "id": lane["id"],
                "when": lane["when"],
                "required_commands": lane["enough_proof"],
            }
            for lane in selected_lanes
        ],
        "required_commands": required_commands,
        "optional_commands": [
            "agentic-workspace proof --target ./repo --current --format json",
            "agentic-workspace summary --format json",
        ],
        "broaden_when": broaden_when,
        "escalate_when": escalate_when,
    }
    surface_value_review = _surface_value_review_for_changed_paths(changed_paths=changed_paths, target_root=target_root)
    if surface_value_review["durable_surface_count"]:
        proof_selection["surface_value_review"] = surface_value_review
    return proof_selection


def _surface_value_review_for_changed_paths(*, changed_paths: list[str], target_root: Path | None) -> dict[str, Any]:
    guardrail = _surface_value_guardrail_payload()
    reviewed_paths: list[dict[str, Any]] = []
    flagged_count = 0
    accepted_count = 0
    for changed_path in changed_paths:
        durable_class = _durable_surface_class(changed_path)
        if not durable_class:
            continue
        path_exists = _changed_path_exists(target_root=target_root, changed_path=changed_path)
        if path_exists:
            result = "accepted"
            disposition = "existing durable surface update"
            reason = "updating an existing durable surface is lower residue than adding a new first-line concept"
            accepted_count += 1
        else:
            result = "flagged"
            disposition = "additive-only durable surface candidate"
            reason = "new durable surfaces need explicit repeated-cost, owner, discovery, and validation answers"
            flagged_count += 1
        reviewed_paths.append(
            {
                "path": changed_path,
                "surface_class": durable_class,
                "exists_under_target": path_exists,
                "result": result,
                "disposition": disposition,
                "reason": reason,
                "required_answers": guardrail["value_questions"],
            }
        )
    status = "not-applicable"
    if flagged_count:
        status = "attention-needed"
    elif accepted_count:
        status = "accepted"
    return {
        "kind": "surface-value-review/v1",
        "status": status,
        "rule": guardrail["rule"],
        "preference_order": guardrail["preference_order"],
        "durable_surface_count": len(reviewed_paths),
        "accepted_count": accepted_count,
        "flagged_count": flagged_count,
        "reviewed_paths": reviewed_paths,
        "accept_when": guardrail["review_result"]["accept_when"],
        "reject_when": guardrail["review_result"]["reject_when"],
        "review_gate": guardrail["review_gate"],
    }


def _changed_path_exists(*, target_root: Path | None, changed_path: str) -> bool:
    path = Path(changed_path)
    if path.is_absolute():
        return path.exists()
    if target_root is None:
        return path.exists()
    return (target_root / path).exists()


def _durable_surface_class(changed_path: str) -> str | None:
    normalized = changed_path.replace("\\", "/").strip("/")
    if normalized in {"AGENTS.md", "llms.txt", "SYSTEM_INTENT.md", "README.md"}:
        return "adapter_or_repo_intent_surface"
    if normalized.startswith("src/agentic_workspace/contracts/"):
        return "workspace_contract_surface"
    if normalized.startswith(".agentic-workspace/docs/") or normalized.startswith("docs/"):
        return "docs_or_review_surface"
    if normalized.startswith(".agentic-workspace/memory/"):
        return "memory_surface"
    if normalized.startswith(".agentic-workspace/planning/execplans/"):
        return "planning_execplan_surface"
    if normalized.startswith(".agentic-workspace/planning/reviews/"):
        return "planning_review_surface"
    if normalized in {".agentic-workspace/WORKFLOW.md", ".agentic-workspace/config.toml", ".agentic-workspace/OWNERSHIP.toml"}:
        return "workspace_policy_surface"
    return None


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


def _ownership_boundary_review(
    *,
    module_roots: list[dict[str, Any]],
    managed_surfaces: list[dict[str, Any]],
    fences: list[dict[str, Any]],
    authority_surfaces: list[dict[str, Any]],
) -> dict[str, Any]:
    def _surface_entry(
        *, surface: str, owner: str, ownership: str, summary: str | None = None, source: str | None = None
    ) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "surface": surface,
            "owner": owner,
            "ownership": ownership,
        }
        if summary:
            entry["summary"] = summary
        if source:
            entry["source"] = source
        return entry

    package_owned = {
        "module_roots": [
            _surface_entry(
                surface=str(entry.get("path", "")),
                owner=str(entry.get("module", "")),
                ownership=str(entry.get("ownership", "")),
                summary=str(entry.get("uninstall_policy", "")) or None,
                source="module_root",
            )
            for entry in module_roots
        ],
        "managed_surfaces": [
            _surface_entry(
                surface=str(entry.get("path", "")),
                owner=str(entry.get("module", "")),
                ownership=str(entry.get("ownership", "")),
                summary=str(entry.get("kind", "")) or None,
                source="managed_surface",
            )
            for entry in managed_surfaces
        ],
    }
    shared_package_state = {
        "managed_surfaces": [
            _surface_entry(
                surface=str(entry.get("path", "")),
                owner=str(entry.get("module", "")),
                ownership=str(entry.get("ownership", "")),
                summary=str(entry.get("kind", "")) or None,
                source="managed_surface",
            )
            for entry in managed_surfaces
            if str(entry.get("ownership", "")) in {"workspace_shared", "module_managed"}
        ],
        "authority_surfaces": [
            _surface_entry(
                surface=str(entry.get("surface", "")),
                owner=str(entry.get("owner", "")),
                ownership=str(entry.get("ownership", "")),
                summary=str(entry.get("concern", "")) or None,
                source="authority_surface",
            )
            for entry in authority_surfaces
            if str(entry.get("ownership", "")) in {"workspace_shared", "module_managed"}
        ],
    }
    repo_specific_package_state = {
        "managed_surfaces": [
            _surface_entry(
                surface=str(entry.get("path", "")),
                owner=str(entry.get("module", "")),
                ownership=str(entry.get("ownership", "")),
                summary=str(entry.get("kind", "")) or None,
                source="managed_surface",
            )
            for entry in managed_surfaces
            if str(entry.get("ownership", "")) == "repo_specific_package_owned"
        ],
        "authority_surfaces": [
            _surface_entry(
                surface=str(entry.get("surface", "")),
                owner=str(entry.get("owner", "")),
                ownership=str(entry.get("ownership", "")),
                summary=str(entry.get("concern", "")) or None,
                source="authority_surface",
            )
            for entry in authority_surfaces
            if str(entry.get("ownership", "")) == "repo_specific_package_owned"
        ],
    }
    repo_owned = {
        "authority_surfaces": [
            _surface_entry(
                surface=str(entry.get("surface", "")),
                owner=str(entry.get("owner", "")),
                ownership=str(entry.get("ownership", "")),
                summary=str(entry.get("concern", "")) or None,
                source="authority_surface",
            )
            for entry in authority_surfaces
            if str(entry.get("ownership", "")) == "repo_owned"
        ],
    }
    middle_ground = {
        "managed_fences": [
            _surface_entry(
                surface=f"{str(entry.get('file', '')).strip()}#agentic-workspace:workflow",
                owner=str(entry.get("module", "")),
                ownership=str(entry.get("ownership", "")),
                summary=str(entry.get("name", "")) or None,
                source="managed_fence",
            )
            for entry in fences
        ],
    }
    smallest_explicit_repo_hook = middle_ground["managed_fences"][0] if middle_ground["managed_fences"] else None
    return {
        "package_owned": package_owned,
        "shared_package_state": shared_package_state,
        "repo_specific_package_state": repo_specific_package_state,
        "repo_owned": repo_owned,
        "middle_ground": middle_ground,
        "smallest_explicit_repo_hook": smallest_explicit_repo_hook,
    }


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
        answer["authority_marker"] = _authority_marker_for_path(repo_path)
        answer["boundary_warning"] = _boundary_warning_for_path(repo_path)
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
    print("Boundary review:")
    for entry in payload["boundary_review"]["repo_owned"]["authority_surfaces"]:
        print(f"- repo-owned: {entry['surface']} ({entry['owner']}, {entry['ownership']})")
    for entry in payload["boundary_review"]["package_owned"]["module_roots"]:
        print(f"- package-owned: {entry['surface']} ({entry['owner']}, {entry['ownership']})")
    for entry in payload["boundary_review"]["package_owned"]["managed_surfaces"]:
        print(f"- package-owned: {entry['surface']} ({entry['owner']}, {entry['ownership']})")
    for entry in payload["boundary_review"]["middle_ground"]["managed_fences"]:
        print(f"- middle-ground: {entry['surface']} ({entry['owner']}, {entry['ownership']})")
    hook = payload["boundary_review"]["smallest_explicit_repo_hook"]
    if hook is not None:
        print(f"Smallest explicit repo hook: {hook['surface']} ({hook['owner']}, {hook['ownership']})")
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
        payload = config_lib.load_toml_payload(path=ledger_path, surface_name=ledger_path.as_posix())
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
        "boundary_review": _ownership_boundary_review(
            module_roots=module_roots,
            managed_surfaces=managed_surfaces,
            fences=fences,
            authority_surfaces=authority_surfaces,
        ),
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


def _delegation_target_closeout_gate(
    *,
    profile: DelegationTargetProfile,
    advisory: dict[str, Any],
    outcome_evidence: dict[str, Any],
) -> dict[str, Any]:
    lower_trust_reasons: list[str] = []
    if str(advisory.get("review_burden", "")).strip() == "high":
        lower_trust_reasons.append("target advisory review burden is high")
    if profile.strength == "weak":
        lower_trust_reasons.append("target strength is weak")
    if isinstance(outcome_evidence.get("average_signal"), (int, float)) and float(outcome_evidence["average_signal"]) < 0:
        lower_trust_reasons.append("delegation outcome evidence trends negative")
    confidence = outcome_evidence.get("confidence")
    if isinstance(confidence, dict) and str(confidence.get("action", "")).strip() == "lower":
        lower_trust_reasons.append("delegation outcome evidence suggests lowering confidence")

    trust = "lower-trust" if lower_trust_reasons else "normal"
    if trust == "lower-trust":
        recommended_next_action = (
            "Treat delegated closeout as lower-trust: require human review and explicit execution residue before archive-and-close."
        )
    else:
        recommended_next_action = "No extra closeout gate beyond normal bounded review is required."
    return {
        "trust": trust,
        "reasons": lower_trust_reasons,
        "required_when_lower_trust": [
            "human review before closeout",
            "explicit execution residue proving bounded scope and validations",
        ],
        "recommended_next_action": recommended_next_action,
    }


def _delegated_run_guardrail_payload(
    *,
    defaults: dict[str, Any],
    profile_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    lower_trust_profiles = [
        profile.get("name", "")
        for profile in profile_payloads
        if isinstance(profile, dict)
        and isinstance(profile.get("closeout_gate"), dict)
        and profile["closeout_gate"].get("trust") == "lower-trust"
    ]
    guardrail_defaults = defaults.get("delegated_run_guardrail", {})
    return {
        "status": "present",
        "rule": guardrail_defaults.get("rule", ""),
        "required_preflight_checks": list(guardrail_defaults.get("required_preflight_checks", [])),
        "closeout_gate": {
            **dict(guardrail_defaults.get("closeout_gate", {})),
            "lower_trust_profiles": sorted([name for name in lower_trust_profiles if name]),
        },
    }


def _strength_rank(strength: str) -> int:
    return {
        "weak": 1,
        "medium": 2,
        "strong": 3,
    }[strength]


def _location_match_score(*, preferred_location: str, target_location: str) -> int:
    if preferred_location == target_location:
        return 2
    if preferred_location == "either" or target_location == "either":
        return 1
    return -2


def _capability_resolution_for_profile(
    *,
    profile: DelegationTargetProfile,
    capability_posture: dict[str, Any],
) -> dict[str, Any]:
    recommended_strength = str(capability_posture.get("recommended strength", "")).strip()
    execution_class = str(capability_posture.get("execution class", "")).strip()
    preferred_location = str(capability_posture.get("preferred location", "")).strip() or "either"
    delegation_friendly = str(capability_posture.get("delegation friendly", "")).strip()
    strong_external_reasoning = str(capability_posture.get("strong external reasoning", "")).strip()

    score = 0
    reasons: list[str] = []

    if recommended_strength:
        profile_rank = _strength_rank(profile.strength)
        required_rank = _strength_rank(recommended_strength)
        if profile_rank < required_rank:
            score -= 3
            reasons.append("target strength is below the recommended strength")
        elif profile.strength == recommended_strength:
            score += 3
            reasons.append("target strength matches the recommended strength")
        else:
            score += 1
            reasons.append("target strength exceeds the recommended strength")

    location_score = _location_match_score(preferred_location=preferred_location, target_location=profile.location)
    score += location_score
    if location_score > 1:
        reasons.append("target location matches the preferred location")
    elif location_score > 0:
        reasons.append("target location remains acceptable because one side is location-agnostic")
    else:
        reasons.append("target location conflicts with the preferred location")

    if execution_class:
        if execution_class in profile.capability_classes:
            score += 2
            reasons.append("target advertises support for the required capability class")
        elif profile.capability_classes:
            score -= 1
            reasons.append("target does not advertise the required capability class")

    if delegation_friendly == "yes":
        if "internal" in profile.execution_methods or "cli" in profile.execution_methods or "api" in profile.execution_methods:
            score += 1
            reasons.append("target exposes an execution method that keeps delegation viable")

    if strong_external_reasoning == "preferred":
        if profile.location == "external":
            score += 2
            reasons.append("target satisfies the strong-external preference directly")
        elif profile.location == "either":
            score += 1
            reasons.append("target can satisfy the strong-external preference through a location-agnostic profile")
        else:
            score -= 2
            reasons.append("target stays local despite a strong-external preference")
    elif strong_external_reasoning == "avoid" and profile.location == "external":
        score -= 1
        reasons.append("target is external even though strong external reasoning is not preferred")

    if score >= 5:
        status = "recommended"
    elif score >= 2:
        status = "acceptable"
    else:
        status = "poor-fit"
    return {
        "status": status,
        "score": score,
        "reasons": reasons,
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
    path, payload, records = config_lib.load_delegation_outcomes(target_root=target_root)
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
    config_lib.write_delegation_outcomes(path=path, payload=updated_payload)
    return {
        "kind": DELEGATION_OUTCOMES_KIND,
        "path": WORKSPACE_DELEGATION_OUTCOMES_PATH.as_posix(),
        "recorded": updated_payload["records"][-1],
        "record_count": len(updated_payload["records"]),
        "rule": "local-only delegation outcome evidence; advisory input for tuning only",
    }


_RUNTIME_RESOLUTION_CATEGORIES = (
    "stay-local",
    "stronger-reasoning",
    "external-delegation",
    "manual-handoff",
)

_RUNTIME_RESOLUTION_GUIDANCE: dict[str, str] = {
    "stay-local": ("Proceed with the current executor. Keep scope bounded and defer judgment-heavy questions to a stronger path."),
    "stronger-reasoning": ("Escalate the current question or bounded task to the stronger in-session planner before proceeding."),
    "external-delegation": ("Delegate the bounded task to an external target using the configured CLI or API execution method."),
    "manual-handoff": (
        "Pause and hand the bounded question to a strong general-purpose reasoning model. "
        "Use the strong_handoff_packet template to structure the escalation compactly."
    ),
}


def _runtime_resolution_payload(
    *,
    config: WorkspaceConfig,
    capability_posture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compact runtime-resolution answer combining work semantics and local execution posture."""
    local_override = config.local_override
    posture = capability_posture or {}

    execution_class = str(posture.get("execution class", "")).strip()
    recommended_strength = str(posture.get("recommended strength", "")).strip()
    preferred_location = str(posture.get("preferred location", "")).strip() or "either"
    delegation_friendly = str(posture.get("delegation friendly", "")).strip()
    strong_external = str(posture.get("strong external reasoning", "")).strip()

    reasons: list[str] = []
    alternatives: list[str] = []

    profile_recommendations: list[dict[str, Any]] = []
    for profile in local_override.delegation_targets:
        rec = _capability_resolution_for_profile(
            profile=profile,
            capability_posture=posture,
        )
        profile_recommendations.append(
            {
                "name": profile.name,
                "strength": profile.strength,
                "location": profile.location,
                "execution_methods": list(profile.execution_methods),
                "recommendation": rec["status"],
                "score": rec["score"],
                "reasons": rec["reasons"],
            }
        )

    has_strong_planner = bool(local_override.strong_planner_available)
    has_cheap_executor = bool(local_override.cheap_bounded_executor_available)

    recommended_external_profiles = [
        p
        for p in profile_recommendations
        if p["recommendation"] in ("recommended", "acceptable")
        and p["location"] == "external"
        and any(m in p["execution_methods"] for m in ("cli", "api"))
    ]
    recommended_local_profiles = [
        p for p in profile_recommendations if p["recommendation"] in ("recommended", "acceptable") and p["location"] in ("local", "either")
    ]

    recommendation: str
    confidence: str

    if strong_external == "preferred":
        if recommended_external_profiles:
            recommendation = "external-delegation"
            confidence = "high"
            reasons.append("capability posture prefers strong external reasoning and external delegation targets are available")
        elif has_strong_planner:
            recommendation = "stronger-reasoning"
            confidence = "medium"
            reasons.append("capability posture prefers strong external reasoning; in-session stronger planner is the fallback")
            alternatives.append("external-delegation when external targets are configured")
        else:
            recommendation = "manual-handoff"
            confidence = "high"
            reasons.append("capability posture prefers strong external reasoning but no automated external path is available")
            alternatives.append("external-delegation when external targets are configured")

    elif execution_class in ("boundary-shaping", "reasoning-heavy") or recommended_strength == "strong":
        if has_strong_planner:
            recommendation = "stronger-reasoning"
            confidence = "high"
            if execution_class:
                reasons.append(f"execution class '{execution_class}' requires stronger reasoning")
            if recommended_strength == "strong":
                reasons.append("capability posture recommends strong execution strength")
            reasons.append("stronger planner is available in this session")
        elif recommended_external_profiles:
            recommendation = "external-delegation"
            confidence = "medium"
            reasons.append("stronger reasoning needed but no in-session strong planner; external delegation is available")
            alternatives.append("stronger-reasoning when a strong in-session planner is available")
        else:
            recommendation = "manual-handoff"
            confidence = "medium"
            reasons.append("stronger reasoning needed but no automated path is available")
            alternatives.append("stronger-reasoning when a strong in-session planner is available")
            alternatives.append("external-delegation when external targets are configured")

    elif execution_class == "mixed":
        if recommended_local_profiles:
            recommendation = "stay-local"
            confidence = "medium"
            reasons.append("execution class is 'mixed'; local profiles are acceptable")
            if has_strong_planner:
                alternatives.append("stronger-reasoning for the reasoning-heavy portions")
        elif has_strong_planner:
            recommendation = "stronger-reasoning"
            confidence = "low"
            reasons.append("execution class is 'mixed' with no suitable local profile; escalating to stronger reasoning")
        else:
            recommendation = "stay-local"
            confidence = "low"
            reasons.append("execution class is 'mixed'; no clear escalation path is available")

    elif execution_class == "mechanical-follow-through" or recommended_strength in ("weak", "medium"):
        recommendation = "stay-local"
        confidence = "high" if execution_class == "mechanical-follow-through" else "medium"
        if execution_class == "mechanical-follow-through":
            reasons.append("execution class 'mechanical-follow-through' is well-suited for local bounded execution")
        if recommended_strength in ("weak", "medium"):
            reasons.append(f"capability posture recommends '{recommended_strength}' execution strength")

    elif not posture:
        if has_cheap_executor:
            recommendation = "stay-local"
            confidence = "medium"
            reasons.append("cheap bounded executor is available; defaulting to stay-local without explicit capability posture")
            if has_strong_planner:
                alternatives.append("stronger-reasoning when the work requires higher judgment")
        elif has_strong_planner:
            recommendation = "stronger-reasoning"
            confidence = "low"
            reasons.append("no capability posture provided; strong planner available as fallback")
            alternatives.append("stay-local when the work is clearly bounded")
        else:
            recommendation = "stay-local"
            confidence = "low"
            reasons.append("no capability posture and no special local config; defaulting to stay-local")

    else:
        recommendation = "stay-local"
        confidence = "low"
        reasons.append("capability posture signals do not map to a clear escalation path; defaulting to stay-local")
        if has_strong_planner:
            alternatives.append("stronger-reasoning if the work turns out to be judgment-heavy")

    _ = preferred_location  # consumed indirectly via _capability_resolution_for_profile
    _ = delegation_friendly  # advisory only; scoring is in _capability_resolution_for_profile

    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "reasons": reasons,
        "alternatives": alternatives,
        "profile_recommendations": profile_recommendations,
        "guidance": _RUNTIME_RESOLUTION_GUIDANCE[recommendation],
        "posture_source": "provided" if posture else "none",
        "resolution_categories": list(_RUNTIME_RESOLUTION_CATEGORIES),
    }


def _strong_handoff_packet_template() -> dict[str, Any]:
    """Template for a compact bounded escalation packet for strong general-purpose reasoning."""
    return {
        "rule": (
            "Use the strong_handoff_packet template when manual-handoff is the runtime recommendation "
            "or when a bounded high-judgment question should be escalated to a strong general-purpose reasoning model. "
            "Keep the packet compact: one question, bounded constraints, no full context dump."
        ),
        "required_fields": [
            "context: one-paragraph summary of the current work and its bounded scope",
            "question: the specific high-judgment question the strong model should answer",
            "constraints: the hard constraints the answer must satisfy",
            "expected_output: what a useful answer looks like (format and scope)",
            "return_to: what the current executor should do with the answer once received",
        ],
        "optional_fields": [
            "background: additional context that would materially help the strong model but is not strictly required",
            "avoid: specific patterns or approaches the answer must not use",
        ],
        "size_guidance": "Target under 500 tokens for the full packet. Escalate one question at a time.",
        "after_receiving_answer": [
            "Apply the answer to the current bounded task.",
            "Do not reopen the full execplan or lane scope based on the answer alone.",
            "Record the answer as a checked-in decision residue if it changes durable state.",
        ],
        "when_to_use": [
            "runtime_resolution recommendation is 'manual-handoff'",
            "a boundary decision requires judgment beyond the current executor's reliable range",
            "an architectural or domain question would benefit from a strong external perspective",
            "review uncertainty is high enough that stronger reasoning would change the closeout decision",
        ],
    }


def _mixed_agent_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    defaults = _defaults_payload()["mixed_agent"]
    local_override = config.local_override
    outcome_records: tuple[DelegationOutcomeRecord, ...] = ()
    outcome_status = "unavailable"
    if config.target_root is not None:
        _, _, outcome_records = config_lib.load_delegation_outcomes(target_root=config.target_root)
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
    profile_payloads: list[dict[str, Any]] = []
    for profile in local_override.delegation_targets:
        advisory = _delegation_target_advisory(profile)
        outcome_evidence = _delegation_outcome_advisory(
            profile=profile,
            records=records_by_target.get(profile.name, ()),
        )
        profile_payloads.append(
            {
                "name": profile.name,
                "strength": profile.strength,
                "location": profile.location,
                "confidence": profile.confidence,
                "task_fit": list(profile.task_fit),
                "capability_classes": list(profile.capability_classes),
                "execution_methods": list(profile.execution_methods),
                "advisory": advisory,
                "outcome_evidence": outcome_evidence,
                "closeout_gate": _delegation_target_closeout_gate(
                    profile=profile,
                    advisory=advisory,
                    outcome_evidence=outcome_evidence,
                ),
            }
        )
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
                "delegation_targets.<target>.location",
                "delegation_targets.<target>.confidence",
                "delegation_targets.<target>.task_fit",
                "delegation_targets.<target>.capability_classes",
                "delegation_targets.<target>.execution_methods",
            ],
            "supported_strengths": list(SUPPORTED_DELEGATION_TARGET_STRENGTHS),
            "supported_locations": list(SUPPORTED_CAPABILITY_LOCATIONS),
            "supported_capability_classes": list(SUPPORTED_CAPABILITY_EXECUTION_CLASSES),
            "supported_execution_methods": list(SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS),
            "profiles": profile_payloads,
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
        "local_integration_area": {
            **_local_integration_area_payload(target_root=config.target_root),
            "rule": ("local-only vendor/runtime aids; may reduce local operating cost, but must not become shared workflow authority"),
        },
        "local_memory": _local_memory_payload(config=config),
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
        "delegated_run_guardrail": _delegated_run_guardrail_payload(
            defaults=defaults,
            profile_payloads=profile_payloads,
        ),
        "runtime_resolution": _runtime_resolution_payload(config=config),
        "strong_handoff_packet": _strong_handoff_packet_template(),
        "success_measures": defaults["success_measures"],
    }


def _config_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    return {
        "target": config.target_root.as_posix() if config.target_root is not None else None,
        "config_path": config.path.as_posix() if config.path is not None else WORKSPACE_CONFIG_PATH.as_posix(),
        "exists": config.exists,
        "schema_version": config.schema_version,
        "warnings": list(config.warnings),
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
            "cli_invoke": config.cli_invoke,
            "cli_invoke_source": config.cli_invoke_source,
            "workflow_artifact_adapter": _workflow_artifact_profile_payload(config.workflow_artifact_profile),
            "agent_configuration_substrate": {
                "canonical_doc": _agent_configuration_system_payload()["canonical_doc"],
                "command": _agent_configuration_system_payload()["command"],
                "owner_surface": _agent_configuration_system_payload()["owner_surface"],
                "rule": _agent_configuration_system_payload()["rule"],
            },
            "system_intent": {
                **_system_intent_source_payload(config),
                "mirror_path": WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix(),
                "workflow_path": WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH.as_posix(),
            },
            "workflow_obligations": _workflow_obligation_payloads(config),
            "local_memory": _local_memory_payload(config=config),
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
    if payload["warnings"]:
        print("Warnings:")
        for warning in payload["warnings"]:
            print(f"- {warning}")
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
    print(
        "Agent configuration substrate: "
        f"{payload['workspace']['agent_configuration_substrate']['canonical_doc']} "
        f"({payload['workspace']['agent_configuration_substrate']['owner_surface']})"
    )
    print(
        "System-intent sources: "
        f"{', '.join(payload['workspace']['system_intent']['sources']) or 'none'} "
        f"({payload['workspace']['system_intent']['sources_source']})"
    )
    print(f"Workflow obligations: {len(payload['workspace']['workflow_obligations'])} configured")
    print(f"Improvement latitude: {payload['workspace']['improvement_latitude']} ({payload['workspace']['improvement_latitude_source']})")
    print(f"Optimization bias: {payload['workspace']['optimization_bias']} ({payload['workspace']['optimization_bias_source']})")
    print(f"CLI invoke: {payload['workspace']['cli_invoke']} ({payload['workspace']['cli_invoke_source']})")
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
        "- local integration area: "
        f"{payload['mixed_agent']['local_integration_area']['root']} "
        f"({payload['mixed_agent']['local_integration_area']['status']})"
    )
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


def _system_intent_command_payload(*, target_root: Path, config: WorkspaceConfig, sync: bool, dry_run: bool = False) -> dict[str, Any]:
    actions: list[dict[str, str]] = []
    if sync:
        actions, mirror = _sync_system_intent_mirror(target_root=target_root, config=config, dry_run=dry_run)
    else:
        mirror = _load_system_intent_mirror(target_root=target_root, config=config)
    return {
        "kind": "workspace-system-intent/v1",
        "command": "system-intent",
        "target": target_root.as_posix(),
        "sync_requested": sync,
        "source_declaration_surface": ".agentic-workspace/config.toml [system_intent]",
        "mirror_surface": WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix(),
        "workflow_surface": WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH.as_posix(),
        "source_declaration": _system_intent_source_payload(config),
        "mirror": mirror,
        "actions": actions,
        "next_action": (
            {
                "summary": "Refresh source discovery metadata or refine the compiled system-intent declaration",
                "commands": [
                    "agentic-workspace system-intent --target ./repo --sync --format json",
                    f"open {WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH.as_posix()} and {WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix()}",
                ],
            }
            if mirror.get("status") != "present" or mirror.get("needs_review", True)
            else {
                "summary": "Compiled system intent is present; refresh metadata on source changes and refine interpretation only when repo direction changed materially",
                "commands": [
                    "agentic-workspace system-intent --target ./repo --sync --format json",
                ],
            }
        ),
    }


def _emit_system_intent(*, format_name: str, target_root: Path, config: WorkspaceConfig, sync: bool) -> None:
    payload = _system_intent_command_payload(target_root=target_root, config=config, sync=sync)
    if format_name == "json":
        print(json.dumps(serialise_value(payload), indent=2))
        return
    print(f"Target: {payload['target']}")
    print(f"Command: {payload['command']}")
    print(f"Sync requested: {payload['sync_requested']}")
    print(f"Source declaration surface: {payload['source_declaration_surface']}")
    print(f"Compiled declaration surface: {payload['mirror_surface']}")
    print(f"Workflow surface: {payload['workflow_surface']}")
    declaration = payload["source_declaration"]
    print(f"Sources: {', '.join(declaration['sources']) or 'none'} ({declaration['sources_source']})")
    print(f"Preferred source: {declaration['preferred_source'] or 'none'} ({declaration['preferred_source_source']})")
    mirror = payload["mirror"]
    print(f"Compiled declaration status: {mirror.get('status', 'unknown')}")
    if mirror.get("summary"):
        print(f"Compiled declaration summary: {mirror['summary']}")
    if payload["actions"]:
        print("Actions:")
        for action in payload["actions"]:
            print(f"- {action['kind']}: {action['path']} ({action['detail']})")
    print(f"Next action: {payload['next_action']['summary']}")
    for command in payload["next_action"]["commands"]:
        print(f"- {command}")


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
        }
        current_path = current.get("path")
        if isinstance(current_path, Path):
            current_payload["path"] = current_path.as_posix()
        else:
            current_payload["path"] = None
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
                    "detail": "module upgrade source metadata differs from .agentic-workspace/config.toml or the product default policy",
                }
            )
            warnings.append(
                {
                    "path": relative.as_posix(),
                    "message": "module upgrade source metadata differs from .agentic-workspace/config.toml or the product default policy",
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
            registry_path=Path(".agentic-workspace/memory/repo/skills/REGISTRY.json"),
            skills_root=Path(".agentic-workspace/memory/repo/skills"),
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
