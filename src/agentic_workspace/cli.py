from __future__ import annotations

import argparse
import copy
import difflib
import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
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
    DEFAULT_ASSURANCE_LEVEL,
    DEFAULT_CLI_INVOKE,
    DEFAULT_IMPROVEMENT_LATITUDE,
    DEFAULT_OPTIMIZATION_BIAS,
    DEFAULT_WORKFLOW_ARTIFACT_PROFILE,
    DELEGATION_OUTCOMES_KIND,
    MEMORY_POINTER_BLOCK,
    MEMORY_WORKFLOW_MARKER_END,
    MEMORY_WORKFLOW_MARKER_START,
    SUPPORTED_ADVANCED_FEATURES,
    SUPPORTED_AGENT_INSTRUCTIONS_FILES,
    SUPPORTED_ASSURANCE_LEVELS,
    SUPPORTED_CAPABILITY_EXECUTION_CLASSES,
    SUPPORTED_CAPABILITY_LOCATIONS,
    SUPPORTED_CLARIFICATION_CONTROL_MODES,
    SUPPORTED_DELEGATION_CONTROL_MODES,
    SUPPORTED_DELEGATION_OUTCOMES,
    SUPPORTED_DELEGATION_TARGET_CONTEXT_CAPACITIES,
    SUPPORTED_DELEGATION_TARGET_COST_CLASSES,
    SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS,
    SUPPORTED_DELEGATION_TARGET_LATENCY_CLASSES,
    SUPPORTED_DELEGATION_TARGET_REASONING_PROFILES,
    SUPPORTED_DELEGATION_TARGET_STRENGTHS,
    SUPPORTED_HANDOFF_SUFFICIENCY,
    SUPPORTED_IMPROVEMENT_LATITUDES,
    SUPPORTED_OPTIMIZATION_BIASES,
    SUPPORTED_REVIEW_BURDENS,
    SUPPORTED_WORKFLOW_ARTIFACT_PROFILES,
    SUPPORTED_WORKFLOW_OBLIGATION_FORCES,
    SUPPORTED_WORKFLOW_OBLIGATION_STAGES,
    WORKSPACE_AGENT_AID_ROOT_PATH,
    WORKSPACE_AGENT_AID_SUBDIRS,
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
    WORKSPACE_LOCAL_SCRATCH_ROOT_PATH,
    WORKSPACE_POINTER_BLOCK,
    WORKSPACE_SUBSYSTEM_INTENT_PATH,
    WORKSPACE_SYSTEM_INTENT_MIRROR_PATH,
    WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH,
    WORKSPACE_WORKFLOW_MARKER_END,
    WORKSPACE_WORKFLOW_MARKER_START,
    AssuranceConfig,
    DelegationOutcomeRecord,
    DelegationTargetProfile,
    MixedAgentLocalOverride,
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
    improvement_signal_contract_manifest,
    module_registry_manifest,
    optimization_bias_policy_manifest,
    preflight_policy_manifest,
    proof_routes_manifest,
    proof_selection_rules_manifest,
    python_runtime_boundary_manifest,
    repo_friction_policy_manifest,
    report_contract_manifest,
    setup_findings_policy_manifest,
    workflow_artifact_profiles_manifest,
    workflow_definition_format_manifest,
    workspace_surfaces_manifest,
)
from agentic_workspace.generated_cli_package import (
    build_generated_parser as build_generated_cli_package_parser,
)
from agentic_workspace.generated_cli_package import (
    run_generated_command as run_generated_cli_package_command,
)
from agentic_workspace.generated_cli_package import (
    supports_generated_command as supports_generated_cli_package_command,
)
from agentic_workspace.generated_command_adapters import GENERATED_COMMAND_ADAPTERS_BY_COMMAND
from agentic_workspace.reporting_support import (
    output_contract_payload,
    repo_friction_payload,
    report_profile_payload,
    report_router_payload,
    report_section_hints,
    select_report_payload,
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
_IMPROVEMENT_SIGNAL_CONTRACT = improvement_signal_contract_manifest()
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
WORKSPACE_CONFIG_CONTRACT_DOC = ".agentic-workspace/docs/workspace-config-contract.md"
WORKSPACE_CONFIG_SOURCE_SCHEMA = "src/agentic_workspace/contracts/schemas/workspace_config.schema.json"
WORKSPACE_CONFIG_REFERENCE_DOC = "docs/reference/workspace-config.md"
SYSTEM_INTENT_MIRROR_KIND = str(_WORKSPACE_SURFACES_MANIFEST["system_intent_mirror_kind"])
SUBSYSTEM_INTENT_KIND = str(_WORKSPACE_SURFACES_MANIFEST["subsystem_intent_kind"])
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


def _path_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _is_agentic_workspace_source_checkout(target_root: Path | None) -> bool:
    if target_root is None:
        return False
    pyproject_path = target_root / "pyproject.toml"
    if not pyproject_path.exists() or not (target_root / "src" / "agentic_workspace").is_dir():
        return False
    try:
        pyproject_text = pyproject_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return 'name = "agentic-workspace"' in pyproject_text or "name = 'agentic-workspace'" in pyproject_text


def _agentic_workspace_package_root() -> Path | None:
    module_path = Path(__file__).resolve()
    for candidate in module_path.parents:
        pyproject_path = candidate / "pyproject.toml"
        if not pyproject_path.exists():
            continue
        try:
            pyproject_text = pyproject_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if 'name = "agentic-workspace"' in pyproject_text or "name = 'agentic-workspace'" in pyproject_text:
            return candidate
    return None


def _invoked_cli_identity_payload(*, target_root: Path | None = None, compact: bool = False) -> dict[str, Any]:
    module_path = Path(__file__).resolve()
    package_root = _agentic_workspace_package_root()
    argv0 = sys.argv[0] if sys.argv else ""
    argv0_path = Path(argv0).resolve() if argv0 else None
    path_entry = shutil.which("agentic-workspace")
    path_entry_path = Path(path_entry).resolve() if path_entry else None
    target_relation = "no-target"
    if target_root is not None:
        target_relation = "inside-target" if _path_within(module_path, target_root) else "outside-target"

    if package_root is not None:
        source_class = "source-checkout"
        confidence = "high"
    elif module_path.exists():
        source_class = "installed-package"
        confidence = "medium"
    else:
        source_class = "unknown"
        confidence = "low"

    payload = {
        "kind": "agentic-workspace/invoked-cli-identity/v1",
        "package": "agentic-workspace",
        "version": __version__,
        "source_class": source_class,
        "confidence": confidence,
        "module_path": module_path.as_posix(),
        "package_root": package_root.as_posix() if package_root is not None else None,
        "python_executable": Path(sys.executable).resolve().as_posix() if sys.executable else "",
        "argv0": argv0,
        "argv0_path": argv0_path.as_posix() if argv0_path is not None else "",
        "path_executable": path_entry_path.as_posix() if path_entry_path is not None else "",
        "target_relation": target_relation,
        "compatibility": "not-evaluated",
        "expectation_source": "repo-owned CLI compatibility contract",
    }
    if compact:
        return {
            key: payload[key]
            for key in (
                "kind",
                "package",
                "version",
                "source_class",
                "module_path",
                "target_relation",
                "compatibility",
            )
        }
    return payload


def _version_key(version: str) -> tuple[int, ...]:
    main = re.split(r"[-+]", version, maxsplit=1)[0]
    return tuple(int(part) for part in main.split(".") if part.isdigit())


def _version_at_least(current: str, minimum: str) -> bool:
    current_parts = _version_key(current)
    minimum_parts = _version_key(minimum)
    width = max(len(current_parts), len(minimum_parts), 1)
    return current_parts + (0,) * (width - len(current_parts)) >= minimum_parts + (0,) * (width - len(minimum_parts))


def _cli_compatibility_payload(*, config: WorkspaceConfig, compact: bool = False) -> dict[str, Any]:
    expectation = config.cli_compatibility
    identity = _invoked_cli_identity_payload(target_root=config.target_root)
    checks: list[dict[str, Any]] = []

    def add_check(name: str, expected: Any, actual: Any, satisfied: bool, *, configured: bool) -> None:
        checks.append(
            {
                "name": name,
                "configured": configured,
                "expected": expected,
                "actual": actual,
                "satisfied": satisfied,
            }
        )

    add_check(
        "exact_version",
        expectation.exact_version,
        identity["version"],
        expectation.exact_version is None or identity["version"] == expectation.exact_version,
        configured=expectation.exact_version is not None,
    )
    add_check(
        "minimum_version",
        expectation.minimum_version,
        identity["version"],
        expectation.minimum_version is None or _version_at_least(str(identity["version"]), expectation.minimum_version),
        configured=expectation.minimum_version is not None,
    )
    add_check(
        "source_class",
        list(expectation.source_classes),
        identity["source_class"],
        not expectation.source_classes or identity["source_class"] in expectation.source_classes,
        configured=bool(expectation.source_classes),
    )
    add_check(
        "target_relation",
        list(expectation.target_relations),
        identity["target_relation"],
        not expectation.target_relations or identity["target_relation"] in expectation.target_relations,
        configured=bool(expectation.target_relations),
    )

    configured_checks = [check for check in checks if check["configured"]]
    failed_checks = [check for check in configured_checks if not check["satisfied"]]
    configured = expectation.enforcement != "off" or bool(configured_checks) or expectation.command is not None
    if not configured:
        status = "no-expectation"
    elif failed_checks and expectation.enforcement == "blocking":
        status = "blocking-drift"
    elif failed_checks:
        status = "advisory-drift"
    else:
        status = "satisfied"

    drift_findings = _cli_compatibility_drift_findings(identity=identity, expectation=expectation, failed_checks=failed_checks)
    remediation = _cli_compatibility_remediation(
        status=status,
        identity=identity,
        expectation=expectation,
        failed_checks=failed_checks,
    )
    payload: dict[str, Any] = {
        "kind": "agentic-workspace/cli-compatibility/v1",
        "status": status,
        "configured": configured,
        "enforcement": expectation.enforcement,
        "enforcement_source": expectation.enforcement_source,
        "expectation_source": expectation.source,
        "expected_command": expectation.command,
        "invocation_confidence": identity["confidence"],
        "drift_findings": drift_findings,
        "remediation": remediation,
        "checks": checks if not compact else configured_checks,
        "failed_checks": [check["name"] for check in failed_checks],
        "rule": (
            "Executable compatibility compares invoked_cli_identity against repo expectations; payload drift remains owned by module lifecycle checks."
        ),
    }
    if compact:
        compact_payload: dict[str, Any] = {
            "kind": payload["kind"],
            "status": payload["status"],
            "configured": payload["configured"],
            "enforcement": payload["enforcement"],
            "failed_checks": payload["failed_checks"],
        }
        if drift_findings:
            compact_payload["drift_findings"] = drift_findings
            compact_payload["remediation"] = remediation
        if identity["confidence"] != "high":
            compact_payload["invocation_confidence"] = identity["confidence"]
        if configured_checks:
            compact_payload["checks"] = payload["checks"]
        return compact_payload
    return payload


def _cli_compatibility_drift_findings(
    *,
    identity: dict[str, Any],
    expectation: Any,
    failed_checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for check in failed_checks:
        name = str(check["name"])
        if name in {"exact_version", "minimum_version"}:
            drift_class = "executable-version-drift"
            summary = "Invoked CLI version does not satisfy the repo-owned compatibility expectation."
        elif name == "source_class":
            drift_class = "executable-source-drift"
            summary = "Invoked CLI source class does not satisfy the repo-owned compatibility expectation."
        elif name == "target_relation":
            drift_class = "executable-location-drift"
            summary = "Invoked CLI location relative to the target does not satisfy the repo-owned compatibility expectation."
        else:
            drift_class = "executable-compatibility-drift"
            summary = "Invoked CLI does not satisfy the repo-owned compatibility expectation."
        findings.append(
            {
                "check": name,
                "class": drift_class,
                "expected": check.get("expected"),
                "actual": check.get("actual"),
                "invocation_confidence": identity.get("confidence", "low"),
                "summary": summary,
            }
        )
    if not failed_checks and identity.get("confidence") == "low":
        findings.append(
            {
                "check": "invocation_confidence",
                "class": "invocation-confidence-unknown",
                "expected": "high or medium",
                "actual": identity.get("confidence", "low"),
                "invocation_confidence": identity.get("confidence", "low"),
                "summary": "Invoked CLI identity could not be classified confidently enough for strong compatibility claims.",
            }
        )
    return findings


def _cli_compatibility_remediation(
    *,
    status: str,
    identity: dict[str, Any],
    expectation: Any,
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    if not failed_checks and identity.get("confidence") != "low":
        return {
            "status": "none",
            "summary": "Invoked CLI satisfies the configured executable compatibility checks.",
            "next_action": None,
        }
    expected_command = expectation.command or DEFAULT_CLI_INVOKE
    failed_names = {str(check["name"]) for check in failed_checks}
    if failed_names & {"source_class", "target_relation"}:
        action = "use-repo-runner"
        summary = "Run the repo-owned or configured CLI invocation so the executable matches the target repo expectation."
        command = expected_command
    elif failed_names & {"exact_version", "minimum_version"}:
        action = "upgrade-or-select-cli"
        summary = "Upgrade or select a CLI version that satisfies the repo-owned compatibility expectation."
        command = expected_command
    else:
        action = "verify-invocation"
        summary = "Verify which CLI executable is being invoked before trusting lifecycle output."
        command = expected_command
    return {
        "status": "required" if status == "blocking-drift" else "recommended",
        "action": action,
        "summary": summary,
        "command": command,
        "payload_drift_separate": True,
        "payload_drift_owner": "module lifecycle status/doctor checks",
    }


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
_PACKAGE_FOOTPRINT = copy.deepcopy(_MODULE_REGISTRY_MANIFEST.get("package_footprint", {}))
_MODULE_COMPONENT_MODEL = copy.deepcopy(_MODULE_REGISTRY_MANIFEST.get("component_model", {}))
_WORKSPACE_COMPONENTS = copy.deepcopy(_MODULE_REGISTRY_MANIFEST.get("workspace_components", {}))
_MODULE_PROFILE_ENTRIES = tuple(copy.deepcopy(item) for item in _MODULE_REGISTRY_MANIFEST.get("module_profiles", []))
_FEATURE_TIER_ENTRIES = tuple(copy.deepcopy(item) for item in _MODULE_REGISTRY_MANIFEST.get("feature_tiers", []))
_ADVANCED_FEATURE_ENTRIES = tuple(copy.deepcopy(item) for item in _MODULE_REGISTRY_MANIFEST.get("advanced_features", []))
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
    scratch_exists = False
    if target_root is not None:
        exists = (target_root / WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH).exists()
        scratch_exists = (target_root / WORKSPACE_LOCAL_SCRATCH_ROOT_PATH).exists()
    return {
        "root": WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH.as_posix(),
        "subfolder_convention": WORKSPACE_LOCAL_INTEGRATION_SUBFOLDER_CONVENTION,
        "example_subfolder": (WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH / "codex").as_posix(),
        "scratch": _local_scratch_payload(exists=scratch_exists),
        "status": "available-local-only",
        "exists": exists,
        "authoritative": False,
        "git_ignored": True,
        "canonical_doc": ".agentic-workspace/docs/local-integration-area.md",
        "runtime_artifact_shim_pattern": _runtime_artifact_shim_pattern_payload(),
        "allowed_aid_kinds": list(WORKSPACE_LOCAL_INTEGRATION_ALLOWED_AID_KINDS),
        "boundary_rules": list(WORKSPACE_LOCAL_INTEGRATION_BOUNDARY_RULES),
    }


def _runtime_artifact_shim_pattern_payload() -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/local-runtime-artifact-shim/v1",
        "root": WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH.as_posix(),
        "status": "local-only-pattern",
        "authoritative": False,
        "git_ignored": True,
        "use_for": [
            "internal agent plans that need compact checked-in planning updates",
            "runtime check bundles that need compact pass/fail plus inspectable logs",
            "handoff or resume state that needs a bounded workspace continuation record",
            "runtime-native planning systems that the agent is already optimized or hardwired to use",
        ],
        "bridge_rule": (
            "Use runtime-native plans as private working memory when they help, but bridge decisions, scope, proof, "
            "and continuation into checked-in Agentic Workspace Planning before implementation handoff or closeout."
        ),
        "preferred_bridge_steps": [
            "capture the runtime-native plan or todo list under the local integration area when it is useful evidence",
            "summarize only durable intent, scope, proof, and next action into checked-in planning state",
            "run agentic-workspace summary --format json after the bridge and resolve warnings before implementation",
        ],
        "artifact_classes": ["internal-plan", "check-bundle", "handoff-state", "runtime-export"],
        "metadata_required": [
            "kind",
            "source_runtime",
            "artifact_class",
            "input_owner",
            "output_target",
            "authority",
            "promotion_target",
            "proof_command",
            "created_at",
        ],
        "compact_output": "short agent-facing status, next action, and proof pointer",
        "full_evidence": "inspectable local artifact, manifest, command log, or exported source file",
        "promotion_boundary": [
            "local shims never become shared authority by existing locally",
            "promote only through checked-in planning, memory, agent-aid, docs, or repo-native review surfaces",
            "record proof before treating shim output as repo-shared state",
            "a runtime-native plan or todo list does not satisfy required Agentic Workspace Planning until bridged",
        ],
        "discovery": [
            "agentic-workspace defaults --section agent_aid_storage --format json",
            "agentic-workspace config --target ./repo --profile tiny --format json",
            "agentic-workspace report --target ./repo --section agent_aids --format json",
        ],
    }


def _assurance_onboarding_payload(*, assurance: AssuranceConfig | None = None) -> dict[str, Any]:
    configured_profiles = list(assurance.proof_profiles) if assurance is not None else []
    host_refs = []
    if assurance is not None:
        host_refs = [ref for ref in [assurance.decision_record_target, assurance.invariant_registry, assurance.risk_registry] if ref]
    has_test_policy = bool(assurance.test_data_policy) if assurance is not None else False
    any_configured = bool(
        configured_profiles
        or host_refs
        or has_test_policy
        or (assurance is not None and assurance.default_level_source != "product-default")
        or (assurance is not None and assurance.strict_closeout)
    )
    usable = bool(configured_profiles and (host_refs or has_test_policy))
    status = "usable" if usable else ("partial" if any_configured else "absent")
    return {
        "status": status,
        "command": "agentic-workspace defaults --section assurance_onboarding --format json",
        "report_command": "agentic-workspace report --target ./repo --section closeout_trust --format json",
        "proof_command": "agentic-workspace proof --target ./repo --profile tiny --changed <paths> --format json",
        "rule": "Host repos own assurance truth; Agentic Workspace only routes levels, gates, refs, proof profiles, and compact evidence state.",
        "configured_profile_count": len(configured_profiles),
        "host_ref_count": len(host_refs),
        "has_test_data_policy": has_test_policy,
        "smallest_useful_config": [
            "[assurance]",
            'default_level = "medium"',
            'decision_record_target = "docs/decisions/"',
            "",
            "[assurance.proof_profiles.example]",
            'required_commands = ["uv run pytest tests -q"]',
            "optional_commands = []",
            "review_aids = []",
        ],
        "states": {
            "absent": "no host assurance profile is configured; low-risk installs stay cheap",
            "partial": "some assurance fields exist, but add at least one proof profile plus a host-owned ref or test-data policy",
            "usable": "at least one proof profile and one host-owned authority or test-data policy are configured",
        },
    }


def _local_scratch_payload(*, exists: bool = False) -> dict[str, Any]:
    return {
        "root": WORKSPACE_LOCAL_SCRATCH_ROOT_PATH.as_posix(),
        "status": "ready-local-only",
        "exists": exists,
        "git_ignored": True,
        "authoritative": False,
        "safe_to_delete": True,
        "sign": "Go ahead and use this for whatever temporary working files you need.",
    }


def _agent_created_aid_affordance_payload() -> dict[str, Any]:
    compact_runner = "uv run python scripts/check/run_compact_command.py"
    return {
        "kind": "agentic-workspace/agent-created-aid-affordance/v1",
        "agent_may_create": True,
        "summary": ("Create a bounded aid when it would reduce repeated work, parsing cost, handoff cost, or error risk."),
        "creation_triggers": [
            "the same command bundle or check sequence is run repeatedly",
            "command output is noisy but the agent only needs pass/fail plus failure tail",
            "handoff or closeout steps are reconstructed from memory across turns",
            "a small template, prompt, runbook, wrapper, or shim would prevent rediscovery",
        ],
        "aid_types": ["script", "runbook", "template", "prompt", "check", "compact-command-runner", "shim"],
        "storage_decision": {
            "local_only": WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH.as_posix(),
            "checked_in_candidate": WORKSPACE_AGENT_AID_ROOT_PATH.as_posix(),
            "promoted_repo_native": "ordinary repo command, check, skill, runbook, prompt, template, or docs surface",
            "rule": (
                "Use local-only for machine/runtime-specific aids; use checked-in candidate storage for repo-shared aids "
                "that are still proving value; promote only after repeated usefulness or clear repo-general value."
            ),
            "prefer_checked_in_when": [
                "the aid benefits any agent working in this repo",
                "the aid is portable enough to review and run across ordinary repo environments",
                "the aid captures repo-specific workflow knowledge that should survive machines and sessions",
            ],
            "prefer_local_only_when": [
                "the aid depends on a specific agent runtime, subscription, account, credential, path, or shell setup",
                "the aid is experimental scratch for one machine",
                "the aid bridges private or machine-local state that must not become shared repo authority",
            ],
            "runtime_artifact_shims": _runtime_artifact_shim_pattern_payload(),
        },
        "authority_boundary": [
            "aids help agents work; they do not silently become required workflow",
            "candidate aids are advisory until promoted through ordinary repo review and proof surfaces",
            "local-only aids are ignored by git, non-authoritative, and safe to delete",
        ],
        "evidence_shape": {
            "compact_output": "short pass/fail/actionable summary for the agent",
            "full_evidence": "inspectable command log, artifact, manifest, or source file",
            "manifest_required_for_checked_in": True,
            "validation": "checked-in executable aids declare validation.commands and pass check_agent_aids",
        },
        "first_pattern": {
            "id": "compact-runner",
            "command": compact_runner,
            "makefile_variable": "COMPACT_RUN",
            "timeout_option": "--timeout-seconds <seconds>",
            "timeout_rule": "Set the runner timeout below the outer tool timeout so compact failure evidence and logs survive.",
            "success_output": "[ok] <label> (<duration>)",
            "failure_output": "failure or timeout header plus tailed command output",
            "full_log_root": "scratch/command-logs",
            "use_for": "wrapping noisy recurring commands without hiding full failure evidence",
        },
        "first_steps": [
            "name the repeated friction and decide local-only vs checked-in candidate",
            "reuse COMPACT_RUN or the same compact-output/full-log pattern for noisy commands",
            "if checked in, add a nearby manifest.json and run python scripts/check/check_agent_aids.py",
            "keep the aid advisory until a promoted repo-native surface owns discovery and proof",
        ],
    }


def _agent_aid_storage_payload(*, target_root: Path | None = None) -> dict[str, Any]:
    exists = False
    if target_root is not None:
        exists = (target_root / WORKSPACE_AGENT_AID_ROOT_PATH).exists()
    creation_affordance = _agent_created_aid_affordance_payload()
    return {
        "status": "available-checked-in-candidate-area",
        "command": "agentic-workspace defaults --section agent_aid_storage --format json",
        "discovery_command": "agentic-workspace report --target ./repo --section agent_aids --format json",
        "task_recommendation_command": 'agentic-workspace skills --target ./repo --task "<task>" --format json',
        "canonical_doc": ".agentic-workspace/docs/agent-aids-storage.md",
        "candidate_root": WORKSPACE_AGENT_AID_ROOT_PATH.as_posix(),
        "candidate_subdirs": list(WORKSPACE_AGENT_AID_SUBDIRS),
        "candidate_root_exists": exists,
        "ordinary_startup": False,
        "manifest_name": "manifest.json",
        "manifest_kind": "agentic-workspace/agent-aid/v1",
        "manifest_schema": "src/agentic_workspace/contracts/schemas/agent_aid_manifest.schema.json",
        "manifest_check": "python scripts/check/check_agent_aids.py",
        "manifest_required": "for checked-in shared aids",
        "creation_affordance": creation_affordance,
        "executable_safety": {
            "rule": "Checked-in executable aids must declare safety, portability, validation, and proof-role metadata.",
            "executable_types": ["script", "check"],
            "non_cross_platform_requires": "portability_justification",
            "platform_specific_checked_in_requires": "checked_in_scope_justification",
            "high_risk_requires_review_when": ["writes_repo", "destructive", "network"],
            "hidden_required_workflow": "forbidden",
            "canonical_proof_role_requires_status": "promoted",
            "candidate_aid_check": "python scripts/check/check_agent_aids.py",
            "candidate_aids_are_not": ["canonical proof routes", "required workflow entrypoints"],
            "canonical_checks_are": "repo-owned checkers and proof routes that validate candidate metadata, not candidate aids themselves",
            "repo_general_preference": "Prefer cross-platform wrappers for repo-shared validation; keep platform-specific helpers local unless justified.",
        },
        "promotion_model": {
            "rule": "Proven aids should move from candidate storage to the strongest repo-native surface and retire or shrink the candidate copy.",
            "target_kinds": [
                "command",
                "check",
                "skill",
                "runbook",
                "prompt",
                "template",
                "module-component",
                "docs-contract",
            ],
            "trigger": "repeated successful use or clear repo-general value",
            "discovery_route_required": True,
            "retirement_required": "candidate manifests declare retention_after_promotion",
            "portable_repo_general_rule": "Repo-shared executable canonical proof aids must be cross-platform.",
            "discovery_after_promotion": {
                "command_or_check": "agentic-workspace proof --changed ... --format json or repo-native check discovery",
                "skill": 'agentic-workspace skills --target ./repo --task "<task>" --format json',
                "runbook_prompt_template_docs": "agentic-workspace report --target ./repo --section agent_aids --format json until promoted surface owns discovery",
                "module_component": "module manifest resources/tools/prompts",
            },
        },
        "storage_classes": [
            {
                "class": "local-only",
                "root": WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH.as_posix(),
                "authority": "none",
                "git_ignored": True,
                "use_for": "runtime-specific or machine-specific helpers that must be safe to delete",
            },
            {
                "class": "checked-in-candidate",
                "root": WORKSPACE_AGENT_AID_ROOT_PATH.as_posix(),
                "authority": "candidate aid metadata plus ordinary repo review",
                "git_ignored": False,
                "use_for": "repo-shared aids that are still proving value before promotion",
            },
            {
                "class": "promoted-repo-native",
                "root": "host repo canonical commands, checks, skills, runbooks, prompts, templates, or docs",
                "authority": "the promoted surface's normal contract, tests, and ownership",
                "git_ignored": False,
                "use_for": "stable aids whose value no longer depends on candidate-aid storage",
            },
            {
                "class": "package-owned",
                "root": "package source or installed payload surfaces",
                "authority": "package contracts and release process",
                "git_ignored": False,
                "use_for": "features shipped by the package, not host-repo local aids",
            },
            {
                "class": "source-checkout-only",
                "root": "maintainer tooling in the package source checkout",
                "authority": "source checkout tests and maintainer workflow",
                "git_ignored": False,
                "use_for": "package-maintainer aids that must not appear as host-repo workflow requirements",
            },
        ],
        "boundary_rules": [
            "local-only helpers remain under the local integration area and must not become shared authority",
            "checked-in candidate aids live under the candidate root until promoted or retired",
            "promoted aids move to the strongest ordinary repo-native surface and should not require candidate storage",
            "package-owned aids are shipped product surfaces, not host-repo custom aids",
            "source-checkout-only maintainer aids must not be required in ordinary host repos",
            "the model is repo-, agent-, tool-, and language-agnostic",
        ],
    }


def _agent_aids_report_payload(*, target_root: Path, cli_invoke: str = DEFAULT_CLI_INVOKE) -> dict[str, Any]:
    checked_in_aids, manifest_warnings = _checked_in_agent_aid_entries(target_root=target_root)
    local_only_entries = _local_only_agent_aid_entries(target_root=target_root)
    visible_checked_in = [entry for entry in checked_in_aids if entry["status"] != "retired"]
    storage = _guidance_with_cli_invoke(value=_agent_aid_storage_payload(target_root=target_root), cli_invoke=cli_invoke)
    creation_affordance = storage.get("creation_affordance", {}) if isinstance(storage, dict) else {}
    aid_discovery_command = _command_with_cli_invoke(
        command='agentic-workspace skills --target ./repo --task "<task>" --format json',
        cli_invoke=cli_invoke,
    )
    recommended_actions = [
        {
            "action": "use-agent-aid",
            "id": entry["id"],
            "summary": "Use this aid only when its manifest matches the current task and its safety summary is acceptable.",
            "type": entry["type"],
            "status": entry["status"],
            "entrypoint": entry["entrypoint"],
            "use_when": entry["use_when"],
            "proof_role": entry["proof_role"],
            "canonical_proof_route": entry["canonical_proof_route"],
            "command": aid_discovery_command,
            "run": aid_discovery_command,
            "risk": "candidate or advisory aid; inspect safety and portability before use",
            "required_inputs": ["current task", "aid safety summary", "proof role"],
            "next_proof": "run the aid's declared validation or route through proof selection before treating it as canonical",
        }
        for entry in visible_checked_in[:3]
    ]
    primary_action = (
        recommended_actions[0]
        if recommended_actions
        else {
            "action": "create-bounded-aid-when-it-reduces-friction",
            "summary": (
                "No checked-in aid is currently recommended; continue through ordinary compact routes, but create a bounded aid "
                "when it would reduce repeated work, parsing cost, handoff cost, or error risk."
            ),
            "command": aid_discovery_command,
            "risk": "read-only discovery unless an aid is later created or promoted",
            "required_inputs": ["current task", "friction evidence", "authority boundary"],
            "next_proof": ("if an aid is checked in, validate its manifest; if local-only, keep it ignored and non-authoritative"),
        }
    )
    if "command" in primary_action:
        primary_action["run"] = primary_action["command"]
    return {
        "kind": "workspace-agent-aids-discovery/v1",
        "status": "available",
        "command": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section agent_aids --format json",
            cli_invoke=cli_invoke,
        ),
        "storage": storage,
        "creation_affordance": creation_affordance,
        "summary": {
            "checked_in_count": len(checked_in_aids),
            "visible_checked_in_count": len(visible_checked_in),
            "retired_count": len(checked_in_aids) - len(visible_checked_in),
            "local_only_container_count": len(local_only_entries),
        },
        "checked_in_aids": checked_in_aids,
        "local_only": {
            "root": WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH.as_posix(),
            "authority": "none",
            "advisory_only": True,
            "entries": local_only_entries,
        },
        "primary_next_action": primary_action,
        "recommended_actions": recommended_actions,
        "recommended_action_omitted_count": max(len(visible_checked_in) - len(recommended_actions), 0),
        "warnings": manifest_warnings,
        "rules": [
            "candidate and advisory aids are discoverable but not canonical proof routes",
            "retired aids remain visible for audit but are not recommended actions",
            "local-only aids are advisory machine-local context and not shared workflow authority",
            "discovery reads only known aid roots and manifest files",
        ],
    }


def _checked_in_agent_aid_entries(*, target_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    root = target_root / WORKSPACE_AGENT_AID_ROOT_PATH
    if not root.exists():
        return [], []
    entries: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    for manifest_path in sorted(root.rglob("manifest.json")):
        relative_manifest = manifest_path.relative_to(target_root).as_posix()
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            warnings.append({"path": relative_manifest, "message": f"manifest cannot be loaded: {exc}"})
            continue
        if not isinstance(payload, dict):
            warnings.append({"path": relative_manifest, "message": "manifest must be a JSON object"})
            continue
        status = str(payload.get("status", "unknown"))
        proof_role = str(payload.get("proof_role", "candidate-aid"))
        safety = payload.get("safety", {})
        safety_summary = {
            "read_only": bool(safety.get("read_only")) if isinstance(safety, dict) else False,
            "writes_repo": bool(safety.get("writes_repo")) if isinstance(safety, dict) else False,
            "destructive": bool(safety.get("destructive")) if isinstance(safety, dict) else False,
            "network": bool(safety.get("network")) if isinstance(safety, dict) else False,
            "requires_review": bool(safety.get("requires_review")) if isinstance(safety, dict) else False,
            "hidden_required_workflow": bool(safety.get("hidden_required_workflow")) if isinstance(safety, dict) else False,
        }
        validation = payload.get("validation", {})
        commands = validation.get("commands") if isinstance(validation, dict) else None
        entries.append(
            {
                "id": str(payload.get("id", manifest_path.parent.name)),
                "manifest": relative_manifest,
                "type": str(payload.get("type", "unknown")),
                "status": status,
                "scope": str(payload.get("scope", "unknown")),
                "portability": str(payload.get("portability", "unknown")),
                "entrypoint": str(payload.get("entrypoint", "")),
                "owner": str(payload.get("owner", "")),
                "use_when": [str(item) for item in payload.get("use_when", []) if isinstance(item, str)],
                "proof_role": proof_role,
                "canonical_proof_route": proof_role == "canonical-proof" and status == "promoted",
                "recommended": status != "retired",
                "safety_summary": safety_summary,
                "validation_summary": {
                    "has_commands": isinstance(commands, list) and bool(commands),
                    "command_count": len(commands) if isinstance(commands, list) else 0,
                    "absent_reason": str(validation.get("absent_reason", "")) if isinstance(validation, dict) else "",
                },
                "promotion_summary": _agent_aid_promotion_summary(payload.get("promotion", {})),
            }
        )
    return entries, warnings


def _agent_aid_promotion_summary(promotion: Any) -> dict[str, Any]:
    if not isinstance(promotion, dict):
        return {
            "target_kind": "",
            "target": "",
            "discovery_route": "",
            "trigger": "",
            "retention_after_promotion": "",
        }
    return {
        "target_kind": str(promotion.get("target_kind", "")),
        "target": str(promotion.get("target", "")),
        "discovery_route": str(promotion.get("discovery_route", "")),
        "trigger": str(promotion.get("trigger", "")),
        "retention_after_promotion": str(promotion.get("retention_after_promotion", "")),
    }


def _local_only_agent_aid_entries(*, target_root: Path) -> list[dict[str, Any]]:
    root = target_root / WORKSPACE_LOCAL_INTEGRATION_ROOT_PATH
    if not root.exists():
        return []
    entries: list[dict[str, Any]] = []
    for path in sorted(root.iterdir()):
        entries.append(
            {
                "id": path.name,
                "path": path.relative_to(target_root).as_posix(),
                "type": "local-only-container",
                "status": "local-only",
                "scope": "machine-local",
                "portability": "runtime-specific",
                "entrypoint": "",
                "authority": "none",
                "advisory_only": True,
                "recommended": False,
            }
        )
    return entries


def _local_memory_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    local_override = config.local_override
    enabled = bool(local_override.local_memory_enabled)
    relative_path = local_override.local_memory_path or WORKSPACE_LOCAL_MEMORY_DEFAULT_PATH
    exists = False
    scratch_exists = False
    if config.target_root is not None:
        exists = (config.target_root / relative_path).exists()
        scratch_exists = (config.target_root / WORKSPACE_LOCAL_SCRATCH_ROOT_PATH).exists()
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
        "scratch": _local_scratch_payload(exists=scratch_exists),
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
            message = (
                f"{message}\nStartup tip: run 'agentic-workspace start --profile tiny --task \"<task>\" --format json' for normal startup "
                "or 'agentic-workspace preflight --format json' to recover a compact takeover context."
            )
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


def _planning_help_payload(*, target: str | None = None) -> dict[str, Any]:
    target_arg = f" --target {target}" if target else " --target ."
    new_plan_command = f"agentic-planning new-plan --id <id> --title <title>{target_arg} --activate --format json"
    prep_only_new_plan_command = f"agentic-planning new-plan --id <id> --title <title>{target_arg} --activate --prep-only --format json"
    promote_command = f"agentic-planning promote-to-plan <item-id>{target_arg} --format json"
    summary_command = f"agentic-workspace summary{target_arg} --profile compact --format json"
    return {
        "kind": "agentic-workspace/planning-help/v1",
        "summary": "Planning files are checked-in execution authority, but their outer structure is package-owned.",
        "orientation": [
            f"agentic-workspace summary{target_arg} --format json",
            f"agentic-workspace preflight{target_arg} --format json",
            f"agentic-workspace proof{target_arg} --changed <paths> --format json",
        ],
        "lifecycle_commands": [
            new_plan_command,
            promote_command,
            f"agentic-planning archive-plan <plan>{target_arg} --format json",
        ],
        "post_new_plan_tightening": {
            "rule": "new-plan creates a schema-valid scaffold, not an implementation-ready contract.",
            "tighten_before_implementation": [
                "goal",
                "non_goals",
                "intent_continuity",
                "execution_bounds",
                "touched_paths",
                "validation_commands",
                "completion_criteria",
                "adaptive_assurance when risk or scope requires it",
            ],
            "after_write": summary_command,
        },
        "sequential_lane_execution": {
            "rule": "For ordered roadmap lanes, promote and complete one lane at a time.",
            "do": [
                "inspect ordered lanes from summary",
                "promote the next lane",
                "create one or more execplans scoped to that lane",
                "implement, prove, close, and archive the lane slice before returning for the next lane",
            ],
            "do_not": "Do not create one combined execplan for unrelated lanes.",
        },
        "durable_state_bridge": {
            "use_when": [
                "the user asks to leave repo-visible state for future agents",
                "the work needs handoff or continuation across sessions",
                "a private runtime plan or todo list contains decisions that must survive the current agent",
                "the task is broad enough that a root PLAN.md would be tempting",
            ],
            "preferred_command": new_plan_command,
            "promote_existing_item_command": promote_command,
            "canonical_surfaces": [
                ".agentic-workspace/planning/state.toml",
                ".agentic-workspace/planning/execplans/<id>.plan.json",
                ".agentic-workspace/planning/decompositions/<id>.decomposition.json for epic shaping",
            ],
            "must_not_create": [
                "PLAN.md",
                "DOC_CLEANUP_PLAN.md",
                "ARCHITECTURE.md or ADR files during planning-only handoff unless explicitly requested",
                "planning/*.json outside .agentic-workspace/planning/decompositions/",
                ".agentic-workspace/WORKFLOW.md task notes",
            ],
            "planning_only_write_scope": [
                ".agentic-workspace/planning/state.toml",
                ".agentic-workspace/planning/execplans/",
                ".agentic-workspace/planning/decompositions/",
            ],
            "planning_only_rule": (
                "When the user asks to prepare, plan, decompose, hand off, or explicitly says not to implement yet, "
                "do not create product source, package, dependency, schema, app scaffold files, or separate architecture docs unless explicitly requested."
            ),
            "reference_validity_rule": (
                "Candidate lane owner_surface values may describe proposed future execplans. Do not report them as existing "
                "next-action files until the files exist and are registered; create/register the execplan or label the reference as proposed/future."
            ),
            "prep_only_route": {
                "use_when": "The user asks to prepare broad work so a later agent can continue, and does not ask to implement.",
                "required_action": "Create or continue canonical checked-in Planning state, verify with summary, then stop; do not stop at a proposal or start implementation.",
                "preferred_command": prep_only_new_plan_command,
                "after_write": summary_command,
                "minimal_success_criteria": [
                    "new-plan --prep-only exits successfully",
                    "agentic-workspace summary reports the active Planning state",
                    "only canonical Planning surfaces changed",
                ],
                "stop_after": "After new-plan --prep-only and summary verification, stop until implementation is explicitly requested.",
                "tightening_policy": (
                    "Prep-only scaffolds are already schema-valid. Do not manually tighten or revalidate generated JSON "
                    "during handoff prep unless summary reports a blocking Planning problem."
                ),
                "allowed_after_new_plan": [
                    "run agentic-workspace summary to verify the Planning state",
                    "only if summary reports a blocking Planning problem, make the smallest schema-preserving Planning edit and rerun summary",
                    "for epic-shaped work, defer schema-backed decomposition enrichment until an implementation or decomposition pass explicitly needs it",
                    "keep the execplan registered in .agentic-workspace/planning/state.toml",
                ],
                "do_not_do": [
                    "do not ask for confirmation instead of leaving durable state when the user already asked you to prepare the repo",
                    "do not create README, PLANNING_STATE, HANDOFF, SLICES, ARCHITECTURE, ADR, package, dependency, source, public, database, schema, or app scaffold files",
                    "do not route durable state to .agentic-workspace/planning/records/",
                    "do not open and manually rework the generated execplan just to improve wording during prep-only handoff",
                    "do not validate generated JSON with ad hoc shell snippets; use summary or package checks",
                ],
            },
            "after_write": summary_command,
        },
        "rules": [
            "Use CLI first for orientation and proof selection.",
            "Use package lifecycle commands for planning mutations when available.",
            "After new-plan, tighten scaffold fields before implementation.",
            "For ordered roadmap lanes, execute one lane at a time; a lane may use multiple execplans, but an execplan should not span unrelated lanes.",
            "Prefer checked-in Agentic Workspace plans as the shared authority for required planning.",
            (
                "If an agent runtime is hardwired to use native plans or todos, treat them as private working memory "
                "and bridge durable decisions into checked-in Planning before implementation, handoff, or closeout; "
                "do not edit .agentic-workspace/WORKFLOW.md as task state."
            ),
            "Do not create root PLAN.md, DOC_CLEANUP_PLAN.md, or similar freehand durable-state files unless repo config explicitly routes there.",
            "For planning-only preparation, keep writes to planning/decomposition surfaces and do not scaffold product files before implementation is requested.",
            "For broad handoff prep, keep architecture assumptions, blockers, and candidate lane notes inside the execplan or decomposition unless the user explicitly asks for separate docs.",
            "For prep-only broad work, use new-plan --prep-only when available; after that, run summary and stop unless summary reports a blocking Planning problem.",
            "Do not claim candidate lane owner_surface paths are valid next-action files until those files actually exist and are registered.",
            "If the user asks to prepare broad work for later continuation, create canonical Planning state, verify it, and stop; a proposal-only answer is not a durable handoff.",
            "Do not invent the outer structure of planning-execplan/v1.",
            "Edit intent, scope, proof, and closeout content inside schema-backed checked-in records.",
            "Copy TEMPLATE.* files to new task-specific filenames; never move, rename, delete, or repurpose templates as live planning records.",
            "After any planning mutation, run agentic-workspace summary --format json or the planning surface checker.",
        ],
        "runtime_native_bridge": {
            "status": "allowed-as-local-aid",
            "local_root": ".agentic-workspace/local/integrations/<vendor-or-runtime>/",
            "rule": (
                "Runtime-native planning can be useful local working memory, but it is not repo-shared execution "
                "authority until summarized into checked-in Agentic Workspace Planning. Use durable_state_bridge "
                "instead of writing a freehand root plan file."
            ),
            "bridge_before": ["implementation for lane/epic work", "handoff", "closeout"],
        },
        "unsafe_state_recovery": {
            "inspect": f"agentic-workspace summary{target_arg} --format json",
            "doctor": f"agentic-workspace doctor{target_arg} --format json",
            "preferred": f"agentic-planning archive-plan <plan>{target_arg} --format json",
            "manual_fallback": (
                "Make the smallest schema-preserving edit to .agentic-workspace/planning/state.toml or the active "
                "plan, then rerun summary; do not invent reset flags."
            ),
        },
        "fallback": (
            "If lifecycle commands are unavailable, copy the package template exactly, edit content inside the schema shape, "
            "register the item in .agentic-workspace/planning/state.toml, then rerun summary."
        ),
    }


def _print_planning_help(payload: dict[str, Any]) -> None:
    print(payload["summary"])
    print("")
    print("Orientation:")
    for command in payload["orientation"]:
        print(f"- {command}")
    print("")
    print("Planning lifecycle:")
    for command in payload["lifecycle_commands"]:
        print(f"- {command}")
    tightening = payload.get("post_new_plan_tightening", {})
    if isinstance(tightening, dict) and tightening:
        print(f"- After new-plan: {tightening.get('rule', '')}")
    sequential_lanes = payload.get("sequential_lane_execution", {})
    if isinstance(sequential_lanes, dict) and sequential_lanes:
        print(f"- Ordered lanes: {sequential_lanes.get('rule', '')}")
    durable_bridge = payload.get("durable_state_bridge", {})
    if isinstance(durable_bridge, dict) and durable_bridge:
        print("")
        print("Durable repo-visible state bridge:")
        print(f"- Preferred: {durable_bridge.get('preferred_command', '')}")
        print(f"- After write: {durable_bridge.get('after_write', '')}")
        if durable_bridge.get("reference_validity_rule"):
            print(f"- Reference validity: {durable_bridge.get('reference_validity_rule', '')}")
        prep_route = durable_bridge.get("prep_only_route", {})
        if isinstance(prep_route, dict) and prep_route:
            print(f"- Prep-only: {prep_route.get('required_action', '')}")
        for blocked in durable_bridge.get("must_not_create", []):
            print(f"- Do not create: {blocked}")
    print("")
    print("Rules:")
    for rule in payload["rules"]:
        print(f"- {rule}")
    bridge = payload.get("runtime_native_bridge", {})
    if isinstance(bridge, dict) and bridge:
        print("")
        print(f"Runtime-native planning bridge: {bridge.get('rule', '')}")
    recovery = payload.get("unsafe_state_recovery", {})
    if isinstance(recovery, dict) and recovery:
        print("")
        print("Unsafe-state recovery:")
        for key in ("inspect", "doctor", "preferred", "manual_fallback"):
            print(f"- {key}: {recovery.get(key, '')}")
    print("")
    print(f"Fallback: {payload['fallback']}")


def _repo_directed_improvement_evidence_threshold_payload() -> dict[str, Any]:
    return copy.deepcopy(_REPO_FRICTION_POLICY["repo_directed_improvement_threshold"])


def _validation_friction_payload() -> dict[str, Any]:
    return copy.deepcopy(_REPO_FRICTION_POLICY["validation_friction"])


def _improvement_boundary_test_payload() -> dict[str, Any]:
    return copy.deepcopy(_REPO_FRICTION_POLICY["improvement_boundary_test"])


def _optimization_bias_payload(mode: str) -> dict[str, Any]:
    return copy.deepcopy(_OPTIMIZATION_BIAS_PAYLOADS[mode])


def _operating_posture_payload(*, config: WorkspaceConfig, surface: str, compact: bool = False) -> dict[str, Any]:
    improvement = _improvement_latitude_payload(config.improvement_latitude)
    bias = _optimization_bias_payload(config.optimization_bias)
    incidental = copy.deepcopy(_IMPROVEMENT_LATITUDE_POLICY["incidental_finding_policy"])
    payload: dict[str, Any] = {
        "kind": "agentic-workspace/operating-posture/v1",
        "status": "present",
        "surface": surface,
        "improvement_latitude": {
            "mode": config.improvement_latitude,
            "source": config.improvement_latitude_source,
            "initiative_posture": improvement["initiative_posture"],
        },
        "optimization_bias": {
            "mode": config.optimization_bias,
            "source": config.optimization_bias_source,
            "report_density": bias["report_density"],
            "residue_density": bias["residue_density"],
            "rendered_view_style": bias["rendered_view_style"],
        },
        "required_behaviors": [
            "act only on bounded evidence-backed improvements",
            "report useful incidental findings compactly even when not acting",
            "separate acted-on, reported-only, dismissed, and routed findings",
            "keep residue terse when canonical state already carries the contract",
        ],
        "closeout_nudge": {
            "field": "improvement_signal_review",
            "rule": "Record incidental findings in the existing review shape; do not add a separate workflow obligation.",
            "categories": ["signals fixed", "signals routed", "signals dismissed"],
        },
        "detail_sections": {
            "improvement": _command_with_cli_invoke(
                command="agentic-workspace report --target ./repo --section repo_friction --format json",
                cli_invoke=config.cli_invoke,
            ),
            "output": _command_with_cli_invoke(
                command="agentic-workspace report --target ./repo --section output_contract --format json",
                cli_invoke=config.cli_invoke,
            ),
        },
    }
    if compact:
        payload["required_behavior_summary"] = "bounded evidence-backed action; compactly report useful incidental findings"
        payload.pop("required_behaviors", None)
    if not compact:
        payload["incidental_finding_policy"] = incidental
        payload["boundaries"] = {
            "not_scheduler": True,
            "not_blanket_refactor_permission": True,
            "proof_and_ownership_stay_invariant": True,
        }
        payload["routing"] = {
            "repeated_or_high_confidence_findings": "planning, review evidence, Memory, docs, config, or agent aids",
            "reported_only_findings": "final answer or improvement_signal_review when the lane already owns closeout evidence",
        }
    return payload


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
    for field in ("observed_during", "cost", "suspected_owner"):
        value = raw.get(field)
        if isinstance(value, str) and value.strip():
            normalized[field] = value.strip()
    signal_kind = raw.get("signal_kind")
    if isinstance(signal_kind, str) and signal_kind in _IMPROVEMENT_SIGNAL_CONTRACT["kinds"]:
        normalized["signal_kind"] = signal_kind
    likely_remediation = raw.get("likely_remediation")
    if isinstance(likely_remediation, str) and likely_remediation in _IMPROVEMENT_SIGNAL_CONTRACT["likely_remediations"]:
        normalized["likely_remediation"] = likely_remediation
    recurrence = raw.get("recurrence")
    if isinstance(recurrence, str) and recurrence in _IMPROVEMENT_SIGNAL_CONTRACT["recurrence"]:
        normalized["recurrence"] = recurrence
    validation_failure_class = raw.get("validation_failure_class")
    validation_failure_classes = {
        str(item.get("class", "")) for item in _IMPROVEMENT_SIGNAL_CONTRACT.get("validation_failure_classes", []) if isinstance(item, dict)
    }
    if isinstance(validation_failure_class, str) and validation_failure_class in validation_failure_classes:
        normalized["validation_failure_class"] = validation_failure_class
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


def _improvement_signal_contract_payload() -> dict[str, Any]:
    return {
        "kind": _IMPROVEMENT_SIGNAL_CONTRACT["kind"],
        "role": _IMPROVEMENT_SIGNAL_CONTRACT["role"],
        "rule": _IMPROVEMENT_SIGNAL_CONTRACT["rule"],
        "candidate_kind": _IMPROVEMENT_SIGNAL_CONTRACT["candidate_kind"],
        "required_fields": list(_IMPROVEMENT_SIGNAL_CONTRACT["required_fields"]),
        "kinds": list(_IMPROVEMENT_SIGNAL_CONTRACT["kinds"]),
        "likely_remediations": list(_IMPROVEMENT_SIGNAL_CONTRACT["likely_remediations"]),
        "validation_failure_classes": list(_IMPROVEMENT_SIGNAL_CONTRACT.get("validation_failure_classes", [])),
        "validation_remedy_order": list(_IMPROVEMENT_SIGNAL_CONTRACT.get("validation_remedy_order", [])),
        "correct_by_design_review": dict(_IMPROVEMENT_SIGNAL_CONTRACT.get("correct_by_design_review", {})),
        "closeout_statuses": list(_IMPROVEMENT_SIGNAL_CONTRACT["closeout_statuses"]),
        "destinations": list(_IMPROVEMENT_SIGNAL_CONTRACT["destinations"]),
        "guardrails": list(_IMPROVEMENT_SIGNAL_CONTRACT["guardrails"]),
    }


def _improvement_signal_candidate(
    *,
    kind: str,
    observed_during: str,
    symptom: str,
    cost: str,
    suspected_owner: str,
    likely_remediation: str,
    confidence: str,
    recurrence: str,
    immediate_action: str,
    retention: str,
    source: str,
) -> dict[str, str]:
    return {
        "candidate_kind": str(_IMPROVEMENT_SIGNAL_CONTRACT["candidate_kind"]),
        "kind": kind,
        "observed_during": observed_during,
        "symptom": symptom,
        "cost": cost,
        "suspected_owner": suspected_owner,
        "likely_remediation": likely_remediation,
        "confidence": confidence,
        "recurrence": recurrence,
        "immediate_action": immediate_action,
        "retention": retention,
        "source": source,
    }


def _confidence_label(confidence: Any) -> str:
    try:
        score = float(confidence)
    except (TypeError, ValueError):
        return "medium"
    if score >= 0.85:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def _improvement_signal_candidates_from_repo_friction(repo_friction: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(repo_friction, dict):
        return []
    candidates: list[dict[str, str]] = []
    for item in _list_payload(
        repo_friction.get("large_file_hotspots", {}).get("items") if isinstance(repo_friction.get("large_file_hotspots"), dict) else []
    ):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        line_count = str(item.get("line_count", "")).strip()
        if not path:
            continue
        likely_remediation = str(item.get("likely_remediation", "refactor")).strip() or "refactor"
        if likely_remediation not in _IMPROVEMENT_SIGNAL_CONTRACT["likely_remediations"]:
            likely_remediation = "refactor"
        candidate = _improvement_signal_candidate(
            kind="architecture_cost",
            observed_during="agentic-workspace report --section repo_friction",
            symptom=f"{path} has {line_count} lines and exceeds the large-file friction threshold.",
            cost="Large surfaces increase reading, review, and change-localization cost.",
            suspected_owner=path,
            likely_remediation=likely_remediation,
            confidence="medium",
            recurrence="first_seen",
            immediate_action="route",
            retention="shrink_after_fix",
            source="repo_friction.large_file_hotspots",
        )
        for field in ("surface_role", "classification", "suggested_action", "context_strategy", "primary_next_action"):
            if field in item:
                candidate[field] = copy.deepcopy(item[field])
        candidates.append(candidate)
    for item in _list_payload(
        repo_friction.get("concept_surface_hotspots", {}).get("items")
        if isinstance(repo_friction.get("concept_surface_hotspots"), dict)
        else []
    ):
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        if not path:
            continue
        candidates.append(
            _improvement_signal_candidate(
                kind="docs_routing" if str(item.get("kind", "")) == "docs" else "footprint_cost",
                observed_during="agentic-workspace report --section repo_friction",
                symptom=f"{path} is a high-volume concept surface.",
                cost="Large concept surfaces can make first-contact routing and review more expensive.",
                suspected_owner=path,
                likely_remediation="docs",
                confidence="medium",
                recurrence="first_seen",
                immediate_action="review",
                retention="shrink_after_fix",
                source="repo_friction.concept_surface_hotspots",
            )
        )
    for evidence in _list_payload(repo_friction.get("external_evidence", [])):
        if not isinstance(evidence, dict) or evidence.get("kind") != "setup-findings":
            continue
        for item in _list_payload(evidence.get("items")):
            if not isinstance(item, dict):
                continue
            validation_failure_class = str(item.get("validation_failure_class", "")).strip()
            signal_kind = str(item.get("signal_kind", "")).strip() or (
                "validation_friction" if validation_failure_class else "workflow_cost"
            )
            if signal_kind not in _IMPROVEMENT_SIGNAL_CONTRACT["kinds"]:
                signal_kind = "workflow_cost"
            likely_remediation = (
                str(item.get("likely_remediation", "")).strip() or str(item.get("suggested_remediation", "unknown")).strip()
            )
            if likely_remediation not in _IMPROVEMENT_SIGNAL_CONTRACT["likely_remediations"]:
                likely_remediation = "unknown"
            candidate = _improvement_signal_candidate(
                kind=signal_kind,
                observed_during=str(item.get("observed_during", item.get("source", "agentic-workspace setup"))).strip()
                or "agentic-workspace setup",
                symptom=str(item.get("symptom", item.get("summary", "Promotable setup finding."))).strip(),
                cost=str(item.get("cost", "Setup finding indicates repeated friction or rediscovery cost.")).strip(),
                suspected_owner=str(item.get("suspected_owner", item.get("path", item.get("owner", "unknown")))).strip() or "unknown",
                likely_remediation=likely_remediation,
                confidence=_confidence_label(item.get("confidence", "medium")),
                recurrence=str(item.get("recurrence", "first_seen")).strip() or "first_seen",
                immediate_action="route",
                retention="shrink_after_fix",
                source="setup_findings.promotable.repo_friction_evidence",
            )
            if validation_failure_class:
                candidate["validation_failure_class"] = validation_failure_class
            candidates.append(candidate)
    return candidates[:5]


def _improvement_intake_payload(
    *,
    target_root: Path | None = None,
    config: WorkspaceConfig | None = None,
    repo_friction: dict[str, Any] | None = None,
) -> dict[str, Any]:
    setup_findings = _setup_findings_input_payload(target_root=target_root) if target_root is not None else None
    review_enabled = bool(config and "review_artifacts" in config.advanced_features)
    signal_candidates = _improvement_signal_candidates_from_repo_friction(repo_friction)
    source_checkout = _is_agentic_workspace_source_checkout(target_root)
    subtypes: list[dict[str, Any]] = [
        {
            "id": "setup_finding",
            "audience": "target-repo",
            "source": SETUP_FINDINGS_PATH.as_posix(),
            "evidence_class": "agent-provided setup artifact",
            "confidence_field": "confidence",
            "accepted_classes": list(SUPPORTED_SETUP_FINDING_CLASSES),
            "primary_route": "repo_friction.external_evidence or planning promotion review",
            "selector": "agentic-workspace setup --target ./repo --format json",
        },
        {
            "id": "review_finding",
            "audience": "target-repo",
            "source": ".agentic-workspace/planning/reviews/",
            "evidence_class": "bounded review finding",
            "confidence_field": "review mode and finding severity/trust",
            "primary_route": "planning review promotion only when the review_artifacts advanced feature is enabled or explicitly selected",
            "selector": "agentic-workspace report --target ./repo --section closeout_trust --format json",
            "advanced_feature": "review_artifacts",
        },
        {
            "id": "validation_friction",
            "audience": "target-repo",
            "source": "src/agentic_workspace/contracts/repo_friction_policy.json",
            "evidence_class": "proof or validation friction",
            "confidence_field": "repeated failure against otherwise straightforward work",
            "primary_route": "repo_friction evidence, config/check improvement, or proof-route cleanup",
            "selector": "agentic-workspace defaults --section improvement_latitude --format json",
            "classification": "user_or_content_error | environment_or_dependency_error | interface_design_error | unclear_proof_contract",
            "correct_by_design_remedies": [
                "scaffold",
                "writer_helper",
                "alias",
                "lifecycle_command",
                "command",
                "agent_aid",
            ],
            "repeat_route": "when interface-design or unclear-proof failures repeat, emit an improvement_signal_candidate instead of only adding validation prose",
        },
        {
            "id": "memory_improvement_signal",
            "audience": "target-repo",
            "source": ".agentic-workspace/memory/WORKFLOW.md",
            "evidence_class": "durable memory note carrying upstream improvement pressure",
            "confidence_field": "memory_role=improvement_signal plus config_treatment",
            "primary_route": "Memory note, config/check follow-up, docs clarification, or issue follow-up",
            "selector": "agentic-workspace report --target ./repo --section repo_friction --format json",
        },
        {
            "id": "repair_recurrence",
            "audience": "target-repo",
            "source": "doctor.repair_actions or doctor.manual_review_actions",
            "evidence_class": "repeated invariant/fault repair class",
            "confidence_field": "recurrence plus affected invariant and proof-after result",
            "primary_route": "correct-by-design remedy, agent aid, regression test, or issue follow-up",
            "selector": "agentic-workspace defaults --section repair_recovery --format json",
            "classification": "first_seen | repeated | human_confirmed",
            "correct_by_design_remedies": [
                "remove_or_merge_wrong_path",
                "affordance",
                "scaffold",
                "writer_helper",
                "agent_aid",
                "regression_test",
            ],
            "repeat_route": "when the same invariant/fault pair repeats, prefer making the right action cheaper before adding more diagnostic prose",
        },
    ]
    source_checkout_only_subtypes = [
        {
            "id": "dogfooding_friction",
            "audience": "source-checkout-only",
            "source": "docs/maintainer/dogfooding-feedback.md",
            "evidence_class": "maintainer dogfooding signal",
            "confidence_field": "repeated practical friction or maintainer override",
            "primary_route": "active execplan, roadmap, Memory, docs, or issue follow-up",
            "selector": "agentic-workspace report --target ./repo --section repo_friction --format json",
        }
    ]
    if source_checkout:
        subtypes[1:1] = source_checkout_only_subtypes
    payload: dict[str, Any] = {
        "kind": "workspace-improvement-intake/v1",
        "role": "router-not-backlog",
        "command": "agentic-workspace report --target ./repo --section improvement_intake --format json",
        "audience_boundary": {
            "status": "source-checkout" if source_checkout else "target-repo",
            "rule": "Reusable host-repo diagnostics are shipped; package-development signals stay source-checkout-only.",
            "source_checkout_only_subtypes": [item["id"] for item in source_checkout_only_subtypes] if source_checkout else [],
        },
        "signal_contract": {
            "command": "agentic-workspace defaults --section improvement_signal --format json",
            "candidate_kind": _IMPROVEMENT_SIGNAL_CONTRACT["candidate_kind"],
            "required_fields": list(_IMPROVEMENT_SIGNAL_CONTRACT["required_fields"]),
            "closeout_statuses": list(_IMPROVEMENT_SIGNAL_CONTRACT["closeout_statuses"]),
            "validation_failure_classes": [
                item.get("class", "")
                for item in _IMPROVEMENT_SIGNAL_CONTRACT.get("validation_failure_classes", [])
                if isinstance(item, dict)
            ],
            "correct_by_design_review": {
                "status": _IMPROVEMENT_SIGNAL_CONTRACT.get("correct_by_design_review", {}).get("status", ""),
                "rule": _IMPROVEMENT_SIGNAL_CONTRACT.get("correct_by_design_review", {}).get("rule", ""),
                "closeout_field": _IMPROVEMENT_SIGNAL_CONTRACT.get("correct_by_design_review", {}).get("closeout_field", ""),
            },
        },
        "default_rule": (
            "Treat setup findings, review findings, validation friction, and memory improvement signals as one intake question: "
            "what should happen to this signal, if anything? Package-development signals are added only in the package source checkout."
        ),
        "promotion_rule": (
            "Preserve or promote only signals with a clear evidence source, confidence/trust signal, and durable owner; "
            "dismiss weak or speculative signals explicitly."
        ),
        "subtypes": subtypes,
        "routing_decision": [
            {
                "step": "classify",
                "question": "Which subtype and evidence source produced the signal?",
            },
            {
                "step": "admit-or-dismiss",
                "question": "Is there enough confidence, repetition, or explicit owner override to preserve it?",
            },
            {
                "step": "choose-owner",
                "question": "Should it become active planning, roadmap, Memory, docs, config/checks, issue follow-up, or be discarded?",
            },
            {
                "step": "prove",
                "question": "Can the reviewer see the evidence and owner without reconstructing chat?",
            },
        ],
        "allowed_destinations": [
            "discard",
            "active planning state or execplan",
            "roadmap",
            "Memory",
            "canonical docs",
            "config/check surface",
            "issue follow-up",
        ],
        "guardrails": [
            "Do not auto-promote every signal to work.",
            "Do not treat review artifacts as ordinary startup input.",
            "Keep speculative findings transient unless a durable owner is clear.",
            "Preserve provenance and confidence when a signal is routed.",
        ],
        "improvement_signal_candidates": signal_candidates,
        "candidate_count": len(signal_candidates),
        "setup_findings": (
            {
                "status": setup_findings.get("status"),
                "path": setup_findings.get("path"),
                "loaded_count": setup_findings.get("loaded_count"),
                "promotable_counts": {
                    key: len(value) for key, value in setup_findings.get("promotable", {}).items() if isinstance(value, list)
                },
                "transient_count": len(setup_findings.get("transient", [])) if isinstance(setup_findings.get("transient"), list) else 0,
            }
            if isinstance(setup_findings, dict)
            else {
                "status": "not-evaluated",
                "path": SETUP_FINDINGS_PATH.as_posix(),
            }
        ),
        "advanced_review_route": {
            "feature": "review_artifacts",
            "enabled": review_enabled,
            "rule": "Review findings are an improvement-intake subtype, but review artifact machinery remains advanced opt-in.",
        },
    }
    if not source_checkout:
        payload["source_checkout_only"] = {
            "status": "hidden-outside-package-source-checkout",
            "hidden_subtype_count": len(source_checkout_only_subtypes),
        }
    return payload


def _with_agent_instructions_file(config: WorkspaceConfig, *, filename: str, source: str) -> WorkspaceConfig:
    return replace(
        config,
        agent_instructions_file=filename,
        agent_instructions_source=source,
    )


def main(argv: list[str] | None = None) -> int:
    argv_list = list(sys.argv[1:] if argv is None else argv)
    generated_result = _run_generated_cli_package_if_supported(argv_list)
    if generated_result is not None:
        return generated_result

    parser = build_parser()
    args = parser.parse_args(argv_list)
    try:
        descriptors = _module_operations()
        _validate_descriptor_contract(descriptors)
        _configure_parser_contract(parser=parser, descriptors=descriptors)
    except WorkspaceUsageError as exc:
        parser.error(str(exc))

    if args.command == "modules":
        try:
            target_root = _resolve_target_root(args.target) if args.target else None
            if target_root is not None:
                _validate_target_root(command_name="modules", target_root=target_root)
            _emit_modules(format_name=args.format, target_root=target_root, profile=getattr(args, "profile", "tiny"))
            return 0
        except WorkspaceUsageError as exc:
            parser.error(str(exc))

    if args.command == "planning":
        payload = _planning_help_payload(target=args.target)
        if args.format == "json":
            print(json.dumps(payload, indent=2))
        else:
            _print_planning_help(payload)
        return 0

    generated_adapter = _generated_adapter_for_command(str(args.command))
    if generated_adapter is not None:
        try:
            return _run_generated_command_adapter(args, adapter=generated_adapter)
        except WorkspaceUsageError as exc:
            parser.error(str(exc))

    if args.command == "summary":
        try:
            target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
            _validate_target_root(command_name="summary", target_root=target_root)
            from repo_planning_bootstrap.cli import _print_summary
            from repo_planning_bootstrap.installer import format_summary_json, planning_summary

            summary_profile = args.profile if args.format == "json" else "full"
            summary = planning_summary(
                target=target_root.as_posix(),
                profile=summary_profile,
                task_text=getattr(args, "task", None),
                changed_paths=list(getattr(args, "changed", []) or []),
            )
            if isinstance(summary, dict):
                config = _load_workspace_config(target_root=target_root)
                summary["memory_consult"] = _memory_consult_payload(
                    target_root=target_root,
                    compact=summary_profile == "compact",
                    cli_invoke=config.cli_invoke,
                )
            if args.format == "json":
                print(format_summary_json(summary))
            else:
                _print_summary(summary)
            return 0
        except ImportError:
            parser.error("The planning module must be installed to use the summary command.")
        except WorkspaceUsageError as exc:
            parser.error(str(exc))

    if args.command == "start":
        try:
            target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
            _validate_target_root(command_name="start", target_root=target_root)
            payload = _start_payload(
                target_root=target_root,
                changed_paths=list(getattr(args, "changed", []) or []),
                task_text=getattr(args, "task", None),
            )
            _emit_payload(payload=payload, format_name=args.format)
            return 0
        except WorkspaceUsageError as exc:
            parser.error(str(exc))

    if args.command == "implement":
        try:
            target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
            _validate_target_root(command_name="implement", target_root=target_root)
            payload = _implement_payload(
                target_root=target_root,
                changed_paths=list(getattr(args, "changed", []) or []),
                task_text=getattr(args, "task", None),
            )
            _emit_payload(payload=payload, format_name=args.format)
            return 0
        except WorkspaceUsageError as exc:
            parser.error(str(exc))

    if args.command == "preflight":
        try:
            target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
            _validate_target_root(command_name="preflight", target_root=target_root)
            payload = _run_preflight_command(
                target_root=target_root,
                active_only=getattr(args, "active_only", False),
                task_text=getattr(args, "task", None),
                profile=getattr(args, "profile", "tiny"),
            )
            _emit_payload(payload=payload, format_name=args.format)
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
                    profile=getattr(args, "profile", "full"),
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
        try:
            target_root = _resolve_target_root(args.target) if args.target else None
            if target_root is not None:
                _validate_target_root(command_name="skills", target_root=target_root)
            _emit_skills(format_name=args.format, target_root=target_root, task_text=args.task)
            return 0
        except WorkspaceUsageError as exc:
            parser.error(str(exc))

    if args.command == "system-intent":
        try:
            target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
            _validate_target_root(command_name="system-intent", target_root=target_root)
            config = config_lib.load_workspace_config(target_root=target_root, valid_presets=set(_preset_modules(descriptors)))
            _emit_system_intent(format_name=args.format, target_root=target_root, config=config, sync=bool(args.sync))
            return 0
        except (ModuleSelectionError, WorkspaceUsageError) as exc:
            parser.error(str(exc))

    if args.command == "external-intent":
        try:
            target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
            _validate_target_root(command_name="external-intent", target_root=target_root)
            if args.external_intent_command == "refresh-github":
                payload = _refresh_github_external_intent_evidence(
                    target_root=target_root,
                    repo=getattr(args, "repo", None),
                    limit=getattr(args, "limit", None),
                    state=getattr(args, "state", None),
                    storage=str(getattr(args, "storage", "cache") or "cache"),
                    dry_run=bool(getattr(args, "dry_run", False)),
                )
                _emit_payload(payload=payload, format_name=args.format)
                return 0
        except WorkspaceUsageError as exc:
            parser.error(str(exc))

    if args.command in {"install", "init"}:
        try:
            repo_root = _resolve_target_root(args.target)
            _validate_target_root(command_name=args.command, target_root=repo_root, local_only=bool(args.local_only))
            _enforce_preflight_gate(parser=parser, args=args, command_name=args.command)
            target_root = repo_root
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
        payload["lifecycle_plan"] = _lifecycle_plan_payload(
            payload=payload,
            command_name=args.command,
            target_root=target_root,
            selected_modules=selected_modules,
            dry_run=args.dry_run,
            local_only=bool(args.local_only),
            cli_invoke=config.cli_invoke,
        )
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
        _ensure_external_intent_cache_if_available(target_root=target_root)
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
            target_root = local_only_repo_root
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
        if getattr(args, "section", None) in {"external_work_reconciliation", "external_work_delta"}:
            _ensure_external_intent_cache_if_available(target_root=target_root)
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
    repair_actions: list[dict[str, Any]] | None = None,
    manual_review_actions: list[dict[str, Any]] | None = None,
    repair_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "module": "workspace",
        "message": message,
        "target_root": target_root.as_posix(),
        "dry_run": dry_run,
        "actions": actions,
        "warnings": warnings,
    }
    if repair_actions is not None:
        payload["repair_actions"] = repair_actions
    if manual_review_actions is not None:
        payload["manual_review_actions"] = manual_review_actions
    if repair_plan is not None:
        payload["repair_plan"] = repair_plan
    return payload


def _repair_recovery_taxonomy_payload() -> dict[str, Any]:
    return {
        "kind": "workspace-repair-recovery-taxonomy/v1",
        "role": "compact diagnostic vocabulary, not a backlog",
        "command": "agentic-workspace defaults --section repair_recovery --format json",
        "fault_classes": [
            {
                "id": "user_content_fault",
                "likely_owner": "repo owner",
                "repairability": "manual-review-first",
                "escalation": "ask for human intent when content authority is ambiguous",
            },
            {
                "id": "agent_operation_fault",
                "likely_owner": "current agent",
                "repairability": "safe helper when the affected surface is managed or generated",
                "escalation": "manual review when ownership or intent is unclear",
            },
            {
                "id": "package_affordance_fault",
                "likely_owner": "package maintainers",
                "repairability": "route to interface/scaffold/helper improvement",
                "escalation": "create an improvement signal when the same class repeats",
            },
            {
                "id": "package_command_bug",
                "likely_owner": "package maintainers",
                "repairability": "safe repair may recover state, but the command path needs regression work",
                "escalation": "capture command, invariant, actual state, affected surfaces, reproduction, and regression-test hint",
            },
            {
                "id": "stale_external_evidence",
                "likely_owner": "evidence adapter or operator",
                "repairability": "refresh or mark stale before acting on counts",
                "escalation": "do not treat stale provider data as current execution pressure",
            },
            {
                "id": "generated_artifact_drift",
                "likely_owner": "generator or agent operation",
                "repairability": "regenerate from declared source when source authority is clear",
                "escalation": "manual review when generated and source surfaces disagree ambiguously",
            },
            {
                "id": "ambiguous_ownership",
                "likely_owner": "repo owner",
                "repairability": "manual-review-only",
                "escalation": "do not overwrite local owner edits without explicit intent",
            },
            {
                "id": "local_only_leakage",
                "likely_owner": "agent/runtime integration",
                "repairability": "move or remove from shared authority when unambiguous",
                "escalation": "manual review if shared state may already depend on it",
            },
        ],
        "invariants": [
            {
                "id": "workspace.required_surface_present",
                "owner": "workspace",
                "severity": "warning",
                "repair_class": "safe-deterministic",
                "fault_classes": ["agent_operation_fault", "package_command_bug"],
            },
            {
                "id": "workspace.external_handoff_current",
                "owner": "workspace",
                "severity": "warning",
                "repair_class": "safe-deterministic",
                "fault_classes": ["generated_artifact_drift", "package_command_bug"],
            },
            {
                "id": "workspace.startup_pointer_present",
                "owner": "repo",
                "severity": "warning",
                "repair_class": "manual-review",
                "fault_classes": ["agent_operation_fault", "ambiguous_ownership"],
            },
            {
                "id": "workspace.no_absolute_paths",
                "owner": "repo",
                "severity": "warning",
                "repair_class": "manual-review",
                "fault_classes": ["user_content_fault", "local_only_leakage"],
            },
            {
                "id": "planning.active_execplan_exists",
                "owner": "planning",
                "severity": "warning",
                "repair_class": "safe-deterministic-when-row-is-stale",
                "fault_classes": ["agent_operation_fault", "package_command_bug"],
            },
            {
                "id": "planning.no_closed_work_in_live_state",
                "owner": "planning",
                "severity": "warning",
                "repair_class": "safe-deterministic-when-closeout-is-unambiguous",
                "fault_classes": ["agent_operation_fault", "package_affordance_fault", "package_command_bug"],
            },
            {
                "id": "structured.schema_valid",
                "owner": "surface owner",
                "severity": "error",
                "repair_class": "manual-review-unless-generated",
                "fault_classes": ["user_content_fault", "agent_operation_fault", "package_command_bug"],
            },
            {
                "id": "memory.no_active_task_state",
                "owner": "memory",
                "severity": "warning",
                "repair_class": "route-to-planning-or-discard",
                "fault_classes": ["agent_operation_fault", "package_affordance_fault"],
            },
            {
                "id": "local_only.not_shared_authority",
                "owner": "workspace",
                "severity": "warning",
                "repair_class": "manual-review",
                "fault_classes": ["local_only_leakage"],
            },
            {
                "id": "external_evidence.aggregates_match_items",
                "owner": "evidence adapter",
                "severity": "warning",
                "repair_class": "safe-deterministic-when-items-are-authoritative",
                "fault_classes": ["stale_external_evidence", "package_command_bug"],
            },
        ],
        "repair_action_shape": {
            "required_fields": [
                "id",
                "invariant",
                "fault_class",
                "severity",
                "owner",
                "safe_to_apply",
                "risk",
                "command",
                "dry_run",
                "proof_after",
                "current_fault_summary",
                "do_not",
            ],
            "rule": "Prefer one primary next action, with detail available in repair_actions or manual_review_actions.",
        },
        "package_command_bug_signal": {
            "required_fields": [
                "command_run",
                "expected_invariant",
                "actual_broken_state",
                "affected_surfaces",
                "safe_repair_available",
                "reproduction_command",
                "suggested_regression_test",
            ],
            "route": "improvement_signal candidate or issue follow-up when a package-owned command violates its postcondition",
        },
        "recurrence_to_improvement": {
            "first_seen": "repair or review the state without promoting product work by default",
            "repeated": "ask whether the wrong path can be removed, merged, scaffolded, or made obvious",
            "human_confirmed": "route to issue, planning, config/check, docs, or agent aid with provenance",
            "preferred_remedies": ["remove_or_merge_wrong_path", "affordance", "scaffold", "writer_helper", "agent_aid", "regression_test"],
        },
        "operational_affordance_rule": (
            "Repair output should show current fault summary, one primary safe next action when possible, resolved command, "
            "risk, dry-run/apply distinction, proof_after, and do_not guidance."
        ),
    }


def _workspace_repair_payload(
    *,
    target_root: Path,
    actions: list[dict[str, str]],
    warnings: list[dict[str, str]],
    command_name: str,
    cli_invoke: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if command_name != "doctor":
        return [], [], _empty_repair_plan(command_name=command_name)

    repair_actions: list[dict[str, Any]] = []
    manual_review_actions: list[dict[str, Any]] = []
    missing_workspace_surfaces: list[str] = []
    generated_handoff_surfaces: list[str] = []
    missing_startup_surfaces: list[str] = []
    pointer_surfaces: list[str] = []
    absolute_path_surfaces: list[str] = []
    contract_drift_surfaces: list[str] = []
    merge_conflict_findings = _workspace_merge_conflict_findings(target_root=target_root)

    for action in actions:
        path = str(action.get("path", ""))
        kind = str(action.get("kind", ""))
        detail = str(action.get("detail", ""))
        if kind == "missing" and path in {relative.as_posix() for relative in WORKSPACE_PAYLOAD_FILES}:
            missing_workspace_surfaces.append(path)
        if path == WORKSPACE_EXTERNAL_AGENT_PATH.as_posix() and kind in {"missing", "warning"}:
            generated_handoff_surfaces.append(path)
        if kind == "missing" and "root startup entrypoint missing" in detail:
            missing_startup_surfaces.append(path)
        if "workspace workflow pointer block missing" in detail:
            pointer_surfaces.append(path)
        if "absolute path found" in detail:
            absolute_path_surfaces.append(path)

    for warning in warnings:
        path = str(warning.get("path", ""))
        message = str(warning.get("message", ""))
        if "contract drift:" in message:
            contract_drift_surfaces.append(path)

    if missing_workspace_surfaces:
        repair_actions.append(
            _workspace_safe_repair_action(
                id="restore-missing-workspace-surface",
                invariant="workspace.required_surface_present",
                fault_class="agent_operation_fault",
                owner="workspace",
                target_root=target_root,
                cli_invoke=cli_invoke,
                affected_surfaces=missing_workspace_surfaces,
                current_fault_summary="Required product-managed workspace surface(s) are missing.",
                risk="low; regenerates managed workspace surfaces from package payloads",
                do_not=[
                    "Do not hand-author managed workspace payloads when upgrade can recreate them.",
                    "Do not treat the missing surface as repo-owned without checking ownership metadata.",
                ],
            )
        )
    if generated_handoff_surfaces:
        repair_actions.append(
            _workspace_safe_repair_action(
                id="refresh-generated-agent-handoff",
                invariant="workspace.external_handoff_current",
                fault_class="generated_artifact_drift",
                owner="workspace",
                target_root=target_root,
                cli_invoke=cli_invoke,
                affected_surfaces=generated_handoff_surfaces,
                current_fault_summary="Generated external-agent handoff surface is missing or stale.",
                risk="low; refreshes generated adapter text from declared workspace/module state",
                do_not=[
                    "Do not make llms.txt a second handbook.",
                    "Do not edit generated adapter doctrine instead of refreshing from source authority.",
                ],
                dry_run_first=True,
            )
        )

    for surface in missing_startup_surfaces:
        manual_review_actions.append(
            _workspace_manual_review_action(
                id="restore-startup-entrypoint-manually",
                invariant="workspace.startup_entrypoint_present",
                fault_class="ambiguous_ownership",
                owner="repo",
                target_root=target_root,
                cli_invoke=cli_invoke,
                affected_surfaces=[surface],
                current_fault_summary="Configured root startup entrypoint is missing.",
                risk="manual review required; startup files are repo-owned authority surfaces",
                do_not=[
                    "Do not overwrite repo-owned startup policy without explicit intent.",
                    "Do not assume AGENTS.md is the configured entrypoint when config says otherwise.",
                ],
            )
        )
    for surface in pointer_surfaces:
        manual_review_actions.append(
            _workspace_manual_review_action(
                id="restore-workspace-pointer-manually",
                invariant="workspace.startup_pointer_present",
                fault_class="agent_operation_fault",
                owner="repo",
                target_root=target_root,
                cli_invoke=cli_invoke,
                affected_surfaces=[surface],
                current_fault_summary="Root startup entrypoint no longer points at the workspace workflow.",
                risk="manual review required; the surrounding startup file is repo-owned",
                do_not=[
                    "Do not replace unfenced repo instructions while restoring the workspace pointer.",
                    "Do not widen the pointer into a second workflow handbook.",
                ],
            )
        )
    if absolute_path_surfaces:
        manual_review_actions.append(
            _workspace_manual_review_action(
                id="remove-or-localize-absolute-paths",
                invariant="workspace.no_absolute_paths",
                fault_class="local_only_leakage",
                owner="repo",
                target_root=target_root,
                cli_invoke=cli_invoke,
                affected_surfaces=absolute_path_surfaces,
                current_fault_summary="Shared workspace surface contains absolute local path(s).",
                risk="manual review required; local paths may encode environment-specific assumptions",
                do_not=[
                    "Do not preserve machine-local paths in shared authority surfaces.",
                    "Do not delete path context if the repo needs a portable replacement.",
                ],
            )
        )
    if contract_drift_surfaces:
        manual_review_actions.append(
            _workspace_manual_review_action(
                id="investigate-contract-drift",
                invariant="structured.schema_valid",
                fault_class="package_command_bug",
                owner="package",
                target_root=target_root,
                cli_invoke=cli_invoke,
                affected_surfaces=contract_drift_surfaces,
                current_fault_summary="Workspace contract integrity check reported drift.",
                risk="manual review required; contract drift may indicate a package-command or generation bug",
                do_not=[
                    "Do not silence contract drift without adding or updating regression proof.",
                    "Do not classify package-created invalid state as an ordinary user edit.",
                ],
                package_command_bug_signal={
                    "command_run": f"{cli_invoke} doctor --target {target_root.as_posix()} --format json",
                    "expected_invariant": "structured.schema_valid",
                    "actual_broken_state": "contract integrity check failed",
                    "affected_surfaces": contract_drift_surfaces,
                    "safe_repair_available": False,
                    "reproduction_command": f"{cli_invoke} doctor --target {target_root.as_posix()} --format json",
                    "suggested_regression_test": "Add a focused contract integrity regression covering the drifted contract surface.",
                },
            )
        )
    for finding in merge_conflict_findings:
        affected = [str(finding.get("path", ""))]
        surface_class = str(finding.get("surface_class", "workspace-surface"))
        invariant = str(finding.get("invariant", "structured.schema_valid"))
        manual_review_actions.append(
            _workspace_manual_review_action(
                id=f"resolve-{surface_class.replace('_', '-').replace('/', '-')}-merge-conflict",
                invariant=invariant,
                fault_class=str(finding.get("fault_class", "agent_operation_fault")),
                owner=str(finding.get("owner", "surface-owner")),
                target_root=target_root,
                cli_invoke=cli_invoke,
                affected_surfaces=affected,
                current_fault_summary=str(finding.get("message", "AW-owned surface contains git merge conflict markers.")),
                risk=str(finding.get("risk", "manual review required; resolve the semantic conflict before continuing")),
                do_not=[
                    str(finding.get("do_not", "Do not delete or blindly regenerate the conflicted surface as the first recovery step.")),
                    "Do not treat conflict markers as ordinary formatting drift.",
                ],
            )
        )

    return (
        repair_actions,
        manual_review_actions,
        _repair_plan_payload(
            command_name=command_name,
            repair_actions=repair_actions,
            manual_review_actions=manual_review_actions,
        ),
    )


def _empty_repair_plan(*, command_name: str) -> dict[str, Any]:
    return {
        "kind": "workspace-repair-plan/v1",
        "command": command_name,
        "status": "not-evaluated",
        "primary_next_action": {
            "action": "none",
            "summary": "Repair actions are emitted by doctor diagnostics.",
            "safe_to_apply": False,
        },
        "repair_action_count": 0,
        "manual_review_action_count": 0,
        "detail_sections": ["repair_actions", "manual_review_actions"],
    }


def _repair_plan_payload(
    *,
    command_name: str,
    repair_actions: list[dict[str, Any]],
    manual_review_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    if repair_actions:
        primary = repair_actions[0]
        status = "safe-action-available"
    elif manual_review_actions:
        primary = manual_review_actions[0]
        status = "manual-review-required"
    else:
        primary = {
            "action": "none",
            "summary": "No repair or manual-review action is needed for workspace diagnostics.",
            "safe_to_apply": False,
        }
        status = "clean"
    return {
        "kind": "workspace-repair-plan/v1",
        "command": command_name,
        "status": status,
        "primary_next_action": primary,
        "repair_action_count": len(repair_actions),
        "manual_review_action_count": len(manual_review_actions),
        "detail_sections": ["repair_actions", "manual_review_actions"],
        "affordance_rule": "Show one primary next action first; keep alternatives and evidence in JSON detail sections.",
    }


def _workspace_safe_repair_action(
    *,
    id: str,
    invariant: str,
    fault_class: str,
    owner: str,
    target_root: Path,
    cli_invoke: str,
    affected_surfaces: list[str],
    current_fault_summary: str,
    risk: str,
    do_not: list[str],
    dry_run_first: bool = False,
) -> dict[str, Any]:
    dry_run = _command_with_cli_invoke(
        command=f"agentic-workspace upgrade --target {target_root.as_posix()} --dry-run --format json",
        cli_invoke=cli_invoke,
    )
    apply_command = _command_with_cli_invoke(
        command=f"agentic-workspace upgrade --target {target_root.as_posix()} --format json",
        cli_invoke=cli_invoke,
    )
    command = dry_run if dry_run_first else apply_command
    proof_after = [
        _command_with_cli_invoke(
            command=f"agentic-workspace doctor --target {target_root.as_posix()} --format json",
            cli_invoke=cli_invoke,
        )
    ]
    return {
        "id": id,
        "action": "inspect-workspace-upgrade-dry-run" if dry_run_first else "run-workspace-upgrade",
        "invariant": invariant,
        "fault_class": fault_class,
        "severity": "warning",
        "owner": owner,
        "safe_to_apply": True,
        "risk": risk,
        "command": command,
        "run": command,
        "dry_run": dry_run,
        **({"apply_after_review": apply_command, "requires_dry_run_review": True} if dry_run_first else {}),
        "proof_after": proof_after,
        "affected_surfaces": affected_surfaces,
        "current_fault_summary": current_fault_summary,
        "do_not": do_not,
        "merge_repair": {
            "status": "safe-rerender-when-source-authority-is-clear",
            "canonical_source": "installed package payloads, module descriptors, and workspace config",
            "rerender_command": apply_command,
            "proof_after": proof_after,
            "rule": (
                "After a merge, repair generated or managed surfaces from canonical source instead of editing generated output by hand. "
                "When requires_dry_run_review is true, inspect the dry-run before applying because the lifecycle repair may refresh more than the reported surface."
            ),
        },
        "recurrence": "first_seen",
        "improvement_signal_candidate": {
            "when": "repeated",
            "kind": "repair_recurrence",
            "route": "agentic-workspace defaults --section improvement_intake --format json",
            "preferred_remedy": "remove, merge, scaffold, or make the correct action more obvious before adding prose",
        },
    }


def _workspace_manual_review_action(
    *,
    id: str,
    invariant: str,
    fault_class: str,
    owner: str,
    target_root: Path,
    cli_invoke: str,
    affected_surfaces: list[str],
    current_fault_summary: str,
    risk: str,
    do_not: list[str],
    package_command_bug_signal: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proof_after = [
        _command_with_cli_invoke(
            command=f"agentic-workspace doctor --target {target_root.as_posix()} --format json",
            cli_invoke=cli_invoke,
        )
    ]
    payload: dict[str, Any] = {
        "id": id,
        "action": "manual-review",
        "invariant": invariant,
        "fault_class": fault_class,
        "severity": "warning",
        "owner": owner,
        "safe_to_apply": False,
        "risk": risk,
        "command": None,
        "run": None,
        "dry_run": None,
        "proof_after": proof_after,
        "affected_surfaces": affected_surfaces,
        "current_fault_summary": current_fault_summary,
        "do_not": do_not,
        "recurrence": "first_seen",
        "improvement_signal_candidate": {
            "when": "repeated",
            "kind": "repair_recurrence",
            "route": "agentic-workspace defaults --section improvement_intake --format json",
            "preferred_remedy": "turn repeated manual repair into a clearer affordance, scaffold, or regression test",
        },
    }
    if package_command_bug_signal is not None:
        payload["package_command_bug_signal"] = package_command_bug_signal
    return payload


_MERGE_CONFLICT_MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")
_MERGE_CONFLICT_EXTENSIONS = {".toml", ".json", ".md", ".txt"}


def _workspace_merge_conflict_findings(*, target_root: Path) -> list[dict[str, Any]]:
    workspace_root = target_root / ".agentic-workspace"
    if not workspace_root.exists():
        return []
    findings: list[dict[str, Any]] = []
    for path in sorted(workspace_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _MERGE_CONFLICT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not any(marker in text for marker in _MERGE_CONFLICT_MARKERS):
            continue
        relative = path.relative_to(target_root).as_posix()
        findings.append(_workspace_merge_conflict_finding(relative))
    return findings


def _workspace_merge_conflict_finding(relative_path: str) -> dict[str, Any]:
    if relative_path in {".agentic-workspace/config.toml", ".agentic-workspace/OWNERSHIP.toml"}:
        return {
            "path": relative_path,
            "surface_class": "workspace_policy",
            "owner": "repo",
            "fault_class": "ambiguous_ownership",
            "invariant": "workspace.policy_conflict_reviewed",
            "message": "Workspace config or ownership surface contains git merge conflict markers.",
            "risk": "manual review required; policy and ownership conflicts are high-impact semantic conflicts",
            "do_not": "Do not resolve config or ownership conflicts by blind regeneration or by committing local-only preferences.",
        }
    if relative_path == ".agentic-workspace/config.local.toml.example":
        return {
            "path": relative_path,
            "surface_class": "local_config_example",
            "owner": "workspace",
            "fault_class": "ambiguous_ownership",
            "invariant": "workspace.policy_conflict_reviewed",
            "message": "Local config example contains git merge conflict markers.",
            "risk": "manual review required; preserve portable examples and keep user-specific local config out of shared state",
            "do_not": "Do not copy user-specific config.local.toml values into the shared example while resolving the conflict.",
        }
    if relative_path.endswith("/state.toml") and relative_path.startswith(".agentic-workspace/planning/"):
        return {
            "path": relative_path,
            "surface_class": "planning_live_state",
            "owner": "planning",
            "fault_class": "agent_operation_fault",
            "invariant": "planning.live_state_conflict_resolved",
            "message": "Live Planning state contains git merge conflict markers.",
            "risk": "manual review required; live state selects future work and must preserve intentional active/queued items",
            "do_not": "Do not delete state.toml or recreate active work from memory as the first recovery step.",
        }
    if relative_path.startswith(".agentic-workspace/planning/execplans/"):
        return {
            "path": relative_path,
            "surface_class": "planning_execplan",
            "owner": "planning",
            "fault_class": "agent_operation_fault",
            "invariant": "planning.execplan_conflict_resolved",
            "message": "Planning execplan contains git merge conflict markers.",
            "risk": "manual review required; preserve the bounded implementation contract before continuing",
            "do_not": "Do not replace the execplan with a new freehand plan unless the conflicting intent has been preserved.",
        }
    if relative_path.startswith(".agentic-workspace/memory/repo/"):
        return {
            "path": relative_path,
            "surface_class": "durable_memory_note",
            "owner": "memory",
            "fault_class": "agent_operation_fault",
            "invariant": "memory.note_conflict_resolved",
            "message": "Durable Memory surface contains git merge conflict markers.",
            "risk": "manual review required; preserve durable facts and split broad notes when conflicts recur",
            "do_not": "Do not treat durable Memory as active task state or discard one side without checking whether it records reusable knowledge.",
        }
    generated_hint = "generated" if "generated" in relative_path or relative_path.endswith(".report.json") else "workspace_surface"
    return {
        "path": relative_path,
        "surface_class": generated_hint,
        "owner": "workspace",
        "fault_class": "generated_artifact_drift" if generated_hint == "generated" else "agent_operation_fault",
        "invariant": "workspace.merge_conflict_resolved",
        "message": "Agentic Workspace surface contains git merge conflict markers.",
        "risk": "manual review required unless a canonical source and safe rerender command are known",
        "do_not": "Do not blindly regenerate repo-owned content; first identify the authoritative source for the conflicted surface.",
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
    ]
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

    scratch_path = target_root / WORKSPACE_LOCAL_SCRATCH_ROOT_PATH
    actions.append(
        {
            "kind": "current" if scratch_path.is_dir() else "available",
            "path": WORKSPACE_LOCAL_SCRATCH_ROOT_PATH.as_posix(),
            "detail": "gitignored local scratch space for temporary agent working files",
        }
    )

    agents_path = target_root / agents_relative
    if not agents_path.exists():
        actions.append({"kind": "missing", "path": agents_relative.as_posix(), "detail": "root startup entrypoint missing"})
        warnings.append({"path": agents_relative.as_posix(), "message": "root startup entrypoint missing"})
        repair_actions, manual_review_actions, repair_plan = _workspace_repair_payload(
            target_root=target_root,
            actions=actions,
            warnings=warnings,
            command_name=command_name,
            cli_invoke=config.cli_invoke,
        )
        return _workspace_report(
            target_root=target_root,
            message=f"{command_name.title()} report",
            dry_run=False,
            actions=actions,
            warnings=warnings,
            repair_actions=repair_actions,
            manual_review_actions=manual_review_actions,
            repair_plan=repair_plan,
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

    repair_actions, manual_review_actions, repair_plan = _workspace_repair_payload(
        target_root=target_root,
        actions=actions,
        warnings=warnings,
        command_name=command_name,
        cli_invoke=config.cli_invoke,
    )

    return _workspace_report(
        target_root=target_root,
        message=f"{command_name.title()} report",
        dry_run=False,
        actions=actions,
        warnings=warnings,
        repair_actions=repair_actions,
        manual_review_actions=manual_review_actions,
        repair_plan=repair_plan,
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
        "Generated compatibility adapter. Canonical startup behavior lives in `AGENTS.md`, workspace contracts, and compact commands.",
        "",
        "Ordinary path:",
        f"- Read `{agent_instructions_file}` first.",
        '- Run `agentic-workspace start --profile tiny --task "<task>" --format json` for compact startup context.',
        "- Run `agentic-workspace summary --format json` when active work or roadmap state matters.",
        "- Run `agentic-workspace proof --profile tiny --changed <paths> --format json` before claiming validation.",
        "",
        "When needed:",
        "- `agentic-workspace preflight --format json` for takeover context.",
        "- `agentic-workspace config --target ./repo --profile tiny --format json` for configured posture or obligations.",
        "- `agentic-workspace report --target ./repo --format json` for health, warnings, and selectors.",
        "- Open raw planning or contract files only when compact commands point there.",
        "",
        "Preferred lifecycle commands:",
        "- Prefer an installed `agentic-workspace` CLI from the target repo's environment.",
        "- If unavailable, install the package into that repo or its tool environment before running lifecycle commands.",
        "- Use `uvx` or `pipx run` only as temporary/debug fallbacks.",
        "- `agentic-workspace defaults --section install_profiles --format json`",
    ]
    if selected_modules == ["planning"]:
        lines.append("- `agentic-workspace install --target ./repo --preset planning`")
    elif selected_modules == ["memory"]:
        lines.append("- `agentic-workspace install --target ./repo --preset memory`")
    else:
        lines.append("- `agentic-workspace install --target ./repo --preset memory`")
        lines.append("- `agentic-workspace install --target ./repo --preset planning`")
        lines.append("- `agentic-workspace install --target ./repo --preset full`")
        lines.append("- Use `full` only when both Memory and Planning are explicitly desired.")
    lines.extend(
        [
            "- `agentic-workspace config --target ./repo --profile tiny --format json`",
            "- `agentic-workspace summary --format json`",
            "- `agentic-workspace report --target ./repo --format json`",
            "",
            "Rules:",
            "- Keep this file lightweight.",
            "- Keep planning and memory ownership boundaries explicit.",
            "- Keep canonical authority in contracts, config, planning, Memory, and checks, not this adapter.",
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


LOCAL_AGENT_INSTRUCTIONS_FILE = Path("AGENTS.local.md")
LOCAL_AGENT_REFERENCE_FILE = Path(DEFAULT_AGENT_INSTRUCTIONS_FILE)
LOCAL_AGENT_REFERENCE_LINE = f"Follow instructions in `{LOCAL_AGENT_INSTRUCTIONS_FILE.as_posix()}` if present."
EXTERNAL_INTENT_CACHE_RELATIVE_PATH = Path(".agentic-workspace") / "local" / "cache" / "external-intent-evidence.json"
EXTERNAL_INTENT_PLANNING_RELATIVE_PATH = Path(".agentic-workspace") / "planning" / "external-intent-evidence.json"
EXTERNAL_INTENT_CACHE_CLOSED_RETENTION_DAYS = 7
LOCAL_ONLY_IGNORE_BLOCK = "# Agentic Workspace local-only storage\n.agentic-workspace/\n"
LOCAL_ONLY_STATE_FILE = Path(".agentic-workspace") / "LOCAL-ONLY.toml"


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


def _local_agent_instructions_text() -> str:
    lines = [
        "# Local Agent Instructions",
        "",
        "Authority marker:",
        "",
        "- authority: local-adapter",
        "- canonical_source: `.agentic-workspace/config.toml` and `agentic-workspace start --target . --format json`",
        "- safe_to_edit: true",
        "- refresh_command: null",
        "",
        WORKSPACE_POINTER_BLOCK,
    ]
    return "\n".join(lines) + "\n"


def _ensure_local_agent_reference_text(text: str) -> tuple[str, bool]:
    if LOCAL_AGENT_REFERENCE_LINE in text:
        return text, False
    if not text:
        return LOCAL_AGENT_REFERENCE_LINE + "\n", True
    lines = text.splitlines()
    trailing_newline = text.endswith("\n")
    if lines and lines[0].startswith("# "):
        insert_at = 1
        while insert_at < len(lines) and lines[insert_at] == "":
            insert_at += 1
        lines[insert_at:insert_at] = ["", LOCAL_AGENT_REFERENCE_LINE]
        updated = "\n".join(lines)
    else:
        updated = LOCAL_AGENT_REFERENCE_LINE + "\n\n" + text.rstrip("\n")
    return updated + ("\n" if trailing_newline or not updated.endswith("\n") else ""), True


def _remove_local_agent_reference_text(text: str) -> tuple[str, bool]:
    pattern = re.compile(r"\n?" + re.escape(LOCAL_AGENT_REFERENCE_LINE) + r"\n?", re.MULTILINE)
    updated, count = pattern.subn("\n", text, count=1)
    if count == 0:
        return text, False
    updated = re.sub(r"\n{3,}", "\n\n", updated).lstrip("\n")
    if updated and not updated.endswith("\n"):
        updated += "\n"
    return updated, True


def _sync_local_agent_startup(*, repo_root: Path, dry_run: bool, replace_reference_file: bool) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    local_path = repo_root / LOCAL_AGENT_INSTRUCTIONS_FILE
    rendered_local = _local_agent_instructions_text()
    existing_local = local_path.read_text(encoding="utf-8") if local_path.exists() else None
    if existing_local == rendered_local:
        actions.append(
            {
                "kind": "current",
                "path": LOCAL_AGENT_INSTRUCTIONS_FILE.as_posix(),
                "detail": "local startup instructions already current",
            }
        )
    else:
        if not dry_run:
            local_path.write_text(rendered_local, encoding="utf-8")
        actions.append(
            {
                "kind": _write_action_kind(dry_run=dry_run, existing=existing_local),
                "path": LOCAL_AGENT_INSTRUCTIONS_FILE.as_posix(),
                "detail": "refresh local startup instructions with the managed workspace workflow pointer",
            }
        )

    reference_path = repo_root / LOCAL_AGENT_REFERENCE_FILE
    existing_reference = reference_path.read_text(encoding="utf-8") if reference_path.exists() else ""
    if replace_reference_file:
        updated_reference = LOCAL_AGENT_REFERENCE_LINE + "\n"
        changed = existing_reference != updated_reference
    else:
        updated_reference, changed = _ensure_local_agent_reference_text(existing_reference)
    if changed:
        if not dry_run:
            reference_path.write_text(updated_reference, encoding="utf-8")
        actions.append(
            {
                "kind": _write_action_kind(dry_run=dry_run, existing=existing_reference if reference_path.exists() else None),
                "path": LOCAL_AGENT_REFERENCE_FILE.as_posix(),
                "detail": (
                    "refresh root startup entrypoint as a tiny local reference"
                    if replace_reference_file
                    else "add tiny local startup reference to AGENTS.local.md"
                ),
            }
        )
    else:
        actions.append(
            {
                "kind": "current",
                "path": LOCAL_AGENT_REFERENCE_FILE.as_posix(),
                "detail": "tiny local startup reference already present",
            }
        )
    return actions


def _remove_local_agent_startup(*, repo_root: Path, dry_run: bool) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    local_path = repo_root / LOCAL_AGENT_INSTRUCTIONS_FILE
    if not local_path.exists():
        actions.append(
            {
                "kind": "skipped",
                "path": LOCAL_AGENT_INSTRUCTIONS_FILE.as_posix(),
                "detail": "local startup instructions already absent",
            }
        )
    elif local_path.read_text(encoding="utf-8") != _local_agent_instructions_text():
        actions.append(
            {
                "kind": "manual review",
                "path": LOCAL_AGENT_INSTRUCTIONS_FILE.as_posix(),
                "detail": "local startup instructions differ from the managed local-only payload",
            }
        )
    else:
        if not dry_run:
            local_path.unlink()
        actions.append(
            {
                "kind": "would remove" if dry_run else "removed",
                "path": LOCAL_AGENT_INSTRUCTIONS_FILE.as_posix(),
                "detail": "remove managed local startup instructions",
            }
        )

    reference_path = repo_root / LOCAL_AGENT_REFERENCE_FILE
    if not reference_path.exists():
        actions.append(
            {
                "kind": "skipped",
                "path": LOCAL_AGENT_REFERENCE_FILE.as_posix(),
                "detail": "root startup reference already absent",
            }
        )
    else:
        existing_reference = reference_path.read_text(encoding="utf-8")
        updated_reference, changed = _remove_local_agent_reference_text(existing_reference)
        if changed:
            if not dry_run:
                reference_path.write_text(updated_reference, encoding="utf-8")
            actions.append(
                {
                    "kind": "would update" if dry_run else "updated",
                    "path": LOCAL_AGENT_REFERENCE_FILE.as_posix(),
                    "detail": "remove tiny local startup reference",
                }
            )
        else:
            actions.append(
                {
                    "kind": "skipped",
                    "path": LOCAL_AGENT_REFERENCE_FILE.as_posix(),
                    "detail": "root startup reference was not present",
                }
            )
    return actions


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
        "detail": "record local-only package-owned state inside the workspace tree",
    }


def _ensure_local_scratch(*, target_root: Path, dry_run: bool) -> dict[str, str]:
    scratch_path = target_root / WORKSPACE_LOCAL_SCRATCH_ROOT_PATH
    if scratch_path.is_dir():
        return {
            "kind": "current",
            "path": WORKSPACE_LOCAL_SCRATCH_ROOT_PATH.as_posix(),
            "detail": "local scratch space ready for temporary agent working files",
        }
    if not dry_run:
        scratch_path.mkdir(parents=True, exist_ok=True)
    return {
        "kind": "would create" if dry_run else "created",
        "path": WORKSPACE_LOCAL_SCRATCH_ROOT_PATH.as_posix(),
        "detail": "create gitignored local scratch space for temporary agent working files",
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


def _managed_workspace_config_header(*, cli_invoke: str) -> str:
    return "\n".join(
        [
            "# Agentic Workspace managed config.",
            "# Edit this file directly only when changing repo-owned policy.",
            f"# Reference: {WORKSPACE_CONFIG_CONTRACT_DOC}",
            f"# Check resolved config: {cli_invoke} config --target . --profile tiny --format json",
        ]
    )


def _seeded_workspace_config_text(*, config: WorkspaceConfig, resolved_preset: str | None) -> str:
    default_preset = resolved_preset or config.default_preset
    lines = [
        _managed_workspace_config_header(cli_invoke=config.cli_invoke),
        "",
        "schema_version = 1",
        "",
        "[workspace]",
        f"default_preset = {json.dumps(default_preset)}",
        f"agent_instructions_file = {json.dumps(config.agent_instructions_file)}",
        f"workflow_artifact_profile = {json.dumps(config.workflow_artifact_profile)}",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _seed_workspace_config_action(
    *,
    target_root: Path,
    resolved_preset: str | None,
    dry_run: bool,
    command_name: str,
    local_only_repo_root: Path | None,
    config: WorkspaceConfig,
) -> dict[str, str] | None:
    if command_name != "init" or local_only_repo_root is not None:
        return None
    config_path = target_root / WORKSPACE_CONFIG_PATH
    if config_path.exists():
        return {
            "kind": "current",
            "path": WORKSPACE_CONFIG_PATH.as_posix(),
            "detail": "workspace config already present; preserved repo-owned policy",
        }
    if not dry_run:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(_seeded_workspace_config_text(config=config, resolved_preset=resolved_preset), encoding="utf-8")
    return {
        "kind": "would create" if dry_run else "created",
        "path": WORKSPACE_CONFIG_PATH.as_posix(),
        "detail": "seed schema-valid workspace config with managed config header and repo-local reference",
    }


def _workspace_init_or_upgrade_report(
    *,
    target_root: Path,
    local_only_repo_root: Path | None,
    selected_modules: list[str],
    resolved_preset: str | None,
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

    config_action = _seed_workspace_config_action(
        target_root=target_root,
        resolved_preset=resolved_preset,
        dry_run=dry_run,
        command_name=command_name,
        local_only_repo_root=local_only_repo_root,
        config=config,
    )
    if config_action is not None:
        actions.append(config_action)

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
    if local_only_repo_root is not None:
        actions.extend(
            _sync_local_agent_startup(
                repo_root=local_only_repo_root,
                dry_run=dry_run,
                replace_reference_file=inspection_mode == "install",
            )
        )
    elif inspection_mode == "install":
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
    if local_only_repo_root is not None:
        actions.append(
            {
                "kind": "skipped",
                "path": WORKSPACE_EXTERNAL_AGENT_PATH.as_posix(),
                "detail": "local-only startup uses AGENTS.local.md and does not create a root external-agent handoff",
            }
        )
    elif existing_handoff == handoff_text:
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

    actions.append(_ensure_local_scratch(target_root=target_root, dry_run=dry_run))

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
    removable_candidates: list[Path] = []
    ambiguous_payloads: list[Path] = []

    for relative in WORKSPACE_PAYLOAD_FILES:
        destination = target_root / relative
        if not destination.exists():
            actions.append({"kind": "skipped", "path": destination.as_posix(), "detail": "already absent"})
            continue
        if destination.read_bytes() == _workspace_payload_bytes(relative):
            removable_candidates.append(relative)
            continue
        ambiguous_payloads.append(relative)
        actions.append(
            {
                "kind": "manual review",
                "path": relative.as_posix(),
                "detail": "local workspace shared-layer file differs from managed payload; remove manually if intended",
            }
        )

    if ambiguous_payloads:
        for relative in removable_candidates:
            actions.append(
                {
                    "kind": "skipped",
                    "path": relative.as_posix(),
                    "detail": "blocked by ambiguous workspace shared-layer ownership; review before destructive uninstall",
                }
            )
        removable: list[Path] = []
    else:
        removable = list(removable_candidates)
        for relative in removable:
            actions.append(
                {
                    "kind": "would remove" if dry_run else "removed",
                    "path": relative.as_posix(),
                    "detail": "matches managed workspace payload content",
                }
            )

    if not dry_run:
        for relative in removable:
            destination = target_root / relative
            if destination.exists():
                destination.unlink()
        _prune_empty_parent_dirs(target_root=target_root, relatives=removable)
        if local_only_repo_root is not None:
            actions.append(_remove_local_only_state(target_root=target_root, dry_run=dry_run))
            local_workspace_root = target_root / ".agentic-workspace"
            if local_workspace_root.exists():
                shutil.rmtree(local_workspace_root)
    if local_only_repo_root is not None:
        if dry_run and target_root.exists():
            actions.append(
                {
                    "kind": "would remove",
                    "path": ".agentic-workspace",
                    "detail": "remove the local-only workspace tree",
                }
            )
        actions.extend(_remove_local_agent_startup(repo_root=local_only_repo_root, dry_run=dry_run))
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
    presets: dict[str, list[str]] = {}
    profile_entries = _MODULE_PROFILE_ENTRIES or tuple(
        {
            "id": module_name,
            "preset": module_name,
            "selected_modules": [module_name],
        }
        for module_name in ordered_module_names
    )
    for profile in profile_entries:
        preset = profile.get("preset")
        if not isinstance(preset, str) or not preset:
            continue
        selected = [str(module_name) for module_name in profile.get("selected_modules", []) if str(module_name) in descriptors]
        presets[preset] = [module_name for module_name in ordered_module_names if module_name in selected]
    for module_name in ordered_module_names:
        presets.setdefault(module_name, [module_name])
    presets.setdefault("full", [module_name for module_name in ordered_module_names if descriptors[module_name].include_in_full_preset])
    return presets


def _feature_tier_payload(
    *,
    selected_modules: list[str],
    installed_modules: list[str] | None = None,
    resolved_preset: str | None = None,
    config: WorkspaceConfig | None = None,
    compact: bool = False,
) -> dict[str, Any]:
    active_modules = installed_modules if installed_modules is not None else selected_modules
    active_set = set(active_modules)
    active_source = "installed_modules" if installed_modules is not None else "selected_modules"
    active_profile = next(
        (
            profile
            for profile in _MODULE_PROFILE_ENTRIES
            if bool(profile.get("default_active", True)) and set(profile.get("selected_modules", [])) == active_set
        ),
        None,
    )
    if active_profile is None:
        active_profile = {
            "id": "custom",
            "label": "Custom",
            "selected_modules": list(active_modules),
            "preset": resolved_preset,
            "default_active": True,
            "activation": "Custom module selection; inspect selected_modules for the exact footprint.",
            "cost_model": "depends on selected modules.",
            "profile_kind": "module-selection",
            "selection_rule": "explicit selected module ids",
        }
    active = {
        "id": str(active_profile.get("id", "")),
        "label": str(active_profile.get("label", active_profile.get("id", ""))),
        "modules": list(active_modules),
        "preset": active_profile.get("preset") or resolved_preset,
        "activation": str(active_profile.get("activation", "")),
        "source": active_source,
    }
    cli_invoke = config.cli_invoke if config is not None else DEFAULT_CLI_INVOKE
    payload: dict[str, Any] = {
        "schema_version": "workspace-feature-tiers/v1",
        "compatibility_status": "deprecated-alias-for-module-profiles",
        "canonical_surface": f"{cli_invoke} modules --target ./repo --format json -> module_profiles",
        "active": active,
        "default_rule": "Use the smallest module profile whose selected modules match the repo footprint; source-checkout maintainer tooling is not a shipped tier.",
        "detail_command": f"{cli_invoke} modules --target ./repo --format json",
    }
    if compact:
        payload["advanced_features_enabled_count"] = len(config.advanced_features) if config is not None else 0
        return payload
    payload["advanced_policy"] = _advanced_feature_policy_payload(config=config, include_catalog=True)
    payload["available_tiers"] = [
        {
            "id": str(profile["id"]),
            "label": str(profile["label"]),
            "modules": list(profile.get("selected_modules", [])),
            "preset": profile.get("preset"),
            "default_active": bool(profile.get("default_active", True)),
            "activation": str(profile.get("activation", "")),
            "cost_model": str(profile.get("cost_model", "")),
        }
        for profile in _MODULE_PROFILE_ENTRIES
    ]
    payload["available_module_profiles"] = copy.deepcopy(list(_MODULE_PROFILE_ENTRIES))
    return payload


def _advanced_feature_policy_payload(*, config: WorkspaceConfig | None, include_catalog: bool = False) -> dict[str, Any]:
    enabled = list(config.advanced_features) if config is not None else []
    cli_invoke = config.cli_invoke if config is not None else DEFAULT_CLI_INVOKE
    payload: dict[str, Any] = {
        "schema_version": "workspace-advanced-feature-policy/v1",
        "enabled_features": enabled,
        "enabled_source": config.advanced_features_source if config is not None else "product-default",
        "default_rule": "Advanced host-repo diagnostics are opt-in; source-checkout-only maintainer tooling is not a shipped feature tier.",
        "ordinary_startup_rule": "Use start, summary, report, defaults, and proof first; inspect advanced review or external-adapter diagnostics only by selector or explicit enabled feature.",
        "config_field": "workspace.advanced_features",
        "detail_command": f"{cli_invoke} modules --target ./repo --format json",
    }
    if include_catalog:
        payload["available_features"] = [
            {
                "id": str(item.get("id", "")),
                "label": str(item.get("label", item.get("id", ""))),
                "tier": str(item.get("tier", "reusable-diagnostics")),
                "default_enabled": bool(item.get("default_enabled", False)),
                "activation": str(item.get("activation", "")),
                "default_surface_policy": str(item.get("default_surface_policy", "")),
                "selector_hint": str(item.get("selector_hint", "")),
            }
            for item in _ADVANCED_FEATURE_ENTRIES
        ]
    return payload


def _context_router_family_payload(*, cli_invoke: str = DEFAULT_CLI_INVOKE, compact: bool = False) -> dict[str, Any]:
    views = [
        {
            "view": "start",
            "command": _command_with_cli_invoke(
                command="agentic-workspace start --target ./repo --profile tiny --format json", cli_invoke=cli_invoke
            ),
            "use_when": "repo entry",
        },
        {
            "view": "summary",
            "command": _command_with_cli_invoke(command="agentic-workspace summary --format json", cli_invoke=cli_invoke),
            "use_when": "active work or handoff",
        },
        {
            "view": "report",
            "command": _command_with_cli_invoke(command="agentic-workspace report --target ./repo --format json", cli_invoke=cli_invoke),
            "use_when": "diagnostics or sections",
        },
        {
            "view": "defaults",
            "command": _command_with_cli_invoke(
                command="agentic-workspace defaults --section <section> --format json", cli_invoke=cli_invoke
            ),
            "use_when": "policy or defaults",
        },
        {
            "view": "preflight",
            "command": _command_with_cli_invoke(command="agentic-workspace preflight --format json", cli_invoke=cli_invoke),
            "use_when": "takeover or recovery",
        },
    ]
    payload: dict[str, Any] = {
        "kind": "workspace-context-router-family/v1",
        "rule": "Use the smallest view that answers the question.",
        "first_view": "start",
        "views": views,
    }
    if not compact:
        payload["non_goal"] = "Do not add a new command layer or require agents to run every view."
    return payload


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
            resolved_preset=resolved_preset,
            descriptors=descriptors,
            dry_run=dry_run,
            inspection_mode=inspection.mode,
            command_name="init",
            config=config,
        )
    )
    effective_config = config
    if not dry_run:
        effective_config = config_lib.load_workspace_config(
            target_root=target_root,
            valid_presets=set(_preset_modules(descriptors)),
        )
    summary = _build_init_summary(
        target_root=target_root,
        selected_modules=selected_modules,
        resolved_preset=resolved_preset,
        descriptors=descriptors,
        inspection=inspection,
        reports=reports,
        config=effective_config,
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
        "config": _config_payload(config=effective_config),
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


_WORKSPACE_ABSENCE_PATTERNS = (
    re.compile(r"\bdoes\s+not\s+use\s+agentic\s+workspace\b", re.IGNORECASE),
    re.compile(r"\bno\s+agentic\s+workspace\b", re.IGNORECASE),
    re.compile(r"\bagentic\s+workspace\s+is\s+not\s+(?:installed|used|enabled)\b", re.IGNORECASE),
)


def _detect_workspace_absence_contradictions(*, target_root: Path, surfaces: list[str]) -> list[str]:
    contradictions: list[str] = []
    for surface in surfaces:
        path = target_root / surface
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        repo_owned_text = _without_workspace_workflow_fence(text)
        if any(pattern.search(repo_owned_text) for pattern in _WORKSPACE_ABSENCE_PATTERNS):
            contradictions.append(
                f"{Path(surface).as_posix()}: preserved repo-owned instructions claim Agentic Workspace is absent; reconcile or remove stale absence wording"
            )
    return contradictions


def _workspace_absence_startup_review(*, target_root: Path, config: WorkspaceConfig) -> dict[str, Any]:
    contradictions = _detect_workspace_absence_contradictions(
        target_root=target_root,
        surfaces=[config.agent_instructions_file, *config.detected_agent_instructions_files],
    )
    if not contradictions:
        return {"status": "clean", "items": []}
    items: list[dict[str, str]] = []
    for contradiction in contradictions:
        path, _, detail = contradiction.partition(": ")
        items.append(
            {
                "path": path,
                "issue": detail or contradiction,
                "action": "reconcile stale no-workspace wording in repo-owned instructions after Agentic Workspace adoption",
            }
        )
    return {
        "status": "attention",
        "items": items,
        "rule": "Resolve contradictory no-workspace wording before relying on startup instructions.",
    }


def _without_workspace_workflow_fence(text: str) -> str:
    return re.sub(
        rf"{re.escape(WORKSPACE_WORKFLOW_MARKER_START)}.*?{re.escape(WORKSPACE_WORKFLOW_MARKER_END)}",
        "",
        text,
        flags=re.DOTALL,
    )


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
    needs_review.extend(
        _detect_workspace_absence_contradictions(
            target_root=target_root,
            surfaces=[config.agent_instructions_file, *config.detected_agent_instructions_files],
        )
    )
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
    compact_status: bool = True,
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
                resolved_preset=resolved_preset,
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
    summary = _summarise_reports(
        target_root=target_root,
        reports=reports,
        descriptors=descriptors,
        command_name=command_name,
    )
    warnings: list[str] = []
    placeholders: list[str] = []
    stale_generated_surfaces: list[str] = []
    warnings.extend(summary["warnings"])
    placeholders.extend(summary["placeholders"])
    stale_generated_surfaces.extend(summary["stale_generated_surfaces"])
    cli_compatibility = _cli_compatibility_payload(config=config, compact=True)
    cli_compatibility_warnings = _cli_compatibility_warning_messages(cli_compatibility)
    warnings.extend(cli_compatibility_warnings)

    payload: dict[str, Any] = {
        "command": command_name,
        "target": target_root.as_posix(),
        "invoked_cli_identity": _invoked_cli_identity_payload(target_root=target_root, compact=True),
        "cli_compatibility": cli_compatibility,
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
        "next_steps": _lifecycle_next_steps(
            command_name=command_name,
            target_root=target_root,
            warnings=warnings,
            cli_invoke=config.cli_invoke,
        ),
        "reports": reports,
        "config": _config_payload(config=config),
    }
    if cli_compatibility_warnings:
        payload["executable_drift_warnings"] = cli_compatibility_warnings
    payload["lifecycle_plan"] = _lifecycle_plan_payload(
        payload=payload,
        command_name=command_name,
        target_root=target_root,
        selected_modules=selected_modules,
        dry_run=dry_run,
        local_only=local_only_repo_root is not None,
        cli_invoke=config.cli_invoke,
    )
    if command_name in {"status", "doctor"}:
        repair_actions, manual_review_actions = _aggregate_repair_actions_from_reports(
            reports,
            target_root=target_root,
            cli_invoke=config.cli_invoke,
            command_name=command_name,
        )
        if command_name == "doctor":
            cli_review_action = _cli_compatibility_manual_review_action(
                target_root=target_root,
                cli_invoke=config.cli_invoke,
                cli_compatibility=cli_compatibility,
            )
            if cli_review_action is not None:
                manual_review_actions.insert(0, cli_review_action)
            if repair_actions or manual_review_actions:
                payload["health"] = "attention-needed"
        payload["repair_actions"] = repair_actions
        payload["manual_review_actions"] = manual_review_actions
        payload["repair_plan"] = _repair_plan_payload(
            command_name=command_name,
            repair_actions=repair_actions,
            manual_review_actions=manual_review_actions,
        )
        if compact_status and command_name in {"status", "doctor"}:
            payload = _compact_status_payload(payload, cli_invoke=config.cli_invoke)
    return payload


def _compact_status_payload(payload: dict[str, Any], *, cli_invoke: str) -> dict[str, Any]:
    reports = payload.get("reports", [])
    compact_reports = []
    if isinstance(reports, list):
        for report in reports:
            if not isinstance(report, dict):
                continue
            actions = report.get("actions", [])
            warnings = report.get("warnings", [])
            compact_actions = []
            if isinstance(actions, list):
                for action in actions[:3]:
                    if isinstance(action, dict):
                        compact_actions.append(
                            {
                                key: action.get(key)
                                for key in ("kind", "path", "detail", "category", "remediation_kind")
                                if action.get(key) not in (None, "")
                            }
                        )
            compact_reports.append(
                {
                    "module": report.get("module", ""),
                    "message": report.get("message", ""),
                    "action_count": len(actions) if isinstance(actions, list) else 0,
                    "actions": compact_actions,
                    "warning_count": len(warnings) if isinstance(warnings, list) else 0,
                    "warnings": warnings[:3] if isinstance(warnings, list) else [],
                    "detail_section": "reports",
                }
            )
    config_payload = payload.get("config", {})
    compact_config = {}
    if isinstance(config_payload, dict):
        workspace = config_payload.get("workspace", {})
        compact_workspace = {}
        if isinstance(workspace, dict):
            compact_workspace = {
                key: workspace.get(key)
                for key in (
                    "default_preset",
                    "agent_instructions_file",
                    "workflow_artifact_profile",
                    "improvement_latitude",
                    "optimization_bias",
                    "cli_invoke",
                )
            }
        compact_config = {
            "config_path": config_payload.get("config_path"),
            "exists": config_payload.get("exists"),
            "warnings": config_payload.get("warnings", []),
            "workspace": compact_workspace,
            "detail_command": _command_with_cli_invoke(
                command="agentic-workspace config --target ./repo --profile tiny --format json", cli_invoke=cli_invoke
            ),
        }
    registry = payload.get("registry", [])
    compact_registry = []
    if isinstance(registry, list):
        compact_registry = [
            {"name": entry.get("name", ""), "installed": entry.get("installed", False)} for entry in registry if isinstance(entry, dict)
        ]
    payload = dict(payload)
    payload["reports"] = compact_reports
    payload["config"] = compact_config
    payload["registry"] = compact_registry
    for key in ("warnings", "needs_review", "repair_actions", "manual_review_actions"):
        values = payload.get(key, [])
        if isinstance(values, list):
            payload[f"{key}_count"] = len(values)
            payload[key] = values[:5]
    payload["lifecycle_plan"] = {
        "status": (
            payload.get("lifecycle_plan", {}).get("status", "available") if isinstance(payload.get("lifecycle_plan"), dict) else "available"
        ),
        "detail_command": _command_with_cli_invoke(
            command=f"agentic-workspace {payload.get('command', 'status')} --target ./repo --format json", cli_invoke=cli_invoke
        ),
    }
    payload["deeper_detail"] = {
        "config_command": _command_with_cli_invoke(
            command="agentic-workspace config --target ./repo --profile tiny --format json", cli_invoke=cli_invoke
        ),
        "report_command": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --profile full --format json", cli_invoke=cli_invoke
        ),
    }
    payload["cost_provenance"] = {
        "classification": "compact-after-lifecycle",
        "module_count": len(compact_reports),
        "source": "workspace lifecycle invokes selected module lifecycle reports before compact projection",
        "detail_command": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section operational_compression --format json",
            cli_invoke=cli_invoke,
        ),
    }
    command_name = str(payload.get("command", "status") or "status")
    if str(payload.get("health", "")) == "healthy":
        payload["next_action"] = {
            "action": "no-immediate-action",
            "summary": "No immediate lifecycle action is required.",
            "commands": [],
        }
    else:
        detail_command = _command_with_cli_invoke(
            command=f"agentic-workspace {command_name} --target ./repo --profile full --format json",
            cli_invoke=cli_invoke,
        )
        if command_name == "status":
            inspect_command = _command_with_cli_invoke(
                command="agentic-workspace doctor --target ./repo --format json",
                cli_invoke=cli_invoke,
            )
            action = "inspect-health-with-doctor"
            summary = "Inspect attention-needed lifecycle state with the compact doctor route."
            commands = [inspect_command]
        else:
            action = "inspect-repair-or-full-detail"
            summary = "Review compact repair and manual-review actions; use full detail only when the compact lists are insufficient."
            commands = [detail_command]
        payload["next_action"] = {
            "action": action,
            "summary": summary,
            "command": commands[0],
            "run": commands[0],
            "commands": commands,
            "detail_command": detail_command,
        }
    return payload


def _cli_compatibility_warning_messages(cli_compatibility: dict[str, Any]) -> list[str]:
    status = str(cli_compatibility.get("status", ""))
    if status not in {"advisory-drift", "blocking-drift"}:
        return []
    failed = ", ".join(str(item) for item in cli_compatibility.get("failed_checks", [])) or "unknown"
    remediation = cli_compatibility.get("remediation", {})
    summary = remediation.get("summary") if isinstance(remediation, dict) else ""
    if not summary:
        summary = "Invoked CLI does not satisfy the repo-owned compatibility expectation."
    return [f"executable compatibility {status}: failed checks: {failed}; {summary}"]


def _cli_compatibility_manual_review_action(
    *,
    target_root: Path,
    cli_invoke: str,
    cli_compatibility: dict[str, Any],
) -> dict[str, Any] | None:
    status = str(cli_compatibility.get("status", ""))
    if status not in {"advisory-drift", "blocking-drift"}:
        return None
    remediation = cli_compatibility.get("remediation", {})
    remediation_summary = (
        str(remediation.get("summary", "")) if isinstance(remediation, dict) else "Invoked CLI compatibility drift detected."
    )
    remediation_command = str(remediation.get("command", cli_invoke)) if isinstance(remediation, dict) else cli_invoke
    severity = "error" if status == "blocking-drift" else "warning"
    action = _workspace_manual_review_action(
        id="resolve-cli-executable-drift",
        invariant="workspace.cli_executable_compatible",
        fault_class="package_affordance_fault",
        owner="repo",
        target_root=target_root,
        cli_invoke=cli_invoke,
        affected_surfaces=[".agentic-workspace/config.toml", "invoked_cli_identity"],
        current_fault_summary=remediation_summary,
        risk="lifecycle output may validate the payload known to the invoked executable while still using the wrong CLI for this repo",
        do_not=[
            "Do not treat module payload freshness as proof that the invoked executable matches repo expectations.",
            "Do not ignore blocking executable drift before trusting lifecycle output.",
        ],
    )
    action["severity"] = severity
    action["action"] = str(remediation.get("action", "manual-review")) if isinstance(remediation, dict) else "manual-review"
    action["command"] = remediation_command
    action["run"] = remediation_command
    action["cli_compatibility"] = {
        "status": status,
        "failed_checks": list(cli_compatibility.get("failed_checks", [])),
        "drift_findings": list(cli_compatibility.get("drift_findings", [])),
        "payload_drift_separate": True,
    }
    return action


def _aggregate_repair_actions_from_reports(
    reports: list[dict[str, Any]],
    *,
    target_root: Path,
    cli_invoke: str,
    command_name: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    repair_actions: list[dict[str, Any]] = []
    manual_review_actions: list[dict[str, Any]] = []
    for report in reports:
        for action in report.get("repair_actions", []):
            if isinstance(action, dict):
                repair_actions.append(action)
        for action in report.get("manual_review_actions", []):
            if isinstance(action, dict):
                manual_review_actions.append(action)
        if command_name == "doctor":
            module_repair = _module_safe_lifecycle_repair_action(
                report=report,
                target_root=target_root,
                cli_invoke=cli_invoke,
            )
            if module_repair is not None:
                repair_actions.append(module_repair)
    return repair_actions, manual_review_actions


def _module_safe_lifecycle_repair_action(
    *,
    report: dict[str, Any],
    target_root: Path,
    cli_invoke: str,
) -> dict[str, Any] | None:
    module = str(report.get("module", "")).strip()
    if not module or module == "workspace":
        return None
    safe_planned_kinds = {"would create", "would copy", "would update", "would overwrite", "would replace"}
    affected_surfaces: list[str] = []
    for action in report.get("actions", []):
        if not isinstance(action, dict):
            continue
        kind = str(action.get("kind", ""))
        if kind not in safe_planned_kinds:
            continue
        if str(action.get("safety", "")) != "safe" and str(action.get("category", "")) != "safe-update":
            continue
        _append_unique(affected_surfaces, _display_path(action.get("path", "."), target_root))
    if not affected_surfaces:
        return None
    target = target_root.as_posix()
    dry_run = _command_with_cli_invoke(
        command=f"agentic-workspace upgrade --target {target} --module {module} --dry-run --format json",
        cli_invoke=cli_invoke,
    )
    command = _command_with_cli_invoke(
        command=f"agentic-workspace upgrade --target {target} --module {module} --format json",
        cli_invoke=cli_invoke,
    )
    proof_after = [
        _command_with_cli_invoke(
            command=f"agentic-workspace doctor --target {target} --module {module} --format json",
            cli_invoke=cli_invoke,
        )
    ]
    return {
        "id": f"apply-safe-{module}-lifecycle-repair",
        "action": "run-module-upgrade",
        "invariant": f"{module}.managed_surfaces_current",
        "fault_class": "agent_operation_fault",
        "severity": "warning",
        "owner": module,
        "safe_to_apply": True,
        "risk": "low; applies safe module-managed lifecycle changes reported by doctor",
        "command": command,
        "run": command,
        "dry_run": dry_run,
        "proof_after": proof_after,
        "affected_surfaces": affected_surfaces,
        "current_fault_summary": f"{module} doctor found safe module-managed lifecycle changes that are not applied.",
        "do_not": [
            "Do not hand-author module-managed payload files when module upgrade can recreate them.",
            "Do not treat safe module payload repairs as proof that unrelated repo-owned content may be overwritten.",
        ],
        "recurrence": "first_seen",
        "improvement_signal_candidate": {
            "when": "repeated",
            "kind": "repair_recurrence",
            "route": "agentic-workspace defaults --section improvement_intake --format json",
            "preferred_remedy": "make safe module repair availability visible from the root lifecycle surface",
        },
    }


def _lifecycle_plan_payload(
    *,
    payload: dict[str, Any],
    command_name: str,
    target_root: Path,
    selected_modules: list[str],
    dry_run: bool,
    local_only: bool,
    cli_invoke: str = DEFAULT_CLI_INVOKE,
) -> dict[str, Any]:
    planned_removals: list[str] = []
    for report in payload.get("module_reports", []) + payload.get("reports", []):
        if not isinstance(report, dict):
            continue
        for action in report.get("actions", []):
            if not isinstance(action, dict):
                continue
            if str(action.get("kind", "")) in {"would remove", "removed"}:
                _append_unique(planned_removals, _display_path(action.get("path", "."), target_root))
    warnings = list(payload.get("warnings", []))
    review_items = list(payload.get("needs_review", [])) + list(payload.get("placeholders", []))
    review_required = bool(review_items or warnings or payload.get("prompt_requirement") in {"required", "recommended"})
    config_payload = payload.get("config", {})
    update_payload = config_payload.get("update", {}) if isinstance(config_payload, dict) else {}
    module_policy_payloads = update_payload.get("modules", []) if isinstance(update_payload, dict) else []
    module_update_freshness = [
        {
            "module": str(module.get("module", "")),
            "freshness": module.get("freshness", {}),
        }
        for module in module_policy_payloads
        if isinstance(module, dict) and str(module.get("module", "")) in set(selected_modules)
    ]
    next_command = _lifecycle_apply_command(
        command_name=command_name,
        target_root=target_root,
        selected_modules=selected_modules,
        local_only=local_only,
        cli_invoke=cli_invoke,
    )
    review_command = _lifecycle_apply_command(
        command_name=command_name,
        target_root=target_root,
        selected_modules=selected_modules,
        local_only=local_only,
        cli_invoke=cli_invoke,
        dry_run=True,
    )
    primary_action_command = (
        review_command
        if review_required
        else next_command
        if dry_run
        else _command_with_cli_invoke(
            command=f"agentic-workspace doctor --target {target_root.as_posix()} --format json", cli_invoke=cli_invoke
        )
    )
    next_status = "review-required" if review_required else "ready"
    next_reason = "Resolve review_items before applying changes." if review_required else "Dry-run plan has no review blockers."
    plan = {
        "kind": "workspace-lifecycle-plan/v1",
        "command": command_name,
        "target_root": target_root.as_posix(),
        "selected_modules": selected_modules,
        "dry_run": dry_run,
        "planned_creates": list(payload.get("created", [])),
        "planned_updates": list(payload.get("updated_managed", [])),
        "planned_removals": planned_removals,
        "preserved_files": list(payload.get("preserved_existing", [])),
        "warnings": warnings,
        "review_required": review_required,
        "review_items": review_items,
        "local_only_state_interaction": "install-root" if local_only else "not-requested",
        "module_update_freshness": module_update_freshness,
        "mutation_safety": _lifecycle_mutation_safety_payload(
            command_name=command_name,
            dry_run=dry_run,
            local_only=local_only,
            review_required=review_required,
            planned_removals=planned_removals,
        ),
        "surface_classifications": _lifecycle_surface_classifications_payload(
            payload=payload,
            command_name=command_name,
            target_root=target_root,
            dry_run=dry_run,
            review_required=review_required,
            planned_removals=planned_removals,
        ),
        "primary_next_action": {
            "action": "resolve-lifecycle-review" if review_required else ("apply-lifecycle-plan" if dry_run else "verify-lifecycle-state"),
            "command": primary_action_command,
            "run": primary_action_command,
            "risk": (
                "blocked until review items are resolved"
                if review_required
                else ("may mutate repo-managed workspace surfaces" if dry_run else "read-only verification recommended after mutation")
            ),
            "required_inputs": ["target repo", "selected modules", "review items"]
            if review_required
            else ["target repo", "selected modules", "dry-run plan"],
            "next_proof": (
                "rerun the lifecycle dry-run after resolving review items"
                if review_required
                else "run doctor after apply and inspect surface classifications"
            ),
        },
        "next_safe_command": {
            "status": next_status,
            "command": review_command if review_required else next_command,
            "reason": next_reason,
        },
    }
    if command_name == "upgrade":
        plan["root_upgrade_front_door"] = _root_upgrade_front_door_payload(
            target_root=target_root,
            selected_modules=selected_modules,
            dry_run=dry_run,
            next_command=next_command,
            review_required=review_required,
            cli_invoke=cli_invoke,
        )
    return plan


def _lifecycle_surface_classifications_payload(
    *,
    payload: dict[str, Any],
    command_name: str,
    target_root: Path,
    dry_run: bool,
    review_required: bool,
    planned_removals: list[str],
) -> dict[str, Any]:
    if command_name not in {"install", "init", "adopt", "upgrade", "uninstall"}:
        return {
            "kind": "workspace-lifecycle-surface-classifications/v1",
            "rule": "Classifications explain lifecycle mutation output; read-only commands keep this detail behind mutation paths.",
            "entries": [],
            "summary_by_class": {},
            "detail_hint": "Use lifecycle mutation commands with --format json for surface classifications.",
        }
    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def add_entry(
        *,
        path: str,
        module: str,
        action: str,
        reason_class: str,
        reason: str,
        source: str,
        ownership: str | None = None,
        review_required_for_surface: bool | None = None,
    ) -> None:
        if not path:
            return
        key = (path, action, reason_class)
        if key in seen:
            return
        seen.add(key)
        entries.append(
            {
                "path": path,
                "module": module,
                "action": action,
                "reason_class": reason_class,
                "ownership": ownership or _lifecycle_ownership_for_reason(reason_class),
                "reason": reason,
                "dry_run": dry_run,
                "review_required": review_required if review_required_for_surface is None else review_required_for_surface,
                "source": source,
            }
        )

    for report in payload.get("reports", []) + payload.get("module_reports", []):
        if not isinstance(report, dict):
            continue
        module = str(report.get("module", "workspace"))
        for action in report.get("actions", []):
            if not isinstance(action, dict):
                continue
            path = _display_path(action.get("path", "."), target_root)
            action_kind = str(action.get("kind", ""))
            detail = str(action.get("detail", ""))
            reason_class, reason = _classify_lifecycle_action(
                path=path,
                action_kind=action_kind,
                detail=detail,
                command_name=command_name,
                review_required=review_required,
            )
            add_entry(
                path=path,
                module=module,
                action=action_kind,
                reason_class=reason_class,
                reason=reason,
                source="module-report",
                review_required_for_surface=reason_class in {"ambiguous ownership manual-review", "refused destructive action"},
            )
        for warning in report.get("warnings", []):
            if not isinstance(warning, dict):
                continue
            path = _display_path(warning.get("path", "."), target_root)
            message = str(warning.get("message", "needs review"))
            reason_class, reason = _classify_lifecycle_action(
                path=path,
                action_kind="warning",
                detail=message,
                command_name=command_name,
                review_required=review_required,
            )
            add_entry(
                path=path,
                module=module,
                action="warning",
                reason_class=reason_class,
                reason=reason,
                source="module-warning",
                review_required_for_surface=reason_class == "ambiguous ownership manual-review",
            )

    for path in payload.get("preserved_existing", []):
        add_entry(
            path=str(path),
            module="workspace",
            action="preserved",
            reason_class="repo-owned preserved",
            reason="Existing repo-owned surface was preserved rather than overwritten.",
            source="summary",
            review_required_for_surface=False,
        )
    for item in payload.get("needs_review", []):
        path, _, detail = str(item).partition(": ")
        reason_class = "ambiguous ownership manual-review"
        if "legacy" in detail.lower():
            reason_class = "legacy unsupported; migration/refusal required"
        add_entry(
            path=path,
            module="workspace",
            action="manual review",
            reason_class=reason_class,
            reason=detail or "Manual review is required before applying this lifecycle change.",
            source="summary",
            review_required_for_surface=True,
        )

    for path in _local_only_surfaces(target_root=target_root):
        add_entry(
            path=path,
            module="workspace",
            action="preserved",
            reason_class="local-only preserved",
            reason="Repo-local private state is preserved unless --local-only explicitly targets it.",
            source="local-only-scan",
            review_required_for_surface=False,
        )

    for path in _unsupported_legacy_surfaces(target_root=target_root):
        add_entry(
            path=path,
            module="workspace",
            action="manual review",
            reason_class="legacy unsupported; migration/refusal required",
            reason="Unsupported legacy compatibility surface requires manual migration or deletion.",
            source="legacy-unsupported-scan",
            review_required_for_surface=True,
        )

    if command_name == "uninstall" and review_required:
        for path in planned_removals:
            add_entry(
                path=path,
                module="workspace",
                action="refused",
                reason_class="refused destructive action",
                reason="Destructive removal requires ownership review before apply.",
                source="destructive-safety",
                review_required_for_surface=True,
            )

    summary_by_class: dict[str, int] = {}
    for entry in entries:
        reason_class = str(entry["reason_class"])
        summary_by_class[reason_class] = summary_by_class.get(reason_class, 0) + 1
    return {
        "kind": "workspace-lifecycle-surface-classifications/v1",
        "rule": "Classifications explain lifecycle output; they do not grant mutation permission.",
        "entries": entries,
        "summary_by_class": dict(sorted(summary_by_class.items())),
        "detail_hint": "Use --format json for full surface classifications; text output stays compact.",
    }


def _classify_lifecycle_action(*, path: str, action_kind: str, detail: str, command_name: str, review_required: bool) -> tuple[str, str]:
    detail_l = detail.lower()
    path_l = path.lower()
    if action_kind == "skipped":
        return "repo-owned preserved", detail or "Existing repo-owned surface was preserved."
    if action_kind in {"manual review", "missing"}:
        if "legacy" in detail_l:
            return "legacy unsupported; migration/refusal required", detail or "Legacy surface requires migration or refusal."
        return "ambiguous ownership manual-review", detail or "Manual review is required before applying this change."
    if action_kind in {"warning", "suggested fix"}:
        if path in {"TODO.md", "ROADMAP.md"} or "legacy" in detail_l or "compatibility" in detail_l:
            return (
                "legacy unsupported; migration/refusal required",
                detail or "Legacy compatibility surface requires manual migration or deletion.",
            )
        return "ambiguous ownership manual-review", detail or "Warning requires review."
    if action_kind in {"would remove", "removed"}:
        if command_name == "uninstall" and review_required:
            return "refused destructive action", detail or "Destructive action requires review."
        return "product-managed replaced", detail or "Managed lifecycle payload was removed."
    if action_kind in {"would update", "updated", "overwritten", "would overwrite", "would replace", "replaced"}:
        if "optional" in detail_l:
            return "optional enabled", detail or "Optional managed surface is enabled or refreshed."
        if path_l.startswith(".agentic-workspace/") or path in {"AGENTS.md", "llms.txt"}:
            return "core refreshed", detail or "Core managed lifecycle surface is refreshed."
        return "product-managed replaced", detail or "Product-managed surface is replaced."
    if action_kind in {"created", "copied", "would create", "would copy"}:
        if "optional" in detail_l:
            return "optional enabled", detail or "Optional managed surface is enabled."
        return "core refreshed", detail or "Core managed lifecycle surface is created or refreshed."
    if "generated" in detail_l or path_l.startswith("tools/"):
        return "generated/dev-only ignored", detail or "Generated or dev-only surface is informational."
    return "core refreshed", detail or "Lifecycle action is managed by the selected module."


def _lifecycle_ownership_for_reason(reason_class: str) -> str:
    if reason_class.startswith("repo-owned"):
        return "repo-owned"
    if reason_class.startswith("local-only"):
        return "local-only"
    if reason_class.startswith("optional"):
        return "optional"
    if reason_class.startswith("generated"):
        return "generated/dev-only"
    if reason_class.startswith("ambiguous"):
        return "ambiguous"
    if reason_class.startswith("refused"):
        return "refused"
    if reason_class.startswith("legacy"):
        return "legacy"
    return "product-managed"


def _local_only_surfaces(*, target_root: Path) -> list[str]:
    local_root = target_root / ".agentic-workspace" / "local"
    if not local_root.exists():
        return []
    paths: list[str] = []
    for path in sorted(local_root.rglob("*")):
        if path.is_file():
            paths.append(path.relative_to(target_root).as_posix())
    return paths


def _unsupported_legacy_surfaces(*, target_root: Path) -> list[str]:
    paths: list[str] = []
    for relative in (Path("TODO.md"), Path("ROADMAP.md")):
        path = target_root / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "GENERATED COMPATIBILITY VIEW" in text or "authoritative source is .agentic-workspace/planning/state.toml" in text:
            paths.append(relative.as_posix())
    return paths


def _root_upgrade_front_door_payload(
    *,
    target_root: Path,
    selected_modules: list[str],
    dry_run: bool,
    next_command: str,
    review_required: bool,
    cli_invoke: str = DEFAULT_CLI_INVOKE,
) -> dict[str, Any]:
    target = target_root.as_posix()
    module_args: list[str] = []
    for module_name in selected_modules:
        module_args.extend(["--module", module_name])
    dry_run_command = _command_with_cli_invoke(
        command=" ".join(["agentic-workspace", "upgrade", "--target", target, *module_args, "--dry-run", "--format", "json"]),
        cli_invoke=cli_invoke,
    )
    apply_command = next_command
    return {
        "kind": "workspace-root-upgrade-front-door/v1",
        "status": "authoritative-host-repo-path",
        "selected_modules": selected_modules,
        "ordinary_sequence": [
            {
                "step": "inspect",
                "command": dry_run_command,
                "safe": True,
                "reason": "Dry-run is the first host-repo update step and reports selected modules, planned changes, review items, and the next safe command.",
            },
            {
                "step": "apply",
                "command": apply_command,
                "safe": not review_required,
                "reason": "Apply only after review_items are resolved when review is required.",
            },
            {
                "step": "verify",
                "command": _command_with_cli_invoke(
                    command=f"agentic-workspace doctor --target {target} --format json", cli_invoke=cli_invoke
                ),
                "safe": True,
                "reason": "Doctor verifies the host repo after lifecycle changes settle.",
            },
        ],
        "package_specific_upgrade_role": "fallback-debug-only",
        "fallback_rule": (
            "Use module package CLIs only for package-local debugging or when root agentic-workspace upgrade cannot run; "
            "host-repo guidance should route through the root command first."
        ),
        "dry_run_first": True,
        "review_required_before_apply": review_required,
    }


def _lifecycle_fixture_matrix_payload() -> list[dict[str, Any]]:
    return [
        {
            "state": "empty repo",
            "commands": ["init", "install"],
            "expected_result": "install-direct",
            "proof": "tests/test_workspace_cli.py::test_root_lifecycle_fixture_matrix_classifies_entry_states",
        },
        {
            "state": "routing-only installed",
            "commands": ["init", "adopt"],
            "expected_result": "preserve-existing-and-adopt",
            "proof": "tests/test_workspace_cli.py::test_root_lifecycle_fixture_matrix_classifies_entry_states",
        },
        {
            "state": "memory-only installed",
            "commands": ["upgrade", "status", "doctor"],
            "expected_result": "memory module selected from install signals",
            "proof": "tests/test_workspace_cli.py::test_root_lifecycle_fixture_matrix_covers_upgrade_shapes",
        },
        {
            "state": "planning-only installed",
            "commands": ["upgrade", "status", "doctor"],
            "expected_result": "planning module selected from install signals",
            "proof": "tests/test_workspace_cli.py::test_root_lifecycle_fixture_matrix_covers_upgrade_shapes",
        },
        {
            "state": "full installed",
            "commands": ["upgrade", "status", "doctor"],
            "expected_result": "planning and memory modules selected from install signals",
            "proof": "tests/test_workspace_cli.py::test_root_lifecycle_fixture_matrix_covers_upgrade_shapes",
        },
        {
            "state": "old current-memory residue",
            "commands": ["status", "doctor"],
            "expected_result": "classified as current-memory review instead of default startup input",
            "proof": "tests/test_workspace_cli.py::test_root_lifecycle_fixture_matrix_classifies_legacy_residue",
        },
        {
            "state": "old optional planning surfaces",
            "commands": ["status", "doctor"],
            "expected_result": "classified as unsupported legacy surfaces with migration/refusal guidance",
            "proof": "tests/test_workspace_cli.py::test_root_lifecycle_fixture_matrix_classifies_legacy_residue",
        },
        {
            "state": "custom AGENTS.md",
            "commands": ["init", "upgrade"],
            "expected_result": "repo-owned prose preserved outside managed workspace fence",
            "proof": "tests/test_workspace_cli.py::test_upgrade_preserves_repo_owned_agents_content_outside_workspace_fence",
        },
        {
            "state": "partial managed state",
            "commands": ["init", "upgrade", "doctor"],
            "expected_result": "manual review or recovery action instead of silent overwrite",
            "proof": "tests/test_workspace_cli.py::test_root_lifecycle_fixture_matrix_classifies_entry_states",
        },
        {
            "state": "local-only state",
            "commands": ["install", "upgrade", "uninstall"],
            "expected_result": "local-only state preserved unless explicitly targeted",
            "proof": "tests/test_workspace_cli.py::test_upgrade_apply_preserves_local_only_memory_and_integration_state",
        },
        {
            "state": "ambiguous ownership state",
            "commands": ["uninstall"],
            "expected_result": "review required before destructive removal",
            "proof": "tests/test_workspace_cli.py::test_uninstall_dry_run_requires_review_for_ambiguous_workspace_payload",
        },
    ]


def _lifecycle_mutation_safety_payload(
    *,
    command_name: str,
    dry_run: bool,
    local_only: bool,
    review_required: bool,
    planned_removals: list[str],
) -> dict[str, Any]:
    mutation_commands = {"install", "init", "adopt", "upgrade", "uninstall"}
    destructive_commands = {"uninstall"}
    is_mutation = command_name in mutation_commands
    is_destructive = command_name in destructive_commands
    classification = "read-only"
    if is_destructive:
        classification = "destructive-mutation"
    elif is_mutation:
        classification = "lifecycle-mutation"
    return {
        "kind": "workspace-lifecycle-mutation-safety/v1",
        "classification": classification,
        "hand_owned_runtime": is_mutation,
        "dry_run_apply_separation": {
            "status": "dry-run-only" if dry_run and is_mutation else "apply-or-read-only",
            "dry_run": dry_run,
            "rule": "Dry-run output is a plan; apply remains a separate lifecycle invocation through hand-owned runtime primitives.",
        },
        "review_required_before_apply": bool(is_mutation and (dry_run or review_required or is_destructive)),
        "strict_preflight": {
            "available": command_name in HIGH_RISK_COMMANDS,
            "required_when_enabled": command_name in HIGH_RISK_COMMANDS,
            "hint": "Run preflight first and pass a fresh token when using --strict-preflight for high-risk mutation.",
        },
        "destructive_risk": {
            "status": "present" if is_destructive else "not-destructive",
            "planned_removal_count": len(planned_removals),
            "planned_removals": planned_removals,
            "rule": "Destructive lifecycle paths require ownership review before deletion.",
        },
        "local_only_preservation": {
            "status": "explicit-local-only-target" if local_only else "preserve-by-default",
            "rule": "Repo-local private memory and integration aids are preserved unless --local-only explicitly targets the local-only workspace tree.",
        },
        "fixture_coverage": [
            {
                "scenario": "upgrade dry-run on installed repo",
                "status": "covered",
                "proof": "tests/test_workspace_cli.py::test_upgrade_json_collects_summary_categories",
            },
            {
                "scenario": "ambiguous ownership uninstall refuses deletion",
                "status": "covered",
                "proof": "tests/test_workspace_cli.py::test_uninstall_dry_run_requires_review_for_ambiguous_workspace_payload",
            },
            {
                "scenario": "local-only memory/integration preservation",
                "status": "covered",
                "proof": "tests/test_workspace_cli.py::test_upgrade_apply_preserves_local_only_memory_and_integration_state",
            },
            {
                "scenario": "second-run lifecycle idempotency",
                "status": "covered",
                "proof": "tests/test_workspace_cli.py::test_install_real_init_creates_combined_memory_and_planning_surfaces",
            },
            {
                "scenario": "strict preflight blocks high-risk mutation",
                "status": "covered",
                "proof": "tests/test_workspace_cli.py::test_upgrade_strict_preflight_requires_token",
            },
        ],
        "fixture_matrix": _lifecycle_fixture_matrix_payload(),
    }


def _lifecycle_apply_command(
    *,
    command_name: str,
    target_root: Path,
    selected_modules: list[str],
    local_only: bool,
    cli_invoke: str = DEFAULT_CLI_INVOKE,
    dry_run: bool = False,
) -> str:
    parts = ["agentic-workspace", command_name, "--target", target_root.as_posix()]
    for module_name in selected_modules:
        parts.extend(["--module", module_name])
    if local_only:
        parts.append("--local-only")
    if dry_run:
        parts.append("--dry-run")
    parts.extend(["--format", "json"])
    return str(_command_with_cli_invoke(command=" ".join(parts), cli_invoke=cli_invoke))


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
        compact_status=False,
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
        incidental_finding_policy=copy.deepcopy(_IMPROVEMENT_LATITUDE_POLICY["incidental_finding_policy"]),
        validation_friction_policy=_validation_friction_payload(),
        cli_invoke=config.cli_invoke,
    )
    repo_friction["capture_shortcut"] = _friction_capture_shortcut_payload()
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
    durable_intent = _intent_decision_projection(target_root=target_root, config=config, compact=True)
    branch_workflow_posture = _branch_workflow_posture_payload(target_root=target_root)
    local_memory = _local_memory_payload(config=config)
    closeout_trust = _report_closeout_trust_payload(
        module_reports=module_reports,
        target_root=target_root,
        config=config,
        cli_invoke=config.cli_invoke,
    )
    surface_value_guardrail = _surface_value_guardrail_payload()
    external_work_delta = _external_work_delta_payload(target_root=target_root)
    external_work_reconciliation = _external_work_reconciliation_payload(
        module_reports=module_reports,
        external_work_delta=external_work_delta,
        cli_invoke=config.cli_invoke,
    )
    ownership_payload = _ownership_payload(target_root=target_root, descriptors=descriptors)
    payload = {
        "kind": "workspace-report/v1",
        "schema": _reporting_schema_payload(),
        "command": "report",
        "target": target_root.as_posix(),
        "invoked_cli_identity": _invoked_cli_identity_payload(target_root=target_root),
        "cli_compatibility": _cli_compatibility_payload(config=config),
        "selected_modules": selected_modules,
        "installed_modules": installed_modules,
        "feature_tier": _feature_tier_payload(
            selected_modules=selected_modules,
            installed_modules=installed_modules,
            resolved_preset=resolved_preset,
            config=config,
        ),
        "health": status_payload["health"],
        "report_profile": _report_profile_payload(cli_invoke=config.cli_invoke),
        "output_contract": output_contract_payload(
            optimization_bias=config.optimization_bias,
            optimization_bias_source=config.optimization_bias_source,
            bias_payload=_optimization_bias_payload(config.optimization_bias),
            surface="report",
        ),
        "operating_posture": _operating_posture_payload(config=config, surface="report"),
        "config_enforcement": _config_enforcement_payload(config=config),
        "config_effect_audit": _config_effect_audit_payload(config=config),
        "branch_workflow_posture": branch_workflow_posture,
        "local_memory": local_memory,
        "memory_consult": _memory_consult_payload(target_root=target_root, cli_invoke=config.cli_invoke),
        "agent_aids": _agent_aids_report_payload(target_root=target_root, cli_invoke=config.cli_invoke),
        "execution_shape": execution_shape,
        "durable_intent": durable_intent,
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
        "product_managed_enclave": _product_managed_enclave_payload(
            target_root=target_root,
            ownership_payload=ownership_payload,
        ),
        "ownership_diagnostics": ownership_payload["diagnostics"],
        "surface_value_guardrail": surface_value_guardrail,
        "effective_authority": _effective_authority_payload(
            target_root=target_root,
            config=config,
            installed_modules=installed_modules,
            module_reports=module_reports,
        ),
        "findings": aggregated_findings,
        "closeout_trust": closeout_trust,
        "external_work_reconciliation": external_work_reconciliation,
        "external_work_delta": external_work_delta,
        "next_action": next_action,
        "discovery": discovery,
        "standing_intent": standing_intent,
        "improvement_intake": _improvement_intake_payload(target_root=target_root, config=config, repo_friction=repo_friction),
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
    payload["maintenance_pressure"] = _maintenance_pressure_payload(
        report_payload=payload,
        module_reports=module_reports,
        findings=aggregated_findings,
    )
    return payload


def _run_report_router_command(
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
        compact_status=True,
    )
    warnings = list(status_payload.get("warnings", []))
    findings = [
        {
            "severity": "warning",
            "module": "workspace",
            "message": str(warning),
        }
        for warning in warnings
    ]
    installed_modules = [
        str(entry["name"])
        for entry in status_payload.get("registry", [])
        if isinstance(entry, dict) and entry.get("installed") and entry.get("name")
    ] or _fast_installed_modules(target_root=target_root)
    external_work_delta = _external_work_delta_payload(target_root=target_root)
    next_command = _command_with_cli_invoke(
        command="agentic-workspace doctor --target ./repo --format json",
        cli_invoke=config.cli_invoke,
    )
    if str(status_payload.get("health", "unknown")) == "healthy":
        next_action = {"summary": "No immediate action", "commands": []}
    else:
        next_action = {
            "summary": "Inspect the reported warnings with the compact doctor route.",
            "commands": [next_command],
            "command": next_command,
            "run": next_command,
        }
    router_source = {
        "kind": "workspace-report/v1",
        "schema": _reporting_schema_payload(),
        "command": "report",
        "target": target_root.as_posix(),
        "selected_modules": selected_modules,
        "installed_modules": installed_modules,
        "feature_tier": _feature_tier_payload(
            selected_modules=selected_modules,
            installed_modules=installed_modules,
            resolved_preset=resolved_preset,
            config=config,
        ),
        "health": status_payload.get("health", "unknown"),
        "output_contract": output_contract_payload(
            optimization_bias=config.optimization_bias,
            optimization_bias_source=config.optimization_bias_source,
            bias_payload=_optimization_bias_payload(config.optimization_bias),
            surface="report",
        ),
        "operating_posture": _operating_posture_payload(config=config, surface="report"),
        "report_profile": _report_profile_payload(cli_invoke=config.cli_invoke),
        "config_enforcement": _config_enforcement_payload(config=config),
        "config_effect_audit": _config_effect_audit_payload(config=config),
        "memory_consult": _tiny_memory_consult_payload(config=config),
        "execution_shape": _report_router_execution_shape_fast(config=config),
        "durable_intent": _intent_decision_projection(target_root=target_root, config=config, compact=True),
        "effective_authority": _effective_authority_payload(
            target_root=target_root,
            config=config,
            installed_modules=installed_modules,
            module_reports=[],
        ),
        "improvement_intake": _improvement_intake_payload(target_root=target_root, config=config, repo_friction=None),
        "external_work_reconciliation": _external_work_reconciliation_payload(
            module_reports=[],
            external_work_delta=external_work_delta,
            cli_invoke=config.cli_invoke,
        ),
        "surface_value_guardrail": _surface_value_guardrail_payload(),
        "next_action": next_action,
        "findings": findings,
        "module_reports": [],
        "reports": [],
        "config": {"workspace": {"cli_invoke": config.cli_invoke}},
    }
    return _report_router_payload(router_source)


def _report_router_execution_shape_fast(*, config: WorkspaceConfig) -> dict[str, Any]:
    return {
        "status": "present",
        "task_shape": {
            "id": "direct-or-no-active-plan",
            "summary": "No active planning record is present; direct work can proceed when the task is narrow and proof is obvious.",
            "why": "The default report router does not load deep planning reports; run the execution_shape section for active-plan detail.",
        },
        "task_shape_recommender": {
            "status": "available",
            "rule": "Choose the cheapest workflow shape that preserves proof and continuation honesty.",
            "shapes": [
                {"id": "direct"},
                {"id": "light-plan"},
                {"id": "checked-in-execplan"},
            ],
        },
        "narrow_work_fast_path": {
            "status": "blessed",
            "one_compact_check": _command_with_cli_invoke(
                command="agentic-workspace config --target ./repo --profile tiny --format json",
                cli_invoke=config.cli_invoke,
            ),
            "rule": "For narrow work, use the smallest compact route that answers state, config, or proof uncertainty.",
            "promote_when": [
                "work claims lane progress",
                "proof is unclear",
                "continuation or handoff would be expensive without checked-in state",
            ],
        },
        "recommendation": {
            "id": "stay-direct",
            "summary": "Stay direct unless the task needs active sequencing, handoff, or non-obvious proof.",
            "consult": [
                _command_with_cli_invoke(
                    command="agentic-workspace config --target ./repo --profile tiny --format json",
                    cli_invoke=config.cli_invoke,
                )
            ],
        },
        "deviation_rule": "Do not implement roadmap or autopilot lanes from router context alone; promote active planning first.",
    }


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
    artifact_footprint = _artifact_footprint_by_class(target=report_payload.get("target"))
    generated_footprint = _generated_output_footprint(target=report_payload.get("target"))
    archive_retention = _archive_retention_policy(
        archived_distillation=archived_distillation,
        artifact_footprint=artifact_footprint,
    )
    closeout_trust = report_payload.get("closeout_trust", {})
    closeout_trust = closeout_trust if isinstance(closeout_trust, dict) else {}
    historical_reviews = closeout_trust.get("historical_review_artifacts", {})
    historical_reviews = historical_reviews if isinstance(historical_reviews, dict) else {}
    review_retention = historical_reviews.get("retention_policy", {})
    review_retention = review_retention if isinstance(review_retention, dict) else {}
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
        "artifact_footprint_by_class": artifact_footprint,
        "generated_output_footprint": generated_footprint,
        "archive_retention_policy": archive_retention,
        "review_retention_policy": review_retention,
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
    if artifact_footprint.get("recommended_cleanup_target"):
        advisory_signals.append(
            {
                "severity": "advisory",
                "measure": "artifact_footprint_by_class",
                "message": "Artifact footprint pressure is present; inspect the recommended cleanup target before expanding residue.",
                "count": artifact_footprint.get("pressure_class_count", 0),
            }
        )
    if generated_footprint.get("status") == "attention":
        advisory_signals.append(
            {
                "severity": "advisory",
                "measure": "generated_output_footprint",
                "message": "Generated-output footprint has unclassified or stale candidates; inspect before expanding generated residue.",
                "count": generated_footprint.get("unclassified_generated_output_count", 0),
            }
        )
    if archive_retention.get("status") == "attention":
        advisory_signals.append(
            {
                "severity": "advisory",
                "measure": "archive_retention_policy",
                "message": "Archived execplan retention pressure is present; review candidates before expanding archive residue.",
                "count": archive_retention.get("candidate_count", 0),
            }
        )
    if review_retention.get("status") == "attention":
        advisory_signals.append(
            {
                "severity": "advisory",
                "measure": "review_retention_policy",
                "message": "Review artifact retention pressure is present; inspect candidates before expanding review residue.",
                "count": review_retention.get("candidate_count", 0),
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


def _sibling_cli_command_with_invoke(*, command: str, workspace_cli_invoke: str, sibling_program: str) -> str:
    if not command.startswith(sibling_program):
        return command
    if workspace_cli_invoke == DEFAULT_CLI_INVOKE:
        return command
    parts = workspace_cli_invoke.split()
    if parts and parts[-1] == DEFAULT_CLI_INVOKE:
        return " ".join([*parts[:-1], sibling_program]) + command.removeprefix(sibling_program)
    return command


def _memory_command_with_invoke(*, command: str, workspace_cli_invoke: str) -> str:
    return _sibling_cli_command_with_invoke(
        command=command,
        workspace_cli_invoke=workspace_cli_invoke,
        sibling_program="agentic-memory",
    )


def _memory_payload_commands_with_invoke(*, value: Any, workspace_cli_invoke: str) -> Any:
    if isinstance(value, str):
        return _memory_command_with_invoke(command=value, workspace_cli_invoke=workspace_cli_invoke)
    if isinstance(value, list):
        return [_memory_payload_commands_with_invoke(value=item, workspace_cli_invoke=workspace_cli_invoke) for item in value]
    if isinstance(value, dict):
        return {
            key: _memory_payload_commands_with_invoke(value=nested, workspace_cli_invoke=workspace_cli_invoke)
            for key, nested in value.items()
        }
    return value


def _memory_consult_payload(
    *,
    target_root: Path,
    changed_paths: list[str] | None = None,
    compact: bool = False,
    cli_invoke: str = DEFAULT_CLI_INVOKE,
) -> dict[str, Any]:
    try:
        from repo_memory_bootstrap.installer import memory_report, route_memory
    except ImportError:
        return {
            "kind": "agentic-workspace/memory-consult/v1",
            "status": "unavailable",
            "reason": "memory module is not importable",
            "read_first": [],
            "max_notes": 0,
            "do_not_bulk_read": True,
        }

    try:
        report = memory_report(target=target_root)
    except Exception as exc:  # pragma: no cover - defensive routing surface
        return {
            "kind": "agentic-workspace/memory-consult/v1",
            "status": "unavailable",
            "reason": f"memory report failed: {exc}",
            "read_first": [],
            "max_notes": 0,
            "do_not_bulk_read": True,
        }

    report_payload: dict[str, Any] = cast(dict[str, Any], report) if isinstance(report, dict) else {}
    habitual_raw = report_payload.get("habitual_pull", {})
    habitual_pull: dict[str, Any] = cast(dict[str, Any], habitual_raw) if isinstance(habitual_raw, dict) else {}
    bundle_raw = habitual_pull.get("ordinary_work_bundle", {})
    bundle: dict[str, Any] = cast(dict[str, Any], bundle_raw) if isinstance(bundle_raw, dict) else {}
    always_load = _list_payload(bundle.get("always_load"))
    read_first = [str(path) for path in always_load]
    route_actions: list[dict[str, Any]] = []
    normalized_paths = _normalize_changed_paths(changed_paths or [])
    if normalized_paths:
        try:
            route_result = route_memory(target=target_root, files=normalized_paths)
            for action in route_result.actions:
                if action.role != "memory-route" or action.kind not in {"required", "optional"}:
                    continue
                source = action.source or action.path.as_posix()
                if source not in read_first:
                    read_first.append(source)
                route_actions.append(
                    {
                        "kind": action.kind,
                        "path": source,
                        "reason": action.detail,
                        "match_source": action.match_source,
                    }
                )
        except Exception:
            route_actions = []

    max_notes = int(bundle.get("working_set_target", 3) or 3)
    if max_notes > 0:
        read_first = read_first[:max_notes]
    evidence = habitual_pull.get("evidence", {})
    status = str(habitual_pull.get("status", "unavailable"))
    consult_status = (
        "recommended" if read_first and status in {"ready-for-ordinary-work", "attention-needed", "needs-more-proof"} else "not-recommended"
    )
    promotion_pressure = report_payload.get("promotion_pressure", {})
    payload = {
        "kind": "agentic-workspace/memory-consult/v1",
        "status": consult_status,
        "source": "memory.habitual_pull",
        "why": habitual_pull.get("summary", ""),
        "read_first": read_first,
        "max_notes": max_notes,
        "do_not_bulk_read": True,
        "selection_rule": bundle.get("route_rule", ""),
        "changed_path_route_count": len(route_actions),
        "route_matches": route_actions[:max_notes],
        "evidence": evidence if isinstance(evidence, dict) else {},
        "capture_helper": _memory_command_with_invoke(
            command="agentic-memory capture-note <slug> --target ./repo --summary <text> --files <changed paths> --format json",
            workspace_cli_invoke=cli_invoke,
        ),
        "promotion_pressure": _memory_payload_commands_with_invoke(value=promotion_pressure, workspace_cli_invoke=cli_invoke),
    }
    if compact:
        if consult_status != "recommended":
            return {
                "kind": payload["kind"],
                "status": consult_status,
                "do_not_bulk_read": True,
            }
        keys = ("kind", "status", "read_first", "max_notes", "do_not_bulk_read")
        keys = (*keys, "why", "selection_rule")
        return {key: payload[key] for key in keys if key in payload}
    return payload


def _maintenance_pressure_payload(
    *,
    report_payload: dict[str, Any],
    module_reports: list[dict[str, Any]],
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    planning_report = next(
        (report for report in module_reports if isinstance(report, dict) and report.get("module") == "planning"),
        {},
    )
    planning_report = planning_report if isinstance(planning_report, dict) else {}
    closeout_trust = report_payload.get("closeout_trust", {})
    closeout_trust = closeout_trust if isinstance(closeout_trust, dict) else {}
    external_work_delta = report_payload.get("external_work_delta", {})
    external_work_delta = external_work_delta if isinstance(external_work_delta, dict) else {}
    operational_compression = report_payload.get("operational_compression", {})
    operational_compression = operational_compression if isinstance(operational_compression, dict) else {}
    operational_measures = operational_compression.get("measures", {})
    operational_measures = operational_measures if isinstance(operational_measures, dict) else {}

    intent_validation = planning_report.get("intent_validation", {}) if isinstance(planning_report, dict) else {}
    intent_counts = intent_validation.get("counts", {}) if isinstance(intent_validation, dict) else {}
    finished_work = planning_report.get("finished_work_inspection", {}) if isinstance(planning_report, dict) else {}
    finished_counts = finished_work.get("counts", {}) if isinstance(finished_work, dict) else {}
    historical_reviews = closeout_trust.get("historical_review_artifacts", {})
    historical_reviews = historical_reviews if isinstance(historical_reviews, dict) else {}
    archived_distillation = operational_measures.get("archived_plan_distillation", {})
    archived_distillation = archived_distillation if isinstance(archived_distillation, dict) else {}
    adapter_lifecycle = operational_measures.get("adapter_surface_lifecycle", {})
    adapter_lifecycle = adapter_lifecycle if isinstance(adapter_lifecycle, dict) else {}
    closeout_check = closeout_trust.get("intent_satisfaction_check", {})
    closeout_check = closeout_check if isinstance(closeout_check, dict) else {}

    def _category(
        *,
        category_id: str,
        status: str,
        count: int,
        summary: str,
        detail_section: str,
        selector_hint: str,
    ) -> dict[str, Any]:
        return {
            "id": category_id,
            "status": status,
            "count": count,
            "summary": summary,
            "detail_section": detail_section,
            "section_command": f"agentic-workspace report --target ./repo --section {detail_section} --format json",
            "selector_hint": selector_hint,
        }

    warning_count = len(findings)
    historical_attention_count = _as_int(finished_counts.get("attention_count")) + _as_int(intent_counts.get("closeout_needs_audit_count"))
    archive_only_residue_count = _as_int(finished_counts.get("archive_only_durable_residue_count"))
    review_item_count = _as_int(historical_reviews.get("item_count"))
    review_retention = historical_reviews.get("retention_policy", {})
    review_retention = review_retention if isinstance(review_retention, dict) else {}
    review_retention_count = _as_int(review_retention.get("candidate_count"))
    archive_missing_count = _as_int(archived_distillation.get("post_contract_missing_distillation_count"))
    adapter_missing_count = _as_int(adapter_lifecycle.get("missing_removal_path_count"))
    external_changed_count = _as_int(external_work_delta.get("changed_count")) + _as_int(external_work_delta.get("closed_count"))
    lower_trust_count = _as_int(closeout_trust.get("lower_trust_closeout_count"))
    followup_required = str(closeout_check.get("trust", "")) == "follow-up-required"

    subcategories = [
        _category(
            category_id="current_state_stale",
            status="attention" if warning_count else "quiet",
            count=warning_count,
            summary="Current report findings are present." if warning_count else "No current report findings are present.",
            detail_section="findings",
            selector_hint="Inspect only when warning_summary or this category is attention.",
        ),
        _category(
            category_id="historical_audit",
            status="attention" if historical_attention_count else "backgrounded",
            count=historical_attention_count,
            summary=(
                "Historical audit or finished-work inspection has attention signals."
                if historical_attention_count
                else "Historical audit detail is backgrounded behind planning module selectors."
            ),
            detail_section="module_reports",
            selector_hint="Use full profile or module reports only for audit work.",
        ),
        _category(
            category_id="archive_only_residue",
            status="attention" if archive_only_residue_count else "quiet",
            count=archive_only_residue_count,
            summary=(
                "Archived closeout residue needs routing to Memory, docs, contracts, checks, or planning."
                if archive_only_residue_count
                else "No archive-only durable residue signals are present."
            ),
            detail_section="module_reports",
            selector_hint="Route residue to a stronger owner instead of reading more archive history.",
        ),
        _category(
            category_id="review_retention",
            status="attention" if review_retention_count else ("evidence-only" if review_item_count else "quiet"),
            count=review_retention_count or review_item_count,
            summary=(
                "Review artifact retention has advisory cleanup candidates."
                if review_retention_count
                else "Historical review artifacts are evidence/history, not ordinary operating input."
            ),
            detail_section="closeout_trust",
            selector_hint="Inspect when a selected issue or audit path asks for review history.",
        ),
        _category(
            category_id="archive_retention",
            status="attention" if archive_missing_count else "measured",
            count=archive_missing_count,
            summary=(
                "Some post-contract archived execplans lack closeout distillation."
                if archive_missing_count
                else "Archive-retention pressure is measured in operational compression detail."
            ),
            detail_section="operational_compression",
            selector_hint="Inspect for archive footprint or retention cleanup work.",
        ),
        _category(
            category_id="generated_output_footprint",
            status="attention" if adapter_missing_count else "measured",
            count=adapter_missing_count,
            summary=(
                "Some adapter/generated surfaces lack removal-path metadata."
                if adapter_missing_count
                else "Generated and adapter surface footprint is measured as detail."
            ),
            detail_section="operational_compression",
            selector_hint="Inspect before expanding generated or adapter surfaces.",
        ),
        _category(
            category_id="external_evidence_stale",
            status="attention" if external_changed_count else str(external_work_delta.get("status", "unavailable")),
            count=external_changed_count,
            summary=(
                "External-work evidence changed since the previous snapshot."
                if external_changed_count
                else "External-work evidence is a routed snapshot/detail signal."
            ),
            detail_section="external_work_delta",
            selector_hint="Inspect when external issue intake, closure, or refresh state matters.",
        ),
        _category(
            category_id="closeout_reconciliation",
            status="attention" if lower_trust_count or followup_required else "quiet",
            count=lower_trust_count + (1 if followup_required else 0),
            summary=(
                "Closeout reconciliation needs attention before treating broad work as closed."
                if lower_trust_count or followup_required
                else "No lower-trust closeout reconciliation signals are present."
            ),
            detail_section="closeout_trust",
            selector_hint="Inspect before broad-work closeout or package-use trust review.",
        ),
    ]
    active = [item for item in subcategories if item["status"] in {"attention", "evidence-only"}]
    attention_count = sum(1 for item in subcategories if item["status"] == "attention")
    if attention_count:
        status = "attention"
        recommended_next_action = (
            "Continue current execution first; inspect maintenance-pressure detail only when the active lane needs residue cleanup."
        )
    elif active:
        status = "evidence-only"
        recommended_next_action = "Treat maintenance residue as background evidence unless the current task selects it."
    else:
        status = "quiet"
        recommended_next_action = "No maintenance-pressure detail is needed for ordinary work."
    return {
        "kind": "workspace-maintenance-pressure/v1",
        "status": status,
        "rule": "One compact router for audit, retention, footprint, external-evidence, and closeout residue; current execution pressure stays separate.",
        "current_execution_separate": True,
        "attention_category_count": attention_count,
        "active_category_count": len(active),
        "subcategories": subcategories,
        "detail_sections": sorted({str(item["detail_section"]) for item in subcategories}),
        "recommended_next_action": recommended_next_action,
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


def _archive_retention_policy(*, archived_distillation: dict[str, Any], artifact_footprint: dict[str, Any]) -> dict[str, Any]:
    archived_count = _as_int(archived_distillation.get("archived_plan_count"))
    legacy_missing = _as_int(archived_distillation.get("legacy_missing_distillation_count"))
    post_contract_missing = _as_int(archived_distillation.get("post_contract_missing_distillation_count"))
    footprint_classes = _list_payload(artifact_footprint.get("classes"))
    archived_footprint = next(
        (item for item in footprint_classes if isinstance(item, dict) and item.get("id") == "archived_execplans"),
        {},
    )
    footprint_pressure = str(archived_footprint.get("pressure", "quiet")) if isinstance(archived_footprint, dict) else "quiet"
    sample_missing = _list_payload(archived_distillation.get("sample_missing_distillation"))
    sample_post_contract = _list_payload(archived_distillation.get("sample_post_contract_missing_distillation"))

    candidates: list[dict[str, Any]] = []
    if post_contract_missing:
        candidates.append(
            {
                "signal": "post-contract-missing-distillation",
                "count": post_contract_missing,
                "recommended_outcome": "promote-summary-elsewhere",
                "candidate_paths": sample_post_contract[:5],
                "why": "Recent archives without closeout distillation should first route durable learning to Memory, docs, contracts, checks, or issues.",
            }
        )
    if legacy_missing:
        candidates.append(
            {
                "signal": "legacy-missing-distillation",
                "count": legacy_missing,
                "recommended_outcome": "stub",
                "candidate_paths": sample_missing[:5],
                "why": "Legacy archives without distillation are candidates for retain-or-stub review after durable facts are promoted elsewhere.",
            }
        )
    if footprint_pressure == "attention":
        candidates.append(
            {
                "signal": "archive-footprint-threshold",
                "count": archived_count,
                "recommended_outcome": "shrink",
                "candidate_paths": _list_payload(archived_footprint.get("sample"))[:5] if isinstance(archived_footprint, dict) else [],
                "why": "Archive count is high enough to merit selector-driven review before adding more residue.",
            }
        )

    return {
        "kind": "workspace-archive-retention-policy/v1",
        "status": "attention" if candidates else "quiet",
        "advisory_only": True,
        "applies_to": ".agentic-workspace/planning/execplans/archive/*.plan.json",
        "outcomes": [
            "retain",
            "shrink",
            "stub",
            "delete",
            "promote-summary-elsewhere",
        ],
        "default_outcome": "retain",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "before_shrink_or_delete": [
            "promote durable learning to Memory, docs, contracts, checks, or issues",
            "preserve enough evidence for restart, review, trust, and continuation",
            "keep ordinary startup and active planning out of archive history",
        ],
        "rule": "Retention pressure is advisory and selector-driven; it recommends review outcomes but never deletes archived evidence automatically.",
    }


def _artifact_footprint_by_class(*, target: Any) -> dict[str, Any]:
    target_text = str(target or "").strip()
    if not target_text:
        return {
            "status": "unavailable",
            "classes": [],
            "pressure_class_count": 0,
            "recommended_cleanup_target": {},
            "rule": "Footprint classes are advisory and selector-driven; they do not delete artifacts.",
        }
    target_root = Path(target_text)

    def _count_files(relative: str, pattern: str = "*") -> tuple[int, list[str]]:
        root = target_root / relative
        if not root.exists():
            return 0, []
        files = sorted(path for path in root.rglob(pattern) if path.is_file())
        return len(files), [_relative_posix(path, target_root) for path in files[:5]]

    def _top_level_plan_count() -> tuple[int, list[str]]:
        root = target_root / ".agentic-workspace" / "planning" / "execplans"
        if not root.exists():
            return 0, []
        files = sorted(path for path in root.glob("*.plan.json") if path.is_file() and path.name not in {"TEMPLATE.plan.json"})
        return len(files), [_relative_posix(path, target_root) for path in files[:5]]

    def _durable_memory_notes() -> tuple[int, list[str]]:
        root = target_root / ".agentic-workspace" / "memory" / "repo"
        if not root.exists():
            return 0, []
        files = sorted(
            path
            for path in root.rglob("*.md")
            if path.is_file() and ".agentic-workspace/memory/repo/current/" not in _relative_posix(path, target_root)
        )
        return len(files), [_relative_posix(path, target_root) for path in files[:5]]

    def _large_docs() -> tuple[int, list[str]]:
        candidates = [path for path in [target_root / "README.md", target_root / "AGENTS.md", target_root / "llms.txt"] if path.is_file()]
        docs_root = target_root / "docs"
        if docs_root.exists():
            candidates.extend(path for path in docs_root.rglob("*.md") if path.is_file())
        large: list[Path] = []
        for path in sorted(candidates):
            try:
                line_count = len(path.read_text(encoding="utf-8").splitlines())
            except OSError:
                continue
            if line_count > 400:
                large.append(path)
        return len(large), [_relative_posix(path, target_root) for path in large[:5]]

    active_count, active_sample = _top_level_plan_count()
    archive_count, archive_sample = _count_files(".agentic-workspace/planning/execplans/archive", "*.plan.json")
    planning_review_count, planning_review_sample = _count_files(".agentic-workspace/planning/reviews", "*.review.json")
    docs_review_count, docs_review_sample = _count_files("docs/reviews")
    current_memory_count, current_memory_sample = _count_files(".agentic-workspace/memory/repo/current")
    durable_memory_count, durable_memory_sample = _durable_memory_notes()
    generated_files = _generated_output_files(target_root=target_root)
    generated_count = len(generated_files)
    generated_sample = [_relative_posix(path, target_root) for path in generated_files[:5]]
    local_count, local_sample = _count_files(".agentic-workspace/local")
    large_docs_count, large_docs_sample = _large_docs()

    classes = [
        _artifact_class(
            class_id="active_execplans",
            role="live operating state",
            count=active_count,
            sample=active_sample,
            pressure="attention" if active_count > 1 else "quiet",
            review_target=active_sample[0] if active_count > 1 and active_sample else "",
        ),
        _artifact_class(
            class_id="archived_execplans",
            role="historical evidence",
            count=archive_count,
            sample=archive_sample,
            pressure="attention" if archive_count > 100 else "measured",
            review_target=".agentic-workspace/planning/execplans/archive/" if archive_count > 100 else "",
        ),
        _artifact_class(
            class_id="review_artifacts",
            role="historical evidence",
            count=planning_review_count + docs_review_count,
            sample=(planning_review_sample + docs_review_sample)[:5],
            pressure="attention" if planning_review_count + docs_review_count else "quiet",
            review_target=(planning_review_sample + docs_review_sample)[0] if planning_review_count + docs_review_count else "",
        ),
        _artifact_class(
            class_id="current_memory_notes",
            role="legacy or optional calibration",
            count=current_memory_count,
            sample=current_memory_sample,
            pressure="attention" if current_memory_count else "quiet",
            review_target=current_memory_sample[0] if current_memory_sample else "",
        ),
        _artifact_class(
            class_id="durable_memory_notes",
            role="durable knowledge",
            count=durable_memory_count,
            sample=durable_memory_sample,
            pressure="measured" if durable_memory_count else "quiet",
            review_target="",
        ),
        _artifact_class(
            class_id="generated_outputs",
            role="derived reproducible artifact",
            count=generated_count,
            sample=generated_sample,
            pressure="measured" if generated_count else "quiet",
            review_target=generated_sample[0] if generated_sample else "",
        ),
        _artifact_class(
            class_id="local_only_state",
            role="local-only state",
            count=local_count,
            sample=local_sample,
            pressure="measured" if local_count else "quiet",
            review_target="",
        ),
        _artifact_class(
            class_id="large_docs_or_package_surfaces",
            role="large reference surface",
            count=large_docs_count,
            sample=large_docs_sample,
            pressure="attention" if large_docs_count else "quiet",
            review_target=large_docs_sample[0] if large_docs_sample else "",
        ),
    ]
    pressure_classes = [item for item in classes if item["pressure"] == "attention"]
    recommended = next((item for item in pressure_classes if item.get("review_target")), None)
    return {
        "status": "attention" if pressure_classes else "measured",
        "classes": classes,
        "pressure_class_count": len(pressure_classes),
        "recommended_cleanup_target": (
            {
                "class_id": recommended["id"],
                "path": recommended["review_target"],
                "action": "review-shrink-route-or-retain",
            }
            if recommended
            else {}
        ),
        "rule": "Footprint classes are advisory and selector-driven; they do not delete artifacts.",
    }


def _artifact_class(
    *,
    class_id: str,
    role: str,
    count: int,
    sample: list[str],
    pressure: str,
    review_target: str,
) -> dict[str, Any]:
    return {
        "id": class_id,
        "role": role,
        "count": count,
        "pressure": pressure,
        "sample": sample,
        "review_target": review_target,
    }


def _generated_output_files(*, target_root: Path) -> list[Path]:
    candidates: list[Path] = []
    for pattern in (
        "generated/**/*",
        "src/**/generated_*",
        "packages/**/generated_*",
        "src/**/generated_cli_package/**/*",
        "packages/**/generated_cli_package/**/*",
    ):
        candidates.extend(path for path in target_root.glob(pattern) if path.is_file() and not _is_runtime_cache_file(path))
    return sorted({path.resolve(): path for path in candidates}.values(), key=lambda path: path.as_posix())


def _is_runtime_cache_file(path: Path) -> bool:
    parts = set(path.parts)
    return "__pycache__" in parts or path.suffix in {".pyc", ".pyo"}


def _generated_output_footprint(*, target: Any) -> dict[str, Any]:
    target_text = str(target or "").strip()
    if not target_text:
        return {
            "kind": "workspace-generated-output-footprint/v1",
            "status": "unavailable",
            "artifact_count": 0,
            "generated_surfaces": [],
            "unclassified_generated_output_count": 0,
            "rule": "Generated outputs are derived reproducible footprint, not hand-authored operating state.",
        }
    target_root = Path(target_text)
    generated_files = _generated_output_files(target_root=target_root)
    generated_relatives = [_relative_posix(path, target_root) for path in generated_files]
    command_package_ir_path = target_root / "src" / "agentic_workspace" / "contracts" / "command_package_ir.json"
    command_adapter_generation_path = target_root / "src" / "agentic_workspace" / "contracts" / "command_adapter_generation.json"
    generator_path = target_root / "scripts" / "generate" / "generate_command_packages.py"
    check_path = target_root / "scripts" / "check" / "check_generated_command_packages.py"

    declared_roots: list[str] = []
    generated_surfaces: list[dict[str, Any]] = []
    role_counts: dict[str, int] = {}

    ir_payload: dict[str, Any] = {}
    if command_package_ir_path.is_file():
        try:
            loaded = json.loads(command_package_ir_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}
        ir_payload = loaded if isinstance(loaded, dict) else {}
    for package in _list_payload(ir_payload.get("packages")):
        if not isinstance(package, dict):
            continue
        package_id = str(package.get("id") or "")
        program = str(package.get("program") or "")
        for target_info in _list_payload(package.get("targets")):
            if not isinstance(target_info, dict):
                continue
            root = str(target_info.get("generated_root") or "").strip().replace("\\", "/")
            if not root:
                continue
            declared_roots.append(root.rstrip("/") + "/")
            files = [path for path in generated_relatives if _relative_is_under(path, root)]
            role = _generated_target_role(target_info)
            role_counts[role] = role_counts.get(role, 0) + 1
            generated_surfaces.append(
                {
                    "id": f"{package_id}:{target_info.get('kind', '')}",
                    "program": program,
                    "kind": str(target_info.get("kind") or ""),
                    "generated_root": root,
                    "generation_status": str(target_info.get("generation_status") or ""),
                    "maturity_level_ref": str(target_info.get("maturity_level_ref") or ""),
                    "test_environment": str(target_info.get("test_environment") or ""),
                    "role": role,
                    "file_count": len(files),
                    "sample": files[:3],
                    "ordinary_startup_surface": False,
                }
            )

    declared_outputs: list[str] = []
    if command_adapter_generation_path.is_file():
        try:
            adapter_payload = json.loads(command_adapter_generation_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            adapter_payload = {}
        if isinstance(adapter_payload, dict):
            for output in _list_payload(adapter_payload.get("generated_outputs")):
                if isinstance(output, dict):
                    path = str(output.get("path") or "").strip().replace("\\", "/")
                    if not path:
                        continue
                    declared_outputs.append(path)
                    role_counts["generated-dispatch-adapter"] = role_counts.get("generated-dispatch-adapter", 0) + 1
                    generated_surfaces.append(
                        {
                            "id": f"{output.get('program', '')}:generated-dispatch-adapter",
                            "program": str(output.get("program") or ""),
                            "kind": "python",
                            "generated_root": path,
                            "generation_status": "generated",
                            "maturity_level_ref": "generated-dispatch-adapter",
                            "test_environment": "python-dev",
                            "role": "generated-dispatch-adapter",
                            "file_count": 1 if path in generated_relatives else 0,
                            "sample": [path] if path in generated_relatives else [],
                            "ordinary_startup_surface": False,
                        }
                    )

    support_artifacts = [
        path for path in generated_relatives if path in {"generated/typescript/Dockerfile", "generated/typescript/Dockerfile.conformance"}
    ]
    if support_artifacts:
        role_counts["proof-container-support"] = role_counts.get("proof-container-support", 0) + len(support_artifacts)
        generated_surfaces.append(
            {
                "id": "typescript:proof-container-support",
                "program": "generated-typescript-packages",
                "kind": "docker",
                "generated_root": "generated/typescript",
                "generation_status": "proof-support",
                "maturity_level_ref": "proof-container-support",
                "test_environment": "docker",
                "role": "proof-container-support",
                "file_count": len(support_artifacts),
                "sample": support_artifacts[:3],
                "ordinary_startup_surface": False,
            }
        )

    classified = set(declared_outputs) | set(support_artifacts)
    for root in declared_roots:
        classified.update(path for path in generated_relatives if _relative_is_under(path, root))
    unclassified = [path for path in generated_relatives if path not in classified]
    freshness_missing = not (generator_path.is_file() and check_path.is_file() and command_package_ir_path.is_file())
    runnable_count = sum(
        1 for surface in generated_surfaces if surface.get("role") in {"runnable-read-only-adapter", "weak-agent-safe-adapter"}
    )
    weak_agent_safe_count = sum(1 for surface in generated_surfaces if surface.get("role") == "weak-agent-safe-adapter")
    proof_fixture_count = sum(1 for surface in generated_surfaces if surface.get("role") == "proof-fixture")
    status = "attention" if freshness_missing or unclassified else "measured"

    return {
        "kind": "workspace-generated-output-footprint/v1",
        "status": status,
        "advisory_only": True,
        "artifact_count": len(generated_relatives),
        "declared_surface_count": len(generated_surfaces),
        "role_counts": role_counts,
        "proof_fixture_count": proof_fixture_count,
        "runnable_adapter_count": runnable_count,
        "weak_agent_safe_adapter_count": weak_agent_safe_count,
        "unclassified_generated_output_count": len(unclassified),
        "sample_unclassified_generated_outputs": unclassified[:5],
        "freshness": {
            "status": "check-available" if not freshness_missing else "missing-check-or-source",
            "source_contract": "src/agentic_workspace/contracts/command_package_ir.json",
            "regeneration_command": "uv run python scripts/generate/generate_command_packages.py",
            "freshness_check": "uv run python scripts/check/check_generated_command_packages.py",
            "docker_proof": "uv run python scripts/check/check_generated_command_packages.py --docker --docker-conformance",
            "ordinary_report_runs_checks": False,
        },
        "guardrails": [
            "Generated outputs are reproducible derived artifacts, not durable hand-authored operating state.",
            "Weak-agent routing follows generated package maturity; proof fixtures are not runnable startup surfaces.",
            "No-direct-edit and freshness proof belong in generated package checks, not ordinary report execution.",
        ],
        "generated_surfaces": generated_surfaces[:12],
        "omitted_generated_surface_count": max(0, len(generated_surfaces) - 12),
        "rule": "Generated-output footprint is selector-driven advisory evidence; inspect it before expanding generated targets or compatibility artifacts.",
    }


def _relative_is_under(path: str, root: str) -> bool:
    normalized_path = path.replace("\\", "/")
    normalized_root = root.strip("/").replace("\\", "/")
    return normalized_path == normalized_root or normalized_path.startswith(normalized_root + "/")


def _generated_target_role(target_info: dict[str, Any]) -> str:
    status = str(target_info.get("generation_status") or "").lower()
    maturity = str(target_info.get("maturity_level_ref") or "").lower()
    if status == "deferred" or maturity == "deferred":
        return "deferred-target"
    if "weak-agent-safe" in status or "weak-agent-safe" in maturity:
        return "weak-agent-safe-adapter"
    if "runnable" in status or "runnable" in maturity:
        return "runnable-read-only-adapter"
    if "fixture" in status or "fixture" in maturity or "supported-now" in status:
        return "proof-fixture"
    return "generated-target"


def _relative_posix(path: Path, target_root: Path) -> str:
    try:
        return path.relative_to(target_root).as_posix()
    except ValueError:
        return path.as_posix()


def _list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _report_profile_payload(*, cli_invoke: str = DEFAULT_CLI_INVOKE) -> dict[str, Any]:
    return report_profile_payload(
        context_router=_context_router_family_payload(cli_invoke=cli_invoke, compact=True),
        cli_invoke=cli_invoke,
    )


def _select_report_payload(payload: dict[str, Any], *, profile: str, section: str | None) -> dict[str, Any]:
    config_payload = payload.get("config", {})
    workspace_config = config_payload.get("workspace", {}) if isinstance(config_payload, dict) else {}
    cli_invoke = str(workspace_config.get("cli_invoke", DEFAULT_CLI_INVOKE)) if isinstance(workspace_config, dict) else DEFAULT_CLI_INVOKE
    return select_report_payload(
        payload,
        profile=profile,
        section=section,
        compact_answer=_compact_contract_answer,
        context_router=_context_router_family_payload(cli_invoke=cli_invoke, compact=True),
        cli_invoke=cli_invoke,
    )


def _report_router_payload(payload: dict[str, Any]) -> dict[str, Any]:
    config_payload = payload.get("config", {})
    workspace_config = config_payload.get("workspace", {}) if isinstance(config_payload, dict) else {}
    cli_invoke = str(workspace_config.get("cli_invoke", DEFAULT_CLI_INVOKE)) if isinstance(workspace_config, dict) else DEFAULT_CLI_INVOKE
    return report_router_payload(
        payload,
        context_router=_context_router_family_payload(cli_invoke=cli_invoke, compact=True),
        cli_invoke=cli_invoke,
    )


def _report_section_hints(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return report_section_hints(payload)


def _report_closeout_trust_payload(
    *,
    module_reports: list[dict[str, Any]],
    target_root: Path | None = None,
    config: WorkspaceConfig | None = None,
    cli_invoke: str = DEFAULT_CLI_INVOKE,
) -> dict[str, Any]:
    strict_closeout = bool(config.assurance.strict_closeout) if config is not None else False

    def strict_gate(*, trust: str, reason: str = "", active_planning_record: bool = False) -> dict[str, Any]:
        if not strict_closeout:
            status = "disabled"
            blocking = False
            summary = "Strict closeout is disabled in assurance config."
        elif not active_planning_record and trust == "normal":
            status = "not-applicable"
            blocking = False
            summary = "Strict closeout has no active planning record to gate; use normal direct-work proof and issue checks."
        elif trust == "normal":
            status = "allowed"
            blocking = False
            summary = "Strict closeout is satisfied by the available planning and closeout-trust evidence."
        elif trust == "lower-trust":
            status = "blocked"
            blocking = True
            summary = "Strict closeout blocks closure until lower-trust planning residue or package evidence is resolved."
        else:
            status = "requires-review"
            blocking = True
            summary = "Strict closeout requires review because closeout evidence is unavailable or incomplete."
        return {
            "status": status,
            "strict_closeout": strict_closeout,
            "blocking": blocking,
            "reason": reason,
            "summary": summary,
            "source": "assurance.strict_closeout",
        }

    def terminal_action(*, trust: str, recommended_next_action: str) -> dict[str, Any]:
        blocking = trust != "normal"
        return {
            "next_command": (
                _command_with_cli_invoke(
                    command="agentic-workspace report --target ./repo --section closeout_trust --format json",
                    cli_invoke=cli_invoke,
                )
                if blocking
                else "none"
            ),
            "why": (
                "Lower-trust closeout signals need routed residue before closure is reliable."
                if trust == "lower-trust"
                else "Closeout trust is unavailable; recover planning output before claiming closure."
                if blocking
                else "No closeout trust blocker is visible; use normal proof and issue-state checks."
            ),
            "blocking": blocking,
            "recommended_next_action": recommended_next_action,
            "changes_closure": (
                "Route missing planning residue, rerun summary/reconcile, then close only when lower_trust_closeout_count is 0."
                if trust == "lower-trust"
                else "Recover planning closeout evidence; closure is blocked until closeout_trust is present."
                if blocking
                else "None for closeout trust; closure changes only if proof, intent satisfaction, issue state, or new residue changes."
            ),
        }

    def durable_residue_action(*, trust: str) -> dict[str, Any]:
        action = {
            "action": "route-durable-residue",
            "summary": (
                "Review lower-trust closeout signals and route missing residue to planning, Memory, docs, checks, or issue follow-up."
                if trust == "lower-trust"
                else "If closeout produced reusable learning, route it to the narrowest durable owner; otherwise record no durable residue."
            ),
            "command": _command_with_cli_invoke(
                command="agentic-workspace report --target ./repo --section closeout_trust --format json",
                cli_invoke=cli_invoke,
            ),
            "risk": "read-only routing; mutations happen only through the selected owner surface",
            "required_inputs": ["validation result", "issue or lane scope", "future relevance of any learning"],
            "destinations": ["none", "planning", "Memory", "docs", "contracts/checks", "issue follow-up", "review/archive evidence"],
            "destination_rule": "future work goes to planning; reusable non-canonical knowledge goes to Memory; stable rules go to docs/contracts/checks; evidence-only stays in review/archive; otherwise choose none",
            "next_proof": "rerun summary/reconcile after routing residue before closing the issue or lane",
        }
        action["run"] = action["command"]
        return action

    planning_report = next(
        (report for report in module_reports if isinstance(report, dict) and report.get("module") == "planning"),
        None,
    )
    if not isinstance(planning_report, dict):
        gate = strict_gate(trust="unavailable", reason="planning module is not installed", active_planning_record=False)
        return {
            "status": "unavailable",
            "reason": "planning module is not installed",
            "strict_closeout_gate": gate,
            "package_workflow_evidence": _package_workflow_evidence_payload(planning_report={}),
            "intent_satisfaction_check": _intent_satisfaction_check_payload(planning_report={}),
            "acceptance_criteria_reconciliation": _acceptance_criteria_reconciliation_payload(planning_report={}),
            "historical_review_artifacts": _historical_review_artifacts_policy(
                planning_report={},
                intent_validation={},
                target_root=target_root,
            ),
            "durable_residue_action": durable_residue_action(trust="unavailable"),
            "terminal_action": terminal_action(
                trust="unavailable",
                recommended_next_action="Install or run planning report before trusting closeout state.",
            ),
        }

    intent_validation = planning_report.get("intent_validation", {})
    if not isinstance(intent_validation, dict):
        gate = strict_gate(trust="unavailable", reason="planning intent validation is unavailable", active_planning_record=False)
        return {
            "status": "unavailable",
            "reason": "planning intent validation is unavailable",
            "strict_closeout_gate": gate,
            "package_workflow_evidence": _package_workflow_evidence_payload(planning_report=planning_report),
            "intent_satisfaction_check": _intent_satisfaction_check_payload(planning_report=planning_report),
            "acceptance_criteria_reconciliation": _acceptance_criteria_reconciliation_payload(planning_report=planning_report),
            "historical_review_artifacts": _historical_review_artifacts_policy(
                planning_report=planning_report,
                intent_validation={},
                target_root=target_root,
            ),
            "durable_residue_action": durable_residue_action(trust="unavailable"),
            "terminal_action": terminal_action(
                trust="unavailable",
                recommended_next_action="Inspect planning report before trusting closeout state.",
            ),
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
    package_workflow_evidence = _package_workflow_evidence_payload(planning_report=planning_report)
    acceptance_reconciliation = _acceptance_criteria_reconciliation_payload(planning_report=planning_report)
    active_planning_record = package_workflow_evidence.get("status") == "present"
    package_absence_signals: list[str] = []
    if package_workflow_evidence.get("status") == "present" and package_workflow_evidence.get("trust") == "lower-trust":
        missing = ", ".join(str(item) for item in package_workflow_evidence.get("missing_expected_surfaces", []))
        missing = missing or "package workflow evidence"
        package_absence_signals.append(
            f"Active planning record is present, but package workflow evidence is incomplete or absent: missing {missing}."
        )
    effective_lower_trust_count = lower_trust_closeout_count + len(package_absence_signals)
    if acceptance_reconciliation.get("trust") == "lower-trust":
        effective_lower_trust_count += 1
    trust = "lower-trust" if effective_lower_trust_count > 0 else "normal"
    if trust == "lower-trust":
        summary = (
            f"{effective_lower_trust_count} closeout signal(s) suggest package bypass, missing package evidence, or missing planning residue; "
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
        "strict_closeout_gate": strict_gate(
            trust=trust,
            reason="active planning record present" if active_planning_record else "no active planning record",
            active_planning_record=active_planning_record,
        ),
        "lower_trust_closeout_count": effective_lower_trust_count,
        "planning_residue_lower_trust_count": lower_trust_closeout_count,
        "package_evidence_lower_trust_count": len(package_absence_signals),
        "acceptance_reconciliation_lower_trust_count": 1 if acceptance_reconciliation.get("trust") == "lower-trust" else 0,
        "summary": summary,
        "sample_signals": [*sample_signals, *package_absence_signals][:3],
        "absence_signals": package_absence_signals,
        "package_workflow_evidence": package_workflow_evidence,
        "intent_satisfaction_check": _intent_satisfaction_check_payload(planning_report=planning_report),
        "acceptance_criteria_reconciliation": acceptance_reconciliation,
        "historical_review_artifacts": _historical_review_artifacts_policy(
            planning_report=planning_report,
            intent_validation=intent_validation,
            target_root=target_root,
        ),
        "durable_residue_action": durable_residue_action(trust=trust),
        "terminal_action": terminal_action(trust=trust, recommended_next_action=recommended_next_action),
        "recommended_next_action": recommended_next_action,
    }


def _historical_review_artifacts_policy(
    *,
    planning_report: dict[str, Any],
    intent_validation: dict[str, Any],
    target_root: Path | None = None,
) -> dict[str, Any]:
    historical = intent_validation.get("historical_audit_references", {}) if isinstance(intent_validation, dict) else {}
    if not isinstance(historical, dict):
        historical = {}
    source_count = _as_int(historical.get("source_count"))
    item_count = _as_int(historical.get("item_count"))
    if source_count == 0 and isinstance(planning_report, dict):
        reconcile = planning_report.get("closeout_reconciliation", {})
        if isinstance(reconcile, dict):
            source_count = _as_int(reconcile.get("source_count"))
            item_count = _as_int(reconcile.get("item_count"))
    return {
        "status": "evidence-only",
        "role": "evidence/history, not ordinary operating input",
        "source_count": source_count,
        "item_count": item_count,
        "rule": "Do not read historical review artifacts during startup unless a selected issue, audit, or report section points there.",
        "selection_path": "agentic-workspace report --target ./repo --section closeout_trust --format json",
        "retention_policy": _review_artifact_retention_policy(target_root=target_root),
        "retention_guidance": [
            "Promote durable findings to planning, canonical docs, checks, or Memory before treating them as current authority.",
            "Shrink, stub, or delete stale review artifacts once findings are promoted, dismissed, or superseded.",
            "Keep review artifacts out of ordinary startup and compact recovery unless the selected work explicitly asks for historical evidence.",
        ],
    }


def _review_artifact_retention_policy(*, target_root: Path | None) -> dict[str, Any]:
    if target_root is None:
        return {
            "kind": "workspace-review-retention-policy/v1",
            "status": "unavailable",
            "advisory_only": True,
            "artifact_count": 0,
            "missing_retention_metadata_count": 0,
            "cleanup_candidate_count": 0,
            "candidate_count": 0,
            "candidates": [],
            "rule": "Review-retention pressure is advisory and selector-driven; it never deletes review artifacts automatically.",
        }

    roots = [
        ("planning-review-record", target_root / ".agentic-workspace" / "planning" / "reviews", "*.review.json"),
        ("docs-review-artifact", target_root / "docs" / "reviews", "*"),
    ]
    artifact_count = 0
    missing_retention: list[str] = []
    cleanup: dict[str, list[str]] = {"shrink": [], "stub": [], "delete": []}
    resolved_full_size: list[str] = []

    for artifact_class, root, pattern in roots:
        if not root.exists():
            continue
        for path in sorted(item for item in root.glob(pattern) if item.is_file()):
            artifact_count += 1
            relative = _relative_posix(path, target_root)
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                missing_retention.append(relative)
                continue

            retention: dict[str, Any] = {}
            resolved = False
            if path.suffix == ".json":
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = {}
                if isinstance(payload, dict):
                    retention_value = payload.get("retention")
                    retention = retention_value if isinstance(retention_value, dict) else {}
                    resolved = _review_artifact_has_resolved_findings(payload)
            else:
                retention = _markdown_retention_metadata(text)
                resolved = _review_markdown_has_resolved_findings(text)

            shape = _review_retention_field(retention, "closeout shape", "closeout_shape", "shape")
            trigger = _review_retention_field(retention, "trigger")
            proof_surface = _review_retention_field(retention, "proof surface", "proof_surface")
            if not (shape and trigger and proof_surface):
                missing_retention.append(relative)

            outcome = _review_retention_outcome(shape)
            if outcome in cleanup:
                cleanup[outcome].append(relative)
            if artifact_class == "docs-review-artifact" and not shape:
                cleanup["shrink"].append(relative)
            if resolved and len(text.splitlines()) > 80 and not shape.lower().startswith("retain"):
                resolved_full_size.append(relative)

    candidates: list[dict[str, Any]] = []
    if missing_retention:
        candidates.append(
            {
                "signal": "missing-retention-metadata",
                "count": len(missing_retention),
                "recommended_outcome": "add-retention-metadata",
                "candidate_paths": missing_retention[:5],
                "why": "Review artifacts without closeout shape, trigger, and proof surface need routing metadata before they can be safely shrunk or retained.",
            }
        )
    for outcome in ("shrink", "stub", "delete"):
        paths = cleanup[outcome]
        if paths:
            candidates.append(
                {
                    "signal": f"retention-shape-{outcome}",
                    "count": len(paths),
                    "recommended_outcome": outcome,
                    "candidate_paths": paths[:5],
                    "why": f"Review artifacts whose own retention shape points to {outcome} should be revisited after findings are promoted, dismissed, or superseded.",
                }
            )
    if resolved_full_size:
        candidates.append(
            {
                "signal": "resolved-full-size-review",
                "count": len(resolved_full_size),
                "recommended_outcome": "shrink",
                "candidate_paths": resolved_full_size[:5],
                "why": "Resolved full-size reviews are candidates for compact evidence once durable findings live in planning, docs, checks, issues, or Memory.",
            }
        )

    return {
        "kind": "workspace-review-retention-policy/v1",
        "status": "attention" if candidates else "quiet",
        "advisory_only": True,
        "applies_to": [
            ".agentic-workspace/planning/reviews/*.review.json",
            "docs/reviews/*",
        ],
        "outcomes": [
            "retain",
            "shrink",
            "stub",
            "delete",
            "add-retention-metadata",
        ],
        "default_outcome": "retain",
        "artifact_count": artifact_count,
        "missing_retention_metadata_count": len(missing_retention),
        "cleanup_candidate_count": sum(len(paths) for paths in cleanup.values()) + len(resolved_full_size),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "before_shrink_or_delete": [
            "promote durable findings to planning, canonical docs, checks, issues, or Memory",
            "preserve enough evidence for audit, trust, and continuation",
            "keep historical reviews out of ordinary startup and compact recovery paths",
        ],
        "rule": "Review-retention pressure is advisory and selector-driven; it recommends cleanup outcomes but never deletes review artifacts automatically.",
    }


def _review_retention_field(retention: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = retention.get(key)
        if str(value or "").strip():
            return str(value).strip()
    return ""


def _review_retention_outcome(shape: str) -> str:
    normalized = shape.lower()
    if "delete" in normalized:
        return "delete"
    if "stub" in normalized:
        return "stub"
    if "shrink" in normalized or "archive" in normalized or "compact" in normalized:
        return "shrink"
    return "retain" if "retain" in normalized or "keep" in normalized else ""


def _review_artifact_has_resolved_findings(payload: dict[str, Any]) -> bool:
    try:
        text = json.dumps(
            {field: payload.get(field) for field in ("findings", "issue_classifications", "classified_items", "closeout_items")},
            sort_keys=True,
        ).lower()
    except TypeError:
        text = ""
    resolved_markers = (
        "closed by implementation",
        "evidence-present",
        '"live_state": "closed',
        'follow_up": ""',
        'follow_up": "none"',
        "resolution",
        "superseded",
        "dismiss",
        "addressed",
    )
    return any(marker in text for marker in resolved_markers)


def _markdown_retention_metadata(text: str) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    lower = text.lower()
    for line in text.splitlines():
        stripped = line.strip()
        normalized = stripped.lower()
        if normalized.startswith("closeout shape:"):
            metadata["closeout shape"] = stripped.split(":", 1)[1].strip()
        elif normalized.startswith("trigger:"):
            metadata["trigger"] = stripped.split(":", 1)[1].strip()
        elif normalized.startswith("proof surface:"):
            metadata["proof surface"] = stripped.split(":", 1)[1].strip()
    if "retention" in lower and not metadata:
        metadata["shape"] = "retain"
    return metadata


def _review_markdown_has_resolved_findings(text: str) -> bool:
    normalized = text.lower()
    return any(marker in normalized for marker in ("closed", "implemented", "superseded", "dismissed", "addressed"))


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
    expected_surfaces = ["preflight", "summary", "report", "proof"]
    optional_surfaces = ["reconcile", "doctor"]
    used_surfaces = [surface for surface in expected_surfaces + optional_surfaces if f"agentic-workspace {surface}" in evidence_text]
    missing_expected_surfaces = [surface for surface in expected_surfaces if surface not in used_surfaces]
    skipped_text = str(execution_run.get("package workflow skipped", "") or execution_run.get("package_workflow_skipped", "")).strip()
    trust = "normal" if used_surfaces and not missing_expected_surfaces and not skipped_text else "lower-trust"
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
        "expected_surfaces": expected_surfaces,
        "optional_surfaces": optional_surfaces,
        "missing_expected_surfaces": missing_expected_surfaces,
        "evidence_quality": "complete" if trust == "normal" else "incomplete",
        "skipped": skipped_text,
        "evidence_sources": [
            "planning.active.planning_record.proof_expectations",
            "planning.active.planning_record.execution_run",
        ],
        "recommended_next_action": recommended_next_action,
    }


def _intent_satisfaction_check_payload(*, planning_report: dict[str, Any]) -> dict[str, Any]:
    active = planning_report.get("active", {}) if isinstance(planning_report, dict) else {}
    planning_record = active.get("planning_record", {}) if isinstance(active, dict) else {}
    if not isinstance(planning_record, dict) or planning_record.get("status") != "present":
        return {
            "status": "unavailable",
            "reason": "no active planning record exposes intent-continuity evidence",
            "required_for_broad_work": True,
            "rule": "Validation success is not enough; closeout should say whether the larger intent is satisfied, partially satisfied, or needs follow-up.",
            "closure_scope": {
                "validation_proof": {
                    "status": "separate-answer",
                    "not_sufficient_for_closure": True,
                    "rule": "Validation success proves implementation behavior, not intent closure by itself.",
                },
                "requested_slice": {"status": "unavailable"},
                "lane_or_system_intent": {"status": "unavailable"},
                "larger_intent_closure": {"status": "unavailable"},
                "non_substitution_rule": "Validation success alone is not closure evidence.",
            },
        }
    intent_continuity = planning_record.get("intent_continuity", {})
    required_continuation = planning_record.get("required_continuation", {})
    hierarchy_contract = active.get("hierarchy_contract", {}) if isinstance(active, dict) else {}
    resumable_contract = active.get("resumable_contract", {}) if isinstance(active, dict) else {}
    hierarchy_required = hierarchy_contract.get("required_continuation", {}) if isinstance(hierarchy_contract, dict) else {}
    if not isinstance(intent_continuity, dict):
        intent_continuity = {}
    if not isinstance(required_continuation, dict):
        required_continuation = {}
    if not isinstance(hierarchy_required, dict):
        hierarchy_required = {}
    if not intent_continuity and hierarchy_required:
        intent_continuity = {
            "larger intended outcome": hierarchy_required.get("larger_intended_outcome", ""),
            "this slice completes the larger intended outcome": hierarchy_required.get("slice_completes_larger_outcome", ""),
            "continuation surface": hierarchy_required.get("continuation_surface", ""),
        }
    if not required_continuation and hierarchy_required:
        required_continuation = {
            "required follow-on for the larger intended outcome": hierarchy_required.get("required_follow_on", ""),
            "owner surface": hierarchy_required.get("owner_surface", ""),
        }
    proof_expectations = [str(item) for item in _list_payload(planning_record.get("proof_expectations"))]
    if not proof_expectations and isinstance(resumable_contract, dict):
        proof_expectations = [str(item) for item in _list_payload(resumable_contract.get("proof_expectations"))]
    active_milestone = planning_record.get("active_milestone", {})
    if (not isinstance(active_milestone, dict) or not active_milestone) and isinstance(resumable_contract, dict):
        active_milestone = resumable_contract.get("active_milestone", {})
    if not isinstance(active_milestone, dict):
        active_milestone = {}
    completion_criteria = [str(item) for item in _list_payload(planning_record.get("completion_criteria"))]
    if not completion_criteria and isinstance(resumable_contract, dict):
        completion_criteria = [str(item) for item in _list_payload(resumable_contract.get("completion_criteria"))]
    proof_report = planning_record.get("proof_report", {})
    if not isinstance(proof_report, dict):
        proof_report = {}
    closure_check = planning_record.get("closure_check", {})
    if not isinstance(closure_check, dict):
        closure_check = {}
    hierarchy_closure = hierarchy_contract.get("closure_check", {}) if isinstance(hierarchy_contract, dict) else {}
    if not closure_check and isinstance(hierarchy_closure, dict):
        closure_check = hierarchy_closure
    completes = str(intent_continuity.get("this slice completes the larger intended outcome", "")).strip().lower()
    continuation = str(required_continuation.get("required follow-on for the larger intended outcome", "")).strip().lower()
    if completes in {"yes", "true"} and continuation in {"no", "false", "none"}:
        trust = "satisfied"
        recommended_next_action = "Closeout may claim intent satisfaction if proof also passed."
    elif completes in {"no", "false"} or continuation in {"yes", "true"}:
        trust = "follow-up-required"
        recommended_next_action = "Record or preserve the continuation surface before treating this closeout as complete."
    else:
        trust = "needs-review"
        recommended_next_action = "Name whether the larger intent is satisfied or requires follow-up before broad-work closeout."
    return {
        "status": "present",
        "required_for_broad_work": True,
        "trust": trust,
        "larger_intent": intent_continuity.get("larger intended outcome", ""),
        "slice_completes_larger_intent": intent_continuity.get("this slice completes the larger intended outcome", ""),
        "required_follow_on": required_continuation.get("required follow-on for the larger intended outcome", ""),
        "continuation_surface": intent_continuity.get("continuation surface", required_continuation.get("owner surface", "")),
        "rule": "Proof and validation answer whether the implementation works; this check answers whether the intended outcome is actually closed.",
        "closure_scope": {
            "validation_proof": {
                "status": "separate-answer",
                "not_sufficient_for_closure": True,
                "proof_expectation_count": len(proof_expectations),
                "proof_report": proof_report.get("validation proof", ""),
                "sources": [
                    "planning.active.planning_record.proof_expectations",
                    "planning.active.planning_record.proof_report",
                ],
                "rule": "Validation success proves implementation behavior, not intent closure by itself.",
            },
            "requested_slice": {
                "status": active_milestone.get("status", ""),
                "milestone_id": active_milestone.get("id", ""),
                "completion_criteria_count": len(completion_criteria),
                "sources": [
                    "planning.active.planning_record.active_milestone",
                    "planning.active.resumable_contract.completion_criteria",
                ],
                "rule": "Slice landing is narrower than lane or larger-intent satisfaction.",
            },
            "lane_or_system_intent": {
                "status": trust,
                "larger_intent": intent_continuity.get("larger intended outcome", ""),
                "slice_completes_larger_intent": intent_continuity.get("this slice completes the larger intended outcome", ""),
                "required_follow_on": required_continuation.get("required follow-on for the larger intended outcome", ""),
                "continuation_surface": intent_continuity.get("continuation surface", required_continuation.get("owner surface", "")),
                "sources": [
                    "planning.active.planning_record.intent_continuity",
                    "planning.active.planning_record.required_continuation",
                    "planning.active.hierarchy_contract.required_continuation",
                ],
            },
            "larger_intent_closure": {
                "status": closure_check.get("larger-intent status", ""),
                "closure_decision": closure_check.get("closure decision", ""),
                "evidence": closure_check.get("evidence carried forward", ""),
                "reopen_trigger": closure_check.get("reopen trigger", ""),
                "source": "planning.active.hierarchy_contract.closure_check",
                "rule": "Only explicit closure-check evidence may close the larger intent.",
            },
            "non_substitution_rule": "Validation success alone is not closure evidence.",
        },
        "recommended_next_action": recommended_next_action,
    }


def _acceptance_criteria_reconciliation_payload(*, planning_report: dict[str, Any]) -> dict[str, Any]:
    active = planning_report.get("active", {}) if isinstance(planning_report, dict) else {}
    planning_record = active.get("planning_record", {}) if isinstance(active, dict) else {}
    if not isinstance(planning_record, dict) or planning_record.get("status") != "present":
        return {
            "status": "unavailable",
            "trust": "not-applicable",
            "required_for_bounded_or_broad_work": True,
            "reason": "no active planning record exposes acceptance reconciliation evidence",
            "rule": "Validation success and self-authored tests do not prove that requested outcomes were delivered.",
            "required_closeout_shape": [
                "requested requirement or criterion",
                "delivered behavior or surface",
                "proof covering it",
                "gap or intentional deviation",
            ],
        }
    active_milestone = planning_record.get("active_milestone", {})
    if not isinstance(active_milestone, dict):
        active_milestone = {}
    completion_criteria = [str(item).strip() for item in _list_payload(planning_record.get("completion_criteria")) if str(item).strip()]
    proof_expectations = [str(item).strip() for item in _list_payload(planning_record.get("proof_expectations")) if str(item).strip()]
    proof_report = planning_record.get("proof_report", {})
    if not isinstance(proof_report, dict):
        proof_report = {}
    closure_check = planning_record.get("closure_check", {})
    if not isinstance(closure_check, dict):
        closure_check = {}
    evidence_text = "\n".join(
        [
            str(proof_report.get("validation proof", "")),
            str(proof_report.get("acceptance reconciliation", "")),
            str(closure_check.get("acceptance reconciliation", "")),
            str(closure_check.get("criteria satisfied", "")),
        ]
    ).lower()
    evidence_present = any(
        marker in evidence_text
        for marker in (
            "requested",
            "delivered",
            "acceptance",
            "criteria",
            "requirement",
            "deviation",
        )
    )
    criteria_count = len(completion_criteria) or (1 if active_milestone else 0)
    trust = "normal" if evidence_present and (criteria_count or proof_expectations) else "lower-trust"
    return {
        "status": "present",
        "trust": trust,
        "required_for_bounded_or_broad_work": True,
        "completion_criteria_count": criteria_count,
        "proof_expectation_count": len(proof_expectations),
        "evidence_present": evidence_present,
        "rule": "Before closeout, reconcile each requested outcome or planning criterion against delivered behavior and proof.",
        "required_closeout_shape": [
            "requested requirement or criterion",
            "delivered behavior or surface",
            "proof covering it",
            "gap or intentional deviation",
        ],
        "recommended_next_action": (
            "Acceptance reconciliation is visible in planning closeout evidence."
            if trust == "normal"
            else "Record requested->delivered->proof->gap reconciliation before claiming successful closeout."
        ),
        "sources": [
            "planning.active.planning_record.completion_criteria",
            "planning.active.planning_record.proof_expectations",
            "planning.active.planning_record.proof_report",
            "planning.active.planning_record.closure_check",
        ],
    }


def _external_work_delta_payload(*, target_root: Path) -> dict[str, Any]:
    evidence_path, evidence_relative_path, evidence_storage = _external_intent_evidence_read_location(target_root)
    provider_rule = "Core planning consumes provider-agnostic external work evidence; provider adapters may refresh it."
    if not evidence_path.is_file():
        return {
            "status": "unavailable",
            "reason": "external intent evidence cache is absent",
            "provider_rule": provider_rule,
            "storage": evidence_storage,
            "open_count": 0,
            "changed_count": 0,
            "closed_count": 0,
            "recommended_next_lane": {},
        }
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "invalid",
            "reason": str(exc),
            "provider_rule": provider_rule,
            "storage": evidence_storage,
            "open_count": 0,
            "changed_count": 0,
            "closed_count": 0,
            "recommended_next_lane": {},
        }
    schema_findings = _external_intent_evidence_schema_findings(target_root=target_root, payload=payload)
    if schema_findings:
        return {
            "status": "invalid",
            "reason": "external intent evidence schema validation failed: " + "; ".join(schema_findings),
            "schema_findings": schema_findings,
            "provider_rule": provider_rule,
            "storage": evidence_storage,
            "open_count": 0,
            "changed_count": 0,
            "closed_count": 0,
            "recommended_next_lane": {},
        }
    items = [item for item in _list_payload(payload.get("items")) if isinstance(item, dict)]
    previous_items = [item for item in _list_payload(payload.get("previous_items")) if isinstance(item, dict)]
    refresh_metadata = payload.get("refresh_metadata", {}) if isinstance(payload.get("refresh_metadata"), dict) else {}
    open_items = [item for item in items if str(item.get("status", "")).lower() == "open"]
    previous_by_id = {str(item.get("id", "")): item for item in previous_items if str(item.get("id", ""))}
    current_by_id = {str(item.get("id", "")): item for item in items if str(item.get("id", ""))}
    new_items = [item for item in items if str(item.get("id", "")) and str(item.get("id", "")) not in previous_by_id]
    closed_items = [
        item
        for item_id, item in current_by_id.items()
        if item_id in previous_by_id
        and str(previous_by_id[item_id].get("status", "")).lower() == "open"
        and str(item.get("status", "")).lower() == "closed"
    ]
    changed_items = [item for item_id, item in current_by_id.items() if item_id in previous_by_id and item != previous_by_id[item_id]]
    recommended = open_items[0] if open_items else {}
    status = "delta-present" if previous_items else "snapshot-only"
    return {
        "status": status,
        "provider_rule": provider_rule,
        "source": evidence_relative_path,
        "storage": evidence_storage,
        "refreshed_at": str(payload.get("refreshed_at", "") or refresh_metadata.get("refreshed_at", "")),
        "refresh_metadata": {
            "adapter": str(refresh_metadata.get("adapter", "")),
            "repository": str(refresh_metadata.get("repository", "")),
            "item_count": int(refresh_metadata.get("item_count", len(items)) or 0),
            "open_count": int(refresh_metadata.get("open_count", len(open_items)) or 0),
            "closed_count": int(refresh_metadata.get("closed_count", 0) or 0),
        },
        "item_count": len(items),
        "open_count": len(open_items),
        "new_count": len(new_items) if previous_items else 0,
        "changed_count": len(changed_items) if previous_items else 0,
        "closed_count": len(closed_items) if previous_items else 0,
        "sample_new": [_external_work_summary(item) for item in new_items[:5]] if previous_items else [],
        "sample_changed": [_external_work_summary(item) for item in changed_items[:5]] if previous_items else [],
        "sample_closed": [_external_work_summary(item) for item in closed_items[:5]] if previous_items else [],
        "recommended_next_lane": _external_work_summary(recommended) if recommended else {},
        "delta_rule": "When previous_items is present, compare provider-agnostic item ids and statuses; otherwise report a compact current snapshot only.",
    }


def _external_work_reconciliation_payload(
    *,
    module_reports: list[dict[str, Any]],
    external_work_delta: dict[str, Any],
    cli_invoke: str = DEFAULT_CLI_INVOKE,
) -> dict[str, Any]:
    planning_report = next(
        (report for report in module_reports if isinstance(report, dict) and report.get("module") == "planning"),
        {},
    )
    intent_validation = planning_report.get("intent_validation", {}) if isinstance(planning_report, dict) else {}
    planning_reconciliation = intent_validation.get("external_work_reconciliation", {}) if isinstance(intent_validation, dict) else {}
    payload: dict[str, Any]
    if isinstance(planning_reconciliation, dict) and planning_reconciliation:
        payload = copy.deepcopy(planning_reconciliation)
    else:
        payload = {
            "kind": "planning-external-work-reconciliation/v1",
            "status": "unavailable",
            "primary_owner": ".agentic-workspace/planning/state.toml",
            "provider_rule": "Core planning consumes provider-agnostic external work evidence; provider-specific refresh belongs in optional adapters.",
            "recommended_next_action": "Install or run planning summary before trusting external-work reconciliation.",
        }
    payload["workspace_report_view"] = {
        "kind": "workspace-external-work-reconciliation-view/v1",
        "section_command": "agentic-workspace report --target ./repo --section external_work_reconciliation --format json",
        "delta_section": "external_work_delta",
        "delta_status": external_work_delta.get("status", "unavailable"),
        "delta_counts": {
            "new_count": external_work_delta.get("new_count", 0),
            "changed_count": external_work_delta.get("changed_count", 0),
            "closed_count": external_work_delta.get("closed_count", 0),
        },
    }
    if "promotion_action" not in payload:
        external_state = payload.get("external_work_state", {}) if isinstance(payload.get("external_work_state"), dict) else {}
        untracked_open = int(external_state.get("untracked_open_count", 0) or 0)
        promotion_action = {
            "action": "promote-external-work-to-planning",
            "summary": (
                "Create one checked-in active execplan/state entry for selected untracked external work."
                if untracked_open
                else "No external-work promotion is currently needed."
            ),
            "command": _command_with_cli_invoke(command="agentic-workspace summary --format json", cli_invoke=cli_invoke),
            "risk": "planning mutation; inspect selected external items before editing checked-in planning state",
            "required_inputs": ["selected external item ids", "requested outcome", "proof expectations", "owner surface"],
            "target_surfaces": [
                ".agentic-workspace/planning/state.toml",
                ".agentic-workspace/planning/execplans/<lane>.plan.json",
            ],
            "state_rule": "Represent promoted work once as the active item and point it at one execplan; do not duplicate active state.",
            "provider_neutral": True,
            "next_proof": "rerun summary and planning doctor after promotion; active_count should be one for a broad active lane",
        }
        promotion_action["run"] = promotion_action["command"]
        payload["promotion_action"] = promotion_action
    elif isinstance(payload.get("promotion_action"), dict):
        action = payload["promotion_action"]
        command = str(action.get("command", "")).strip()
        if command:
            action["command"] = _command_with_cli_invoke(command=command, cli_invoke=cli_invoke)
            action["run"] = action["command"]
    payload.setdefault(
        "detail_sections",
        [
            "current_external_work",
            "closeout_reconciliation",
            "landed_open_issue_reconciliation",
        ],
    )
    return payload


def _external_work_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")),
        "title": str(item.get("title", "")),
        "status": str(item.get("status", "")),
        "kind": str(item.get("kind", "")),
        "parent_id": str(item.get("parent_id", "")),
        "reopens": [str(entry).strip() for entry in _list_payload(item.get("reopens")) if str(entry).strip()],
    }


def _external_intent_evidence_path(target_root: Path) -> Path:
    return target_root / EXTERNAL_INTENT_CACHE_RELATIVE_PATH


def _external_intent_planning_evidence_path(target_root: Path) -> Path:
    return target_root / EXTERNAL_INTENT_PLANNING_RELATIVE_PATH


def _external_intent_evidence_write_location(target_root: Path, storage: str) -> tuple[Path, str, str]:
    if storage == "cache":
        return target_root / EXTERNAL_INTENT_CACHE_RELATIVE_PATH, EXTERNAL_INTENT_CACHE_RELATIVE_PATH.as_posix(), "cache"
    if storage == "planning":
        return target_root / EXTERNAL_INTENT_PLANNING_RELATIVE_PATH, EXTERNAL_INTENT_PLANNING_RELATIVE_PATH.as_posix(), "planning"
    raise WorkspaceUsageError("--storage must be one of: cache, planning.")


def _external_intent_evidence_read_location(target_root: Path) -> tuple[Path, str, str]:
    cache_path = target_root / EXTERNAL_INTENT_CACHE_RELATIVE_PATH
    if cache_path.exists():
        return cache_path, EXTERNAL_INTENT_CACHE_RELATIVE_PATH.as_posix(), "cache"
    planning_path = target_root / EXTERNAL_INTENT_PLANNING_RELATIVE_PATH
    return planning_path, EXTERNAL_INTENT_PLANNING_RELATIVE_PATH.as_posix(), "planning-legacy"


def _ensure_external_intent_cache_if_available(target_root: Path) -> dict[str, Any]:
    cache_path = target_root / EXTERNAL_INTENT_CACHE_RELATIVE_PATH
    if cache_path.exists():
        return {"status": "present", "path": EXTERNAL_INTENT_CACHE_RELATIVE_PATH.as_posix()}
    try:
        return _refresh_github_external_intent_evidence(
            target_root=target_root,
            repo=None,
            limit=None,
            state=None,
            storage="cache",
            dry_run=False,
        )
    except WorkspaceUsageError as exc:
        return {
            "status": "unavailable",
            "reason": str(exc),
            "path": EXTERNAL_INTENT_CACHE_RELATIVE_PATH.as_posix(),
            "provider_rule": "GitHub reconstruction is optional; missing gh leaves offline planning usable.",
        }


def _run_gh_json(args: list[str], *, cwd: Path) -> Any:
    command = ["gh", *args]
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False)
    except FileNotFoundError as exc:
        raise WorkspaceUsageError("GitHub external-intent refresh requires the optional `gh` CLI to be installed.") from exc
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip() or f"`gh {' '.join(args)}` failed"
        raise WorkspaceUsageError(stderr)
    try:
        return json.loads(result.stdout or "null")
    except json.JSONDecodeError as exc:
        raise WorkspaceUsageError(f"`gh {' '.join(args)}` did not return valid JSON: {exc}") from exc


def _resolve_github_repo_for_external_intent(*, target_root: Path, repo: str | None) -> str:
    if repo and repo.strip():
        return repo.strip()
    payload = _run_gh_json(["repo", "view", "--json", "nameWithOwner"], cwd=target_root)
    if isinstance(payload, dict) and isinstance(payload.get("nameWithOwner"), str) and payload["nameWithOwner"].strip():
        return str(payload["nameWithOwner"]).strip()
    raise WorkspaceUsageError("Could not resolve GitHub repository; pass --repo owner/name.")


def _github_label_names(raw_labels: Any) -> list[str]:
    labels: list[str] = []
    for raw_label in _list_payload(raw_labels):
        if isinstance(raw_label, dict):
            name = str(raw_label.get("name", "")).strip()
        else:
            name = str(raw_label).strip()
        if name and name not in labels:
            labels.append(name)
    return labels


def _github_comments_count(raw_comments: Any) -> int:
    if isinstance(raw_comments, list):
        return len(raw_comments)
    try:
        return int(raw_comments or 0)
    except (TypeError, ValueError):
        return 0


def _github_planning_residue_expected(labels: list[str]) -> str:
    normalized = {label.lower() for label in labels}
    if normalized & {"planning-residue-required", "requires-planning-residue"}:
        return "required"
    if normalized & {"planning-residue-none", "no-planning-residue"}:
        return "none"
    return "optional"


def _markdown_section_value(body: str, heading: str) -> str:
    lines = body.splitlines()
    heading_normalized = heading.strip().lower()
    for index, line in enumerate(lines):
        stripped = line.strip().lstrip("#").strip().lower()
        if stripped != heading_normalized:
            continue
        values: list[str] = []
        for candidate in lines[index + 1 :]:
            candidate_stripped = candidate.strip()
            if candidate_stripped.startswith("##"):
                break
            if candidate_stripped:
                values.append(candidate_stripped)
        return "\n".join(values).strip()
    return ""


def _infer_external_issue_kind(*, body: str) -> str:
    issue_kind = _markdown_section_value(body, "Issue kind").lower()
    if "child" in issue_kind or "slice" in issue_kind:
        return "slice"
    if "parent" in issue_kind or "lane" in issue_kind:
        return "lane"
    return "issue"


def _infer_external_issue_parent_id(body: str) -> str:
    section_value = _markdown_section_value(body, "Parent issue or lane")
    section_match = re.search(r"#(\d+)\b", section_value)
    if section_match:
        return f"#{section_match.group(1)}"
    for pattern in (
        r"(?im)^\s*parent(?:\s+issue|\s+lane)?\s*[:#]\s*#?(\d+)\b",
        r"(?im)^\s*belongs\s+to\s*[:#]?\s*#?(\d+)\b",
    ):
        match = re.search(pattern, body)
        if match:
            return f"#{match.group(1)}"
    return ""


def _infer_external_issue_reopens(body: str) -> list[str]:
    refs: list[str] = []
    for heading in ("Closed lane(s) to revisit", "Closed lanes to revisit", "Reopens"):
        section_value = _markdown_section_value(body, heading)
        for match in re.finditer(r"#(\d+)\b", section_value):
            ref = f"#{match.group(1)}"
            if ref not in refs:
                refs.append(ref)
    return refs


def _github_issue_to_external_intent_item(*, issue: dict[str, Any], repo: str) -> dict[str, Any] | None:
    number = issue.get("number")
    if number is None:
        return None
    try:
        issue_number = int(number)
    except (TypeError, ValueError):
        return None
    state = str(issue.get("state", "")).strip().lower()
    if state not in {"open", "closed"}:
        state = "closed" if bool(issue.get("closed")) else "open"
    labels = _github_label_names(issue.get("labels"))
    body = str(issue.get("body", "") or "")
    return {
        "system": "github",
        "id": f"#{issue_number}",
        "title": str(issue.get("title", "")).strip(),
        "status": state,
        "kind": _infer_external_issue_kind(body=body),
        "parent_id": _infer_external_issue_parent_id(body),
        "reopens": _infer_external_issue_reopens(body),
        "planning_residue_expected": _github_planning_residue_expected(labels),
        "url": str(issue.get("url", "")).strip(),
        "source_repository": repo,
        "labels": labels,
        "created_at": str(issue.get("createdAt", "")).strip(),
        "updated_at": str(issue.get("updatedAt", "")).strip(),
        "closed_at": str(issue.get("closedAt", "") or "").strip(),
        "comments_count": _github_comments_count(issue.get("comments")),
    }


def _load_existing_external_intent_evidence(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"kind": "planning-external-intent-evidence/v1", "items": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkspaceUsageError(f"Cannot refresh invalid external intent evidence at {path.as_posix()}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("kind") != "planning-external-intent-evidence/v1":
        raise WorkspaceUsageError(f"{path.as_posix()} must contain kind planning-external-intent-evidence/v1.")
    schema_findings = _external_intent_evidence_schema_findings(target_root=_workspace_root_for_evidence_path(path), payload=payload)
    if schema_findings:
        raise WorkspaceUsageError(f"Cannot refresh invalid external intent evidence at {path.as_posix()}: " + "; ".join(schema_findings))
    return payload


def _workspace_root_for_evidence_path(path: Path) -> Path:
    for parent in path.parents:
        if parent.name == ".agentic-workspace":
            return parent.parent
    return path.parent


def _external_intent_evidence_schema_findings(*, target_root: Path, payload: object) -> list[str]:
    if not isinstance(payload, dict):
        return ["external intent evidence must be a JSON object"]
    evidence_payload = cast(dict[str, Any], payload)
    schema_path = target_root / ".agentic-workspace" / "planning" / "schemas" / "planning-external-intent-evidence.schema.json"
    findings = _external_intent_evidence_consistency_findings(evidence_payload)
    if not schema_path.exists():
        return findings
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return findings
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"schema is missing or invalid JSON: {exc}", *findings]
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda error: list(error.path))
    for error in errors:
        location = ".".join(str(part) for part in error.path) or "<root>"
        findings.append(f"{location}: {error.message}")
    return findings


def _external_intent_evidence_consistency_findings(payload: dict[str, Any]) -> list[str]:
    metadata = payload.get("refresh_metadata", {})
    if not isinstance(metadata, dict):
        return []
    items = [item for item in _list_payload(payload.get("items")) if isinstance(item, dict)]
    expected_counts = {
        "item_count": len(items),
        "open_count": sum(1 for item in items if str(item.get("status", "")).strip().lower() == "open"),
        "closed_count": sum(1 for item in items if str(item.get("status", "")).strip().lower() == "closed"),
    }
    findings: list[str] = []
    for field, expected in expected_counts.items():
        if field in metadata and metadata.get(field) != expected:
            findings.append(f"refresh_metadata.{field} must equal {expected} from items, got {metadata.get(field)!r}")
    return findings


def _parse_external_intent_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw_value = value.strip()
    if raw_value.endswith("Z"):
        raw_value = raw_value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw_value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _checked_in_planning_issue_refs(target_root: Path) -> set[str]:
    planning_root = target_root / ".agentic-workspace" / "planning"
    if not planning_root.exists():
        return set()
    refs: set[str] = set()
    ref_patterns = (
        re.compile(r"(?<![\w/-])#(\d+)\b"),
        re.compile(r"/issues/(\d+)\b"),
    )
    for path in planning_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".toml", ".md"}:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        for pattern in ref_patterns:
            refs.update(f"#{match}" for match in pattern.findall(text))
    return refs


def _compact_external_intent_cache_items(
    *,
    items: list[dict[str, Any]],
    target_root: Path,
    refreshed_at: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    refreshed_at_datetime = _parse_external_intent_timestamp(refreshed_at) or datetime.now(timezone.utc).replace(microsecond=0)
    cutoff = refreshed_at_datetime - timedelta(days=EXTERNAL_INTENT_CACHE_CLOSED_RETENTION_DAYS)
    referenced_ids = _checked_in_planning_issue_refs(target_root)
    compacted: list[dict[str, Any]] = []
    retained_recent_closed = 0
    retained_referenced_closed = 0
    dropped_closed = 0
    for item in items:
        if str(item.get("status", "")).strip().lower() != "closed":
            compacted.append(item)
            continue
        item_id = str(item.get("id", "")).strip()
        closed_at = _parse_external_intent_timestamp(item.get("closed_at"))
        updated_at = _parse_external_intent_timestamp(item.get("updated_at"))
        recency_timestamp = closed_at or updated_at
        is_recent = recency_timestamp is None or recency_timestamp >= cutoff
        is_referenced = item_id in referenced_ids
        if is_recent or is_referenced:
            compacted.append(item)
            if is_recent:
                retained_recent_closed += 1
            if is_referenced:
                retained_referenced_closed += 1
        else:
            dropped_closed += 1
    return compacted, {
        "enabled": True,
        "storage": "cache",
        "closed_retention_days": EXTERNAL_INTENT_CACHE_CLOSED_RETENTION_DAYS,
        "cutoff": cutoff.replace(microsecond=0).isoformat(),
        "retained_item_count": len(compacted),
        "dropped_closed_count": dropped_closed,
        "retained_recent_closed_count": retained_recent_closed,
        "retained_referenced_closed_count": retained_referenced_closed,
        "referenced_issue_count": len(referenced_ids),
    }


def _refresh_github_external_intent_evidence(
    *,
    target_root: Path,
    repo: str | None,
    limit: int | None,
    state: str | None,
    storage: str,
    dry_run: bool,
) -> dict[str, Any]:
    evidence_path, evidence_relative_path, storage_class = _external_intent_evidence_write_location(target_root, storage)
    previous_payload = _load_existing_external_intent_evidence(evidence_path)

    resolved_state = str(state).strip() if state is not None else ""
    state_source = "explicit" if resolved_state else "default"
    if not resolved_state:
        resolved_state = "all"
        state_source = "product_default"
    if resolved_state not in {"open", "closed", "all"}:
        raise WorkspaceUsageError("--state must be one of: open, closed, all.")

    resolved_limit = limit
    limit_source = "explicit" if resolved_limit is not None else "default"
    if resolved_limit is None:
        resolved_limit = 1000
        limit_source = "product_default"
    if resolved_limit <= 0:
        raise WorkspaceUsageError("--limit must be greater than 0.")
    resolved_repo = _resolve_github_repo_for_external_intent(target_root=target_root, repo=repo)
    raw_issues = _run_gh_json(
        [
            "issue",
            "list",
            "--repo",
            resolved_repo,
            "--state",
            resolved_state,
            "--limit",
            str(resolved_limit),
            "--json",
            "number,title,state,url,labels,createdAt,updatedAt,closedAt,body,comments",
        ],
        cwd=target_root,
    )
    if not isinstance(raw_issues, list):
        raise WorkspaceUsageError("GitHub issue list did not return a JSON list.")
    items = [
        item
        for item in (
            _github_issue_to_external_intent_item(issue=issue, repo=resolved_repo) for issue in raw_issues if isinstance(issue, dict)
        )
        if item is not None
    ]
    items.sort(key=lambda item: int(str(item["id"]).lstrip("#") or "0"))
    previous_count = len([item for item in _list_payload(previous_payload.get("items")) if isinstance(item, dict)])
    refreshed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    fetched_item_count = len(items)
    fetched_open_count = sum(1 for item in items if item["status"] == "open")
    fetched_closed_count = sum(1 for item in items if item["status"] == "closed")
    cache_compaction: dict[str, Any] | None = None
    if storage_class == "cache":
        items, cache_compaction = _compact_external_intent_cache_items(
            items=items,
            target_root=target_root,
            refreshed_at=refreshed_at,
        )
    refresh_metadata: dict[str, Any] = {
        "adapter": "github-gh-cli",
        "repository": resolved_repo,
        "refreshed_at": refreshed_at,
        "item_count": len(items),
        "open_count": sum(1 for item in items if item["status"] == "open"),
        "closed_count": sum(1 for item in items if item["status"] == "closed"),
        "fetched_item_count": fetched_item_count,
        "fetched_open_count": fetched_open_count,
        "fetched_closed_count": fetched_closed_count,
        "limit": resolved_limit,
        "state": resolved_state,
        "state_source": state_source,
        "limit_source": limit_source,
        "command": f"gh issue list --state {resolved_state} --json number,title,state,url,labels,createdAt,updatedAt,closedAt,body,comments",
    }
    next_payload: dict[str, Any] = {
        "kind": "planning-external-intent-evidence/v1",
        "systems": ["github"],
        "refreshed_at": refreshed_at,
        "refresh_metadata": refresh_metadata,
        "items": items,
    }
    if cache_compaction is not None:
        next_payload["refresh_metadata"]["cache_compaction"] = cache_compaction
    if not dry_run:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(next_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return {
        "kind": "external-intent-refresh/v1",
        "provider": "github",
        "adapter": "github-gh-cli",
        "target": target_root.as_posix(),
        "storage": storage_class,
        "path": evidence_relative_path,
        "dry_run": dry_run,
        "written": not dry_run,
        "repository": resolved_repo,
        "refreshed_at": refreshed_at,
        "item_count": len(items),
        "open_count": next_payload["refresh_metadata"]["open_count"],
        "closed_count": next_payload["refresh_metadata"]["closed_count"],
        "fetched_item_count": fetched_item_count,
        "fetched_open_count": fetched_open_count,
        "fetched_closed_count": fetched_closed_count,
        "previous_item_count": previous_count,
        "cache_compaction": cache_compaction,
        "state": resolved_state,
        "limit": resolved_limit,
        "state_source": state_source,
        "limit_source": limit_source,
        "provider_rule": "Core planning consumes only provider-agnostic external intent evidence; GitHub access stays in this optional adapter.",
    }


def _tiny_preflight_payload(payload: dict[str, Any], *, config: WorkspaceConfig) -> dict[str, Any]:
    active_state = payload.get("active_planning_state", {})
    todo = active_state.get("todo", {}) if isinstance(active_state, dict) else {}
    execplans = active_state.get("execplans", {}) if isinstance(active_state, dict) else {}
    planning_record = active_state.get("planning_record", {}) if isinstance(active_state, dict) else {}
    active_execplans = execplans.get("active_execplans", []) if isinstance(execplans, dict) else []
    branch_posture = payload.get("branch_workflow_posture", {})
    if isinstance(branch_posture, dict):
        branch_posture = {
            key: branch_posture.get(key)
            for key in (
                "status",
                "current_branch",
                "default_branch",
                "risk",
                "recommended_next_action",
                "upstream_divergence",
                "shared_state_mutation_risk",
            )
            if key in branch_posture
        }
    local_memory = payload.get("local_memory", {})
    if isinstance(local_memory, dict):
        local_memory = {key: local_memory.get(key) for key in ("status", "path", "rule") if key in local_memory}
    closeout = payload.get("closeout_obligations", {})
    if isinstance(closeout, dict):
        closeout = {key: closeout.get(key) for key in ("status", "activation_rule", "detail_command") if key in closeout}
    posture = payload.get("operating_posture", {})
    if isinstance(posture, dict):
        posture = {key: posture.get(key) for key in ("status", "required_behavior_summary", "detail_command") if key in posture}
    intent = payload.get("durable_intent", {})
    if isinstance(intent, dict):
        subsystem = intent.get("subsystem_intent", {})
        intent = {
            "status": intent.get("status", "unknown"),
            "subsystem_intent": {
                "status": subsystem.get("status", "unknown") if isinstance(subsystem, dict) else "unknown",
                "matched_count": subsystem.get("matched_count", 0) if isinstance(subsystem, dict) else 0,
            },
            "inspect": intent.get("inspect", ""),
        }
    return {
        "kind": payload.get("kind", "preflight-response/v1"),
        "mode": "tiny-takeover-router",
        "target": payload.get("target", ""),
        "issued_at": payload.get("issued_at", ""),
        "preflight_token": payload.get("preflight_token", ""),
        "timestamp_hint": payload.get("timestamp_hint", ""),
        "branch_workflow_posture": branch_posture,
        "local_memory": local_memory,
        "workflow_obligations": {
            "status": payload.get("workflow_obligations", {}).get("status", "unknown")
            if isinstance(payload.get("workflow_obligations"), dict)
            else "unknown",
            "match_count": payload.get("workflow_obligations", {}).get("match_count", 0)
            if isinstance(payload.get("workflow_obligations"), dict)
            else 0,
            "detail_command": "agentic-workspace preflight --profile full --format json",
        },
        "closeout_obligations": closeout,
        "operating_posture": posture,
        "durable_intent": intent,
        "active_state_summary": {
            "todo_active_count": todo.get("active_count", 0) if isinstance(todo, dict) else 0,
            "active_execplan_count": len(active_execplans) if isinstance(active_execplans, list) else 0,
            "planning_status": planning_record.get("status", "unavailable") if isinstance(planning_record, dict) else "unavailable",
        },
        "detail_commands": {
            "full_takeover": f"{config.cli_invoke} preflight --target . --profile full --format json",
            "active_state": f"{config.cli_invoke} preflight --target . --active-only --profile full --format json",
            "startup": f'{config.cli_invoke} start --target . --profile tiny --task "<task>" --format json',
            "config": f"{config.cli_invoke} config --target . --profile tiny --format json",
            "summary": f"{config.cli_invoke} summary --target . --format json",
        },
    }


def _tiny_preflight_payload_fast(
    *,
    target_root: Path,
    config: WorkspaceConfig,
    issued_at: str,
    preflight_token: str,
    task_text: str | None,
    changed_paths: list[str] | None,
) -> dict[str, Any]:
    active_summary = _fast_planning_active_summary(target_root=target_root)
    active_execplan_count = 1 if active_summary.get("active_execplan") else 0
    durable_intent: dict[str, Any] = {
        "status": "not-evaluated",
        "subsystem_intent": {"status": "not-evaluated", "matched_count": 0},
        "inspect": f'{config.cli_invoke} start --target . --profile tiny --task "<task>" --format json',
    }
    if task_text or changed_paths:
        durable_intent = _intent_decision_projection(
            target_root=target_root,
            config=config,
            task_text=task_text,
            changed_paths=changed_paths,
            compact=True,
        )
        subsystem = durable_intent.get("subsystem_intent", {})
        durable_intent = {
            "status": durable_intent.get("status", "unknown"),
            "subsystem_intent": {
                "status": subsystem.get("status", "unknown") if isinstance(subsystem, dict) else "unknown",
                "matched_count": subsystem.get("matched_count", 0) if isinstance(subsystem, dict) else 0,
            },
            "inspect": durable_intent.get("inspect", ""),
        }
    return {
        "kind": "preflight-response/v1",
        "mode": "tiny-takeover-router",
        "target": target_root.as_posix(),
        "issued_at": issued_at,
        "preflight_token": preflight_token,
        "timestamp_hint": "Use this compact answer to recover orientation; request full takeover context only when needed.",
        "branch_workflow_posture": {
            key: value
            for key, value in _branch_workflow_posture_payload(target_root=target_root).items()
            if key
            in {
                "status",
                "current_branch",
                "default_branch",
                "risk",
                "recommended_next_action",
                "upstream_divergence",
                "shared_state_mutation_risk",
            }
        },
        "local_memory": {key: value for key, value in _local_memory_payload(config=config).items() if key in {"status", "path", "rule"}},
        "workflow_obligations": {
            "status": "not-evaluated",
            "match_count": 0,
            "detail_command": f"{config.cli_invoke} preflight --profile full --format json",
        },
        "closeout_obligations": {
            "status": "present",
            "activation_rule": "closeout obligations apply after implementation or lane closeout",
            "detail_command": f"{config.cli_invoke} report --target ./repo --section closeout_trust --format json",
        },
        "operating_posture": _operating_posture_payload(config=config, surface="preflight", compact=True),
        "durable_intent": durable_intent,
        "active_state_summary": {
            "todo_active_count": int(active_summary.get("todo_active_count", 0) or 0),
            "active_execplan_count": active_execplan_count,
            "planning_status": active_summary.get("planning_status", "unavailable"),
        },
        "immediate_next_allowed_action": {
            "action": "recover-orientation",
            "summary": "Use the compact recovery routes below; request full takeover context only if active state or obligations are unclear.",
            "command": f'{config.cli_invoke} start --target . --profile tiny --task "<task>" --format json',
            "run": f'{config.cli_invoke} start --target . --profile tiny --task "<task>" --format json',
            "risk": "read-only recovery routing",
            "required_inputs": ["current task"],
            "next_proof": "select proof after changed paths are known",
        },
        "detail_commands": {
            "full_takeover": f"{config.cli_invoke} preflight --target . --profile full --format json",
            "active_state": f"{config.cli_invoke} preflight --target . --active-only --profile full --format json",
            "startup": f'{config.cli_invoke} start --target . --profile tiny --task "<task>" --format json',
            "config": f"{config.cli_invoke} config --target . --profile tiny --format json",
            "summary": f"{config.cli_invoke} summary --target . --format json",
        },
    }


def _run_preflight_command(
    *,
    target_root: Path,
    active_only: bool = False,
    task_text: str | None = None,
    changed_paths: list[str] | None = None,
    profile: str = "tiny",
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
    if profile == "tiny" and not active_only:
        return _tiny_preflight_payload_fast(
            target_root=target_root,
            config=config,
            issued_at=issued_at,
            preflight_token=preflight_token,
            task_text=task_text,
            changed_paths=changed_paths,
        )

    active_state = _preflight_active_state_payload(target_root=target_root)
    planning_record = active_state.get("planning_record", {"status": "unavailable"})
    branch_workflow_posture = _branch_workflow_posture_payload(target_root=target_root)
    local_memory = _local_memory_payload(config=config)
    active_count = int(active_state.get("todo", {}).get("active_count", 0) or 0)
    obligation_record = (
        planning_record if isinstance(planning_record, dict) and (planning_record.get("status") == "present" or active_count > 0) else None
    )
    workflow_obligations = _workflow_obligations_report_payload(
        config=config,
        active_planning_record=obligation_record,
        task_text=task_text,
        changed_paths=changed_paths,
    )
    closeout_obligations = _closeout_workflow_obligations_payload(workflow_obligations)
    durable_intent = _intent_decision_projection(
        target_root=target_root,
        config=config,
        task_text=task_text,
        compact=True,
    )

    if active_only:
        # Return only compact active state for polling/monitoring.
        # This remains useful even when the repo has active TODO state but no active execplan.

        active_payload = {
            "kind": "preflight-response/v1",
            "mode": "active-state-only",
            "target": target_root.as_posix(),
            "issued_at": issued_at,
            "preflight_token": preflight_token,
            "timestamp_hint": "Run this periodically to poll current active state without startup overhead.",
            "branch_workflow_posture": branch_workflow_posture,
            "local_memory": local_memory,
            "memory_consult": _memory_consult_payload(target_root=target_root, compact=True, cli_invoke=config.cli_invoke),
            "workflow_obligations": workflow_obligations,
            "closeout_obligations": closeout_obligations,
            "operating_posture": _operating_posture_payload(config=config, surface="preflight", compact=True),
            "durable_intent": durable_intent,
            "skill_routing": _task_skill_recommendations_payload(
                target_root=target_root,
                task_text=task_text,
                cli_invoke=config.cli_invoke,
            ),
            "active_planning_state": active_state,
            "planning_record": planning_record if isinstance(planning_record, dict) else {"status": "unavailable"},
        }
        return active_payload

    # Full preflight: startup + config + active state for takeover recovery
    # Get startup guidance
    startup_payload = _defaults_payload().get("startup", {})
    tiny_safe_model = startup_payload.get("tiny_safe_model", {})
    first_compact_queries = [
        _command_with_cli_invoke(command=str(query), cli_invoke=config.cli_invoke)
        for query in tiny_safe_model.get("first_compact_queries", [])
    ]
    escalation_rules = _guidance_with_cli_invoke(value=startup_payload.get("escalation_cues", [])[:2], cli_invoke=config.cli_invoke)
    skill_routing = _guidance_with_cli_invoke(
        value=_startup_skill_routing_payload(
            cli_invoke=config.cli_invoke,
            enabled_advanced_features=config.advanced_features,
            target_root=target_root,
            task_text=task_text,
        ),
        cli_invoke=config.cli_invoke,
    )
    planning_record_present = isinstance(planning_record, dict) and (
        planning_record.get("status") == "present"
        or active_state.get("todo", {}).get("active_count", 0)
        or active_state.get("execplans", {}).get("active_execplans")
    )
    preflight_primary_command = (
        _command_with_cli_invoke(command="agentic-workspace summary --format json", cli_invoke=config.cli_invoke)
        if planning_record_present
        else None
    )

    # Get config
    config_payload = _config_payload(config=config)

    startup_guidance = {
        "kind": "preflight-response/v1",
        "mode": "full-takeover-context",
        "target": target_root.as_posix(),
        "issued_at": issued_at,
        "preflight_token": preflight_token,
        "timestamp_hint": "Use this to bootstrap into an interrupted or takeover recovery.",
        "startup_guidance": {
            "context_router": _context_router_family_payload(cli_invoke=config.cli_invoke, compact=True),
            "entrypoint": startup_payload.get("default_canonical_agent_instructions_file", "AGENTS.md"),
            "entry_query": _command_with_cli_invoke(
                command=str(tiny_safe_model.get("entry_query", 'agentic-workspace start --profile tiny --task "<task>" --format json')),
                cli_invoke=config.cli_invoke,
            ),
            "primary_next_action": {
                "action": "continue-active-planning-record" if planning_record_present else "use-preflight-context",
                "summary": (
                    str(planning_record.get("next_action", "") or "Continue from the active planning record.")
                    if planning_record_present
                    else "Use this preflight answer as takeover context; run more commands only when a listed route is needed."
                ),
                "command": preflight_primary_command,
                "run": preflight_primary_command,
                "risk": "read-only routing",
                "required_inputs": ["target repo", "current task"],
                "next_proof": "select proof after changed paths are known",
            },
            "first_compact_queries": first_compact_queries,
            "work_intent_gate": _guidance_with_cli_invoke(
                value=startup_payload.get("work_intent_gate", {}),
                cli_invoke=config.cli_invoke,
            ),
            "escalation_rules": escalation_rules,  # Top 2 most common
            "skill_routing": skill_routing,
        },
        "resolved_config": {
            "workspace_config": config_payload.get("workspace", {}),
            "config_enforcement": config_payload.get("config_enforcement", {}),
            "optimization_bias": config_payload.get("optimization_bias"),
            "agent_instructions_file": config_payload.get("workspace", {}).get("agent_instructions_file", "AGENTS.md"),
        },
        "branch_workflow_posture": branch_workflow_posture,
        "local_memory": local_memory,
        "memory_consult": _memory_consult_payload(target_root=target_root, compact=True, cli_invoke=config.cli_invoke),
        "workflow_obligations": workflow_obligations,
        "closeout_obligations": closeout_obligations,
        "operating_posture": _operating_posture_payload(config=config, surface="preflight"),
        "durable_intent": durable_intent,
        "active_planning_state": active_state,
    }
    vague_orientation = _vague_outcome_orientation_payload(task_text=task_text, cli_invoke=config.cli_invoke)
    if vague_orientation["applies_to_current_task"]:
        startup_guidance["startup_guidance"]["vague_outcome_orientation"] = vague_orientation
    if profile == "tiny":
        return _tiny_preflight_payload(startup_guidance, config=config)
    return startup_guidance


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
    shared_state_risk = _workspace_shared_state_mutation_risk(target_root=target_root)
    upstream_divergence = _git_upstream_divergence(target_root=target_root)

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
            "upstream_divergence": upstream_divergence,
            "shared_state_mutation_risk": shared_state_risk,
            "recommended_next_action": "Inspect git branch state before implementation, commit, or push.",
        }

    default_branch_known = bool(default_branch)
    on_default_branch = default_branch_known and current_branch == default_branch
    likely_default_name = current_branch in {"main", "master", "trunk"}
    risk = "default-branch-commit-risk" if on_default_branch or (not default_branch_known and likely_default_name) else "normal"
    if shared_state_risk["risk"] == "high":
        recommended_next_action = str(shared_state_risk["recommended_next_action"])
    elif risk == "default-branch-commit-risk":
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
        "upstream_divergence": upstream_divergence,
        "shared_state_mutation_risk": shared_state_risk,
        "sources": sources,
        "recommended_next_action": recommended_next_action,
    }


def _workspace_shared_state_mutation_risk(*, target_root: Path) -> dict[str, Any]:
    changed_paths = _git_status_short_paths(target_root=target_root)
    surfaces = [_workspace_shared_state_surface(path) for path in changed_paths]
    surfaces = [surface for surface in surfaces if surface is not None]
    if not surfaces:
        return {
            "kind": "workspace-shared-state-mutation-risk/v1",
            "status": "clear",
            "risk": "low",
            "changed_surface_count": 0,
            "surfaces": [],
            "recommended_next_action": "No changed Agentic Workspace shared-state surfaces detected.",
            "rule": "Shared-state risk is merge pressure, not a lock or concurrency guarantee.",
        }
    high_classes = {"planning-live-state", "active-planning-execplan", "workspace-policy", "durable-memory-note"}
    risk = "high" if any(surface["class"] in high_classes for surface in surfaces) else "medium"
    first = surfaces[0]
    return {
        "kind": "workspace-shared-state-mutation-risk/v1",
        "status": "attention",
        "risk": risk,
        "changed_surface_count": len(surfaces),
        "surfaces": surfaces[:12],
        "recommended_next_action": (
            f"Review changed shared workspace surface {first['path']} before closeout or push; "
            "confirm it is intentional branch-local state or durable shared knowledge."
        ),
        "rule": "Shared-state risk is merge pressure, not a lock or concurrency guarantee.",
    }


def _workspace_shared_state_surface(path: str) -> dict[str, str] | None:
    normalized = path.replace("\\", "/")
    if normalized == ".agentic-workspace/planning/state.toml":
        return {
            "path": normalized,
            "class": "planning-live-state",
            "why": "selects active or queued future work and is a shared hot file",
        }
    if normalized.startswith(".agentic-workspace/planning/execplans/") and "/archive/" not in normalized:
        return {
            "path": normalized,
            "class": "active-planning-execplan",
            "why": "active execution contracts can conflict when multiple branches edit the same plan",
        }
    if normalized in {".agentic-workspace/config.toml", ".agentic-workspace/OWNERSHIP.toml"}:
        return {
            "path": normalized,
            "class": "workspace-policy",
            "why": "config and ownership changes are rare but high-impact shared policy edits",
        }
    if normalized == ".agentic-workspace/config.local.toml":
        return {
            "path": normalized,
            "class": "local-only-config",
            "why": "local config should normally remain uncommitted and machine-local",
        }
    if normalized == ".agentic-workspace/config.local.toml.example":
        return {
            "path": normalized,
            "class": "local-config-example",
            "why": "shared examples must remain portable and free of user-specific settings",
        }
    if normalized.startswith(".agentic-workspace/memory/repo/") and normalized.endswith(".md"):
        return {
            "path": normalized,
            "class": "durable-memory-note",
            "why": "durable shared knowledge can conflict when branches update the same note",
        }
    if normalized.startswith(".agentic-workspace/") and (
        normalized.endswith(".toml") or normalized.endswith(".json") or normalized.endswith(".md")
    ):
        return {
            "path": normalized,
            "class": "workspace-surface",
            "why": "checked-in workspace surface participates in ordinary git merge semantics",
        }
    return None


def _git_status_short_paths(*, target_root: Path) -> list[str]:
    if _git_metadata_dir(target_root=target_root) is None:
        return []
    try:
        completed = subprocess.run(
            ["git", "-C", str(target_root), "status", "--short", "--untracked-files=all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if completed.returncode != 0:
        return []
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        raw_path = line[3:].strip()
        if " -> " in raw_path:
            raw_path = raw_path.split(" -> ", 1)[1].strip()
        normalized = raw_path.replace("\\", "/")
        if normalized:
            paths.append(normalized)
    return paths


def _git_upstream_divergence(*, target_root: Path) -> dict[str, Any]:
    if _git_metadata_dir(target_root=target_root) is None:
        return {"status": "unavailable", "ahead": None, "behind": None}
    try:
        completed = subprocess.run(
            ["git", "-C", str(target_root), "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return {"status": "unknown", "ahead": None, "behind": None}
    if completed.returncode != 0:
        return {"status": "unknown", "ahead": None, "behind": None}
    parts = completed.stdout.strip().split()
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return {"status": "unknown", "ahead": None, "behind": None}
    ahead = int(parts[0])
    behind = int(parts[1])
    return {
        "status": "diverged" if ahead and behind else "ahead" if ahead else "behind" if behind else "in-sync",
        "ahead": ahead,
        "behind": behind,
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


def _read_budget_payload(*, profile: str, current_need: str, required_sections: list[str], optional_sections: list[str]) -> dict[str, Any]:
    if profile == "tiny":
        max_detail = "next-action packet only"
    elif profile == "compact":
        max_detail = "current-state packet"
    else:
        max_detail = "full diagnostic packet"
    return {
        "profile": profile,
        "current_need": current_need,
        "max_detail": max_detail,
        "required_sections": required_sections,
        "optional_sections": optional_sections,
        "raw_file_reads": "only after a detail command or active plan points there",
    }


def _adaptive_routing_payload(
    *,
    surface: str,
    profile: str,
    current_need: str,
    why_this_packet: str,
    required_sections: list[str],
    optional_sections: list[str],
    detail_commands: dict[str, str],
    when_to_escalate: list[str],
    not_needed_now: list[str],
) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/adaptive-routing/v1",
        "surface": surface,
        "current_need": current_need,
        "read_budget": _read_budget_payload(
            profile=profile,
            current_need=current_need,
            required_sections=required_sections,
            optional_sections=optional_sections,
        ),
        "why_this_packet": why_this_packet,
        "when_to_escalate": when_to_escalate,
        "not_needed_now": not_needed_now,
        "detail_commands": detail_commands,
        "rule": "Return the smallest packet that supports the next correct action; escalate detail only when a listed condition applies.",
    }


def _tiny_adaptive_routing_payload(
    *,
    surface: str,
    profile: str = "tiny",
    current_need: str,
    why_this_packet: str,
    detail_commands: dict[str, str],
    when_to_escalate: list[str],
    not_needed_now: list[str],
) -> dict[str, Any]:
    return {
        "current_need": current_need,
        "read_budget": {
            "profile": profile,
            "raw_file_reads": "only after a detail command points there",
        },
        "why": why_this_packet,
        "escalate_when": when_to_escalate[:3],
        "not_needed_now": not_needed_now[:3],
        "detail_commands": detail_commands,
    }


def _tiny_start_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Project startup context to the smallest schema-compatible first-contact answer."""
    immediate = copy.deepcopy(payload["immediate_next_allowed_action"])
    if not immediate.get("command") and not immediate.get("read_first"):
        immediate["required_inputs"] = []
        immediate["next_proof"] = "select proof after changed paths are known"
    skill_routing = payload.get("skill_routing", {})
    task_recommendations = skill_routing.get("task_recommendations", {}) if isinstance(skill_routing, dict) else {}
    top_recommendations = task_recommendations.get("top_recommendations", []) if isinstance(task_recommendations, dict) else []
    preferred_routes = [
        {"task_shape": "current task", "skill": str(item.get("id", ""))}
        for item in top_recommendations[:2]
        if isinstance(item, dict) and item.get("id")
    ]
    if not preferred_routes and isinstance(skill_routing, dict):
        preferred_routes = [
            {"task_shape": str(item.get("task_shape", "")), "skill": str(item.get("skill", ""))}
            for item in skill_routing.get("preferred_routes", [])[:2]
            if isinstance(item, dict)
        ]

    task_intent = payload.get("task_intent", {})
    detail_commands = {
        "known_changed_paths": "agentic-workspace implement --profile tiny --changed <paths> --format json",
        "active_state": "agentic-workspace summary --format json",
        "task_scoped_state": "agentic-workspace summary --profile compact --task <task> --format json",
        "takeover_or_recovery": "agentic-workspace preflight --format json",
        "startup_reference": "agentic-workspace defaults --section startup --format json",
    }
    if isinstance(task_intent, dict) and task_intent.get("implement_changed_command"):
        detail_commands["known_changed_paths"] = "Use task_intent.implement_changed_command after changed paths are known."

    feature_tier = payload.get("feature_tier", {})
    active_tier = feature_tier.get("active", {}) if isinstance(feature_tier, dict) else {}
    compact_active_tier = {
        key: active_tier.get(key) for key in ("id", "modules", "preset", "source") if isinstance(active_tier, dict) and key in active_tier
    }
    identity = payload.get("invoked_cli_identity", {})
    compact_identity = {
        key: identity.get(key)
        for key in ("kind", "package", "version", "source_class", "module_path", "target_relation", "compatibility")
        if isinstance(identity, dict) and key in identity
    }

    projected = {
        "kind": payload["kind"],
        "target": ".",
        "adaptive_routing": _tiny_adaptive_routing_payload(
            surface="start",
            current_need=payload.get("adaptive_routing", {}).get("current_need", "first-contact-routing"),
            why_this_packet=payload.get("adaptive_routing", {}).get(
                "why_this_packet",
                "Tiny startup returns only identity, next action, active-state summary, obligations, and direct detail commands.",
            ),
            detail_commands=detail_commands,
            when_to_escalate=[
                "changed paths are known",
                "active planning or handoff state matters",
                "takeover or recovery is needed",
                "config or proof selection becomes the question",
            ],
            not_needed_now=[
                "raw planning files",
                "full summary",
                "historical audit detail",
                "full memory tree",
            ],
        ),
        "invoked_cli_identity": compact_identity,
        "cli_invocation": payload.get("cli_invocation", {}),
        "startup_sequence": payload["startup_sequence"][:1],
        "context_router": {
            "kind": "workspace-context-router-family/v1",
            "first_view": "start",
            "rule": "This tiny profile is the first-contact answer; run detail commands only when the next action says why.",
            "detail_commands": detail_commands,
        },
        "feature_tier": {
            "active": compact_active_tier,
            "detail_command": feature_tier.get("detail_command", "agentic-workspace modules --target ./repo --format json")
            if isinstance(feature_tier, dict)
            else "agentic-workspace modules --target ./repo --format json",
        },
        "active_state_summary": payload["active_state_summary"],
        "package_boundary": payload["package_boundary"],
        "authority_markers": payload["authority_markers"][:1],
        "immediate_next_allowed_action": immediate,
        "workflow_obligations": {
            "status": payload.get("workflow_obligations", {}).get("status", "unknown"),
            "match_count": payload.get("workflow_obligations", {}).get("match_count", 0),
            "detail_command": payload.get("workflow_obligations", {}).get("detail_command", "agentic-workspace preflight --format json"),
        },
        "closeout_obligations": {
            "status": payload.get("closeout_obligations", {}).get("status", "unknown"),
            "activation_rule": payload.get("closeout_obligations", {}).get(
                "activation_rule",
                "closeout obligations apply after implementation or lane closeout, not ordinary first-contact orientation",
            ),
            "detail_command": payload.get("closeout_obligations", {}).get(
                "detail_command",
                "agentic-workspace report --target ./repo --section closeout_trust --format json",
            ),
        },
        "memory_consult": {
            "status": payload.get("memory_consult", {}).get("status", "unknown"),
            "read_first": payload.get("memory_consult", {}).get("read_first", []),
            "do_not_bulk_read": payload.get("memory_consult", {}).get("do_not_bulk_read", True),
        },
        "operating_posture": {
            "status": payload.get("operating_posture", {}).get("status", "unknown"),
            "required_behavior_summary": payload.get("operating_posture", {}).get("required_behavior_summary", ""),
        },
        "delegation_decision": _compact_start_delegation_decision(payload.get("delegation_decision", {})),
        "skill_routing": {
            "status": skill_routing.get("status", "unknown") if isinstance(skill_routing, dict) else "unknown",
            "rule": "Use listed skills only when directly relevant; otherwise proceed from the next action.",
            "query": (
                skill_routing.get("query", 'agentic-workspace skills --target ./repo --task "<task>" --format json')
                if isinstance(skill_routing, dict)
                else 'agentic-workspace skills --target ./repo --task "<task>" --format json'
            ),
            "preferred_routes": preferred_routes,
        },
    }
    proof = payload.get("proof", {})
    if isinstance(proof, dict) and proof.get("kind") == "proof-selection/v1":
        projected["proof"] = _compact_start_proof_payload(proof)
        immediate["next_proof"] = "run the selected required validation commands before closeout"
    cli_compatibility = payload.get("cli_compatibility", {})
    if isinstance(cli_compatibility, dict) and cli_compatibility.get("status") in {"blocking-drift", "warning-drift"}:
        projected["cli_compatibility"] = cli_compatibility
    vague_orientation = payload.get("vague_outcome_orientation", {})
    if isinstance(vague_orientation, dict) and vague_orientation.get("applies_to_current_task") is True:
        projected["vague_outcome_orientation"] = vague_orientation
    durable_intent = payload.get("durable_intent", {})
    subsystem_intent = durable_intent.get("subsystem_intent", {}) if isinstance(durable_intent, dict) else {}
    matched_count = int(subsystem_intent.get("matched_count", 0) or 0) if isinstance(subsystem_intent, dict) else 0
    if isinstance(durable_intent, dict) and durable_intent.get("status") == "present" and matched_count:
        projected["durable_intent"] = _tiny_durable_intent(durable_intent)
    if isinstance(task_recommendations, dict) and task_recommendations.get("status") == "recommended":
        compact_recommendations = []
        for item in task_recommendations.get("top_recommendations", [])[:2]:
            if not isinstance(item, dict):
                continue
            compact_recommendations.append({key: item.get(key) for key in ("id", "path", "score") if item.get(key) not in ("", None)})
        projected["skill_routing"]["task_recommendations"] = {
            "status": task_recommendations.get("status", "recommended"),
            "top_recommendations": compact_recommendations,
            "warning_count": task_recommendations.get("warning_count", 0),
        }
    if isinstance(task_intent, dict) and task_intent.get("status") == "present":
        projected["task_intent"] = {
            "status": "present",
            "carry_forward_rule": task_intent.get("carry_forward_rule", ""),
            "requested_outcomes": task_intent.get("requested_outcomes", [])[:8],
            "implement_changed_command": task_intent.get("implement_changed_command"),
        }
        for optional_key in (
            "task_argument_mode",
            "task_file",
            "task_file_instruction",
            "task_excerpt",
            "task_digest",
            "task_text_length",
        ):
            if optional_key in task_intent:
                projected["task_intent"][optional_key] = task_intent[optional_key]
    startup_review = payload.get("startup_review", {})
    if isinstance(startup_review, dict) and startup_review.get("status") == "attention":
        projected["startup_review"] = startup_review
    if "prep_only_handoff" in payload:
        projected["prep_only_handoff"] = _compact_start_prep_only_handoff(payload["prep_only_handoff"])
    return projected


def _compact_start_proof_payload(proof: dict[str, Any]) -> dict[str, Any]:
    compact = {
        key: proof.get(key)
        for key in (
            "kind",
            "changed_paths",
            "selected_lanes",
            "required_commands",
            "required_validation_commands",
        )
        if key in proof
    }
    cli_authority_review = proof.get("cli_authority_review", {})
    if isinstance(cli_authority_review, dict):
        compact["cli_authority_review"] = {
            "status": cli_authority_review.get("status", "unknown"),
            "classifications": cli_authority_review.get("classifications", []),
            "detail_command": "agentic-workspace proof --profile full --changed <paths> --format json",
        }
    changed = proof.get("changed_paths", [])
    if isinstance(changed, list) and changed:
        compact["detail_command"] = "agentic-workspace proof --profile full --changed <paths> --format json"
    return compact


def _tiny_durable_intent(value: dict[str, Any]) -> dict[str, Any]:
    subsystem = value.get("subsystem_intent", {}) if isinstance(value.get("subsystem_intent"), dict) else {}
    ownership = subsystem.get("ownership_registry", {}) if isinstance(subsystem.get("ownership_registry"), dict) else {}
    return {
        "kind": value.get("kind", "agentic-workspace/durable-intent-decision/v1"),
        "status": value.get("status", "unknown"),
        "subsystem_intent": {
            "status": subsystem.get("status", "unknown"),
            "surface": subsystem.get("surface", ".agentic-workspace/system-intent/subsystems.toml"),
            "matched_count": subsystem.get("matched_count", 0),
            "ownership_registry": {key: ownership.get(key) for key in ("status", "surface", "subsystem_count") if key in ownership},
            "matches": [
                {key: match.get(key) for key in ("id", "match_source", "needs_review") if isinstance(match, dict) and key in match}
                for match in subsystem.get("matches", [])[:4]
                if isinstance(match, dict)
            ],
        },
        "inspect": value.get("inspect", "agentic-workspace report --target ./repo --section durable_intent --format json"),
    }


def _compact_start_delegation_decision(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    common_keys = (
        "kind",
        "status",
        "mode",
        "clarification_mode",
        "decision",
        "work_shape",
        "proof_burden",
        "quality_risk",
        "token_savings_expected",
        "required_next_action",
    )
    compact = {key: value.get(key) for key in common_keys if key in value}
    decision = str(value.get("decision", ""))
    config_effect = value.get("config_effect")
    config_changes_effective_behavior = isinstance(config_effect, dict) and (
        config_effect.get("configured_delegation_mode") != config_effect.get("delegation_mode")
        or config_effect.get("disabled_reason") not in (None, "")
        or config_effect.get("safe_to_auto_run_commands") is False
    )
    if decision != "stay-local" or value.get("required_next_action") != "continue-local" or config_changes_effective_behavior:
        routed_keys = ("route_obligation", "config_effect")
        if decision == "stay-local" and value.get("required_next_action") == "continue-local":
            routed_keys = ("config_effect",)
        for routed_key in routed_keys:
            if routed_key in value:
                routed_value = value.get(routed_key)
                if routed_key == "route_obligation" and isinstance(routed_value, dict):
                    compact[routed_key] = {
                        key: routed_value.get(key) for key in ("must", "report_if_skipped") if routed_value.get(key) not in ("", None)
                    }
                elif routed_key == "config_effect" and isinstance(routed_value, dict):
                    compact[routed_key] = {
                        key: routed_value.get(key)
                        for key in (
                            "authority",
                            "source_path",
                            "configured_delegation_mode",
                            "delegation_mode",
                            "safe_to_auto_run_commands",
                            "disabled_reason",
                            "execution_authority",
                        )
                        if key in routed_value
                    }
                else:
                    compact[routed_key] = routed_value
    if decision in {"suggest-delegation", "suggest-downroute", "suggest-escalation", "delegate-bounded-slice"}:
        compact["target"] = value.get("target")
        compact["reason"] = value.get("reason")
    if decision in {"suggest-escalation", "delegate-bounded-slice", "manual-handoff", "ask-human"}:
        if value.get("handoff_command"):
            compact["handoff_command"] = value.get("handoff_command")
        if value.get("manual_prompt"):
            compact["manual_prompt"] = value.get("manual_prompt")
        if value.get("delegation_next_step"):
            next_step = value.get("delegation_next_step")
            compact["delegation_next_step"] = (
                {
                    key: next_step.get(key)
                    for key in ("status", "action", "target", "command", "execution_methods", "must_report_if_not_run")
                    if key in next_step
                }
                if isinstance(next_step, dict)
                else next_step
            )
    return compact


def _compact_start_prep_only_handoff(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    keys = (
        "kind",
        "status",
        "reason",
        "first_command",
        "reference_command",
        "preferred_mutation_command_template",
        "after_write",
        "required_action",
        "minimal_success_criteria",
        "stop_after_summary",
        "open_execplan_after_creation",
        "manual_execplan_tightening",
        "allowed_write_scope",
        "allowed_after_new_plan",
        "forbidden_until_implementation_requested",
    )
    return {key: value.get(key) for key in keys if key in value}


def _is_prep_only_handoff_task(task_text: str | None) -> bool:
    normalized = " ".join((task_text or "").lower().split())
    if not normalized:
        return False
    future_or_handoff = any(
        marker in normalized
        for marker in (
            "future agent",
            "later agent",
            "later coding pass",
            "future coding pass",
            "durable state",
            "durable implementation",
            "plan/state",
            "repository state",
            "repo-visible state",
            "handoff",
            "continue later",
            "continuation",
            "prepare enough",
            "groundwork",
            "later pass",
            "next pass",
            "first slice",
            "safe start",
            "prepare the repo",
            "prepare repository",
            "future",
            "ready for",
        )
    )
    prep_or_plan = any(marker in normalized for marker in ("prepare", "plan", "decompose", "shape", "scaffold planning"))
    implementation_blocked = any(
        marker in normalized
        for marker in (
            "do not implement",
            "don't implement",
            "without implementing",
            "not implement",
            "no implementation",
            "no code changes",
            "no feature implementation",
            "do not build",
            "don't build",
            "do not scaffold",
            "don't scaffold",
            "not build",
        )
    )
    return future_or_handoff and (prep_or_plan or implementation_blocked)


def _is_config_posture_task(task_text: str | None) -> bool:
    normalized = " ".join((task_text or "").lower().split())
    if not normalized:
        return False
    posture_markers = (
        "configured operating",
        "operating posture",
        "reporting posture",
        "closeout setting",
        "closeout settings",
        "reporting setting",
        "reporting settings",
        "repository-specific closeout",
        "repo-specific closeout",
        "configured operating settings",
        "configured settings",
        "config settings",
        "local runtime settings",
        "delegation posture",
        "safe_to_auto_run_commands",
        "improvement_latitude",
        "optimization_bias",
        "workflow_obligations",
    )
    return any(marker in normalized for marker in posture_markers)


def _prep_only_handoff_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    planning_command = _command_with_cli_invoke(command="agentic-workspace planning --format json", cli_invoke=config.cli_invoke)
    summary_command = _command_with_cli_invoke(
        command="agentic-workspace summary --profile compact --format json", cli_invoke=config.cli_invoke
    )
    new_plan_template = _command_with_cli_invoke(
        command="agentic-planning new-plan --id <id> --title <title> --target . --activate --prep-only --format json",
        cli_invoke=config.cli_invoke,
    )
    return {
        "kind": "agentic-workspace/prep-only-handoff-route/v1",
        "status": "required",
        "reason": "The task asks for durable continuation state before implementation.",
        "first_command": new_plan_template,
        "reference_command": planning_command,
        "preferred_mutation_command_template": new_plan_template,
        "after_write": summary_command,
        "required_action": (
            "Create or continue canonical checked-in Planning state with new-plan --prep-only, verify with compact summary, then stop."
        ),
        "minimal_success_criteria": [
            "a prep-only execplan is registered in Planning state",
            "summary verification exits successfully",
            "no product, test, dependency, README feature, or handoff files were created",
        ],
        "stop_after_summary": True,
        "open_execplan_after_creation": "no, unless compact summary reports a blocking Planning problem",
        "manual_execplan_tightening": "defer unless summary reports a blocking Planning problem",
        "allowed_write_scope": [
            ".agentic-workspace/planning/state.toml",
            ".agentic-workspace/planning/execplans/",
            ".agentic-workspace/planning/decompositions/",
        ],
        "allowed_after_new_plan": [
            "run the after_write summary command",
            "make only the smallest schema-preserving Planning edit if summary reports a blocking problem",
            "otherwise stop and report the canonical Planning state created",
        ],
        "forbidden_until_implementation_requested": [
            "product source files",
            "tests or fixtures",
            "README feature docs",
            "package/dependency/app scaffold files",
            "freehand PLAN/HANDOFF/ARCHITECTURE docs",
            "manual JSON polishing or ad hoc validation loops",
        ],
    }


def _start_payload(
    *,
    target_root: Path,
    changed_paths: list[str],
    task_text: str | None = None,
    profile: str = "full",
) -> dict[str, Any]:
    startup_template = _CONTEXT_TEMPLATES["startup_context"]
    config = _load_workspace_config(target_root=target_root)
    if profile == "tiny":
        return _start_tiny_payload_fast(
            target_root=target_root,
            changed_paths=changed_paths,
            task_text=task_text,
            config=config,
            startup_template=startup_template,
        )
    descriptors = _module_operations()
    registry = _module_registry(descriptors=descriptors, target_root=target_root)
    installed_modules = [entry.name for entry in registry if entry.installed]
    preflight = _run_preflight_command(target_root=target_root, task_text=task_text, changed_paths=changed_paths, profile="full")
    active_state = preflight.get("active_planning_state", {})
    selected_modules = installed_modules or _preset_modules(descriptors).get(config.default_preset, [])
    if not installed_modules and isinstance(active_state, dict):
        active_count = active_state.get("todo", {}).get("active_count", 0)
        if active_count or active_state.get("planning_record", {}).get("status") == "present":
            selected_modules = ["planning"]
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
        step["command"] = _command_with_cli_invoke(command=step.get("command"), cli_invoke=config.cli_invoke)
    active_planning_present = bool(
        isinstance(planning_record, dict)
        and (
            planning_record.get("status") == "present"
            or active_state.get("todo", {}).get("active_count", 0)
            or active_state.get("execplans", {}).get("active_execplans")
        )
    )
    primary_command = (
        _command_with_cli_invoke(command="agentic-workspace summary --format json", cli_invoke=config.cli_invoke)
        if active_planning_present
        else None
    )

    workflow_obligations = preflight.get("workflow_obligations", {})
    compact_workflow_obligations = _compact_start_workflow_obligations(workflow_obligations)
    current_need = "continue-active-planning" if active_planning_present else "first-contact-routing"
    if changed_paths:
        current_need = "changed-path-startup"
    elif _is_config_posture_task(task_text):
        current_need = "config-posture-routing"
    elif _is_prep_only_handoff_task(task_text):
        current_need = "prep-only-planning-routing"
    payload: dict[str, Any] = {
        "kind": "startup-context/v1",
        "target": target_root.as_posix(),
        "invoked_cli_identity": _invoked_cli_identity_payload(target_root=target_root, compact=True),
        "startup_sequence": startup_sequence,
        "context_router": _context_router_family_payload(cli_invoke=config.cli_invoke, compact=True),
        "adaptive_routing": {
            "current_need": current_need,
            "read_budget": f"{profile}; raw files only by detail command",
            "detail_commands": {
                "c": _command_with_cli_invoke(
                    command="agentic-workspace implement --profile tiny --changed <paths> --format json",
                    cli_invoke=config.cli_invoke,
                ),
                "t": _command_with_cli_invoke(
                    command='agentic-workspace summary --profile compact --task "<task>" --format json',
                    cli_invoke=config.cli_invoke,
                ),
            },
            "escalate_when": ["changed paths", "handoff", "lane/epic"],
        },
        "feature_tier": _feature_tier_payload(
            selected_modules=selected_modules,
            installed_modules=installed_modules or None,
            resolved_preset=config.default_preset,
            config=config,
            compact=True,
        ),
        "active_state_summary": {
            "todo_active_count": active_state.get("todo", {}).get("active_count", 0),
            "active_execplan": active_execplan,
            "planning_status": planning_record.get("status", "unavailable") if isinstance(planning_record, dict) else "unavailable",
        },
        "package_boundary": _package_boundary_payload(target_root=target_root),
        "authority_markers": _authority_markers_for_startup(active_execplan=active_execplan),
        "immediate_next_allowed_action": {
            "action": ("continue-active-planning-record" if active_planning_present else "choose-smallest-workflow-shape"),
            "summary": next_action,
            "command": primary_command,
            "run": primary_command,
            "risk": "read-only routing",
            "required_inputs": ["target repo", "current task"],
            "next_proof": "run proof selection once changed paths are known",
            "read_first": (
                [_command_with_cli_invoke(command="agentic-workspace summary --format json", cli_invoke=config.cli_invoke)]
                if active_planning_present
                else []
            ),
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
        },
        "workflow_obligations": compact_workflow_obligations,
        "closeout_obligations": _compact_start_closeout_obligations(preflight.get("closeout_obligations", {})),
        "memory_consult": _memory_consult_payload(
            target_root=target_root,
            changed_paths=changed_paths,
            compact=True,
            cli_invoke=config.cli_invoke,
        ),
        "operating_posture": _operating_posture_payload(config=config, surface="start", compact=True),
        "skill_routing": _guidance_with_cli_invoke(
            value=_startup_skill_routing_payload(
                cli_invoke=config.cli_invoke,
                enabled_advanced_features=config.advanced_features,
                compact=True,
                target_root=target_root,
                task_text=task_text,
            ),
            cli_invoke=config.cli_invoke,
        ),
    }
    startup_review = _workspace_absence_startup_review(target_root=target_root, config=config)
    if startup_review["status"] == "attention":
        payload["startup_review"] = startup_review
    task_intent = _task_intent_carry_forward_payload(task_text=task_text, cli_invoke=config.cli_invoke)
    if task_intent["status"] == "present":
        payload["task_intent"] = task_intent
    task_mentioned_paths = _task_mentioned_existing_paths(task_text=task_text, target_root=target_root)
    vague_orientation = _vague_outcome_orientation_payload(task_text=task_text, cli_invoke=config.cli_invoke)
    if vague_orientation["applies_to_current_task"]:
        payload["vague_outcome_orientation"] = vague_orientation
    if task_text or changed_paths:
        durable_intent = _intent_decision_projection(
            target_root=target_root,
            config=config,
            task_text=task_text,
            changed_paths=changed_paths,
            compact=True,
        )
        subsystem_projection = durable_intent.get("subsystem_intent", {})
        subsystem_matched_count = int(subsystem_projection.get("matched_count", 0) or 0) if isinstance(subsystem_projection, dict) else 0
        if task_text or subsystem_matched_count:
            payload["durable_intent"] = durable_intent
    execution_posture = _execution_posture_payload(
        config=config,
        changed_paths=_normalize_changed_paths(changed_paths),
        task_text=task_text,
    )
    payload["delegation_decision"] = execution_posture["delegation_decision"]
    if not active_planning_present and task_mentioned_paths and not changed_paths and not _is_config_posture_task(task_text):
        implement_command = str(task_intent.get("implement_changed_command", "")) if isinstance(task_intent, dict) else ""
        if implement_command:
            implement_command = implement_command.replace("<paths>", " ".join(task_mentioned_paths))
        else:
            implement_command = _command_with_cli_invoke(
                command=f"agentic-workspace implement --profile tiny --changed {' '.join(task_mentioned_paths)} --format json",
                cli_invoke=config.cli_invoke,
            )
        payload["immediate_next_allowed_action"] = {
            "action": "inspect-known-task-paths",
            "summary": (
                "The task text names existing repo paths. Run the tiny implement surface for those paths before broader startup "
                "or raw workspace reads."
            ),
            "command": implement_command,
            "run": implement_command,
            "risk": "read-only changed-path routing",
            "required_inputs": ["target repo", "named path(s)"],
            "next_proof": "use the proof.required_commands from implement output",
            "read_first": [implement_command],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
            "detected_paths": task_mentioned_paths,
        }
    elif not active_planning_present and _is_prep_only_handoff_task(task_text):
        prep_only = _prep_only_handoff_payload(config=config)
        planning_command = prep_only["first_command"]
        summary_command = prep_only["after_write"]
        payload["prep_only_handoff"] = prep_only
        payload["immediate_next_allowed_action"] = {
            "action": "create-prep-only-planning-state",
            "summary": (
                "Prep-only durable handoff requested. Run the prep-only new-plan command, create or continue canonical Planning "
                "state, verify with summary, then stop; do not create product source, tests, fixtures, README feature "
                "docs, dependencies, or app scaffolding until implementation is requested."
            ),
            "command": planning_command,
            "run": planning_command,
            "risk": "planning-only write routing",
            "required_inputs": ["target repo", "current task"],
            "next_proof": summary_command,
            "read_first": [],
            "open_execplan_only_when": "compact summary reports a blocking Planning problem after the prep-only scaffold is created",
        }
    elif _is_config_posture_task(task_text):
        config_command = _command_with_cli_invoke(
            command="agentic-workspace config --profile tiny --format json",
            cli_invoke=config.cli_invoke,
        )
        payload["immediate_next_allowed_action"] = {
            "action": "inspect-effective-config",
            "summary": (
                "The task asks about configured operating, reporting, closeout, or delegation posture. "
                "Run the tiny config surface before raw config files; use compact or full only if the tiny answer is insufficient."
            ),
            "command": config_command,
            "run": config_command,
            "risk": "read-only config routing",
            "required_inputs": ["target repo", "current task"],
            "next_proof": "no file proof unless the task later becomes an edit",
            "read_first": [config_command],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
        }
    cli_compatibility = _cli_compatibility_payload(config=config, compact=True)
    if cli_compatibility["configured"]:
        payload["cli_compatibility"] = cli_compatibility
    normalized_paths = _normalize_changed_paths(changed_paths)
    if normalized_paths:
        proof_payload = _proof_selection_for_changed_paths(
            changed_paths=normalized_paths,
            target_root=target_root,
            include_durable_intent=False,
        )
        payload["proof"] = _compact_start_proof_payload(proof_payload)
        payload["path_boundaries"] = [_boundary_warning_for_path(path) for path in normalized_paths]
    if profile == "tiny":
        payload["cli_invocation"] = _cli_invocation_payload(config=config)
        return _tiny_start_payload(payload)
    return payload


def _start_tiny_payload_fast(
    *,
    target_root: Path,
    changed_paths: list[str],
    task_text: str | None,
    config: WorkspaceConfig,
    startup_template: dict[str, Any],
) -> dict[str, Any]:
    active_summary = _fast_planning_active_summary(target_root=target_root)
    active_planning_present = bool(active_summary["todo_active_count"] or active_summary["active_execplan"])
    next_action_summary = (
        "Run the compact planning summary before implementation."
        if active_planning_present
        else str(startup_template["fallback_next_action"])
    )
    primary_command = (
        _command_with_cli_invoke(command="agentic-workspace summary --format json", cli_invoke=config.cli_invoke)
        if active_planning_present
        else None
    )
    startup_sequence = [
        {
            "id": "entrypoint",
            "command": None,
            "surface": config.agent_instructions_file,
            "why": "configured ordinary repo startup entrypoint",
        }
    ]
    current_need = "continue-active-planning" if active_planning_present else "first-contact-routing"
    if changed_paths:
        current_need = "changed-path-startup"
    elif _is_config_posture_task(task_text):
        current_need = "config-posture-routing"
    elif _is_prep_only_handoff_task(task_text):
        current_need = "prep-only-planning-routing"
    installed_modules = _fast_installed_modules(target_root=target_root)
    selected_modules = installed_modules or _preset_modules(_module_operations()).get(config.default_preset, [])
    payload: dict[str, Any] = {
        "kind": "startup-context/v1",
        "target": target_root.as_posix(),
        "invoked_cli_identity": _invoked_cli_identity_payload(target_root=target_root, compact=True),
        "cli_invocation": _cli_invocation_payload(config=config),
        "startup_sequence": startup_sequence,
        "context_router": _context_router_family_payload(cli_invoke=config.cli_invoke, compact=True),
        "adaptive_routing": {
            "current_need": current_need,
            "read_budget": {
                "profile": "tiny",
                "raw_file_reads": "only after a detail command points there",
            },
            "why": "Tiny startup returns only identity, next action, active-state summary, obligations, and direct detail commands.",
            "escalate_when": [
                "changed paths are known",
                "active planning or handoff state matters",
                "takeover or recovery is needed",
            ],
            "not_needed_now": [
                "raw planning files",
                "full summary",
                "historical audit detail",
            ],
            "detail_commands": {
                "known_changed_paths": "Use task_intent.implement_changed_command after changed paths are known.",
                "active_state": _command_with_cli_invoke(command="agentic-workspace summary --format json", cli_invoke=config.cli_invoke),
                "task_scoped_state": _command_with_cli_invoke(
                    command="agentic-workspace summary --profile compact --task <task> --format json",
                    cli_invoke=config.cli_invoke,
                ),
                "takeover_or_recovery": _command_with_cli_invoke(
                    command="agentic-workspace preflight --format json",
                    cli_invoke=config.cli_invoke,
                ),
                "startup_reference": _command_with_cli_invoke(
                    command="agentic-workspace defaults --section startup --format json",
                    cli_invoke=config.cli_invoke,
                ),
            },
        },
        "feature_tier": _feature_tier_payload(
            selected_modules=selected_modules,
            installed_modules=installed_modules or None,
            resolved_preset=config.default_preset,
            config=config,
            compact=True,
        ),
        "active_state_summary": active_summary,
        "package_boundary": _package_boundary_payload(target_root=target_root),
        "authority_markers": _authority_markers_for_startup(active_execplan=active_summary["active_execplan"]),
        "immediate_next_allowed_action": {
            "action": ("continue-active-planning-record" if active_planning_present else "choose-smallest-workflow-shape"),
            "summary": next_action_summary,
            "command": primary_command,
            "run": primary_command,
            "risk": "read-only routing",
            "required_inputs": [],
            "next_proof": "select proof after changed paths are known",
            "read_first": [primary_command] if primary_command else [],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
        },
        "workflow_obligations": {
            "status": "not-evaluated",
            "match_count": 0,
            "detail_command": _command_with_cli_invoke(command="agentic-workspace preflight --format json", cli_invoke=config.cli_invoke),
        },
        "closeout_obligations": {
            "status": "present",
            "activation_rule": "closeout obligations apply after implementation or lane closeout, not ordinary first-contact orientation",
            "detail_command": _command_with_cli_invoke(
                command="agentic-workspace report --target ./repo --section closeout_trust --format json",
                cli_invoke=config.cli_invoke,
            ),
        },
        "memory_consult": _tiny_memory_consult_payload(config=config),
        "operating_posture": _operating_posture_payload(config=config, surface="start", compact=True),
        "skill_routing": _guidance_with_cli_invoke(
            value=_startup_skill_routing_payload(
                cli_invoke=config.cli_invoke,
                enabled_advanced_features=config.advanced_features,
                compact=True,
                target_root=target_root,
                task_text=task_text,
            ),
            cli_invoke=config.cli_invoke,
        ),
    }
    startup_review = _workspace_absence_startup_review(target_root=target_root, config=config)
    if startup_review["status"] == "attention":
        payload["startup_review"] = startup_review
    task_intent = _task_intent_carry_forward_payload(task_text=task_text, cli_invoke=config.cli_invoke)
    if task_intent["status"] == "present":
        payload["task_intent"] = task_intent
    task_mentioned_paths = _task_mentioned_existing_paths(task_text=task_text, target_root=target_root)
    vague_orientation = _vague_outcome_orientation_payload(task_text=task_text, cli_invoke=config.cli_invoke)
    if vague_orientation["applies_to_current_task"]:
        payload["vague_outcome_orientation"] = vague_orientation
    if task_text or changed_paths:
        durable_intent = _intent_decision_projection(
            target_root=target_root,
            config=config,
            task_text=task_text,
            changed_paths=changed_paths,
            compact=True,
        )
        subsystem_projection = durable_intent.get("subsystem_intent", {})
        subsystem_matched_count = int(subsystem_projection.get("matched_count", 0) or 0) if isinstance(subsystem_projection, dict) else 0
        if task_text or subsystem_matched_count:
            payload["durable_intent"] = durable_intent
    execution_posture = _execution_posture_payload(
        config=config,
        changed_paths=_normalize_changed_paths(changed_paths),
        task_text=task_text,
    )
    payload["delegation_decision"] = execution_posture["delegation_decision"]
    if not active_planning_present and task_mentioned_paths and not changed_paths and not _is_config_posture_task(task_text):
        implement_command = str(task_intent.get("implement_changed_command", "")) if isinstance(task_intent, dict) else ""
        if implement_command:
            implement_command = implement_command.replace("<paths>", " ".join(task_mentioned_paths))
        else:
            implement_command = _command_with_cli_invoke(
                command=f"agentic-workspace implement --profile tiny --changed {' '.join(task_mentioned_paths)} --format json",
                cli_invoke=config.cli_invoke,
            )
        payload["immediate_next_allowed_action"] = {
            "action": "inspect-known-task-paths",
            "summary": (
                "The task text names existing repo paths. Run the tiny implement surface for those paths before broader startup "
                "or raw workspace reads."
            ),
            "command": implement_command,
            "run": implement_command,
            "risk": "read-only changed-path routing",
            "required_inputs": ["target repo", "named path(s)"],
            "next_proof": "use the proof.required_commands from implement output",
            "read_first": [implement_command],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
            "detected_paths": task_mentioned_paths,
        }
    elif not active_planning_present and _is_prep_only_handoff_task(task_text):
        prep_only = _prep_only_handoff_payload(config=config)
        payload["prep_only_handoff"] = prep_only
        payload["immediate_next_allowed_action"] = {
            "action": "create-prep-only-planning-state",
            "summary": (
                "Prep-only durable handoff requested. Run the prep-only new-plan command, create or continue canonical Planning "
                "state, verify with summary, then stop; do not create product source, tests, fixtures, README feature "
                "docs, dependencies, or app scaffolding until implementation is requested."
            ),
            "command": prep_only["first_command"],
            "run": prep_only["first_command"],
            "risk": "planning-only write routing",
            "required_inputs": ["target repo", "current task"],
            "next_proof": prep_only["after_write"],
            "read_first": [],
            "open_execplan_only_when": "compact summary reports a blocking Planning problem after the prep-only scaffold is created",
        }
    elif _is_config_posture_task(task_text):
        config_command = _command_with_cli_invoke(
            command="agentic-workspace config --profile tiny --format json", cli_invoke=config.cli_invoke
        )
        payload["immediate_next_allowed_action"] = {
            "action": "inspect-effective-config",
            "summary": (
                "The task asks about configured operating, reporting, closeout, or delegation posture. "
                "Run the tiny config surface before raw config files; use compact or full only if the tiny answer is insufficient."
            ),
            "command": config_command,
            "run": config_command,
            "risk": "read-only config routing",
            "required_inputs": ["target repo", "current task"],
            "next_proof": "no file proof unless the task later becomes an edit",
            "read_first": [config_command],
            "open_execplan_only_when": startup_template["open_execplan_only_when"],
        }
    normalized_paths = _normalize_changed_paths(changed_paths)
    if normalized_paths:
        payload["proof"] = _proof_selection_for_changed_paths(
            changed_paths=normalized_paths,
            target_root=target_root,
            include_durable_intent=False,
        )
        payload["path_boundaries"] = [_boundary_warning_for_path(path) for path in normalized_paths]
    cli_compatibility = _cli_compatibility_payload(config=config, compact=True)
    if cli_compatibility["configured"]:
        payload["cli_compatibility"] = cli_compatibility
    return _tiny_start_payload(payload)


def _fast_installed_modules(*, target_root: Path) -> list[str]:
    workspace_root = target_root / ".agentic-workspace"
    installed: list[str] = []
    if (workspace_root / "planning").exists():
        installed.append("planning")
    if (workspace_root / "memory").exists():
        installed.append("memory")
    return installed


def _fast_planning_active_summary(*, target_root: Path) -> dict[str, Any]:
    state_path = target_root / ".agentic-workspace" / "planning" / "state.toml"
    if not state_path.exists():
        return {"todo_active_count": 0, "active_execplan": None, "planning_status": "unavailable"}
    try:
        data = tomllib.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {"todo_active_count": 0, "active_execplan": None, "planning_status": "unavailable"}
    todo = data.get("todo", {}) if isinstance(data, dict) else {}
    active_items = todo.get("active_items", []) if isinstance(todo, dict) else []
    active_items = active_items if isinstance(active_items, list) else []
    active_execplan = None
    if active_items and isinstance(active_items[0], dict):
        active_execplan = active_items[0].get("surface")
    return {
        "todo_active_count": len(active_items),
        "active_execplan": active_execplan,
        "planning_status": "present" if active_items else "unavailable",
    }


def _planning_state_has_active_items(*, target_root: Path) -> bool:
    return bool(_fast_planning_active_summary(target_root=target_root)["todo_active_count"])


def _tiny_memory_consult_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/memory-consult/v1",
        "status": "recommended",
        "read_first": [".agentic-workspace/memory/repo/index.md"],
        "do_not_bulk_read": True,
        "why": "Start with the Memory index, then load only route-matched durable notes when the task or changed paths justify them.",
        "selection_rule": "after the baseline, load only manifest- or index-routed durable notes from touched files or explicit surfaces",
        "capture_helper": f"{config.cli_invoke} memory capture-note <slug> --summary <text> --files <changed paths> --format json",
    }


def _compact_start_workflow_obligations(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    relevant = value.get("relevant_to_current_work", [])
    if not isinstance(relevant, list):
        relevant = []
    match_evidence = value.get("match_evidence", {})
    if not isinstance(match_evidence, dict):
        match_evidence = {}
    configured_count = int(value.get("configured_count", 0) or 0)
    match_count = int(match_evidence.get("match_count", len(relevant)) or 0)
    return {
        "status": "matched" if match_count else "none-matched",
        "configured_count": configured_count,
        "match_count": match_count,
        "current_scope_tags": value.get("current_scope_tags", []),
        "relevant_ids": [str(item.get("id", "")) for item in relevant if isinstance(item, dict)],
        "detail_command": "agentic-workspace preflight --format json",
        "rule": value.get("rule", ""),
    }


def _compact_start_closeout_obligations(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    required = value.get("required_before_lane_closeout", [])
    if not isinstance(required, list):
        required = []
    return {
        "status": value.get("status", "unknown"),
        "required_before_lane_closeout_count": len(required),
        "required_before_lane_closeout_ids": [str(item.get("id", "")) for item in required if isinstance(item, dict)],
        "activation_rule": "closeout obligations apply after implementation or lane closeout, not ordinary first-contact orientation",
        "detail_command": "agentic-workspace report --target ./repo --section closeout_trust --format json",
    }


_TASK_STOPWORDS = {
    "add",
    "and",
    "are",
    "before",
    "behavior",
    "behaviour",
    "build",
    "change",
    "code",
    "create",
    "deliver",
    "docs",
    "file",
    "files",
    "fix",
    "for",
    "from",
    "function",
    "helper",
    "helpers",
    "implement",
    "into",
    "issue",
    "make",
    "module",
    "package",
    "pass",
    "public",
    "repo",
    "request",
    "requested",
    "run",
    "should",
    "small",
    "task",
    "test",
    "tests",
    "the",
    "this",
    "use",
    "with",
}


def _cli_invocation_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    target_root = config.target_root or Path.cwd()
    identity = _invoked_cli_identity_payload(target_root=target_root, compact=True)
    local_config_path = target_root / config_lib.WORKSPACE_LOCAL_CONFIG_PATH
    payload: dict[str, Any] = {
        "kind": "agentic-workspace/cli-invocation/v1",
        "primary": config.cli_invoke,
        "source": config.cli_invoke_source,
        "bare_command": DEFAULT_CLI_INVOKE,
        "fallback_when_unavailable": "Use primary from resolved config; config.local.toml [workspace].cli_invoke overrides bare PATH lookup.",
    }
    if config.cli_invoke != DEFAULT_CLI_INVOKE:
        payload["stale_bare_command_warning"] = (
            "Do not substitute the bare command for primary; PATH may resolve a stale installed selector outside this repo."
        )
    mismatch_reasons: list[str] = []
    if config.cli_invoke_source == "local-override" and identity["target_relation"] == "outside-target":
        mismatch_reasons.append("invoked CLI module is outside the target repo")
    if identity["source_class"] == "installed-package" and _is_agentic_workspace_source_checkout(config.target_root):
        mismatch_reasons.append("target repo looks like an agentic-workspace source checkout but invocation came from an installed package")
    if config.cli_invoke_source == "product-default" and local_config_path.exists():
        mismatch_reasons.append(".agentic-workspace/config.local.toml exists but did not supply workspace.cli_invoke")
    if (
        config.cli_invoke_source == "product-default"
        and identity["source_class"] == "installed-package"
        and identity["target_relation"] == "outside-target"
    ):
        mismatch_reasons.append("no repo-local invocation override is active; bare PATH may be stale for this repo")
    if mismatch_reasons:
        payload["mismatch"] = {
            "status": "attention",
            "reasons": mismatch_reasons,
            "invoked_source_class": identity["source_class"],
            "invoked_target_relation": identity["target_relation"],
            "required_next_action": (
                "Rerun startup with the configured cli_invocation.primary when it is repo-local; otherwise inspect "
                ".agentic-workspace/config.local.toml [workspace].cli_invoke before non-trivial edits."
            ),
            "trust": "lower-trust-until-confirmed",
        }
    return payload


def _extract_requested_outcomes(task_text: str | None) -> list[str]:
    text = str(task_text or "")
    if not text.strip():
        return []
    outcomes: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        token = value.strip().strip("`'\".,:;()[]{}")
        if not token:
            return
        if len(token) < 4 or token.lower() in _TASK_STOPWORDS:
            return
        if token not in seen:
            seen.add(token)
            outcomes.append(token)

    for match in re.finditer(r"`([^`]+)`", text):
        add(match.group(1))
    for match in re.finditer(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\(", text):
        add(match.group(0).split("(", 1)[0])
    for match in re.finditer(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b", text):
        add(match.group(0))
    for match in re.finditer(r"\b[A-Za-z][A-Za-z0-9]*[.][A-Za-z_][A-Za-z0-9_]*\b", text):
        add(match.group(0))
    return outcomes[:12]


def _task_mentioned_existing_paths(*, task_text: str | None, target_root: Path) -> list[str]:
    text = str(task_text or "")
    if not text.strip():
        return []
    candidates = re.findall(r"(?<![\w./\\-])(?:[\w.-]+[/\\])*[\w.-]+\.[A-Za-z0-9]{1,8}(?![\w/\\-])", text)
    found: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        normalized = raw.replace("\\", "/").strip("`'\".,;:()[]{}")
        if not normalized or normalized.lower().startswith(("http:", "https:")):
            continue
        candidate_path = Path(normalized)
        if candidate_path.is_absolute() or ".." in candidate_path.parts:
            continue
        if not (target_root / candidate_path).exists():
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append(normalized)
    return found[:6]


_TASK_INTENT_INLINE_COMMAND_MAX_CHARS = 1200
_TASK_INTENT_SCRATCH_FILE = WORKSPACE_LOCAL_SCRATCH_ROOT_PATH / "task-intent.txt"


def _task_intent_carry_forward_payload(*, task_text: str | None, cli_invoke: str) -> dict[str, Any]:
    task = str(task_text or "").strip()
    has_task = bool(task)
    requested_outcomes = _extract_requested_outcomes(task)
    command = "agentic-workspace implement --profile tiny --changed <paths> --format json"
    task_argument_mode = "absent"
    optional: dict[str, Any] = {}
    if has_task:
        if len(task) <= _TASK_INTENT_INLINE_COMMAND_MAX_CHARS:
            task_argument_mode = "inline"
            command = f"agentic-workspace implement --profile tiny --changed <paths> --task {_shell_quote(task)} --format json"
        else:
            task_argument_mode = "task-file"
            task_file = _TASK_INTENT_SCRATCH_FILE.as_posix()
            command = f"agentic-workspace implement --profile tiny --changed <paths> --task-file {task_file} --format json"
            optional = {
                "task_file": task_file,
                "task_file_instruction": (
                    "Write the original request once to this local scratch file, then pass --task-file instead of repeating "
                    "the full task text in follow-up commands."
                ),
                "task_excerpt": task[:180].rstrip() + "...",
                "task_digest": hashlib.sha256(task.encode("utf-8")).hexdigest()[:16],
                "task_text_length": len(task),
            }
    return {
        "kind": "agentic-workspace/task-intent-carry-forward/v1",
        "status": "present" if has_task else "absent",
        "carry_forward_rule": (
            "Carry the original task intent into implement --changed so acceptance reconciliation and objective-drift checks use the request."
        ),
        "task_text_available": has_task,
        "task_argument_mode": task_argument_mode,
        "requested_outcomes": requested_outcomes,
        "implement_changed_command": _command_with_cli_invoke(command=command, cli_invoke=cli_invoke),
        "closeout_rule": "Before closeout, map requested outcomes to delivered surfaces and proof; self-authored tests alone are not enough.",
        **optional,
    }


def _read_task_text_from_file(*, target_root: Path, task_file: str | None) -> str | None:
    if not task_file:
        return None
    raw_path = Path(task_file)
    path = raw_path if raw_path.is_absolute() else target_root / raw_path
    resolved = path.resolve()
    try:
        resolved.relative_to(target_root.resolve())
    except ValueError as exc:
        raise WorkspaceUsageError("--task-file must resolve inside the target repository.") from exc
    if not resolved.is_file():
        raise WorkspaceUsageError(f"--task-file does not exist or is not a file: {task_file}")
    return resolved.read_text(encoding="utf-8").strip()


def _read_changed_surface_text(*, target_root: Path, changed_paths: list[str], max_bytes: int = 200_000) -> str:
    chunks: list[str] = []
    remaining = max_bytes
    for path_text in changed_paths:
        if remaining <= 0:
            break
        path = (target_root / path_text).resolve()
        try:
            path.relative_to(target_root.resolve())
        except ValueError:
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        chunks.append(text[:remaining])
        remaining -= len(chunks[-1])
    return "\n".join(chunks)


def _objective_drift_payload(*, target_root: Path, changed_paths: list[str], task_text: str | None) -> dict[str, Any]:
    requested_outcomes = _extract_requested_outcomes(task_text)
    if not task_text:
        return {
            "kind": "agentic-workspace/objective-drift/v1",
            "status": "unavailable",
            "reason": "no task text was provided to compare against changed surfaces",
            "requested_outcomes": [],
            "missing_from_changed_surface": [],
        }
    if not requested_outcomes:
        return {
            "kind": "agentic-workspace/objective-drift/v1",
            "status": "not-enough-explicit-outcomes",
            "reason": "task text did not contain explicit symbols, code identifiers, or backticked outcomes",
            "requested_outcomes": [],
            "missing_from_changed_surface": [],
        }
    surface_text = _read_changed_surface_text(target_root=target_root, changed_paths=changed_paths)
    searchable = surface_text.lower()
    missing = [item for item in requested_outcomes if item.lower() not in searchable]
    status = "warning" if missing and changed_paths else "clear"
    return {
        "kind": "agentic-workspace/objective-drift/v1",
        "status": status,
        "requested_outcomes": requested_outcomes,
        "missing_from_changed_surface": missing,
        "rule": "Do not claim completion until each requested outcome is mapped to delivered behavior and proof, or explicitly marked out of scope.",
        "recommended_next_action": (
            "Inspect changed files, exports, docs, and tests for the missing requested outcomes before closeout."
            if status == "warning"
            else "Use acceptance reconciliation before closeout."
        ),
        "heuristic": "identifier and backtick-term overlap between task text and changed file contents",
    }


def _implement_payload(*, target_root: Path, changed_paths: list[str], task_text: str | None = None) -> dict[str, Any]:
    implementer_template = _CONTEXT_TEMPLATES["implementer_context"]
    normalized_paths = _normalize_changed_paths(changed_paths)
    config = _load_workspace_config(target_root=target_root)
    proof = (
        _proof_selection_for_changed_paths(
            changed_paths=normalized_paths,
            target_root=target_root,
            include_durable_intent=False,
        )
        if normalized_paths
        else copy.deepcopy(implementer_template["unknown_scope_proof"])
    )
    path_boundaries = [_boundary_warning_for_path(path) for path in normalized_paths]
    attention_paths = [item["path"] for item in path_boundaries if item["requires_attention"]]
    inspect_files = normalized_paths or list(implementer_template["default_inspect_files"])
    task_routing = _implementation_task_routing(target_root=target_root, task_text=task_text)
    execution_posture = _execution_posture_payload(
        config=config,
        changed_paths=normalized_paths,
        task_text=task_text,
    )
    implement_current_need = "changed-path-implementation" if normalized_paths else "unknown-scope-routing"
    payload = {
        "kind": "implementer-context/v1",
        "target": target_root.as_posix(),
        "adaptive_routing": _adaptive_routing_payload(
            surface="implement",
            profile="full",
            current_need=implement_current_need,
            why_this_packet=(
                "Changed paths are known, so implement can return bounded inspect files, proof, path warnings, and acceptance checks."
                if normalized_paths
                else "Changed paths are missing, so implement can only route the agent away from broad implementation."
            ),
            required_sections=[
                "changed_paths",
                "inspect_files",
                "proof",
                "acceptance_reconciliation",
                "objective_drift",
                "next_allowed_action",
            ],
            optional_sections=[
                "path_boundaries",
                "execution_posture",
                "delegation_decision",
                "durable_intent",
                "handoff_requirements",
            ],
            detail_commands={
                "tiny_next_action": "agentic-workspace implement --profile tiny --changed <paths> --format json",
                "proof_detail": "agentic-workspace proof --profile full --changed <paths> --format json",
                "active_state": "agentic-workspace summary --profile compact --changed <paths> --format json",
                "takeover_or_recovery": "agentic-workspace preflight --format json",
            },
            when_to_escalate=[
                "changed paths are missing or incomplete",
                "proof, path authority, or objective-drift warnings appear",
                "task routing says planning is needed",
                "delegation decision requests escalation or handoff",
            ],
            not_needed_now=[
                "full planning summary unless active state or task routing requires it",
                "raw planning files before compact summary points there",
                "unrelated memory notes",
            ],
        ),
        "changed_paths": normalized_paths,
        "inspect_files": inspect_files,
        "files_to_avoid": list(implementer_template["files_to_avoid"]),
        "package_boundary": _package_boundary_payload(target_root=target_root),
        "path_boundaries": path_boundaries,
        "authority_markers": [_authority_marker_for_path(path) for path in (normalized_paths or ["AGENTS.md", "llms.txt"])],
        "proof": proof,
        "required_validation_commands": proof["required_commands"],
        "acceptance_reconciliation": _acceptance_reconciliation_prompt_payload(task_text=task_text),
        "objective_drift": _objective_drift_payload(
            target_root=target_root,
            changed_paths=normalized_paths,
            task_text=task_text,
        ),
        "orientation": {
            "status": "changed-path-context" if normalized_paths else "unknown-scope",
            "minimum_before_editing": (
                "Inspect the listed files, path boundaries, workflow obligations, and selected proof before editing."
                if normalized_paths
                else "Provide --changed paths or run preflight before broad implementation."
            ),
            "preflight_command": "agentic-workspace preflight --format json",
            "summary_command": "agentic-workspace summary --format json",
            "trust_note": (
                "Skipping workspace orientation may be faster for this edit, but lowers continuation and review trust for planned or high-risk work."
            ),
        },
        "inference_limits": {
            "rule": (
                "implement --changed derives bounded context from changed paths, config, active planning, and package metadata; "
                "it can be used to inspect the live projection shape before contract, schema, or docs changes, but it does not know unstated intent."
            ),
            "can_infer": [
                "path-owned proof lanes",
                "configured workflow obligations visible from the target",
                "active planning assurance when Planning exposes it",
                "path boundary and generated-surface warnings",
                "current implementer-context projection keys for the selected changed paths",
            ],
            "cannot_infer": [
                "whether the human intended a larger lane than the changed paths imply",
                "whether proof commands were actually executed unless evidence is recorded elsewhere",
                "whether missing changed paths hide additional risk",
                "whether external tracker state is authoritative for the repo",
            ],
            "when_uncertain": (
                "Run preflight or summary and promote to checked-in planning before implementation when scope, proof, "
                "or continuation is not obvious."
            ),
        },
        "execution_posture": execution_posture,
        "delegation_decision": execution_posture["delegation_decision"],
        "durable_intent": _intent_decision_projection(
            target_root=target_root,
            config=config,
            task_text=task_text,
            changed_paths=normalized_paths,
            compact=True,
        ),
        "handoff_requirements": copy.deepcopy(implementer_template["handoff_requirements"]),
        "next_allowed_action": (
            implementer_template["next_allowed_action"]["attention"]
            if attention_paths
            else implementer_template["next_allowed_action"]["default"]
        ),
    }
    if task_routing is not None:
        payload["task_routing"] = task_routing
        if task_routing.get("status") == "needs-planning":
            payload["next_allowed_action"] = (
                "Promote/create an active planning record, or narrow to one explicit issue before implementation."
            )
            payload["handoff_requirements"]["stop_when"] = [
                "task routing status is needs-planning for broad external-work ingestion",
                *payload["handoff_requirements"]["stop_when"],
            ]
    return payload


def _tiny_implement_payload(payload: dict[str, Any]) -> dict[str, Any]:
    path_warnings = [
        {
            "path": item.get("path"),
            "authority": item.get("authority"),
            "warning": item.get("warning"),
        }
        for item in payload.get("path_boundaries", [])
        if isinstance(item, dict) and item.get("requires_attention")
    ]
    task_routing = payload.get("task_routing")
    next_action = payload.get("next_allowed_action", "")
    if isinstance(task_routing, dict) and task_routing.get("status") == "needs-planning":
        next_action = "Plan or narrow before implementation."
    elif path_warnings:
        next_action = "Resolve path authority warnings before editing."
    elif not payload.get("changed_paths"):
        next_action = "Provide --changed paths or use start/preflight before broad implementation."

    proof_commands = payload.get("required_validation_commands", [])
    primary_command = proof_commands[0] if isinstance(proof_commands, list) and proof_commands else None
    execution_posture = payload.get("execution_posture", {})
    capability = execution_posture.get("capability_posture", {}) if isinstance(execution_posture, dict) else {}
    runtime_resolution = execution_posture.get("runtime_resolution", {}) if isinstance(execution_posture, dict) else {}
    detail_commands = {
        "full_context": "agentic-workspace implement --profile full --changed <paths> --format json",
        "proof_detail": "agentic-workspace proof --profile full --changed <paths> --format json",
        "task_scoped_state": "agentic-workspace summary --profile compact --changed <paths> --format json",
        "takeover_or_recovery": "agentic-workspace preflight --format json",
    }
    return {
        "kind": "implementer-context-tiny/v1",
        "target": payload.get("target"),
        "adaptive_routing": _tiny_adaptive_routing_payload(
            surface="implement",
            current_need="changed-path-next-action" if payload.get("changed_paths") else "unknown-scope-routing",
            why_this_packet="Tiny implement returns only the next action, changed-path scope, proof commands, reconciliation checks, and escalation pointers.",
            detail_commands=detail_commands,
            when_to_escalate=[
                "changed paths are missing or wrong",
                "proof commands are insufficient",
                "objective drift is warning",
                "delegation or planning routing changes the next action",
            ],
            not_needed_now=[
                "package boundary detail when there are no warnings",
                "full execution posture unless delegation is selected",
                "raw workspace files",
            ],
        ),
        "next": {
            "action": next_action,
            "summary": next_action,
            "command": primary_command,
            "run": primary_command,
            "commands": proof_commands if isinstance(proof_commands, list) else [],
            "status": payload.get("orientation", {}).get("status", "unknown"),
            "ask_human_only_if": "scope, authority, risk, or intent is genuinely blocked after inspecting the listed paths",
        },
        "scope": {
            "changed_paths": payload.get("changed_paths", []),
            "inspect_files": payload.get("inspect_files", []),
            "warnings": path_warnings,
        },
        "proof": {
            "kind": payload.get("proof", {}).get("kind", "proof-selection/v1")
            if isinstance(payload.get("proof"), dict)
            else "proof-selection/v1",
            "required_commands": payload.get("required_validation_commands", []),
            "detail_command": "agentic-workspace proof --profile full --changed <paths> --format json",
        },
        "acceptance_reconciliation": _tiny_acceptance_reconciliation(payload.get("acceptance_reconciliation", {})),
        "objective_drift": _tiny_objective_drift(payload.get("objective_drift", {})),
        "routing": {
            "task_status": task_routing.get("status") if isinstance(task_routing, dict) else None,
            "work_shape": capability.get("work_shape"),
            "proof_burden": capability.get("proof_burden"),
            "delegation_recommendation": runtime_resolution.get("recommendation"),
        },
        "delegation_decision": _compact_start_delegation_decision(execution_posture.get("delegation_decision", {})),
        "detail_command": detail_commands["full_context"],
        "detail_commands": detail_commands,
    }


def _tiny_acceptance_reconciliation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    return {
        "status": value.get("status", "unknown"),
        "task_text_available": bool(value.get("task_text_available")),
        "requested_outcomes": value.get("requested_outcomes", []),
        "compact_closeout_prompt": value.get("compact_closeout_prompt", ""),
    }


def _tiny_objective_drift(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    return {
        "status": value.get("status", "unknown"),
        "requested_outcomes": value.get("requested_outcomes", []),
        "missing_from_changed_surface": value.get("missing_from_changed_surface", []),
        "recommended_next_action": value.get("recommended_next_action", ""),
    }


def _acceptance_reconciliation_prompt_payload(*, task_text: str | None) -> dict[str, Any]:
    has_task = bool(str(task_text or "").strip())
    requested_outcomes = _extract_requested_outcomes(task_text)
    return {
        "kind": "agentic-workspace/acceptance-reconciliation/v1",
        "status": "required-before-closeout" if has_task else "required-when-task-intent-is-known",
        "rule": "Validation success is not enough; before closeout, reconcile requested outcomes against delivered behavior and tests.",
        "requested_outcomes": requested_outcomes,
        "checklist": [
            "list each explicit user requirement or accepted planning criterion",
            "name the delivered surface or behavior for each requirement",
            "name proof covering each requirement, or mark the gap",
            "state intentional deviations before claiming success",
        ],
        "compact_closeout_prompt": (
            "Before final answer: requested -> delivered -> proof -> gaps/deviations. "
            "Do not claim completion from self-authored tests alone."
        ),
        "task_text_available": has_task,
        "task_carry_forward_hint": (
            "Pass --task from start into implement --changed when possible so this checklist can name concrete outcomes."
        ),
    }


def _implementation_task_routing(*, target_root: Path, task_text: str | None) -> dict[str, Any] | None:
    normalized = " ".join((task_text or "").lower().split())
    if not normalized:
        return None
    issue_refs = sorted(set(re.findall(r"#\d+", task_text or "")))
    external_terms = ("issue", "issues", "github", "tracker", "ticket", "tickets", "external work", "external-work")
    broad_terms = ("all", "open", "many", "multiple", "batch", "broad", "lane by lane", "lanes")
    intake_terms = ("ingest", "intake", "import", "sync", "triage", "implement")
    is_external_work = any(term in normalized for term in external_terms) or bool(issue_refs)
    is_broad = any(term in normalized for term in broad_terms) or len(issue_refs) > 1
    asks_intake_or_implementation = any(term in normalized for term in intake_terms)
    if not is_external_work or not asks_intake_or_implementation:
        return {
            "status": "not-external-work",
            "task": task_text,
            "broad_external_work": False,
            "allowed_next_actions": ["continue with changed-path proof selection"],
        }
    if len(issue_refs) == 1 and not is_broad:
        return {
            "status": "narrow-external-work",
            "task": task_text,
            "issue_refs": issue_refs,
            "broad_external_work": False,
            "allowed_next_actions": ["continue if the issue is small enough for direct work or promote it through upstream-task intake"],
        }
    planning_status = "unavailable"
    readiness: dict[str, Any] = {}
    try:
        from repo_planning_bootstrap.installer import planning_summary

        summary = planning_summary(target=target_root, profile="compact")
        planning_record = summary.get("planning_record", {})
        if isinstance(planning_record, dict):
            planning_status = str(planning_record.get("status", "unavailable"))
        raw_readiness = summary.get("execution_readiness", {})
        if isinstance(raw_readiness, dict):
            readiness = raw_readiness
    except ImportError:
        planning_status = "planning-module-unavailable"
    if planning_status == "present" or readiness.get("status") == "planning-backed":
        return {
            "status": "planning-backed",
            "task": task_text,
            "issue_refs": issue_refs,
            "broad_external_work": True,
            "planning_readiness": readiness,
            "allowed_next_actions": ["execute from the active checked-in planning record"],
        }
    return {
        "status": "needs-planning",
        "task": task_text,
        "issue_refs": issue_refs,
        "broad_external_work": True,
        "planning_status": planning_status,
        "planning_readiness": readiness,
        "allowed_next_actions": [
            "promote/create one active TODO item plus an execplan for the selected lane",
            "narrow the request to one explicit issue if direct work is truly small",
        ],
        "rule": "Broad external-work ingestion is not executable from issue text alone when no active planning record exists.",
    }


def _capability_posture_for_implementation(*, changed_paths: list[str], task_text: str | None) -> dict[str, Any]:
    normalized_task = " ".join((task_text or "").lower().split())
    path_text = " ".join(path.lower() for path in changed_paths)
    combined = f"{normalized_task} {path_text}".strip()
    if not combined:
        return {
            "status": "insufficient-task-signal",
            "posture": {},
            "reason": "No task text or changed paths were provided, so execution posture cannot infer task capability safely.",
        }
    issue_refs = re.findall(r"#\d+", task_text or "")
    judgment_terms = (
        "architecture",
        "contract",
        "schema",
        "config",
        "orchestration",
        "delegation",
        "workflow",
        "planning",
        "assurance",
        "risk",
        "policy",
    )
    mechanical_terms = ("format", "typo", "docs", "documentation", "generated", "snapshot", "fixture", "lint", "mechanical")
    high_risk_terms = ("schema", "contract", "config", "workflow", "planning", "delegation", "assurance", "policy")
    risk_flags = sorted({term for term in high_risk_terms if term in combined})
    if len(changed_paths) >= 6:
        risk_flags.append("many changed paths")
    if len(set(path.split("/")[0] for path in changed_paths if path)) >= 3:
        risk_flags.append("cross-surface breadth")
    if len(issue_refs) > 1 or "epic" in combined:
        work_shape = "epic" if "epic" in combined else "lane"
    elif "lane" in combined or len(changed_paths) >= 4:
        work_shape = "lane"
    elif changed_paths or task_text:
        work_shape = "bounded"
    else:
        work_shape = "direct"

    def enrich(posture: dict[str, Any], *, reason: str) -> dict[str, Any]:
        execution_class = posture["execution class"]
        if execution_class in ("boundary-shaping", "reasoning-heavy") or risk_flags or work_shape in ("lane", "epic"):
            proof_burden = "high"
        elif execution_class == "mechanical-follow-through":
            proof_burden = "obvious"
        else:
            proof_burden = "non-obvious"
        inspection_evidence = [
            "changed paths",
            "task text",
            "runtime_resolution",
            "proof route",
        ]
        if work_shape in ("lane", "epic"):
            inspection_evidence.append("active planning state")
        enriched_posture = {
            **posture,
            "work shape": work_shape,
            "proof burden": proof_burden,
            "risk flags": risk_flags,
            "inspection evidence required": inspection_evidence,
            "classification authority": "structural task/path signals",
            "self-assessment authority": "advisory-only",
        }
        return {
            "status": "inferred",
            "posture": enriched_posture,
            "work_shape": work_shape,
            "proof_burden": proof_burden,
            "risk_flags": risk_flags,
            "inspection_evidence_required": inspection_evidence,
            "classification_authority": "structural task/path signals",
            "self_assessment_authority": "advisory-only",
            "reason": reason,
        }

    if any(term in combined for term in judgment_terms):
        return enrich(
            {
                "execution class": "boundary-shaping",
                "recommended strength": "strong",
                "preferred location": "either",
                "delegation friendly": "yes",
                "strong external reasoning": "allowed",
                "why": "The task touches workflow, config, schema, or orchestration behavior where quality-sensitive judgment matters.",
            },
            reason="judgment-heavy terms were present in the task or changed paths",
        )
    if any(term in combined for term in mechanical_terms):
        return enrich(
            {
                "execution class": "mechanical-follow-through",
                "recommended strength": "weak",
                "preferred location": "either",
                "delegation friendly": "yes",
                "strong external reasoning": "avoid",
                "why": "The task appears bounded and mechanical enough for a cheaper executor when proof remains unchanged.",
            },
            reason="mechanical or documentation terms were present in the task or changed paths",
        )
    return enrich(
        {
            "execution class": "mixed",
            "recommended strength": "medium",
            "preferred location": "either",
            "delegation friendly": "yes",
            "strong external reasoning": "allowed",
            "why": "The task has enough context for a mixed local posture but not enough to justify automatic escalation.",
        },
        reason="defaulted to mixed posture from available task context",
    )


def _delegation_control_payload(local_override: MixedAgentLocalOverride) -> dict[str, Any]:
    configured_mode = local_override.delegation_mode or "suggest"
    safe_to_auto = bool(local_override.safe_to_auto_run_commands)
    if configured_mode == "auto" and not safe_to_auto:
        effective_mode = "suggest"
        execution_permitted = False
        disabled_reason = "delegation.mode is auto, but safety.safe_to_auto_run_commands is not true"
    else:
        effective_mode = configured_mode
        execution_permitted = configured_mode == "auto" and safe_to_auto
        disabled_reason = None
    if effective_mode == "off":
        next_action = "Do not use local delegation targets; stay direct unless another checked-in workflow surface requires escalation."
    elif effective_mode == "manual":
        next_action = "Prepare a handoff packet or prompt only; a human or runtime must execute it."
    elif effective_mode == "suggest":
        next_action = "Suggest a target and rationale, but do not execute delegation automatically."
    else:
        next_action = "Automatic delegation may proceed only within local safety and target-profile limits."
    return {
        "configured_mode": configured_mode,
        "effective_mode": effective_mode,
        "supported_modes": list(SUPPORTED_DELEGATION_CONTROL_MODES),
        "source": "local-override" if local_override.delegation_mode is not None else "default",
        "execution_permitted": execution_permitted,
        "safe_to_auto_run_commands": safe_to_auto,
        "disabled_reason": disabled_reason,
        "human_control": {
            "rule": "Local delegation posture may prepare or suggest work, but must not take control away from the human unless effective_mode is auto.",
            "next_action": next_action,
        },
    }


def _clarification_control_payload(local_override: MixedAgentLocalOverride) -> dict[str, Any]:
    configured_mode = local_override.clarification_mode or "suggest"
    mode_actions = {
        "ask-first": "Stop and ask the human when task intent, ownership, or required information is unclear.",
        "suggest": "Surface the ask-human option when uncertainty is material, but continue when the next action is otherwise safe.",
        "auto-continue": "Continue with the best bounded interpretation unless a hard blocker or safety boundary is present.",
    }
    return {
        "configured_mode": configured_mode,
        "effective_mode": configured_mode,
        "supported_modes": list(SUPPORTED_CLARIFICATION_CONTROL_MODES),
        "source": "local-override" if local_override.clarification_mode is not None else "default",
        "human_control": {
            "rule": "Clarification posture controls when the agent should stop for human input instead of guessing or widening scope.",
            "next_action": mode_actions.get(configured_mode, mode_actions["suggest"]),
        },
    }


def _delegation_next_action_decision(
    *,
    config: WorkspaceConfig,
    execution_posture: dict[str, Any],
    task_text: str | None,
    changed_paths: list[str],
) -> dict[str, Any]:
    capability = execution_posture.get("capability_posture", {})
    runtime_resolution = execution_posture.get("runtime_resolution", {})
    delegation_control = execution_posture.get("delegation_control", _delegation_control_payload(config.local_override))
    clarification_control = _clarification_control_payload(config.local_override)
    recommendation = str(runtime_resolution.get("recommendation", "stay-local"))
    mode = str(delegation_control.get("effective_mode", "suggest"))
    clarification_mode = str(clarification_control.get("effective_mode", "suggest"))
    selected_target = execution_posture.get("selected_target")
    target_name = str(selected_target.get("name")) if isinstance(selected_target, dict) and selected_target.get("name") else None
    capability_status = str(capability.get("status", "unknown")) if isinstance(capability, dict) else "unknown"
    posture = capability.get("posture", {}) if isinstance(capability, dict) else {}
    work_shape = capability.get("work_shape") or (posture.get("work shape") if isinstance(posture, dict) else None)
    proof_burden = capability.get("proof_burden") or (posture.get("proof burden") if isinstance(posture, dict) else None)
    reasons = list(runtime_resolution.get("reasons", [])) if isinstance(runtime_resolution.get("reasons", []), list) else []
    if not reasons:
        reasons = [str(runtime_resolution.get("guidance", "Local posture did not produce a specific reason."))]

    missing_task_signal = capability_status == "insufficient-task-signal" or (not task_text and not changed_paths)
    decision = "stay-local"
    required_next_action = "continue-local"
    handoff_command: str | None = None
    manual_prompt: dict[str, Any] | None = None
    mode_effect = "Delegation mode is suggest by default: surface the decision, but do not delegate automatically."

    downrouting = runtime_resolution.get("downrouting_guardrail", {})
    downrouting_active = isinstance(downrouting, dict) and downrouting.get("status") == "active"

    if missing_task_signal and clarification_mode == "ask-first":
        decision = "ask-human"
        required_next_action = "stop-and-ask-human"
        reasons = ["clarification.mode is ask-first and the command lacks enough task or changed-path signal"]
    elif recommendation == "manual-handoff":
        decision = "manual-handoff"
        required_next_action = "prepare-manual-handoff"
    elif recommendation == "stronger-reasoning":
        decision = "suggest-escalation"
        required_next_action = "mention-suggestion" if mode == "suggest" else "prepare-handoff"
    elif recommendation == "external-delegation":
        decision = "suggest-delegation"
        required_next_action = "mention-suggestion" if mode == "suggest" else "prepare-handoff"
    elif downrouting_active:
        decision = "suggest-downroute"
        required_next_action = "mention-suggestion" if mode == "suggest" else "prepare-handoff"
    elif (
        recommendation == "stay-local"
        and mode == "auto"
        and delegation_control.get("execution_permitted") is True
        and isinstance(selected_target, dict)
        and str(selected_target.get("strength", "")) in {"weak", "medium"}
        and proof_burden != "high"
        and work_shape in {"direct", "bounded"}
    ):
        decision = "delegate-bounded-slice"
        required_next_action = "execute-when-safe"
        reasons = [
            (
                f"auto delegation is permitted and target '{target_name}' fits bounded work; "
                "delegate a narrow implementation or validation slice only if proof expectations stay unchanged"
            )
        ]

    if mode == "off":
        mode_effect = "delegation.mode is off: do not use local delegation targets."
        if decision in {"suggest-delegation", "suggest-downroute"}:
            decision = "stay-local"
            required_next_action = "continue-local"
    elif mode == "manual":
        mode_effect = "delegation.mode is manual: prepare a handoff prompt or packet and stop for human/runtime execution."
        if decision in {"suggest-delegation", "suggest-downroute", "suggest-escalation"}:
            required_next_action = "prepare-handoff"
    elif mode == "auto" and delegation_control.get("execution_permitted") is True:
        mode_effect = "delegation.mode is auto and safety permits execution within target-profile limits."
        if decision in {"suggest-delegation", "suggest-downroute", "suggest-escalation"}:
            required_next_action = "execute-when-safe"

    if decision in {
        "suggest-delegation",
        "suggest-downroute",
        "suggest-escalation",
        "manual-handoff",
        "delegate-bounded-slice",
    }:
        handoff_command = _command_with_cli_invoke(
            command="agentic-planning handoff --target . --format json",
            cli_invoke=config.cli_invoke,
        )
    if decision in {"manual-handoff", "ask-human"}:
        manual_prompt = {
            "kind": "agentic-workspace/manual-human-prompt/v1",
            "target": "human-or-external-strong-general-purpose-model",
            "context": "The current agent needs bounded input before safely choosing or continuing the next action.",
            "question": "Clarify the intended outcome, missing constraints, or high-judgment decision for this task.",
            "constraints": [
                "Keep the answer bounded to the current task.",
                "Do not widen implementation scope unless explicitly intended.",
                "State any hard stop conditions or proof expectations.",
            ],
            "expected_output": "A short decision, constraint list, or answer the current agent can apply directly.",
            "return_to": "Paste the answer back into the current agent session for integration.",
        }
    delegation_next_step: dict[str, Any] | None = None
    if decision in {
        "suggest-delegation",
        "suggest-downroute",
        "suggest-escalation",
        "manual-handoff",
        "delegate-bounded-slice",
    }:
        delegation_next_step = {
            "kind": "agentic-workspace/delegation-next-step/v1",
            "status": "executable" if required_next_action == "execute-when-safe" else "prepare-or-report",
            "action": required_next_action,
            "target": target_name,
            "command": handoff_command,
            "execution_methods": selected_target.get("execution_methods", []) if isinstance(selected_target, dict) else [],
            "must_report_if_not_run": required_next_action == "execute-when-safe",
            "scope_rule": "Delegate only a bounded slice with unchanged proof expectations; otherwise stay local and state why.",
            "return_contract": [
                "what changed",
                "proof run and result",
                "scope or stop-condition issues",
                "residue to route into planning, memory, docs, or issues",
            ],
        }

    if required_next_action == "continue-local":
        must = "Continue locally; no delegation action is required for this step."
        must_not = "Do not invent delegation work just because targets are configured."
    elif required_next_action == "mention-suggestion":
        must = "State the suggested route and rationale before continuing locally or preparing handoff."
        must_not = "Do not execute delegation automatically in suggest mode."
    elif required_next_action == "prepare-handoff":
        must = "Prepare the handoff packet or prompt before implementation continues on the delegated slice."
        must_not = "Do not treat the suggestion as optional background when the route is capability-driven."
    elif required_next_action == "execute-when-safe":
        must = "Execute only when local auto mode, target profile, scope, and proof constraints all remain satisfied."
        must_not = "Do not widen scope, lower proof, or use a target outside its configured execution methods."
    elif required_next_action == "stop-and-ask-human":
        must = "Stop and ask for the bounded missing input before continuing."
        must_not = "Do not guess the missing human intent or ownership boundary."
    else:
        must = "Follow required_next_action before implementation continues."
        must_not = "Do not bypass the configured local posture silently."

    route_obligation = {
        "must": must,
        "must_not": must_not,
        "report_if_skipped": (
            "If you do not follow this route, report why local execution is safer or cheaper without reducing quality, proof, or control."
        ),
    }
    config_effect = {
        "authority": "local-config",
        "source_path": ".agentic-workspace/config.local.toml",
        "configured_delegation_mode": delegation_control.get("configured_mode", mode),
        "delegation_mode": mode,
        "clarification_mode": clarification_mode,
        "safe_to_auto_run_commands": delegation_control.get("safe_to_auto_run_commands"),
        "disabled_reason": delegation_control.get("disabled_reason"),
        "execution_authority": (
            "auto-execution-permitted"
            if mode == "auto" and delegation_control.get("execution_permitted") is True
            else "suggest-or-handoff-only"
        ),
        "human_control": "auto execution requires local safety permission; otherwise surface suggest/handoff first.",
    }

    return {
        "kind": "agentic-workspace/delegation-next-action/v1",
        "status": "evaluated",
        "mode": mode,
        "clarification_mode": clarification_mode,
        "decision": decision,
        "target": target_name,
        "work_shape": work_shape,
        "proof_burden": proof_burden,
        "quality_risk": "high" if proof_burden == "high" else ("medium" if proof_burden == "non-obvious" else "low"),
        "token_savings_expected": "likely"
        if decision in {"suggest-downroute", "delegate-bounded-slice"}
        else ("possible" if decision == "suggest-delegation" else "none"),
        "required_next_action": required_next_action,
        "mode_effect": mode_effect,
        "config_effect": config_effect,
        "reason": reasons[0],
        "handoff_command": handoff_command,
        "handoff_surface": _delegation_handoff_surface(command=handoff_command) if handoff_command else None,
        "delegation_next_step": delegation_next_step,
        "manual_prompt": manual_prompt,
        "route_obligation": route_obligation,
        "human_control_summary": (
            "Local posture may suggest delegation or clarification, but only auto mode may execute without a human handoff."
        ),
    }


def _delegation_handoff_surface(*, command: str | None) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/delegation-handoff-surface/v1",
        "command": command,
        "status": "available-when-active-planning-exists",
        "fallback_when_unavailable": (
            "Use the current start/implement payload plus checked-in planning refs; if no active execplan exists, "
            "create or select the bounded planning slice before delegating implementation."
        ),
        "required_packet_fields": [
            "intent",
            "constraints",
            "read_first_refs",
            "owned_scope",
            "proof_expectations",
            "stop_conditions",
            "return_contract",
            "target_posture",
        ],
        "return_contract": [
            "what changed",
            "proof run and result",
            "scope or stop-condition issues",
            "residue to route into planning, memory, docs, or issues",
        ],
        "control": "Only delegation.mode=auto may execute without first surfacing this packet to the human or orchestrator.",
    }


def _execution_posture_payload(
    *,
    config: WorkspaceConfig,
    changed_paths: list[str],
    task_text: str | None,
) -> dict[str, Any]:
    posture = _capability_posture_for_implementation(changed_paths=changed_paths, task_text=task_text)
    runtime_resolution = _runtime_resolution_payload(config=config, capability_posture=posture["posture"])
    delegation_control = _delegation_control_payload(config.local_override)
    target = next(
        (
            profile
            for profile in runtime_resolution["profile_recommendations"]
            if profile["recommendation"] in ("recommended", "acceptable")
        ),
        None,
    )
    recommendation = runtime_resolution["recommendation"]
    if recommendation == "stay-local":
        quality_tradeoff = "Stay direct when delegation overhead is not justified or local bounded execution is sufficient."
        token_tradeoff = "Token saving is acceptable only if the task stays bounded and proof requirements are unchanged."
    elif recommendation == "stronger-reasoning":
        quality_tradeoff = "Use stronger reasoning because quality-sensitive judgment is likely worth the overhead."
        token_tradeoff = "Token saving should wait until the judgment-heavy part is resolved without compromising quality."
    elif recommendation == "external-delegation":
        quality_tradeoff = "External delegation is justified only if the selected target materially improves fit for this task."
        token_tradeoff = "External delegation may save local tokens, but only under the same proof and quality requirements."
    else:
        quality_tradeoff = "Manual handoff is the safer path when automated execution authority is absent or unclear."
        token_tradeoff = "Manual handoff may save tokens later, but the immediate value is preserving judgment quality and control."
    ready_handoff = None
    handoff_guardrail_active = (
        runtime_resolution["weak_target_guardrail"]["status"] == "active"
        or runtime_resolution["downrouting_guardrail"]["status"] == "active"
    )
    if (
        recommendation in ("stronger-reasoning", "external-delegation", "manual-handoff") or handoff_guardrail_active
    ) and delegation_control["effective_mode"] in ("manual", "suggest"):
        packet_type = "manual_human_clarification"
        if runtime_resolution["weak_target_guardrail"]["status"] == "active":
            packet_type = "weak_target_escalation"
        elif runtime_resolution["downrouting_guardrail"]["status"] == "active":
            packet_type = "strong_target_downrouting"
        elif recommendation == "manual-handoff" and not target:
            packet_type = "no_safe_route"
        ready_handoff = _ready_capability_handoff_packet(
            packet_type=packet_type,
            mode=delegation_control["effective_mode"],
            target=target["name"] if target else None,
            posture=posture,
            runtime_resolution=runtime_resolution,
        )
    return {
        "kind": "agentic-workspace/execution-posture/v1",
        "capability_posture": posture,
        "runtime_resolution": runtime_resolution,
        "delegation_control": delegation_control,
        "selected_target": target,
        "capability_handoff_packets": _capability_handoff_packet_templates(),
        "recommended_action": recommendation,
        "quality_tradeoff": quality_tradeoff,
        "token_tradeoff": token_tradeoff,
        "ready_handoff": ready_handoff,
        "delegation_decision": _delegation_next_action_decision(
            config=config,
            execution_posture={
                "capability_posture": posture,
                "runtime_resolution": runtime_resolution,
                "delegation_control": delegation_control,
                "selected_target": target,
            },
            task_text=task_text,
            changed_paths=changed_paths,
        ),
        "inference_limits": [
            "Task posture is inferred from changed paths and optional --task text; it is not proof of human intent.",
            "No delegation target may reduce required validation, review, or closeout evidence.",
            "Automatic execution is permitted only when local delegation control resolves to auto.",
        ],
    }


def _command_with_cli_invoke(*, command: str | None, cli_invoke: str) -> str | None:
    if command is None:
        return None
    if command == "agentic-workspace" or command.startswith("agentic-workspace "):
        return f"{cli_invoke}{command.removeprefix('agentic-workspace')}"
    for sibling_program in ("agentic-planning", "agentic-memory"):
        if command == sibling_program or command.startswith(f"{sibling_program} "):
            return _sibling_cli_command_with_invoke(
                command=command,
                workspace_cli_invoke=cli_invoke,
                sibling_program=sibling_program,
            )
    return command


def _shell_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _text_with_cli_invoke(*, text: str, cli_invoke: str) -> str:
    if text == "agentic-workspace" or text.startswith("agentic-workspace "):
        return str(_command_with_cli_invoke(command=text, cli_invoke=cli_invoke))
    if text.startswith("use agentic-workspace "):
        command = str(_command_with_cli_invoke(command=text.removeprefix("use "), cli_invoke=cli_invoke))
        return f"use {command}"
    return text


def _guidance_with_cli_invoke(*, value: Any, cli_invoke: str) -> Any:
    if isinstance(value, str):
        return _text_with_cli_invoke(text=value, cli_invoke=cli_invoke)
    if isinstance(value, list):
        return [_guidance_with_cli_invoke(value=item, cli_invoke=cli_invoke) for item in value]
    if isinstance(value, dict):
        return {key: _guidance_with_cli_invoke(value=nested, cli_invoke=cli_invoke) for key, nested in value.items()}
    return value


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
            "force": obligation.force,
            "scope_tags": list(obligation.scope_tags),
            "commands": list(obligation.commands),
            "review_hint": obligation.review_hint,
        }
        for obligation in config.workflow_obligations
    ]


def _config_field_enforcement_entries() -> list[dict[str, Any]]:
    return [
        {
            "field": "schema_version",
            "enforcement": "hard",
            "scope": "repo-config",
            "used_by": ["config loader", "all workspace commands"],
        },
        {
            "field": "workspace.default_preset",
            "enforcement": "operational",
            "scope": "repo-config",
            "used_by": ["setup", "install", "init", "module selection"],
        },
        {
            "field": "workspace.agent_instructions_file",
            "enforcement": "operational",
            "scope": "repo-config",
            "used_by": ["startup adapters", "install", "init"],
        },
        {
            "field": "workspace.workflow_artifact_profile",
            "enforcement": "operational",
            "scope": "repo-config",
            "used_by": ["startup adapters", "handoff guidance"],
        },
        {
            "field": "workspace.improvement_latitude",
            "enforcement": "advisory",
            "scope": "repo-config",
            "used_by": ["report.repo_friction", "report.improvement_intake", "defaults.improvement_latitude"],
        },
        {
            "field": "workspace.optimization_bias",
            "enforcement": "advisory",
            "scope": "repo-config",
            "used_by": ["report.output_contract", "report section hints", "rendered output density"],
        },
        {
            "field": "workspace.advanced_features",
            "enforcement": "operational",
            "scope": "repo-config",
            "used_by": ["report advanced sections", "skills routing", "startup guidance"],
        },
        {
            "field": "system_intent.sources",
            "enforcement": "operational",
            "scope": "repo-config",
            "used_by": ["config", "system-intent", "report.system_intent_mirror"],
        },
        {
            "field": "system_intent.preferred_source",
            "enforcement": "operational",
            "scope": "repo-config",
            "used_by": ["config", "system-intent", "report.system_intent_mirror"],
        },
        {
            "field": "workflow_obligations.<name>.*",
            "enforcement": "advisory-operational",
            "scope": "repo-config",
            "used_by": ["report.workflow_obligations", "preflight.closeout_obligations", "closeout gate force"],
        },
        {
            "field": "assurance.*",
            "enforcement": "advisory-operational",
            "scope": "repo-config",
            "used_by": ["config.assurance", "summary.planning_record", "proof concern profiles", "closeout guidance"],
        },
        {
            "field": "cli_compatibility.*",
            "enforcement": "advisory-operational",
            "scope": "repo-config",
            "used_by": ["config.cli_compatibility", "status/start/report CLI compatibility comparison"],
        },
        {
            "field": "update.modules.<module>.*",
            "enforcement": "operational",
            "scope": "repo-config",
            "used_by": ["config.update", "status/doctor/upgrade source metadata"],
        },
        {
            "field": "workspace.cli_invoke",
            "enforcement": "operational",
            "scope": "local-config",
            "used_by": ["copyable commands", "startup/report/proof/lifecycle guidance"],
        },
        {
            "field": "runtime|handoff|safety|delegation_targets",
            "enforcement": "local-advisory",
            "scope": "local-config",
            "used_by": ["mixed_agent.runtime_resolution", "delegated_run_guardrail", "handoff guidance"],
        },
        {
            "field": "local_memory.enabled/path",
            "enforcement": "local-advisory",
            "scope": "local-config",
            "used_by": ["config.local_memory", "report.local_memory"],
        },
    ]


def _config_enforcement_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    entries = _config_field_enforcement_entries()
    counts: dict[str, int] = {}
    for entry in entries:
        enforcement = str(entry["enforcement"])
        counts[enforcement] = counts.get(enforcement, 0) + 1
    return {
        "kind": "workspace-config-enforcement/v1",
        "status": "present",
        "rule": (
            "Config fields declare policy and posture at different strengths; advisory fields must stay visible as "
            "advisory instead of being mistaken for hard execution gates."
        ),
        "config_exists": config.exists,
        "local_override_applied": config.local_override.applied,
        "classes": {
            "hard": "invalid values stop command execution",
            "operational": "validated values directly change package output or lifecycle behavior",
            "advisory": "validated values shape compact guidance but do not execute work",
            "local-advisory": "machine-local posture that may shape guidance but cannot become shared repo authority",
        },
        "field_count_by_class": counts,
        "fields": entries,
        "weak_field_routes": [
            {
                "field": "workspace.improvement_latitude",
                "command": _command_with_cli_invoke(
                    command="agentic-workspace report --target ./repo --section repo_friction --format json",
                    cli_invoke=config.cli_invoke,
                ),
            },
            {
                "field": "workspace.optimization_bias",
                "command": _command_with_cli_invoke(
                    command="agentic-workspace report --target ./repo --section output_contract --format json",
                    cli_invoke=config.cli_invoke,
                ),
            },
            {
                "field": "workflow_obligations.<name>.*",
                "command": _command_with_cli_invoke(
                    command="agentic-workspace report --target ./repo --section workflow_obligations --format json",
                    cli_invoke=config.cli_invoke,
                ),
            },
            {
                "field": "cli_compatibility.*",
                "command": _command_with_cli_invoke(
                    command="agentic-workspace config --target ./repo --profile compact --format json",
                    cli_invoke=config.cli_invoke,
                ),
                "field_path": "cli_compatibility",
            },
            {
                "field": "local runtime/delegation posture",
                "command": _command_with_cli_invoke(
                    command="agentic-workspace config --target ./repo --profile tiny --format json",
                    cli_invoke=config.cli_invoke,
                ),
                "field_path": "mixed_agent.runtime_resolution",
            },
        ],
    }


def _config_effect_audit_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    entries = _config_field_enforcement_entries()
    effect_classes = {
        "hard": {
            "force": "blocking",
            "agent_dependency": "none-after-command-start",
            "meaning": "invalid values stop command execution or validation",
        },
        "operational": {
            "force": "tool-behavior",
            "agent_dependency": "low",
            "meaning": "validated values directly change package output, lifecycle behavior, or diagnostics",
        },
        "advisory-operational": {
            "force": "structured-decision-or-diagnostic",
            "agent_dependency": "medium",
            "meaning": "values produce structured decisions or diagnostics, but action still depends on later tool use or agent uptake",
        },
        "advisory": {
            "force": "guidance-only",
            "agent_dependency": "high",
            "meaning": "values shape compact guidance but do not execute work or block claims by themselves",
        },
        "local-advisory": {
            "force": "machine-local-guidance",
            "agent_dependency": "high",
            "meaning": "machine-local posture shapes routing without becoming shared repo authority",
        },
        "unused": {
            "force": "none-detected",
            "agent_dependency": "not-applicable",
            "meaning": "field is configured or known but no concrete tool output route is currently declared",
        },
    }

    def field_effect(entry: dict[str, Any]) -> dict[str, Any]:
        effect_type = str(entry.get("enforcement", "unused"))
        used_by = [str(item) for item in _list_payload(entry.get("used_by"))]
        field = str(entry.get("field", ""))
        concrete_commands: list[str] = []
        payload_fields: list[str] = []

        def command(raw_command: str) -> str:
            return _command_with_cli_invoke(command=raw_command, cli_invoke=config.cli_invoke) or raw_command

        if field.startswith("workspace.improvement_latitude"):
            concrete_commands = [command("agentic-workspace report --target ./repo --section repo_friction --format json")]
            payload_fields = ["repo_friction.policy_mode", "operating_posture.improvement_latitude"]
        elif field.startswith("workspace.optimization_bias"):
            concrete_commands = [command("agentic-workspace report --target ./repo --section output_contract --format json")]
            payload_fields = ["output_contract", "operating_posture.optimization_bias"]
        elif field.startswith("workflow_obligations"):
            concrete_commands = [
                command("agentic-workspace report --target ./repo --section workflow_obligations --format json"),
                command("agentic-workspace preflight --target ./repo --format json"),
            ]
            payload_fields = ["workflow_obligations", "closeout_obligations"]
        elif field.startswith("assurance"):
            concrete_commands = [
                command("agentic-workspace config --target ./repo --profile compact --format json"),
                command("agentic-workspace proof --target ./repo --changed <paths> --format json"),
            ]
            payload_fields = ["assurance", "proof", "closeout_trust"]
        elif field.startswith("cli_compatibility"):
            concrete_commands = [command("agentic-workspace config --target ./repo --profile compact --format json")]
            payload_fields = ["cli_compatibility"]
        elif field.startswith("runtime|handoff|safety|delegation_targets"):
            concrete_commands = [
                command('agentic-workspace start --target ./repo --profile tiny --task "<task>" --format json'),
                command("agentic-workspace implement --target ./repo --profile tiny --changed <paths> --format json"),
            ]
            payload_fields = ["delegation_decision", "mixed_agent.runtime_resolution"]
        elif field.startswith("local_memory"):
            concrete_commands = [command("agentic-workspace report --target ./repo --section local_memory --format json")]
            payload_fields = ["local_memory"]
        elif field.startswith("workspace.cli_invoke"):
            concrete_commands = [command("agentic-workspace config --target ./repo --profile compact --format json")]
            payload_fields = ["copyable command strings"]
        elif field.startswith("system_intent"):
            concrete_commands = [command("agentic-workspace system-intent --target ./repo --format json")]
            payload_fields = ["system_intent_mirror", "durable_intent"]
        elif field.startswith("update.modules"):
            concrete_commands = [
                command("agentic-workspace status --target ./repo --format json"),
                command("agentic-workspace upgrade --target ./repo --dry-run --format json"),
            ]
            payload_fields = ["update.modules", "module freshness"]
        else:
            concrete_commands = [command("agentic-workspace config --target ./repo --profile compact --format json")]
            payload_fields = used_by

        return {
            "field": field,
            "scope": str(entry.get("scope", "")),
            "effect_type": effect_type,
            "force": effect_classes.get(effect_type, effect_classes["unused"])["force"],
            "agent_dependency": effect_classes.get(effect_type, effect_classes["unused"])["agent_dependency"],
            "concrete_commands": concrete_commands,
            "payload_fields": payload_fields,
            "used_by": used_by,
        }

    field_effects = [field_effect(entry) for entry in entries]
    counts: dict[str, int] = {key: 0 for key in effect_classes}
    for effect in field_effects:
        effect_type = str(effect.get("effect_type", "unused"))
        counts[effect_type] = counts.get(effect_type, 0) + 1
    warnings: list[dict[str, Any]] = []
    return {
        "kind": "workspace-config-effect-audit/v1",
        "status": "present",
        "rule": "Config settings must state whether they block, change tool behavior, shape diagnostics, or only advise agents.",
        "config_exists": config.exists,
        "local_override_applied": config.local_override.applied,
        "effect_classes": effect_classes,
        "field_count_by_effect": counts,
        "field_effects": field_effects,
        "agent_dependent_fields": [effect for effect in field_effects if str(effect.get("agent_dependency")) in {"medium", "high"}],
        "claimed_vs_actual_warnings": warnings,
        "unused_fields": [effect for effect in field_effects if effect.get("effect_type") == "unused"],
        "detail_command": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section config_effect_audit --format json",
            cli_invoke=config.cli_invoke,
        ),
    }


def _scope_tags_for_current_work(
    *,
    active_planning_record: dict[str, Any] | None,
    task_text: str | None = None,
    changed_paths: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    tags: set[str] = set()
    sources: list[str] = []
    touched_scope = active_planning_record.get("touched_scope", []) if isinstance(active_planning_record, dict) else []
    if isinstance(touched_scope, list):
        for raw_item in touched_scope:
            tags.update(_scope_tags_for_path(str(raw_item)))
        if touched_scope:
            sources.append("active planning touched_scope")
    if active_planning_record:
        tags.add("planning")
        sources.append("active planning presence")
    normalized_task = " ".join((task_text or "").lower().split())
    if normalized_task:
        task_tags = _scope_tags_for_task_text(normalized_task)
        if task_tags:
            tags.update(task_tags)
            sources.append("task text")
    normalized_paths = _normalize_changed_paths(changed_paths or [])
    for path in normalized_paths:
        tags.update(_scope_tags_for_path(path))
    if normalized_paths:
        sources.append("changed paths")
    return sorted(tags), sources


def _scope_tags_for_path(path: str) -> set[str]:
    normalized = path.lower().replace("\\", "/")
    tags: set[str] = set()
    if any(token in normalized for token in ("src/agentic_workspace", ".agentic-workspace/docs", "readme.md")):
        tags.add("workspace")
    if any(token in normalized for token in (".agentic-workspace/planning", "packages/planning")):
        tags.add("planning")
    if any(token in normalized for token in (".agentic-workspace/memory", "packages/memory")):
        tags.add("memory")
    if any(token in normalized for token in ("agents.md", "llms.txt", "tools/agent_quickstart", "tools/agent_routing")):
        tags.add("adapter-surfaces")
    if "config.toml" in normalized or "workspace_config" in normalized:
        tags.add("workspace")
    if "system-intent" in normalized or "system_intent" in normalized:
        tags.add("system-intent")
    return tags


def _scope_tags_for_task_text(normalized_task: str) -> set[str]:
    tags: set[str] = set()
    if any(
        token in normalized_task
        for token in (
            "workspace",
            "workflow",
            "obligation",
            "orchestrat",
            "start",
            "startup",
            "preflight",
            "config",
            "ownership",
            "implementation style",
        )
    ):
        tags.add("workspace")
    if any(token in normalized_task for token in ("agent instructions", "agents.md", "llms.txt", "adapter", "routing surface")):
        tags.add("adapter-surfaces")
    if any(token in normalized_task for token in ("planning", "plan", "execplan", "lane", "epic", "future work")):
        tags.add("planning")
    if any(token in normalized_task for token in ("memory", "durable knowledge", "rediscovery")):
        tags.add("memory")
    if any(token in normalized_task for token in ("dogfood", "self-improvement", "optimisation", "optimization")):
        tags.update({"dogfooding", "self-improvement"})
    if "system intent" in normalized_task or "subsystem intent" in normalized_task:
        tags.add("system-intent")
    if "package boundary" in normalized_task or "package boundaries" in normalized_task:
        tags.add("package-boundaries")
    return tags


def _workflow_obligations_report_payload(
    *,
    config: WorkspaceConfig,
    active_planning_record: dict[str, Any] | None,
    task_text: str | None = None,
    changed_paths: list[str] | None = None,
) -> dict[str, Any]:
    configured = _workflow_obligation_payloads(config)
    current_tags, scope_sources = _scope_tags_for_current_work(
        active_planning_record=active_planning_record,
        task_text=task_text,
        changed_paths=changed_paths,
    )
    matching: list[dict[str, Any]] = []
    relevant: list[dict[str, Any]] = []
    current_tag_set = set(current_tags)
    for obligation in configured:
        obligation_tags = {str(tag) for tag in obligation["scope_tags"]}
        matched_tags = sorted(obligation_tags & current_tag_set)
        matched = bool(matched_tags)
        if matched:
            relevant.append(obligation)
        matching.append(
            {
                "id": obligation["id"],
                "matched": matched,
                "matched_scope_tags": matched_tags,
                "non_match_reason": "" if matched else "no overlap with current_scope_tags",
                "stage": obligation["stage"],
                "force": obligation.get("force", "recommended"),
                "gate_status": _workflow_obligation_gate_status(obligation=obligation, matched=matched),
            }
        )
    return {
        "canonical_doc": ".agentic-workspace/docs/workspace-config-contract.md",
        "rule": (
            "Repo-custom workflow obligations live in workspace config so planning can consume them when relevant "
            "without becoming the owner of workflow extension machinery."
        ),
        "configured_count": len(configured),
        "current_scope_tags": current_tags,
        "match_evidence": {
            "observed_scope_source": ", ".join(scope_sources)
            if scope_sources
            else "no active planning record, task text, or changed paths",
            "current_scope_tags": current_tags,
            "match_count": len(relevant),
            "matching": matching,
        },
        "configured": configured,
        "relevant_to_current_work": relevant,
    }


def _workflow_obligation_gate_status(*, obligation: dict[str, Any], matched: bool) -> str:
    force = str(obligation.get("force", "recommended"))
    if force == "informational":
        return "informational"
    if force == "recommended":
        return "recommended" if matched else "not-currently-relevant"
    if force == "required-before-closeout":
        return "required-before-closeout" if matched else "standing-closeout-requirement"
    if force == "blocking":
        return "blocking" if matched else "standing-blocking-requirement"
    return "unknown"


def _closeout_workflow_obligations_payload(workflow_obligations: dict[str, Any]) -> dict[str, Any]:
    relevant = workflow_obligations.get("relevant_to_current_work", [])
    if not isinstance(relevant, list):
        relevant = []
    configured = workflow_obligations.get("configured", [])
    if not isinstance(configured, list):
        configured = []
    closeout_stages = {"before-claiming-completion", "closeout"}
    closeout_relevant = [
        obligation for obligation in relevant if isinstance(obligation, dict) and str(obligation.get("stage", "")) in closeout_stages
    ]
    standing_closeout = [
        obligation for obligation in configured if isinstance(obligation, dict) and str(obligation.get("stage", "")) in closeout_stages
    ]
    closeout_required = [
        obligation
        for obligation in (closeout_relevant or standing_closeout)
        if str(obligation.get("force", "recommended")) in {"required-before-closeout", "blocking"}
    ]
    closeout_recommended = [
        obligation
        for obligation in (closeout_relevant or standing_closeout)
        if str(obligation.get("force", "recommended")) in {"informational", "recommended"}
    ]
    primary_obligation = closeout_required[0] if closeout_required else (closeout_recommended[0] if closeout_recommended else None)
    primary_commands = primary_obligation.get("commands", []) if isinstance(primary_obligation, dict) else []
    primary_command = str(primary_commands[0]) if isinstance(primary_commands, list) and primary_commands else ""
    return {
        "status": "present" if closeout_required else ("recommended" if closeout_recommended else "none-configured-for-current-work"),
        "rule": (
            "Before claiming work, a lane, or a milestone is complete, run closeout obligations from repo config; "
            "validation success alone is not a closeout."
        ),
        "primary_next_action": (
            {
                "action": "run-closeout-obligation",
                "id": str(primary_obligation.get("id", "")),
                "summary": str(primary_obligation.get("summary", "")),
                "command": primary_command,
                "run": primary_command,
                "risk": "may surface required closeout work but should not mutate repo state unless the command itself says so",
                "required_inputs": ["task scope or active planning record", "changed paths or proof scope", "validation results"],
                "next_proof": "record closeout evidence, route durable residue, then rerun summary/reconcile before issue closure",
            }
            if isinstance(primary_obligation, dict)
            else None
        ),
        "required_before_lane_closeout": closeout_required,
        "recommended_before_lane_closeout": closeout_recommended,
        "blocking_count": sum(1 for obligation in closeout_required if str(obligation.get("force", "")) == "blocking"),
        "recommended_next_action": (
            "Run the listed closeout obligation commands and record any friction as planning, memory, review, or issue follow-up."
            if closeout_required
            else "Consider the listed closeout obligation commands before claiming completion."
            if closeout_recommended
            else "No repo-custom closeout obligation is configured."
        ),
    }


def _system_intent_source_payload(config: WorkspaceConfig) -> dict[str, Any]:
    return {
        "sources": list(config.system_intent.sources),
        "sources_source": config.system_intent.sources_source,
        "preferred_source": config.system_intent.preferred_source,
        "preferred_source_source": config.system_intent.preferred_source_source,
    }


INTENT_RECORD_STATUSES = {"active", "proposed", "needs-review", "superseded", "retired"}
INTENT_CONFIDENCE_VALUES = {"low", "medium", "high"}


def _intent_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _intent_source_records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    records: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        source_type = str(item.get("source_type", item.get("type", ""))).strip()
        records.append(
            {
                "source_type": source_type or "unspecified",
                "ref": str(item.get("ref", item.get("path", ""))).strip(),
                "summary": str(item.get("summary", "")).strip(),
                "observed_at": str(item.get("observed_at", "")).strip(),
            }
        )
    return records


def _validate_intent_lifecycle_fields(*, surface: str, item: dict[str, Any]) -> None:
    status = str(item.get("status", "proposed")).strip()
    if status and status not in INTENT_RECORD_STATUSES:
        accepted = ", ".join(sorted(INTENT_RECORD_STATUSES))
        raise WorkspaceUsageError(f"{surface} status must be one of: {accepted}.")
    confidence = str(item.get("confidence", "low")).strip()
    if confidence and confidence not in INTENT_CONFIDENCE_VALUES:
        accepted = ", ".join(sorted(INTENT_CONFIDENCE_VALUES))
        raise WorkspaceUsageError(f"{surface} confidence must be one of: {accepted}.")


def _default_subsystem_intent_text() -> str:
    subsystems: list[dict[str, Any]] = [
        {
            "id": "planning",
            "scope": "planning module and checked-in planning surfaces",
            "status": "active",
            "summary": "Planning should preserve current execution intent, proof expectations, and honest continuation without becoming historical storage.",
            "governing_intents": [
                "Keep task intent bounded, closable, and tied to proof.",
                "Keep larger intent explicit when a slice only completes part of it.",
                "Route durable reusable learning to Memory, docs, config, or durable intent instead of leaving it in archived plans.",
            ],
            "anti_intents": [
                "Do not let planning state become a historical archive.",
                "Do not treat validation success alone as intent satisfaction.",
            ],
            "decision_tests": [
                "Does this planning change make the next correct action more obvious and compact?",
                "Does closeout preserve useful durable direction somewhere other than completed planning state?",
            ],
            "confidence": "high",
            "needs_review": False,
            "source_records": [
                {
                    "source_type": "issue",
                    "ref": "#746",
                    "summary": "Intent lifecycle parent issue requires durable task/system/subsystem distinction.",
                }
            ],
        },
        {
            "id": "memory",
            "scope": "memory module and checked-in durable repo knowledge",
            "status": "active",
            "summary": "Memory should preserve reusable understanding that prevents expensive rediscovery without becoming policy, active task state, or a wiki.",
            "governing_intents": [
                "Promote only durable, shareable, non-private knowledge that helps future agents.",
                "Prefer compact routed notes over broad narrative archives.",
            ],
            "anti_intents": [
                "Do not use Memory as a substitute for active Planning.",
                "Do not encode binding workflow policy as Memory when config, contracts, or checks own it.",
            ],
            "decision_tests": [
                "Would this knowledge be expensive to reconstruct and useful beyond the current task?",
                "Is Memory the stronger home than subsystem intent, docs, config, or a check?",
            ],
            "confidence": "high",
            "needs_review": False,
            "source_records": [
                {
                    "source_type": "issue",
                    "ref": "#748",
                    "summary": "Task-to-durable promotion should distinguish Memory from system/subsystem intent.",
                }
            ],
        },
    ]
    rule = "Subsystem intent is durable scoped decision pressure, not active task state by default."
    lines = [
        "schema_version = 1",
        f'kind = "{SUBSYSTEM_INTENT_KIND}"',
        f"rule = {json.dumps(rule)}",
    ]
    for subsystem in subsystems:
        raw_records = subsystem.get("source_records", [])
        records = raw_records if isinstance(raw_records, list) else []
        source_records = [
            "{ "
            + ", ".join(
                [
                    f"source_type = {json.dumps(str(record.get('source_type', '')))}",
                    f"ref = {json.dumps(str(record.get('ref', '')))}",
                    f"summary = {json.dumps(str(record.get('summary', '')))}",
                ]
            )
            + " }"
            for record in records
            if isinstance(record, dict)
        ]
        lines.extend(
            [
                "",
                "[[subsystems]]",
                f"id = {json.dumps(subsystem['id'])}",
                f"scope = {json.dumps(subsystem['scope'])}",
                f"status = {json.dumps(subsystem['status'])}",
                f"summary = {json.dumps(subsystem['summary'])}",
                f"governing_intents = {json.dumps(subsystem['governing_intents'])}",
                f"anti_intents = {json.dumps(subsystem['anti_intents'])}",
                f"decision_tests = {json.dumps(subsystem['decision_tests'])}",
                f"confidence = {json.dumps(subsystem['confidence'])}",
                f"needs_review = {'true' if subsystem['needs_review'] else 'false'}",
                f"source_records = [{', '.join(source_records)}]",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def _load_subsystem_intent(*, target_root: Path) -> dict[str, Any]:
    path = target_root / WORKSPACE_SUBSYSTEM_INTENT_PATH
    ownership_ledger = target_root / _defaults_payload()["ownership_mapping"]["ledger"]
    ownership_subsystems = _load_ownership_subsystems(target_root=target_root)
    ownership_ids = {str(subsystem.get("id", "")).strip() for subsystem in ownership_subsystems if str(subsystem.get("id", "")).strip()}
    if not path.exists():
        return {
            "status": "missing",
            "path": WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix(),
            "kind": SUBSYSTEM_INTENT_KIND,
            "sync_command": "agentic-workspace system-intent --target ./repo --sync --format json",
            "ownership_registry": {
                "surface": ".agentic-workspace/OWNERSHIP.toml",
                "status": "present" if ownership_ledger.exists() else "missing",
                "subsystem_count": len(ownership_ids),
            },
            "subsystems": [],
        }
    payload = config_lib.load_toml_payload(path=path, surface_name=WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix())
    raw_subsystems = payload.get("subsystems", [])
    if not isinstance(raw_subsystems, list):
        raise WorkspaceUsageError(f"{WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix()} subsystems must be an array of tables.")
    subsystems: list[dict[str, Any]] = []
    for raw in raw_subsystems:
        if not isinstance(raw, dict):
            raise WorkspaceUsageError(f"{WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix()} subsystem entries must be tables.")
        identifier = str(raw.get("id", "")).strip()
        if not identifier:
            raise WorkspaceUsageError(f"{WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix()} subsystem entries must set id.")
        if ownership_ledger.exists() and identifier not in ownership_ids:
            accepted = ", ".join(sorted(ownership_ids)) or "none"
            raise WorkspaceUsageError(
                f"{WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix()} subsystem {identifier} is not declared in "
                f".agentic-workspace/OWNERSHIP.toml [[subsystems]]. Accepted subsystem ids: {accepted}."
            )
        _validate_intent_lifecycle_fields(surface=f"{WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix()} subsystem {identifier}", item=raw)
        subsystems.append(
            {
                "id": identifier,
                "scope": str(raw.get("scope", "")).strip(),
                "status": str(raw.get("status", "proposed")).strip() or "proposed",
                "summary": str(raw.get("summary", "")).strip(),
                "governing_intents": _intent_string_list(raw.get("governing_intents", [])),
                "anti_intents": _intent_string_list(raw.get("anti_intents", [])),
                "decision_tests": _intent_string_list(raw.get("decision_tests", [])),
                "open_questions": _intent_string_list(raw.get("open_questions", [])),
                "confidence": str(raw.get("confidence", "low")).strip() or "low",
                "needs_review": bool(raw.get("needs_review", True)),
                "supersedes": _intent_string_list(raw.get("supersedes", [])),
                "superseded_by": _intent_string_list(raw.get("superseded_by", [])),
                "last_reviewed_at": str(raw.get("last_reviewed_at", "")).strip(),
                "interpretation_notes": str(raw.get("interpretation_notes", "")).strip(),
                "source_records": _intent_source_records(raw.get("source_records", [])),
                "ownership_ref": identifier,
            }
        )
    return {
        "status": "present",
        "path": WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix(),
        "kind": str(payload.get("kind", SUBSYSTEM_INTENT_KIND)),
        "schema_version": int(payload.get("schema_version", 1)),
        "rule": str(payload.get("rule", "Subsystem intent is durable scoped decision pressure, not active task state by default.")),
        "ownership_registry": {
            "surface": ".agentic-workspace/OWNERSHIP.toml",
            "status": "present" if ownership_ledger.exists() else "missing",
            "subsystem_count": len(ownership_ids),
            "known_ids": sorted(ownership_ids),
            "rule": "OWNERSHIP.toml [[subsystems]] is authoritative for subsystem ids; subsystem intent attaches durable direction to those ids.",
        },
        "subsystem_count": len(subsystems),
        "subsystems": subsystems,
    }


def _intent_terms(value: str) -> set[str]:
    return {part for part in re.split(r"[^a-z0-9_-]+", value.lower()) if len(part) >= 3}


def _intent_decision_projection(
    *,
    target_root: Path,
    config: WorkspaceConfig,
    task_text: str | None = None,
    changed_paths: list[str] | None = None,
    compact: bool = False,
) -> dict[str, Any]:
    mirror = _load_system_intent_mirror(target_root=target_root, config=config)
    subsystem_intent = _load_subsystem_intent(target_root=target_root)
    ownership_matches = _subsystem_matches_for_changed_paths(target_root=target_root, changed_paths=changed_paths or [])
    ownership_matched_ids = {
        str(subsystem.get("id", "")).strip()
        for subsystem in ownership_matches.get("matched_subsystems", [])
        if isinstance(subsystem, dict) and str(subsystem.get("id", "")).strip()
    }
    ownership_matches_by_id = {
        str(subsystem.get("id", "")).strip(): subsystem
        for subsystem in ownership_matches.get("matched_subsystems", [])
        if isinstance(subsystem, dict) and str(subsystem.get("id", "")).strip()
    }
    task_terms = _intent_terms(task_text or "")
    path_terms = _intent_terms(" ".join(changed_paths or []))
    query_terms = task_terms | path_terms
    matched_subsystems: list[dict[str, Any]] = []
    for subsystem in subsystem_intent.get("subsystems", []):
        if not isinstance(subsystem, dict) or subsystem.get("status") in {"retired", "superseded"}:
            continue
        haystack = " ".join(
            [
                str(subsystem.get("id", "")),
                str(subsystem.get("scope", "")),
                str(subsystem.get("summary", "")),
                " ".join(subsystem.get("decision_tests", []) if isinstance(subsystem.get("decision_tests"), list) else []),
            ]
        )
        terms = _intent_terms(haystack)
        identifier = str(subsystem.get("id", "")).strip()
        if identifier in ownership_matched_ids or not query_terms or query_terms & terms:
            ownership_match = ownership_matches_by_id.get(identifier, {})
            matched_subsystems.append(
                {
                    "id": identifier,
                    "status": subsystem.get("status", ""),
                    "summary": subsystem.get("summary", ""),
                    "decision_tests": list(subsystem.get("decision_tests", []))[: 2 if compact else 4],
                    "confidence": subsystem.get("confidence", "low"),
                    "needs_review": subsystem.get("needs_review", True),
                    "match_source": "ownership-path" if identifier in ownership_matched_ids else "task-or-path-text",
                    **(
                        {
                            "ownership": {
                                "matched_paths": ownership_match.get("matched_paths", []),
                                "matched_patterns": ownership_match.get("matched_patterns", []),
                            }
                        }
                        if ownership_match
                        else {}
                    ),
                }
            )
    system_tests = mirror.get("decision_tests", []) if mirror.get("status") == "present" else []
    projection = {
        "kind": "agentic-workspace/durable-intent-decision/v1",
        "status": "present" if mirror.get("status") == "present" or subsystem_intent.get("status") == "present" else "missing",
        "rule": "Durable intent is decision pressure for scope, proof, delegation, and closeout; it is not active task state by default.",
        "task_intent": {
            "role": "bounded and closable",
            "promotion_question": "Did this task reveal reusable direction that should become Memory, subsystem intent, or system intent?",
        },
        "system_intent": {
            "status": mirror.get("status", "missing"),
            "surface": WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix(),
            "summary": mirror.get("summary", ""),
            "decision_tests": list(system_tests)[: 3 if compact else 6],
            "confidence": mirror.get("confidence", "low"),
            "needs_review": mirror.get("needs_review", True),
        },
        "subsystem_intent": {
            "status": subsystem_intent.get("status", "missing"),
            "surface": WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix(),
            "matched_count": len(matched_subsystems),
            "matches": matched_subsystems[: 3 if compact else 10],
        },
        "decision_effects": [
            "Use relevant decision tests before choosing scope or proof.",
            "Escalate when relevant durable intent is low-confidence, needs review, or implies compliance, accessibility, security, or high judgment.",
            "At closeout, classify discovered intent as do-not-promote, Memory, subsystem intent, system intent, refine-existing, or supersede-existing.",
        ],
        "commands": {
            "inspect": "agentic-workspace report --target ./repo --section durable_intent --format json",
            "refresh": "agentic-workspace system-intent --target ./repo --sync --format json",
            "defaults": "agentic-workspace defaults --section durable_intent --format json",
        },
    }
    if compact:
        projection = {
            "kind": projection["kind"],
            "status": projection["status"],
            "rule": "Use durable intent as decision pressure; it is not active task state.",
            "task_intent": {
                "role": "bounded and closable",
                "promotion_question": "Did this reveal durable direction?",
            },
            "system_intent": {
                "status": projection["system_intent"]["status"],
                "surface": projection["system_intent"]["surface"],
                "decision_tests": projection["system_intent"]["decision_tests"][:1],
                "needs_review": projection["system_intent"]["needs_review"],
            },
            "subsystem_intent": {
                "status": projection["subsystem_intent"]["status"],
                "surface": projection["subsystem_intent"]["surface"],
                "matched_count": projection["subsystem_intent"]["matched_count"],
                "ownership_registry": {
                    "surface": subsystem_intent.get("ownership_registry", {}).get("surface", ".agentic-workspace/OWNERSHIP.toml"),
                    "status": subsystem_intent.get("ownership_registry", {}).get("status", "unknown"),
                    "subsystem_count": subsystem_intent.get("ownership_registry", {}).get("subsystem_count", 0),
                },
                "matches": [
                    {
                        "id": match.get("id", ""),
                        "decision_tests": list(match.get("decision_tests", []))[:1],
                        "needs_review": match.get("needs_review", True),
                        "match_source": match.get("match_source", ""),
                    }
                    for match in projection["subsystem_intent"]["matches"][:2]
                    if isinstance(match, dict)
                ],
            },
            "decision_effects": ["Use relevant decision tests before choosing scope or proof."],
            "inspect": "agentic-workspace report --target ./repo --section durable_intent --format json",
        }
    return projection


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
    subsystem_path = target_root / WORKSPACE_SUBSYSTEM_INTENT_PATH
    if not subsystem_path.exists():
        subsystem_text = _default_subsystem_intent_text()
        if not dry_run:
            subsystem_path.parent.mkdir(parents=True, exist_ok=True)
            subsystem_path.write_text(subsystem_text, encoding="utf-8")
        actions.append(
            {
                "kind": "would-create" if dry_run else "created",
                "path": WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix(),
                "detail": "create editable subsystem-intent store with starter planning and memory records",
            }
        )
    else:
        actions.append(
            {
                "kind": "current",
                "path": WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix(),
                "detail": "subsystem-intent store already present",
            }
        )
    return actions, _load_system_intent_mirror(target_root=target_root, config=config)


def _system_intent_report_payload(*, target_root: Path, config: WorkspaceConfig) -> dict[str, Any]:
    mirror = _load_system_intent_mirror(target_root=target_root, config=config)
    subsystem_intent = _load_subsystem_intent(target_root=target_root)
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
        "subsystem_intent": subsystem_intent,
        "decision_projection": _intent_decision_projection(target_root=target_root, config=config),
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
                "agentic-workspace config --target ./repo --profile tiny --format json",
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
        "agentic-workspace config --target ./repo --profile tiny --format json",
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
        "task_shape_recommender": _task_shape_recommender_payload(),
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
                "consult": ["agentic-planning handoff --format json"],
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
    payload["narrow_work_fast_path"] = {
        "status": "blessed",
        "one_compact_check": "agentic-workspace report --target ./repo --format json",
        "rule": "For small direct tasks, use one compact state check, do the work, and promote only if scope widens into sequencing, proof ambiguity, or handoff continuity.",
        "promote_when": [
            "the task claims roadmap or issue-lane progress",
            "proof scope becomes expensive or ambiguous to reconstruct",
            "handoff or restart continuity would be costly without checked-in state",
        ],
    }
    payload["recommendation"] = {
        "id": "stay-direct",
        "summary": "Stay direct unless the work widens enough to need checked-in planning or a compact handoff.",
        "why": [
            "There is no active planning-backed slice that justifies a planner-to-worker split by default.",
            "The mixed-agent posture remains advisory rather than scheduler-like when work is still cheap and self-sufficient.",
        ],
        "consult": ["agentic-workspace config --target ./repo --profile tiny --format json"],
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


def _task_shape_recommender_payload() -> dict[str, Any]:
    return {
        "status": "available",
        "rule": "Choose the cheapest workflow shape that preserves proof and continuation honesty.",
        "shapes": [
            {
                "id": "direct",
                "use_when": "one bounded answer or edit can be completed and proved without sequencing or handoff state",
                "minimum_package_use": "one compact report or summary check when repo state matters",
                "promote_when": "the task starts claiming lane progress, unclear proof, or expensive continuation",
            },
            {
                "id": "light-plan",
                "use_when": "the task has a few ordered steps but does not need durable cross-session ownership",
                "minimum_package_use": "summary/report plus explicit final proof",
                "promote_when": "later review would need checked-in milestone, intent, or handoff evidence",
            },
            {
                "id": "checked-in-execplan",
                "use_when": "broad lane work, autopilot work, issue batches, handoff-sensitive work, or intent that is expensive to reconstruct",
                "minimum_package_use": "active todo item, execplan, proof selection, and closeout evidence",
                "promote_when": "already required",
            },
        ],
    }


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
        "subsystem_surface": WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix(),
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
        "durable_intent_command": "agentic-workspace defaults --section durable_intent --format json",
    }


def _durable_intent_payload() -> dict[str, Any]:
    return {
        "canonical_doc": ".agentic-workspace/docs/system-intent-contract.md",
        "command": "agentic-workspace defaults --section durable_intent --format json",
        "rule": "Task intent is closable work; system and subsystem intent are durable, editable decision pressure with provenance.",
        "intent_scopes": [
            {
                "id": "task",
                "role": "bounded goal for current work",
                "closure": "can be satisfied and validated during implementation",
                "promotion": "classify at closeout; do not persist by default",
            },
            {
                "id": "subsystem",
                "role": "durable direction for a component, module, concern, or owned surface",
                "surface": WORKSPACE_SUBSYSTEM_INTENT_PATH.as_posix(),
                "registry": ".agentic-workspace/OWNERSHIP.toml [[subsystems]]",
                "closure": "not closed by one task; revised, superseded, or retired over time",
            },
            {
                "id": "system",
                "role": "durable repo/system-wide direction, purpose, constraint, or invariant",
                "surface": WORKSPACE_SYSTEM_INTENT_MIRROR_PATH.as_posix(),
                "closure": "not active work; inspected and refined as understanding or requirements change",
            },
        ],
        "promotion_choices": [
            "do-not-promote",
            "memory",
            "subsystem-intent",
            "system-intent",
            "refine-existing-intent",
            "supersede-existing-intent",
        ],
        "promotion_rule": (
            "Promotion from task evidence creates reviewable durable intent proposals with evidence and confidence; "
            "agents must not silently make inferred intent authoritative. Subsystem intent ids must already exist in "
            ".agentic-workspace/OWNERSHIP.toml [[subsystems]]."
        ),
        "record_fields": [
            "id",
            "scope",
            "status",
            "summary",
            "governing_intents",
            "anti_intents",
            "decision_tests",
            "source_records",
            "confidence",
            "needs_review",
            "supersedes",
            "superseded_by",
            "last_reviewed_at",
            "open_questions",
        ],
        "decision_consumption": [
            "start/preflight can surface compact relevant intent pressure before implementation",
            "report --section durable_intent returns the inspectable projection",
            "planning closeout asks whether task intent revealed durable intent worth promotion",
            "proof/delegation should escalate when relevant intent implies compliance, accessibility, security, or high judgment",
        ],
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
        "rule": "Use a strong planner to normalize the vague prompt, then hand compact exploration, implementation, or validation contracts to bounded executors without prescribing the execution method.",
        "selection_rule": (
            "Use the effective mixed-agent posture from agentic-workspace config, then keep the same handoff contract whether execution stays internal, external over cli or api, or direct."
        ),
        "handoff_command": "agentic-planning handoff --format json",
        "planner_role": {
            "summary": "shape confirmed and interpreted intent, choose the proof lane, and freeze the smallest safe contract.",
            "does": [
                "clarify the request with the smallest repo-context follow-up",
                "choose the narrow proof lane and owner surface",
                "preserve escalation boundaries before the handoff freezes",
            ],
        },
        "explorer_role": {
            "summary": "answer one bounded repo-inspection question without owning writes or implementation direction.",
            "does": [
                "inspect only the listed files, commands, or planning surfaces",
                "return compact evidence, uncertainty, and the next recommended read",
                "stop before editing, broad synthesis, or product-shape decisions",
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
                "read-only exploration for one explicit question when assigned",
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
    *,
    target_root: Path,
    reports: list[dict[str, Any]],
    descriptors: dict[str, ModuleDescriptor],
    command_name: str,
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
            if kind in {"created", "copied"} or (command_name not in {"status", "doctor"} and kind in {"would create", "would copy"}):
                _append_unique(created, relative_path)
            elif kind in {"updated", "overwritten"} or (
                command_name not in {"status", "doctor"} and kind in {"would update", "would overwrite"}
            ):
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


def _lifecycle_next_steps(*, command_name: str, target_root: Path, warnings: list[str], cli_invoke: str = DEFAULT_CLI_INVOKE) -> list[str]:
    target = target_root.as_posix()
    if command_name == "status":
        command = _command_with_cli_invoke(command=f"agentic-workspace doctor --target {target}", cli_invoke=cli_invoke)
        return [] if not warnings else [f"Run {command} to inspect the reported warnings."]
    if command_name == "doctor":
        return [] if not warnings else ["Review the warning list and apply the narrowest remediation that closes each issue."]
    if command_name == "upgrade":
        command = _command_with_cli_invoke(command=f"agentic-workspace doctor --target {target}", cli_invoke=cli_invoke)
        return [f"Run {command} after the refresh completes."]
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
            "agentic-workspace config --target ./repo --profile tiny --format json",
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
        "first_contact_budget": {
            "status": "active",
            "ordinary_entry": "AGENTS.md -> agentic-workspace report --target ./repo --format json",
            "warning": "Do not add another first-contact surface unless it replaces, merges, compresses, or backgrounds an existing route.",
            "review_test": [
                "does the new surface make the package easier to enter, recover, verify, or trust?",
                "does it remove, merge, compress, or background an existing surface?",
                "can a reviewer see the improvement without reconstructing chat?",
            ],
        },
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
            "ordinary_path": "agentic-workspace proof --target ./repo --profile tiny --changed <paths> --format json",
            "answer_field": "surface_value_review",
            "rule": "Durable-surface changes should carry an inspectable answer during ordinary proof selection.",
            "flags_additive_only_when": [
                "the changed durable path does not currently exist under the target",
                "the change appears to add a new first-line docs, contract, schema, workflow, adapter, report, memory, or planning surface",
                "no repeated-cost, ownership, discovery, and validation answer is visible",
            ],
        },
    }


def _friction_capture_shortcut_payload() -> dict[str, Any]:
    return {
        "status": "available",
        "owner_surface": "repo_friction",
        "rule": "Capture friction as structured evidence first; promote only when repeated evidence justifies active work.",
        "minimum_record": [
            "observed friction",
            "evidence source",
            "likely classification",
            "why workspace adaptation can or cannot absorb it",
            "desired cheaper correction",
        ],
        "cheap_destinations": [
            "agentic-workspace report --target ./repo --section repo_friction --format json",
            ".agentic-workspace/planning/reviews/ for bounded review evidence",
            ".agentic-workspace/planning/state.toml only when promotion is justified",
        ],
        "promotion_trigger": "repeated shared friction, or one bounded review artifact plus one repeated maintenance or dogfooding pass",
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
    idle_context: list[dict[str, str]] = []
    if active_status == "absent":
        idle_context.append(
            {
                "id": "no-active-planning-record",
                "summary": "No active planning record is present; this is normal for idle or narrow direct work.",
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
                "concern": "compiled subsystem intent",
                "authority_class": "authoritative",
                "owner": "workspace",
                "surface": ".agentic-workspace/system-intent/subsystems.toml",
                "status": "present" if target_root and (target_root / WORKSPACE_SUBSYSTEM_INTENT_PATH).exists() else "missing",
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
        "owner_choice_review": contract_inventory.get("owner_choice_model", {}),
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
        "idle_context": idle_context,
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
                "ask_first": "agentic-workspace config --target ./repo --profile tiny --format json",
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
                "agentic-workspace config --target ./repo --profile tiny --format json",
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
                    "agentic-workspace config --target ./repo --profile tiny --format json",
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
            {"field": "force", "purpose": "whether the matched obligation is informational, recommended, required, or blocking"},
            {"field": "scope_tags", "purpose": "which slices or surfaces should consider the obligation relevant"},
            {"field": "commands", "purpose": "bounded commands or checks the repo expects before the stage completes"},
            {"field": "review_hint", "purpose": "compact reminder for review or closure surfaces"},
        ],
        "supported_stages": list(SUPPORTED_WORKFLOW_OBLIGATION_STAGES),
        "supported_forces": list(SUPPORTED_WORKFLOW_OBLIGATION_FORCES),
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
        "invoked_cli_identity": _invoked_cli_identity_payload(target_root=target_root, compact=True),
        "active_intent": active_record.get("requested_outcome") or "No active intent",
        "immediate_next_action": active_record.get("next_action") or "No next action",
        "tiny_safe_model": tiny_safe_model,
        "module_boundaries": _defaults_payload()["startup"]["top_level_capabilities"],
        "critical_invariants": manifest.get("invariants") or [],
        "escalation_boundaries": active_record.get("escalate_when") or [],
        "relevant_handoff_context": plan_report.get("active", {}).get("handoff_contract") or {},
    }
    cli_compatibility = _cli_compatibility_payload(config=config, compact=True)
    if cli_compatibility["configured"]:
        payload["cli_compatibility"] = cli_compatibility

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


def _emit_modules(*, format_name: str, target_root: Path | None, profile: str = "tiny") -> None:
    descriptors = _module_operations()
    registry = _module_registry(descriptors=descriptors, target_root=target_root)
    full_payload = {
        "package_footprint": copy.deepcopy(_PACKAGE_FOOTPRINT),
        "component_model": copy.deepcopy(_MODULE_COMPONENT_MODEL),
        "workspace_components": copy.deepcopy(_WORKSPACE_COMPONENTS),
        "module_profiles": copy.deepcopy(list(_MODULE_PROFILE_ENTRIES)),
        "feature_tiers": copy.deepcopy(list(_FEATURE_TIER_ENTRIES)),
        "feature_tiers_compatibility": {
            "status": "deprecated-alias",
            "canonical_field": "module_profiles",
            "rule": "Feature tiers are retained for weak-agent/backward compatibility; module_profiles are the canonical module-selection contract.",
        },
        "advanced_features": copy.deepcopy(list(_ADVANCED_FEATURE_ENTRIES)),
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
                "components": copy.deepcopy(_MODULE_REGISTRY_ENTRIES.get(entry.name, {}).get("components", {})),
                "result_contract": {
                    "schema_version": entry.result_contract.schema_version,
                    "guaranteed_fields": list(entry.result_contract.guaranteed_fields),
                    "action_fields": list(entry.result_contract.action_fields),
                    "warning_fields": list(entry.result_contract.warning_fields),
                },
                "command_args": {name: list(args) for name, args in descriptors[entry.name].command_args.items()},
            }
            for entry in registry
        ],
    }
    if profile == "tiny":
        installed = [entry for entry in registry if entry.installed]
        payload = {
            "kind": "agentic-workspace/modules-router/v1",
            "profile": "tiny",
            "target": target_root.as_posix() if target_root is not None else None,
            "active_module_count": len(installed),
            "active_modules": [entry.name for entry in installed],
            "available_module_profiles": [
                {
                    "id": str(entry.get("id", "")),
                    "modules": list(entry.get("selected_modules", [])),
                    "preset": entry.get("preset"),
                    "default_active": bool(entry.get("default_active", True)),
                }
                for entry in _MODULE_PROFILE_ENTRIES
            ],
            "detail_commands": {
                "full": "agentic-workspace modules --target . --profile full --format json",
                "status": "agentic-workspace status --target . --format json",
            },
        }
    else:
        payload = full_payload
    _emit_payload(payload=payload, format_name=format_name)


def _startup_skill_routing_payload(
    *,
    cli_invoke: str = DEFAULT_CLI_INVOKE,
    enabled_advanced_features: Sequence[str] = (),
    compact: bool = False,
    target_root: Path | None = None,
    task_text: str | None = None,
) -> dict[str, Any]:
    skill_command = _command_with_cli_invoke(
        command='agentic-workspace skills --target ./repo --task "<task>" --format json',
        cli_invoke=cli_invoke,
    )
    core_routes = [
        {
            "task_shape": "active planning report, restart, or proof posture",
            "skill": "planning-reporting",
            "fallback": "agentic-workspace summary --format json",
        },
        {
            "task_shape": "managed planning bootstrap upgrade",
            "skill": "bootstrap-upgrade",
            "fallback": "agentic-workspace doctor --target ./repo --modules planning --format json",
        },
    ]
    configured_features = set(enabled_advanced_features)
    available_advanced_routes = [
        {
            "task_shape": "active planned work or autopilot execution",
            "skill": "planning-autopilot",
            "feature": "autopilot_loops",
            "fallback": "agentic-workspace summary --format json, then the active execplan",
        },
        {
            "task_shape": "external issue or tracker intake",
            "skill": "planning-intake-upstream-task",
            "feature": "external_adapters",
            "fallback": ".agentic-workspace/planning/upstream-task-intake.md plus checked-in planning state",
        },
        {
            "task_shape": "bounded review or finding capture",
            "skill": "planning-review-pass",
            "feature": "review_artifacts",
            "fallback": "agentic-workspace report --target ./repo --format json before selecting any review artifact",
        },
    ]
    advanced_routes = [route for route in available_advanced_routes if str(route.get("feature", "")) in configured_features]
    payload: dict[str, Any] = {
        "status": "advisory",
        "rule": "Prefer task-specific package skills when the runtime supports them; keep compact CLI and workflow docs as the fallback. Advanced host-repo diagnostics are opt-in.",
        "query": skill_command,
        "advanced_route_rule": "Review and external-intake skills are surfaced only when the repo enables the matching reusable diagnostic feature. Source-checkout-only maintainer skills stay outside shipped feature tiers.",
        "fallback_when_skills_unavailable": [
            "follow AGENTS.md and .agentic-workspace/WORKFLOW.md",
            'use agentic-workspace start --profile tiny --task "<task>" --format json for ordinary first contact',
            "use agentic-workspace summary --format json before raw planning reads",
        ],
        "preferred_routes": core_routes + advanced_routes,
    }
    if configured_features:
        payload["enabled_advanced_routes"] = [route["feature"] for route in advanced_routes]
    else:
        payload["available_advanced_route_command"] = "agentic-workspace modules --target ./repo --format json"
    task_recommendations = _task_skill_recommendations_payload(
        target_root=target_root,
        task_text=task_text,
        cli_invoke=cli_invoke,
        compact=compact,
    )
    if task_recommendations["status"] != "not-requested":
        payload["task_recommendations"] = task_recommendations
    if compact:
        fallback_items = payload.pop("fallback_when_skills_unavailable", [])
        payload["preferred_routes"] = [
            {"task_shape": route["task_shape"], "skill": route["skill"]} for route in payload["preferred_routes"] if isinstance(route, dict)
        ]
        payload["fallback_when_skills_unavailable_count"] = len(fallback_items) if isinstance(fallback_items, list) else 0
        payload["fallback_detail"] = "Use AGENTS.md and compact CLI routers when skills are unavailable."
    return payload


def _task_skill_recommendations_payload(
    *,
    target_root: Path | None,
    task_text: str | None,
    cli_invoke: str,
    compact: bool = False,
) -> dict[str, Any]:
    skill_command = _command_with_cli_invoke(
        command='agentic-workspace skills --target ./repo --task "<task>" --format json',
        cli_invoke=cli_invoke,
    )
    if not task_text or not task_text.strip():
        return {
            "status": "not-requested",
            "command": skill_command,
            "hint": "Pass --task with the current user request to include task-specific skill recommendations in startup output.",
        }
    if target_root is None:
        return {"status": "unavailable", "command": skill_command, "reason": "target_root is required for skill discovery"}
    skills_payload = _skills_payload(target_root=target_root, task_text=task_text)
    recommendations = skills_payload.get("recommendations", [])
    compact_items = [
        {
            "id": str(item.get("id", "")),
            "path": str(item.get("path", "")),
            "summary": str(item.get("summary", "")),
            "score": item.get("score"),
            **({"reasons": item.get("reasons", [])[:2]} if not compact else {}),
        }
        for item in recommendations[:3]
        if isinstance(item, dict)
    ]
    return {
        "status": "recommended" if compact_items else "no-match",
        "task": task_text,
        "command": _command_with_cli_invoke(
            command=f"agentic-workspace skills --target ./repo --task {_shell_quote(task_text)} --format json",
            cli_invoke=cli_invoke,
        ),
        "top_recommendations": compact_items,
        "warning_count": len(skills_payload.get("warnings", [])) if isinstance(skills_payload.get("warnings", []), list) else 0,
    }


def _vague_outcome_orientation_payload(*, task_text: str | None, cli_invoke: str = DEFAULT_CLI_INVOKE) -> dict[str, Any]:
    task_lower = (task_text or "").lower()
    markers = (
        "feel more trustworthy",
        "trustworthy",
        "trust",
        "repeat what i meant",
        "what i meant",
        "less rework",
        "rework",
        "handoff",
        "hand work back",
        "intended outcome",
        "intent",
        "vague outcome",
        "satisfaction",
        "satisfied",
    )
    applies = bool(task_lower and any(marker in task_lower for marker in markers))
    return {
        "status": "applicable" if applies else "available",
        "applies_to_current_task": applies,
        "rule": "For vague outcome prompts, resolve intent and satisfaction evidence from compact CLI output before raw workspace reads.",
        "first_surface": "startup_guidance.primary_next_action from preflight or immediate_next_allowed_action from start",
        "compact_commands": [
            _command_with_cli_invoke(
                command='agentic-workspace preflight --target . --task "<task>" --format json',
                cli_invoke=cli_invoke,
            ),
            _command_with_cli_invoke(
                command='agentic-workspace start --target . --task "<task>" --format json',
                cli_invoke=cli_invoke,
            ),
            _command_with_cli_invoke(
                command='agentic-workspace skills --target . --task "<task>" --format json',
                cli_invoke=cli_invoke,
            ),
        ],
        "answer_contract": [
            "state the inferred intended outcome",
            "name the first repo-visible surface or compact command to inspect",
            "define satisfaction evidence before choosing an implementation",
            "separate one possible solution from the intended outcome",
        ],
        "raw_read_rule": "Open raw .agentic-workspace files only after compact output points there or the CLI is unavailable.",
    }


def _defaults_payload() -> dict[str, Any]:
    compact_manifest = compact_contract_manifest()
    proof_manifest = proof_routes_manifest()
    validation_lanes = [
        {
            "id": "generated_command_packages",
            "when": [
                "command-package IR, generator, or generated Python/TypeScript package outputs change",
                "the trust question is generated package freshness or non-Python package conformance",
            ],
            "enough_proof": [
                "uv run python scripts/check/check_generated_command_packages.py",
                "uv run python scripts/check/check_generated_command_packages.py --conformance --require-node",
                "uv run python scripts/check/check_generated_command_packages.py --docker --require-docker",
                "uv run python scripts/check/check_generated_command_packages.py --docker-conformance --require-docker",
            ],
            "proof_responsibility": "local-serial",
            "execution_mode": "serial",
            "ci_relationship": "CI may repeat generated-package proof; local closeout should run this lane serially to avoid package-build contention.",
            "broaden_when": [
                "the change also alters runtime CLI behavior outside generated metadata",
                "the change also touches package installer behavior beyond generated package surfaces",
            ],
            "escalate_when": [
                "generated package proof no longer covers the changed implementation boundary",
            ],
            "recovery_signal": (
                "Generated adapter/package changes must route back through command-package checks and conformance proof "
                "instead of being trusted as hand edits."
            ),
            "weak_agent_safe_routing": {
                "status": "proof-gated",
                "rule": (
                    "Generated targets are weak-agent safe only when command_package_ir selects weak-agent-safe-adapter "
                    "and generated-package static plus conformance proof pass."
                ),
                "checks": [
                    "help output includes supported commands and routing status",
                    "unsupported command errors include recovery guidance",
                    "runtime handoff failures include recovery guidance",
                ],
            },
        },
        {
            "id": "cli_authority",
            "when": [
                "generated, projected, or executable CLI files change",
                "the trust question is whether direct CLI editing is allowed for this slice",
            ],
            "enough_proof": [
                "agentic-workspace defaults --section root_cli_authority --format json",
            ],
            "broaden_when": [
                "the change also alters command contracts, generated packages, or package payloads",
            ],
            "escalate_when": [
                "the proof output cannot classify the CLI file as source, generator, projection, or hand-owned executable code",
                "a generated or projection target lacks a named source contract and regeneration path",
            ],
            "recovery_signal": "Use cli_authority_review to decide whether the edit is allowed runtime work or must route back to source contracts and regeneration.",
        },
        {
            "id": "contract_tooling",
            "when": [
                "workspace contract, schema, or contract-check surfaces change without runtime behavior changes",
                "the trust question is contract freshness, schema validation, or inventory/check policy",
            ],
            "enough_proof": [
                "uv run python scripts/check/check_contract_tooling_surfaces.py --quiet-success",
                "uv run python scripts/check/check_structured_file_inventory.py --quiet-success",
                "uv run ruff check src/agentic_workspace/contracts scripts/check tests/test_structured_file_inventory.py",
            ],
            "broaden_when": [
                "the change also touches runtime CLI behavior, report/startup rendering, generated adapters, or package payloads",
            ],
            "escalate_when": [
                "contract-only validation no longer proves the touched behavior boundary",
            ],
            "recovery_signal": (
                "Contract/check-only changes should use focused contract and inventory proof before broad workspace CLI tests."
            ),
        },
        {
            "id": "agent_aid_manifests",
            "when": [
                "checked-in candidate agent aids or their manifests change",
                "the trust question is candidate aid metadata, ownership, safety, portability, and proof-role policy",
            ],
            "enough_proof": [
                "uv run python scripts/check/check_agent_aids.py --quiet-success",
            ],
            "broaden_when": [
                "the change promotes an aid into a canonical proof route or repo-native checker",
                "the change also touches runtime CLI behavior, generated adapters, or package payloads",
            ],
            "escalate_when": [
                "candidate aid metadata no longer proves the workflow boundary",
                "a candidate aid is being treated as a required workflow entrypoint",
            ],
            "recovery_signal": (
                "Candidate aid changes should validate manifest safety and portability metadata; do not execute candidate aids "
                "as canonical proof until they are promoted."
            ),
        },
        {
            "id": "repo_docs_review",
            "when": [
                "ordinary repository documentation changes without code, generated docs, or adapter surfaces",
                "the trust question is whether the docs diff satisfies the requested outcome without adding misleading guidance",
            ],
            "enough_proof": [
                "git diff -- README.md docs .agentic-workspace/docs packages/planning/README.md packages/memory/README.md packages/command-generation/README.md",
            ],
            "proof_kind": "diff-review",
            "proof_responsibility": "local-closeout",
            "execution_mode": "review",
            "ci_relationship": "CI is not expected to prove docs intent; local diff review owns the trust question.",
            "broaden_when": [
                "the docs change updates generated maintainer surfaces, schema reference docs, or package payloads",
                "the docs change describes behavior whose implementation also changed or needs executable proof",
            ],
            "escalate_when": [
                "the documentation outcome cannot be verified from the diff and nearby docs alone",
            ],
            "recovery_signal": (
                "Docs-only wording changes should use compact diff review; broaden to maintainer or code proof when the docs "
                "are generated, adapter-owned, or coupled to behavior changes."
            ),
        },
        {
            "id": "workspace_cli",
            "when": [
                "root workspace CLI changes",
                "root tests changes",
                "root src/agentic_workspace changes",
            ],
            "enough_proof": [
                "make test-workspace",
                "make lint-workspace",
            ],
            "proof_kind": "targeted-test",
            "proof_responsibility": "local-closeout",
            "execution_mode": "parallel-ok",
            "ci_relationship": "CI may repeat broad tests; local proof should run the selected targeted lane before closeout.",
            "broaden_when": [
                "the change also touches generated maintainer docs",
                "the change also touches installed package payloads or shared orchestration boundaries",
            ],
            "escalate_when": [
                "the narrow lane cannot prove the change on its own",
                "package or repo-wide behavior is now part of the trust question",
            ],
            "recovery_signal": (
                "Direct workspace CLI changes need workspace CLI proof and, for interface changes, review against generated command contracts."
            ),
        },
        {
            "id": "planning_package",
            "when": [
                "package-local planning source or tests change",
                "the behavior remains inside packages/planning",
            ],
            "enough_proof": [
                "make test-planning",
                "make lint-planning",
            ],
            "proof_kind": "targeted-test",
            "proof_responsibility": "local-closeout",
            "execution_mode": "parallel-ok",
            "ci_relationship": "CI may repeat package tests; local proof should run the selected targeted lane before closeout.",
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
                "make test-memory",
                "make lint-memory",
            ],
            "proof_kind": "targeted-test",
            "proof_responsibility": "local-closeout",
            "execution_mode": "parallel-ok",
            "ci_relationship": "CI may repeat package tests; local proof should run the selected targeted lane before closeout.",
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
            "proof_responsibility": "local-closeout",
            "execution_mode": "parallel-ok",
            "ci_relationship": "CI may not have the live planning state being edited; local proof owns this check.",
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
            "proof_responsibility": "local-closeout",
            "execution_mode": "parallel-ok",
            "ci_relationship": "CI may repeat maintainer-surface checks; local proof owns generated-surface freshness before closeout.",
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
            "context_router": _context_router_family_payload(),
            "primary": [
                'For ordinary first contact, run `agentic-workspace start --profile tiny --task "<task>" --format json`.',
                "Use `agentic-workspace implement --profile tiny --changed <paths> --format json` when changed paths are already known.",
                "For takeover or recovery context, run `agentic-workspace preflight --format json`.",
                "Read the configured root startup file from `agentic-workspace config --target ./repo --profile tiny --format json` (default `AGENTS.md`).",
                "Use `agentic-workspace summary --format json` only when current planning state matters before opening raw planning files.",
                "Open `.agentic-workspace/planning/state.toml` or an active execplan only when compact output points there.",
            ],
            "tiny_safe_model": {
                "summary": "Start from one repo entrypoint, one ordinary startup query, and conditional deeper reads.",
                "entrypoint": "AGENTS.md",
                "entry_query": 'agentic-workspace start --profile tiny --task "<task>" --format json',
                "first_compact_queries": [
                    'agentic-workspace start --target ./repo --profile tiny --task "<task>" --format json',
                    "agentic-workspace implement --profile tiny --changed <paths> --format json",
                    "agentic-workspace config --target ./repo --profile tiny --format json",
                    "agentic-workspace summary --format json",
                ],
                "deeper_reads_become_valid_when": [
                    "the active summary points at an execplan or raw planning detail is still needed for direct planning maintenance",
                    "startup or routing ambiguity survives the compact startup answer",
                    "the task crosses a planning, memory, or lifecycle boundary that the small model cannot settle safely",
                ],
            },
            "vague_outcome_route": _vague_outcome_orientation_payload(task_text=None),
            "work_intent_gate": {
                "rule": "Choose the smallest workflow shape before implementation; when Planning is installed, broad work should become checked-in planning before edits.",
                "planning_mutation_rule": (
                    "Use compact CLI for orientation and proof selection; use package lifecycle commands such as "
                    "`agentic-planning new-plan`, `promote-to-plan`, and `archive-plan` for planning mutations when available; "
                    "edit checked-in planning records directly only for bounded content/fallback edits, then rerun summary."
                ),
                "levels": [
                    {
                        "id": "direct",
                        "use_when": "One coherent local pass can finish safely and validation is obvious.",
                        "required_surface": "chat plus narrow code/docs context",
                    },
                    {
                        "id": "bounded",
                        "use_when": "The task is one slice but needs explicit done-when, proof, or short continuation state.",
                        "required_surface": "configured planning or handoff surface when restart cost matters",
                    },
                    {
                        "id": "lane",
                        "use_when": "The work spans milestones, managed payloads, proof scope, or handoff risk.",
                        "required_surface": "Planning active item plus schema-backed execplan created by package command when installed; otherwise equivalent durable handoff surface",
                    },
                    {
                        "id": "epic",
                        "use_when": "The request contains multiple lanes or needs product shaping before implementation.",
                        "required_surface": "schema-backed decomposition record first when Planning provides one; split into bounded lanes before implementation execplans",
                    },
                ],
                "external_tracker_rule": "GitHub, Linear, Jira, Notion, and similar trackers are optional intake evidence; checked-in planning remains execution authority.",
                "assurance_rule": "Assess assurance from risk and scope signals; high-risk lane or epic work records adaptive_assurance when Planning is installed.",
            },
            "default_canonical_agent_instructions_file": DEFAULT_AGENT_INSTRUCTIONS_FILE,
            "supported_agent_instructions_files": list(SUPPORTED_AGENT_INSTRUCTIONS_FILES),
            "first_queries": [
                {
                    "question": "What is the ordinary first-contact path?",
                    "command": 'agentic-workspace start --profile tiny --task "<task>" --format json',
                    "field": "immediate_next_allowed_action",
                    "why": "start bundles ordinary startup routing, active-state summary, and task-specific skill recommendations",
                },
                {
                    "question": "What is the ordinary repo startup path?",
                    "command": "agentic-workspace defaults --section startup --format json",
                    "why": "startup defaults carry reference routing when start is unavailable or insufficient",
                },
                {
                    "question": "Which startup file is canonical here?",
                    "command": "agentic-workspace config --target ./repo --profile tiny --format json",
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
                    "role": "planning source behind compact summary, not ordinary first-contact reading",
                    "owner": "repo",
                    "kind": "canonical",
                    "edit_rule": "edit directly only when maintaining planning state or when compact output points here",
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
                "Use `agentic-workspace summary --format json` before checking raw planning state for promotion work.",
                "Read package-local `AGENTS.md` only for the package being edited.",
                "Read memory only when installed and the task needs durable context.",
            ],
            "escalation_cues": [
                {
                    "boundary": "workspace",
                    "cue": "The question is startup order, lifecycle behavior, config, ownership, or combined workspace state.",
                    "load_next": [
                        "agentic-workspace defaults --section startup --format json",
                        "agentic-workspace config --target ./repo --profile tiny --format json",
                        "agentic-workspace report --target ./repo --format json",
                    ],
                    "why": "Workspace-level surfaces own routing, lifecycle orchestration, and cross-module coordination.",
                },
                {
                    "boundary": "planning",
                    "cue": "The task needs active sequencing, blockers, proof expectations, promotion decisions, or cross-session continuation.",
                    "load_next": [
                        "agentic-workspace summary --format json",
                        "agentic-workspace summary --format json --profile full",
                        ".agentic-workspace/planning/state.toml only when the summary points there",
                        ".agentic-workspace/planning/execplans/ only when the summary points at an active execplan",
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
                    "`agentic-workspace config --target ./repo --profile tiny --format json` and follow "
                    "the configured startup file; if the CLI is unavailable, fall back to "
                    "`AGENTS.md` or another supported startup file already present."
                ),
                (
                    "If you need takeover guidance plus live state together, prefer "
                    "`agentic-workspace preflight --format json` before running multiple compact queries or rereading repo prose."
                ),
                (
                    "If the question is active planning recovery rather than startup order, "
                    "prefer the tiny default `agentic-workspace summary --format json` before raw "
                    "planning state or execplan prose; use `--profile compact` only when the tiny router is insufficient."
                ),
            ],
            "workflow_recovery": [
                (
                    "When takeover or recovery is unclear, prefer "
                    '`agentic-workspace start --profile tiny --task "<task>" --format json`, then '
                    "`agentic-workspace preflight --format json`, "
                    "`agentic-workspace defaults --section startup --format json`, "
                    "`agentic-workspace config --target ./repo --profile tiny --format json`, and "
                    "`agentic-workspace summary --format json` before broader "
                    "prose or repo-local workaround guidance."
                ),
            ],
            "skill_routing": _startup_skill_routing_payload(),
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
                        "agentic-workspace config --target ./repo --profile tiny --format json",
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
                    "ask_first": "agentic-workspace config --target ./repo --profile tiny --format json",
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
            "rule": (
                "Use an installed public workspace entrypoint and choose the smallest preset that matches the repo's main "
                "operating problem."
            ),
            "default_entrypoint": "agentic-workspace",
            "cli_availability": {
                "preferred": "Use `agentic-workspace` already installed in the target repo's environment.",
                "if_unavailable": "Install `agentic-workspace` into the target repo or its tool environment, then rerun the same lifecycle command.",
                "temporary_fallback": "`uvx` or `pipx run` may be used for explicit temporary/debug runs, but they are not the default host-repo install path.",
                "why": "Startup and follow-on work rely on repeated CLI calls, so a stable installed command is cheaper and safer than one-shot no-install runners.",
            },
            "default_answer": "Start with `memory` when durable repo knowledge is the main problem; choose `planning` for active execution continuity and `full` only when both are justified.",
            "recommendation_order": [
                "memory",
                "planning",
                "full",
            ],
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
                "summary": "Choose `memory` when you want the smallest useful shared core.",
                "why": "It keeps the visible surface smaller than `planning` or `full` while still giving the repo durable knowledge and compact routing.",
            },
        },
        "lifecycle": {
            "primary_entrypoint": "agentic-workspace",
            "default_install_command": "agentic-workspace install --target ./repo --preset <memory|planning|full>",
            "cli_availability_rule": "Prefer the installed `agentic-workspace` command; if missing, install it before bootstrap instead of defaulting to uvx or pipx.",
            "default_setup_posture": "smallest-viable-preset-first",
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
            "primary_router": "agentic-workspace defaults --section improvement_intake --format json",
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
        "improvement_intake": {
            "canonical_doc": "src/agentic_workspace/contracts/improvement_signal_contract.json",
            "command": "agentic-workspace defaults --section improvement_intake --format json",
            "rule": "Use one improvement-intake router before treating setup findings, review findings, validation friction, or memory improvement signals as separate mechanisms.",
            "payload": _improvement_intake_payload(),
        },
        "repair_recovery": _repair_recovery_taxonomy_payload(),
        "improvement_signal": {
            "canonical_doc": "src/agentic_workspace/contracts/improvement_signal_contract.json",
            "command": "agentic-workspace defaults --section improvement_signal --format json",
            "rule": "Use the compact signal shape to capture friction before deciding whether to fix, route, remember, review, or dismiss it.",
            "payload": _improvement_signal_contract_payload(),
        },
        "agent_configuration_system": _agent_configuration_system_payload(),
        "agent_configuration_queries": _agent_configuration_queries_payload(),
        "agent_configuration_workflow_extensions": _agent_configuration_workflow_extensions_payload(),
        "agent_aid_storage": _agent_aid_storage_payload(),
        "system_intent": _system_intent_payload(),
        "durable_intent": _durable_intent_payload(),
        "surface_value_guardrail": _surface_value_guardrail_payload(),
        "effective_authority": _effective_authority_payload(),
        "intent": _intent_contract_payload(),
        "clarification": _clarification_contract_payload(),
        "prompt_routing": _prompt_routing_contract_payload(),
        "relay": _relay_contract_payload(),
        "config": {
            "path": ".agentic-workspace/config.toml",
            "command": "agentic-workspace config --target ./repo --profile tiny --format json",
            "supported_fields": [
                "workspace.default_preset",
                "workspace.agent_instructions_file",
                "workspace.workflow_artifact_profile",
                "workspace.improvement_latitude",
                "workspace.optimization_bias",
                "workspace.advanced_features",
                "system_intent.sources",
                "system_intent.preferred_source",
                "workflow_obligations.<name>.summary",
                "workflow_obligations.<name>.stage",
                "workflow_obligations.<name>.force",
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
            "incidental_finding_policy": copy.deepcopy(_IMPROVEMENT_LATITUDE_POLICY["incidental_finding_policy"]),
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
                "optional local machine/runtime override",
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
                "supported_target_context_capacities": list(SUPPORTED_DELEGATION_TARGET_CONTEXT_CAPACITIES),
                "supported_target_reasoning_profiles": list(SUPPORTED_DELEGATION_TARGET_REASONING_PROFILES),
                "supported_target_cost_classes": list(SUPPORTED_DELEGATION_TARGET_COST_CLASSES),
                "supported_target_latency_classes": list(SUPPORTED_DELEGATION_TARGET_LATENCY_CLASSES),
                "supported_delegation_modes": list(SUPPORTED_DELEGATION_CONTROL_MODES),
                "supported_clarification_modes": list(SUPPORTED_CLARIFICATION_CONTROL_MODES),
                "intended_scope": [
                    "machine-specific capability posture",
                    "account- or cost-profile asymmetry",
                    "local execution preferences that do not redefine repo semantics",
                    "available delegation target hints that stay advisory and local-only",
                ],
            },
            "delegation_control": {
                "field": "delegation.mode",
                "default": "suggest",
                "supported_modes": list(SUPPORTED_DELEGATION_CONTROL_MODES),
                "quality_first_rule": (
                    "Delegation should improve quality where it matters and is worth the overhead; "
                    "token saving is valid only when safe and not quality-compromising."
                ),
                "mode_semantics": {
                    "off": "do not recommend local delegation targets",
                    "manual": "prepare handoff packets or prompts only",
                    "suggest": "recommend a target and rationale, but do not execute",
                    "auto": "permit automatic delegation only when local safety and target rules allow it",
                },
            },
            "clarification_control": {
                "field": "clarification.mode",
                "default": "suggest",
                "supported_modes": list(SUPPORTED_CLARIFICATION_CONTROL_MODES),
                "mode_semantics": {
                    "ask-first": "stop and ask when task intent, ownership, or required information is unclear",
                    "suggest": "surface the ask-human option without forcing it when uncertainty is material",
                    "auto-continue": "continue with the best bounded interpretation unless a hard blocker is present",
                },
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
            "local_scratch": _local_scratch_payload(),
            "agent_aid_storage": _agent_aid_storage_payload(),
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
                "weak_target_escalation": {
                    "rule": (
                        "A weak target may save tokens only for work inside its advertised fit. When runtime_resolution "
                        "marks a weak target below the recommended strength for boundary-shaping or reasoning-heavy work, "
                        "the target must not execute directly; it must escalate, request a stronger planner, or return a "
                        "compact manual handoff depending on delegation.mode."
                    ),
                    "mode_actions": {
                        "off": "stay direct only for current-agent execution; do not delegate to the weak target",
                        "manual": "prepare a strong_handoff_packet and stop for human/runtime execution",
                        "suggest": "recommend a stronger planner or handoff packet; do not execute the weak target automatically",
                        "auto": "route to a stronger configured target when safety allows; otherwise stop with manual-handoff",
                    },
                    "quality_over_cost": "Cost saving is valid only after capability fit and proof expectations remain safe.",
                },
                "strong_target_downrouting": {
                    "rule": (
                        "A strong target should not monopolize mechanical-follow-through work when a configured cheaper "
                        "bounded executor fits the task and proof remains clear. Prefer down-routing in suggest/auto modes, "
                        "but keep execution quality and human control ahead of token saving."
                    ),
                    "mode_actions": {
                        "off": "stay direct; do not force delegation for cheap work",
                        "manual": "prepare a compact handoff for the cheaper target and stop",
                        "suggest": "recommend the cheaper bounded executor and keep the strong target as planner/reviewer fallback",
                        "auto": "delegate to the cheaper bounded executor when safety allows; otherwise stay direct",
                    },
                    "quality_over_cost": "Down-routing is valid only when the task is bounded, mechanical, and cheaply provable.",
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
                    "work shape",
                    "proof burden",
                    "risk flags",
                    "inspection evidence required",
                ],
                "resolution_algorithm": [
                    "weak target below recommended_strength on boundary-shaping or reasoning-heavy work -> escalate-before-execution; never treat the weak target as the executor of record",
                    "strong target above recommended_strength on mechanical-follow-through work -> delegate-down-when-safe if a cheaper fit exists; keep strong planner/reviewer fallback",
                    "strong_external_reasoning='preferred' → external-delegation if external targets exist, else stronger-reasoning, else manual-handoff",
                    "execution_class in (boundary-shaping, reasoning-heavy) or recommended_strength=strong → stronger-reasoning if available, else external-delegation, else manual-handoff",
                    "execution_class=mixed → stay-local if local profiles acceptable, else stronger-reasoning",
                    "execution_class=mechanical-follow-through or recommended_strength in (weak, medium) → stay-local",
                    "no posture → stay-local with confidence derived from cheap_bounded_executor_available",
                ],
                "confidence_levels": ["high", "medium", "low"],
                "self_assessment": _self_assessment_authority_payload(),
            },
            "capability_handoff_packets": _capability_handoff_packet_templates(),
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
                "split it into planner/explorer/implementer/validator subtasks, or escalate to a stronger planner."
            ),
            "preferred_split": [
                "planner",
                "explorer",
                "implementer",
                "validator",
            ],
            "post_decomposition_checkpoint": {
                "rule": "After a decomposition or execplan exists, revisit each bounded slice for safe token-saving or quality-improving routes.",
                "route_candidates": [
                    "keep-local",
                    "delegate-exploration",
                    "delegate-implementation",
                    "delegate-validation",
                    "escalate-review",
                    "no-safe-route",
                ],
                "required_fields": [
                    "slice id",
                    "route",
                    "reason",
                    "quality risk",
                    "token-saving class",
                    "read-first refs",
                    "write scope",
                    "proof burden",
                    "stop conditions",
                    "return contract",
                ],
            },
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
                "Do not use weak targets for high-judgment work just to save tokens; escalate first.",
                "Do not spend strong-agent budget on mechanical work when a safe cheaper route is configured.",
                "Do not silently rewrite ends.",
            ],
            "capability_posture_fields": [
                "execution class",
                "recommended strength",
                "preferred location",
                "delegation friendly",
                "strong external reasoning",
                "work shape",
                "proof burden",
                "risk flags",
                "inspection evidence required",
                "classification authority",
                "self-assessment authority",
                "why",
            ],
            "outcome_feedback_fields": [
                "route chosen",
                "route skipped reason",
                "expected savings",
                "actual friction",
                "proof result",
                "quality concern",
                "decomposition adjustment",
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
            "construction_boundary": {
                "rule": "Validation should confirm correct construction, not teach agents how to construct the artifact or workflow after failure.",
                "route_repeated_repair_to": [
                    "scaffold",
                    "writer_helper",
                    "alias",
                    "lifecycle_command",
                    "compact_route",
                    "agent_aid",
                ],
            },
            "default_routes": {
                "workspace_cli": "make test-workspace",
                "planning_package": "make test-planning",
                "memory_package": "make test-memory",
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
            "construction_boundary": "Proof and validation confirm correct construction; repeated construction repair loops should route to interface/scaffold improvements instead of more validation prose.",
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
        "root_cli_authority": python_runtime_boundary_manifest()["root_cli_authority_audit"],
        "assurance_onboarding": _assurance_onboarding_payload(),
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
            "primary": "agentic-workspace install --target ./repo --preset <memory|planning|full>",
            "cli_availability_rule": "Use an installed `agentic-workspace` CLI first; install it if unavailable, and reserve uvx/pipx for explicit temporary fallback.",
            "full_when": "Use --preset full only when both active-now planning and durable anti-rediscovery memory are worth the shared footprint.",
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
                "agentic-workspace config --target ./repo --profile tiny --format json",
            ],
            "refresh_contract": [
                "uv run agentic-planning upgrade --target .",
                "uv run agentic-memory upgrade --target .",
            ],
            "handoff_surfaces": [
                "llms.txt",
                ".agentic-workspace/bootstrap-handoff.md",
                ".agentic-workspace/bootstrap-handoff.json",
            ],
            "effective_output_posture": {
                "command": "agentic-workspace config --target ./repo --profile tiny --format json",
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


def _tiny_defaults_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sections = sorted(str(key) for key in payload)
    return {
        "kind": "agentic-workspace/defaults-router/v1",
        "profile": "tiny",
        "summary": "Default-route contract sections are available on demand; request one section or full detail instead of loading the whole contract.",
        "available_sections": sections,
        "common_sections": [
            "startup",
            "proof_surfaces",
            "memory_routing",
            "capability_routing",
            "closeout_trust",
            "compact_contract_profile",
        ],
        "detail_commands": {
            "section": "agentic-workspace defaults --section <section> --format json",
            "full": "agentic-workspace defaults --profile full --format json",
        },
    }


def _emit_defaults(*, format_name: str, section: str | None = None, profile: str = "tiny") -> None:
    payload = _defaults_payload()
    if section is not None:
        payload = _select_defaults_section(payload, section=section)
    elif profile == "tiny":
        payload = _tiny_defaults_payload(payload)
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


def _tiny_proof_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("profile") == "compact-contract-answer/v1":
        answer = payload.get("answer", {})
        required_commands = answer.get("required_commands", []) if isinstance(answer, dict) else []
        validation_plan = answer.get("validation_plan", {}) if isinstance(answer, dict) else {}
        primary = validation_plan.get("primary_next_action") if isinstance(validation_plan, dict) else None
        if not isinstance(primary, dict):
            primary = {
                "action": "run-validation-command" if required_commands else "select-proof-scope",
                "command": required_commands[0] if required_commands else None,
                "run": required_commands[0] if required_commands else None,
            }
        surface_value = answer.get("surface_value_review") if isinstance(answer, dict) else None
        warnings: list[dict[str, Any]] = []
        if isinstance(surface_value, dict) and surface_value.get("status") in {"blocked", "needs-review"}:
            warnings.append(
                {
                    "status": surface_value.get("status"),
                    "summary": surface_value.get("summary") or surface_value.get("rule"),
                }
            )
        return {
            "kind": "proof-next-decision/v1",
            "target": payload.get("target"),
            "selector": payload.get("selector", {}),
            "next": {
                "action": primary.get("action", "run-validation-command"),
                "command": primary.get("command"),
                "run": primary.get("run"),
                "required": primary.get("required", bool(required_commands)),
            },
            "required_commands": required_commands,
            "warnings": warnings,
            "detail_command": "agentic-workspace proof --profile full --changed <paths> --format json",
        }
    return {
        "kind": "proof-next-decision/v1",
        "target": payload.get("target"),
        "selector": {},
        "next": {
            "action": "select-proof-scope",
            "command": "agentic-workspace proof --profile tiny --changed <paths> --format json",
            "run": None,
            "required": False,
        },
        "required_commands": [],
        "warnings": [],
        "detail_command": "agentic-workspace proof --profile full --format json",
    }


def _emit_proof(
    *,
    format_name: str,
    target_root: Path,
    descriptors: dict[str, ModuleDescriptor],
    route: str | None = None,
    current_only: bool = False,
    changed_paths: list[str] | None = None,
    profile: str = "full",
) -> None:
    normalized_paths = _normalize_changed_paths(changed_paths or [])
    if profile == "tiny" and normalized_paths:
        answer = _proof_selection_for_changed_paths(
            changed_paths=normalized_paths,
            target_root=target_root,
            include_durable_intent=False,
        )
        payload = _tiny_proof_payload(
            {
                "profile": "compact-contract-answer/v1",
                "target": target_root.as_posix(),
                "selector": {"changed": normalized_paths},
                "answer": answer,
            }
        )
        if format_name == "json":
            print(json.dumps(serialise_value(payload), indent=2))
            return
        _emit_compact_answer_text(payload)
        return
    payload = _proof_payload(target_root=target_root, descriptors=descriptors)
    payload = _select_proof_payload(
        payload,
        target_root=target_root,
        route=route,
        current_only=current_only,
        changed_paths=changed_paths,
    )
    if profile == "tiny":
        payload = _tiny_proof_payload(payload)
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


def _generated_adapter_for_command(command_name: str) -> dict[str, Any] | None:
    return GENERATED_COMMAND_ADAPTERS_BY_COMMAND.get(command_name)


def _run_generated_cli_package_if_supported(argv: list[str]) -> int | None:
    if not supports_generated_cli_package_command(argv):
        return None
    try:
        return run_generated_cli_package_command(argv, _run_generated_cli_operation)
    except WorkspaceUsageError as exc:
        build_generated_cli_package_parser().error(str(exc))


def _run_generated_cli_operation(operation_id: str, args: argparse.Namespace) -> int:
    handler = _GENERATED_RUNTIME_HANDLERS.get(operation_id)
    if handler is None:
        raise WorkspaceUsageError(f"Generated adapter for {args.command} references unsupported operation {operation_id}.")
    return handler(args)


def _run_defaults_report_adapter(args: argparse.Namespace) -> int:
    _emit_defaults(format_name=args.format, section=getattr(args, "section", None), profile=getattr(args, "profile", "tiny"))
    return 0


def _run_config_report_adapter(args: argparse.Namespace) -> int:
    descriptors = _module_operations()
    _validate_descriptor_contract(descriptors)
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name="config", target_root=target_root)
    _emit_config(
        format_name=args.format,
        profile=getattr(args, "profile", "tiny"),
        config=config_lib.load_workspace_config(target_root=target_root, valid_presets=set(_preset_modules(descriptors))),
    )
    return 0


def _run_modules_report_adapter(args: argparse.Namespace) -> int:
    target_root = _resolve_target_root(args.target) if args.target else None
    if target_root is not None:
        _validate_target_root(command_name="modules", target_root=target_root)
    _emit_modules(format_name=args.format, target_root=target_root, profile=getattr(args, "profile", "tiny"))
    return 0


def _run_start_context_adapter(args: argparse.Namespace) -> int:
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name="start", target_root=target_root)
    payload = _start_payload(
        target_root=target_root,
        changed_paths=list(getattr(args, "changed", []) or []),
        task_text=getattr(args, "task", None),
        profile=getattr(args, "profile", "tiny"),
    )
    _emit_payload(payload=payload, format_name=args.format)
    return 0


def _run_summary_report_adapter(args: argparse.Namespace) -> int:
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name="summary", target_root=target_root)
    from repo_planning_bootstrap.cli import _print_summary
    from repo_planning_bootstrap.installer import format_summary_json, planning_summary

    summary_profile = args.profile if args.format == "json" else "full"
    summary = planning_summary(
        target=target_root.as_posix(),
        profile=summary_profile,
        task_text=getattr(args, "task", None),
        changed_paths=list(getattr(args, "changed", []) or []),
    )
    if isinstance(summary, dict):
        config = _load_workspace_config(target_root=target_root)
        summary["memory_consult"] = _memory_consult_payload(
            target_root=target_root,
            compact=summary_profile in {"tiny", "compact"},
            cli_invoke=config.cli_invoke,
        )
    if args.format == "json":
        print(format_summary_json(summary))
    else:
        _print_summary(summary)
    return 0


def _run_implement_context_adapter(args: argparse.Namespace) -> int:
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name="implement", target_root=target_root)
    task_text = getattr(args, "task", None)
    if task_text and getattr(args, "task_file", None):
        raise WorkspaceUsageError("Use either --task or --task-file, not both.")
    if not task_text:
        task_text = _read_task_text_from_file(target_root=target_root, task_file=getattr(args, "task_file", None))
    payload = _implement_payload(
        target_root=target_root,
        changed_paths=list(getattr(args, "changed", []) or []),
        task_text=task_text,
    )
    if getattr(args, "profile", "tiny") == "tiny":
        payload = _tiny_implement_payload(payload)
    _emit_payload(payload=payload, format_name=args.format)
    return 0


def _run_preflight_report_adapter(args: argparse.Namespace) -> int:
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name="preflight", target_root=target_root)
    payload = _run_preflight_command(
        target_root=target_root,
        active_only=bool(getattr(args, "active_only", False)),
        task_text=getattr(args, "task", None),
        profile=getattr(args, "profile", "tiny"),
    )
    _emit_payload(payload=payload, format_name=args.format)
    return 0


def _run_proof_report_adapter(args: argparse.Namespace) -> int:
    descriptors = _module_operations()
    _validate_descriptor_contract(descriptors)
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name="proof", target_root=target_root)
    _emit_proof(
        format_name=args.format,
        target_root=target_root,
        descriptors=descriptors,
        route=getattr(args, "route", None),
        current_only=bool(getattr(args, "current", False)),
        changed_paths=list(getattr(args, "changed", []) or []),
        profile=getattr(args, "profile", "full"),
    )
    return 0


def _run_ownership_report_adapter(args: argparse.Namespace) -> int:
    descriptors = _module_operations()
    _validate_descriptor_contract(descriptors)
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name="ownership", target_root=target_root)
    _emit_ownership(
        format_name=args.format,
        target_root=target_root,
        descriptors=descriptors,
        concern=getattr(args, "concern", None),
        repo_path=getattr(args, "path", None),
    )
    return 0


def _run_skills_report_adapter(args: argparse.Namespace) -> int:
    target_root = _resolve_target_root(args.target) if args.target else None
    if target_root is not None:
        _validate_target_root(command_name="skills", target_root=target_root)
    _emit_skills(format_name=args.format, target_root=target_root, task_text=getattr(args, "task", None))
    return 0


def _selected_runtime_context(
    *,
    args: argparse.Namespace,
    command_name: str,
) -> tuple[Path, dict[str, ModuleDescriptor], WorkspaceConfig, list[str], str | None]:
    descriptors = _module_operations()
    _validate_descriptor_contract(descriptors)
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name=command_name, target_root=target_root)
    config = config_lib.load_workspace_config(target_root=target_root, valid_presets=set(_preset_modules(descriptors)))
    selected_modules, resolved_preset = _selected_modules(
        command_name=command_name,
        preset_name=getattr(args, "preset", None),
        module_arg=getattr(args, "modules", None),
        target_root=target_root,
        descriptors=descriptors,
        config=config,
    )
    _validate_selected_module_contract(selected_modules=selected_modules, descriptors=descriptors)
    return target_root, descriptors, config, selected_modules, resolved_preset


def _run_report_combined_adapter(args: argparse.Namespace) -> int:
    target_root, descriptors, config, selected_modules, resolved_preset = _selected_runtime_context(args=args, command_name="report")
    if getattr(args, "startup", False):
        _emit_startup_report(format_name=args.format, target_root=target_root, descriptors=descriptors, config=config)
        return 0
    profile = str(getattr(args, "profile", "router"))
    if profile == "tiny":
        profile = "router"
    section = getattr(args, "section", None)
    if section in {"external_work_reconciliation", "external_work_delta"}:
        _ensure_external_intent_cache_if_available(target_root=target_root)
    if profile == "router" and section is None and args.format == "json":
        payload = _run_report_router_command(
            target_root=target_root,
            selected_modules=selected_modules,
            resolved_preset=resolved_preset,
            descriptors=descriptors,
            config=config,
        )
        _emit_payload(payload=payload, format_name=args.format)
        return 0
    payload = _run_report_command(
        target_root=target_root,
        selected_modules=selected_modules,
        resolved_preset=resolved_preset,
        descriptors=descriptors,
        config=config,
    )
    payload = _select_report_payload(
        payload,
        profile=profile,
        section=section,
    )
    _emit_payload(payload=payload, format_name=args.format)
    return 0


def _run_reconcile_report_adapter(args: argparse.Namespace) -> int:
    target_root = _resolve_target_root(args.target) if args.target else _resolve_target_root(None)
    _validate_target_root(command_name="reconcile", target_root=target_root)
    from repo_planning_bootstrap.cli import _print_reconcile
    from repo_planning_bootstrap.installer import planning_reconcile

    _ensure_external_intent_cache_if_available(target_root=target_root)
    payload = planning_reconcile(target=target_root)
    if args.format == "json":
        _emit_payload(payload=payload, format_name=args.format)
    else:
        _print_reconcile(payload)
    return 0


def _run_setup_guidance_adapter(args: argparse.Namespace) -> int:
    target_root, descriptors, config, selected_modules, resolved_preset = _selected_runtime_context(args=args, command_name="setup")
    _emit_setup(
        format_name=args.format,
        target_root=target_root,
        selected_modules=selected_modules,
        resolved_preset=resolved_preset,
        descriptors=descriptors,
        config=config,
    )
    return 0


def _run_lifecycle_report_adapter(args: argparse.Namespace) -> int:
    command_name = str(args.command)
    target_root, descriptors, config, selected_modules, resolved_preset = _selected_runtime_context(args=args, command_name=command_name)
    payload = _run_lifecycle_command(
        command_name=command_name,
        target_root=target_root,
        local_only_repo_root=None,
        selected_modules=selected_modules,
        resolved_preset=resolved_preset,
        descriptors=descriptors,
        dry_run=False,
        non_interactive=bool(getattr(args, "non_interactive", False)),
        config=config,
        compact_status=getattr(args, "profile", "tiny") == "tiny",
    )
    _emit_payload(payload=payload, format_name=args.format)
    return 0


_GENERATED_RUNTIME_HANDLERS: dict[str, Callable[[argparse.Namespace], int]] = {
    "config.report": _run_config_report_adapter,
    "defaults.report": _run_defaults_report_adapter,
    "doctor.report": _run_lifecycle_report_adapter,
    "implement.context": _run_implement_context_adapter,
    "modules.report": _run_modules_report_adapter,
    "ownership.report": _run_ownership_report_adapter,
    "preflight.report": _run_preflight_report_adapter,
    "proof.report": _run_proof_report_adapter,
    "reconcile.report": _run_reconcile_report_adapter,
    "report.combined": _run_report_combined_adapter,
    "setup.guidance": _run_setup_guidance_adapter,
    "skills.report": _run_skills_report_adapter,
    "start.context": _run_start_context_adapter,
    "status.report": _run_lifecycle_report_adapter,
    "summary.report": _run_summary_report_adapter,
}


def _run_generated_command_adapter(args: argparse.Namespace, *, adapter: dict[str, Any]) -> int:
    operation_id = str(adapter["operation_id"])
    handler = _GENERATED_RUNTIME_HANDLERS.get(operation_id)
    if handler is None:
        raise WorkspaceUsageError(f"Generated adapter for {args.command} references unsupported operation {operation_id}.")
    return handler(args)


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


def _validation_plan_step(
    *,
    command: str,
    index: int,
    required: bool,
    lane_id: str | None = None,
    cli_invoke: str = DEFAULT_CLI_INVOKE,
) -> dict[str, Any]:
    cwd = "."
    runnable_command = command
    prefix = "cd "
    separator = " && "
    if command.startswith(prefix) and separator in command:
        cwd_part, command_part = command.split(separator, 1)
        cwd = cwd_part.removeprefix(prefix).strip() or "."
        runnable_command = command_part.strip()
    runnable_command = str(_command_with_cli_invoke(command=runnable_command, cli_invoke=cli_invoke))
    step = {
        "order": index,
        "action": "run-validation-command",
        "command": command,
        "cwd": cwd,
        "run": runnable_command,
        "required": required,
        "risk": "read-only validation",
        "required_inputs": ["changed_paths", "selected_lanes"],
        "next_proof": "continue to the next required step, then rerun proof selection if changed paths expand",
    }
    if lane_id:
        step["lane_id"] = lane_id
    return step


def _proof_target_argument(target_root: Path | None) -> str:
    if target_root is None:
        return "./repo"
    try:
        if target_root.resolve() == Path.cwd().resolve():
            return "."
    except OSError:
        pass
    return _shell_quote(target_root.as_posix())


def _proof_command_for_target(*, command: str, target_root: Path | None) -> str:
    return command.replace("--target ./repo", f"--target {_proof_target_argument(target_root)}")


def _validation_plan_for_proof(
    *,
    selected_lanes: list[dict[str, Any]],
    optional_commands: list[str],
    target_root: Path | None = None,
    cli_invoke: str = DEFAULT_CLI_INVOKE,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    seen_required: set[str] = set()
    for lane in selected_lanes:
        for command in lane.get("enough_proof", []):
            command_text = _proof_command_for_target(command=str(command), target_root=target_root)
            if command_text in seen_required:
                continue
            seen_required.add(command_text)
            steps.append(
                _validation_plan_step(
                    command=command_text,
                    index=len(steps) + 1,
                    required=True,
                    lane_id=str(lane["id"]),
                    cli_invoke=cli_invoke,
                )
            )
    optional_steps = [
        _validation_plan_step(
            command=_proof_command_for_target(command=str(command), target_root=target_root),
            index=index,
            required=False,
            cli_invoke=cli_invoke,
        )
        for index, command in enumerate(optional_commands, start=1)
    ]
    primary_action = steps[0] if steps else (optional_steps[0] if optional_steps else None)
    return {
        "kind": "validation-plan/v1",
        "status": "inspect-before-run",
        "rule": "Commands are selected proof, not hidden automation; inspect the plan before executing it.",
        "primary_next_action": primary_action,
        "required_count": len(steps),
        "optional_count": len(optional_steps),
        "required": steps,
        "optional": optional_steps,
        "next_proof": "proof is complete when all required steps pass for the current changed paths",
    }


def _proof_kind_for_lane(lane: dict[str, Any]) -> str:
    explicit = str(lane.get("proof_kind", "")).strip()
    if explicit:
        return explicit
    lane_id = str(lane.get("id", "")).strip()
    configured = _PROOF_SELECTION_RULES.get("lane_proof_kinds", {})
    if isinstance(configured, dict):
        value = str(configured.get(lane_id, "")).strip()
        if value:
            return value
    if str(lane_id).startswith("concern:"):
        return "targeted-test"
    if str(lane_id).startswith("subsystem:"):
        return "targeted-test"
    return "targeted-test"


def _docs_only_reduction_lane(*, changed_path: str, matched_lane: str) -> str | None:
    reducer = _PROOF_SELECTION_RULES.get("docs_only_reducer", {})
    if not isinstance(reducer, dict):
        return None
    source_lanes = {str(item) for item in reducer.get("source_lanes", [])}
    if matched_lane not in source_lanes:
        return None
    extensions = tuple(str(item) for item in reducer.get("extensions", []) if str(item).strip())
    if extensions and not changed_path.endswith(extensions):
        return None
    exact = {str(item) for item in reducer.get("exact", [])}
    prefixes = tuple(str(item) for item in reducer.get("prefixes", []) if str(item).strip())
    if changed_path in exact or (prefixes and changed_path.startswith(prefixes)):
        reduced_lane = str(reducer.get("lane", "")).strip()
        return reduced_lane or None
    return None


def _active_planning_assurance_for_proof(*, target_root: Path | None) -> dict[str, Any]:
    if target_root is None:
        return {"status": "unavailable", "reason": "requires a target root"}
    if not _planning_state_has_active_items(target_root=target_root):
        return {"status": "unavailable", "reason": "no active planning record"}
    try:
        from repo_planning_bootstrap.installer import planning_summary

        summary = planning_summary(target=target_root, profile="compact")
    except Exception as exc:  # pragma: no cover - defensive; proof must remain usable without planning.
        return {"status": "unavailable", "reason": f"planning summary unavailable: {exc}"}
    planning_record = summary.get("planning_record", {}) if isinstance(summary, dict) else {}
    if not isinstance(planning_record, dict) or planning_record.get("status") != "present":
        return {"status": "unavailable", "reason": "no active planning record"}
    adaptive_assurance = planning_record.get("adaptive_assurance", {})
    test_data_policy = planning_record.get("test_data_policy", {})
    layer_scaffold = planning_record.get("layer_scaffold", {})
    proof_profiles = []
    if isinstance(adaptive_assurance, dict):
        proof_profiles.extend(str(item).strip() for item in adaptive_assurance.get("proof_profiles", []) if str(item).strip())
    if isinstance(test_data_policy, dict):
        proof_profiles.extend(str(item).strip() for item in test_data_policy.get("proof_required", []) if str(item).strip())
    if isinstance(layer_scaffold, dict):
        proof_profiles.extend(str(item).strip() for item in layer_scaffold.get("suggested_proof_profiles", []) if str(item).strip())
    required_refs = []
    if isinstance(adaptive_assurance, dict):
        required_refs = [str(item).strip() for item in adaptive_assurance.get("required_refs", []) if str(item).strip()]
    traceability_refs = planning_record.get("traceability_refs", {})
    missing_required_refs: list[str] = []
    if isinstance(traceability_refs, dict):
        for ref_field in required_refs:
            ref_values = traceability_refs.get(ref_field, [])
            if not isinstance(ref_values, list) or not [item for item in ref_values if str(item).strip()]:
                missing_required_refs.append(ref_field)
    control_gates = planning_record.get("control_gates", [])
    pending_blocking_gates = [
        gate
        for gate in control_gates
        if isinstance(gate, dict)
        and bool(gate.get("blocking", False))
        and str(gate.get("status", "")).strip() not in {"satisfied", "waived"}
    ]
    implementation_blockers = planning_record.get("implementation_blockers", [])
    do_not_implement_blockers = [
        blocker for blocker in implementation_blockers if isinstance(blocker, dict) and bool(blocker.get("do_not_implement", False))
    ]
    strict_closeout = bool(adaptive_assurance.get("strict_closeout", False)) if isinstance(adaptive_assurance, dict) else False
    closeout_status = (
        "blocked" if strict_closeout and (missing_required_refs or pending_blocking_gates or do_not_implement_blockers) else "open"
    )
    proof_execution_evidence = planning_record.get("proof_execution_evidence", planning_record.get("proof_execution", []))
    if not proof_execution_evidence:
        proof_report = planning_record.get("proof_report", {})
        if isinstance(proof_report, dict):
            raw_proof_execution = proof_report.get("proof execution evidence", proof_report.get("proof_execution_evidence", ""))
            if isinstance(raw_proof_execution, str) and raw_proof_execution.strip():
                try:
                    proof_execution_evidence = json.loads(raw_proof_execution)
                except json.JSONDecodeError:
                    proof_execution_evidence = []
    if not proof_execution_evidence:
        task = planning_record.get("task", {})
        surface = str(task.get("surface", "")).strip() if isinstance(task, dict) else ""
        record_path = target_root / surface if surface else None
        if record_path is not None and record_path.exists() and record_path.suffix == ".json":
            try:
                raw_record = json.loads(record_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                raw_record = {}
            raw_proof_report = raw_record.get("proof_report", {}) if isinstance(raw_record, dict) else {}
            if isinstance(raw_proof_report, dict):
                raw_proof_execution = raw_proof_report.get("proof execution evidence", raw_proof_report.get("proof_execution_evidence", ""))
                if isinstance(raw_proof_execution, str) and raw_proof_execution.strip():
                    try:
                        proof_execution_evidence = json.loads(raw_proof_execution)
                    except json.JSONDecodeError:
                        proof_execution_evidence = []
    return {
        "status": "present",
        "task": planning_record.get("task", {}),
        "adaptive_assurance": adaptive_assurance if isinstance(adaptive_assurance, dict) else {},
        "traceability_refs": traceability_refs if isinstance(traceability_refs, dict) else {},
        "control_gates": control_gates,
        "pending_blocking_gates": pending_blocking_gates,
        "implementation_blockers": implementation_blockers,
        "do_not_implement_blockers": do_not_implement_blockers,
        "risk_registry_refs": planning_record.get("risk_registry_refs", []),
        "invariant_refs": planning_record.get("invariant_refs", []),
        "test_data_policy": test_data_policy if isinstance(test_data_policy, dict) else {},
        "layer_scaffold": layer_scaffold if isinstance(layer_scaffold, dict) else {},
        "architecture_decision_promotion": planning_record.get("architecture_decision_promotion", {}),
        "threat_failure_aids": planning_record.get("threat_failure_aids", []),
        "proof_profiles": _dedupe(proof_profiles),
        "proof_execution_evidence": proof_execution_evidence if isinstance(proof_execution_evidence, list | dict) else [],
        "required_refs": required_refs,
        "missing_required_refs": missing_required_refs,
        "closeout_status": closeout_status,
        "closeout_rule": "Strict closeout is blocked by missing required refs, pending blocking gates, or do-not-implement blockers.",
    }


def _assurance_item_state(
    *,
    item_id: str,
    declared_status: str,
    blocking: bool = False,
    evidence: list[Any] | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    normalized_status = declared_status.strip() or "missing"
    evidence_items = [str(item) for item in evidence or [] if str(item).strip()]
    waived = normalized_status == "waived"
    satisfied = normalized_status in {"satisfied", "passed", "present"} or (waived and bool(evidence_items or reason))
    if blocking and not satisfied:
        enforcement = "blocking"
    elif blocking:
        enforcement = "required"
    else:
        enforcement = "advisory"
    return {
        "id": item_id,
        "declared_status": normalized_status,
        "enforcement": enforcement,
        "evidence_state": "present" if evidence_items else "missing",
        "waiver_state": "waived-with-evidence"
        if waived and (evidence_items or reason)
        else ("waived-missing-reason" if waived else "not-waived"),
        "trust": "satisfied" if satisfied else ("blocking" if blocking else "advisory"),
        **({"reason": reason} if reason else {}),
    }


def _proof_execution_evidence_summary(*, declared: Any, required_commands: list[str]) -> dict[str, Any]:
    raw_entries: list[Any]
    if isinstance(declared, dict):
        raw_entries = list(declared.get("commands", [])) if isinstance(declared.get("commands", []), list) else []
    elif isinstance(declared, list):
        raw_entries = declared
    else:
        raw_entries = []
    by_command: dict[str, dict[str, Any]] = {}
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        command = str(entry.get("command", "")).strip()
        if command:
            by_command[command] = entry
    statuses = ["passed", "failed", "skipped", "unavailable", "waived", "missing"]
    counts = {status: 0 for status in statuses}
    command_states: list[dict[str, Any]] = []
    for command in required_commands:
        entry = by_command.get(command, {})
        status = str(entry.get("status", "missing")).strip() if entry else "missing"
        if status not in statuses:
            status = "unavailable"
        reason = str(entry.get("reason", "")).strip()
        evidence_ref = str(entry.get("evidence_ref", entry.get("evidence", ""))).strip()
        waiver_has_reason = status != "waived" or bool(reason or evidence_ref)
        lowers_trust = status in {"failed", "skipped", "unavailable", "missing"} or not waiver_has_reason
        counts[status] += 1
        command_states.append(
            {
                "command": command,
                "status": status,
                "required": True,
                "trust": "lower-trust" if lowers_trust else "satisfied",
                "evidence_state": "present" if evidence_ref else "missing",
                "waiver_state": "waived-with-reason"
                if status == "waived" and waiver_has_reason
                else ("waived-missing-reason" if status == "waived" else "not-waived"),
                **({"reason": reason} if reason else {}),
                **({"evidence_ref": evidence_ref} if evidence_ref else {}),
            }
        )
    lower_trust_count = sum(1 for item in command_states if item["trust"] == "lower-trust")
    return {
        "status": "complete" if command_states and lower_trust_count == 0 else ("absent" if not command_states else "attention"),
        "rule": "Selected proof is not executed proof; required commands need compact evidence or an explicit waiver reason.",
        "required_command_count": len(command_states),
        "lower_trust_required_count": lower_trust_count,
        "counts": counts,
        "commands": command_states,
    }


def _proof_selection_for_changed_paths(
    *,
    changed_paths: list[str],
    target_root: Path | None = None,
    include_durable_intent: bool = True,
) -> dict[str, Any]:
    defaults = _defaults_payload()
    cli_invoke = DEFAULT_CLI_INVOKE
    config: WorkspaceConfig | None = None
    if target_root is not None:
        config = _load_workspace_config(target_root=target_root)
        cli_invoke = config.cli_invoke
    validation_lanes = defaults["validation"]["lanes"]
    cli_authority_lane = _PROOF_SELECTION_RULES.get("cli_authority", {}).get("lane")

    def _lane(lane_id: str) -> dict[str, Any]:
        return next(lane for lane in validation_lanes if lane["id"] == lane_id)

    selected_ids: list[str] = []
    routing_reductions: list[dict[str, str]] = []

    def _select(lane_id: str) -> None:
        if lane_id not in selected_ids:
            selected_ids.append(lane_id)

    for changed_path in changed_paths:
        matched_rule = False
        for rule in _PROOF_SELECTION_RULES["rules"]:
            exact_matches = set(rule.get("exact", []))
            prefixes = tuple(rule.get("prefixes", []))
            if changed_path in exact_matches or changed_path.startswith(prefixes):
                matched_lane = str(rule["lane"])
                selected_lane = _docs_only_reduction_lane(changed_path=changed_path, matched_lane=matched_lane) or matched_lane
                if selected_lane != matched_lane:
                    routing_reductions.append(
                        {
                            "path": changed_path,
                            "from_lane": matched_lane,
                            "to_lane": selected_lane,
                            "reason": str(_PROOF_SELECTION_RULES.get("docs_only_reducer", {}).get("rule", "")),
                        }
                    )
                _select(selected_lane)
                matched_rule = True
                break
        if not matched_rule:
            _select(str(_PROOF_SELECTION_RULES["fallback_lane"]))
        if cli_authority_lane and _cli_authority_classification_for_path(changed_path):
            _select(str(cli_authority_lane))

    selected_lanes = [_lane(lane_id) for lane_id in selected_ids]
    subsystem_matches = _subsystem_matches_for_changed_paths(target_root=target_root, changed_paths=changed_paths)
    subsystem_lanes: list[dict[str, Any]] = []
    for subsystem in subsystem_matches["matched_subsystems"]:
        proof_commands = [str(command) for command in subsystem.get("proof", []) if str(command).strip()]
        if not proof_commands:
            continue
        subsystem_lanes.append(
            {
                "id": f"subsystem:{subsystem['id']}",
                "when": "changed path matches host-repo subsystem ownership",
                "enough_proof": proof_commands,
                "recovery_signal": "missing or failing subsystem proof should block closeout for changes in this subsystem",
                "subsystem": {
                    "id": subsystem["id"],
                    "matched_paths": subsystem.get("matched_paths", []),
                    "owns": subsystem.get("owns", []),
                    "does_not_own": subsystem.get("does_not_own", []),
                    "escalate_when": subsystem.get("escalate_when", []),
                },
            }
        )
    selected_lanes.extend(subsystem_lanes)
    planning_assurance = _active_planning_assurance_for_proof(target_root=target_root)
    configured_profiles = {profile.id: profile for profile in (config.assurance.proof_profiles if config is not None else ())}
    concern_lanes: list[dict[str, Any]] = []
    missing_concern_profiles: list[str] = []
    if planning_assurance.get("status") == "present":
        for profile_id in planning_assurance.get("proof_profiles", []):
            profile = configured_profiles.get(str(profile_id))
            if profile is None:
                missing_concern_profiles.append(str(profile_id))
                continue
            concern_lanes.append(
                {
                    "id": f"concern:{profile.id}",
                    "when": "active planning assurance declares this proof concern",
                    "enough_proof": list(profile.required_commands),
                    "recovery_signal": "missing or failing concern proof should block high-assurance closeout until resolved or explicitly waived",
                    "proof_profile": profile.id,
                    "optional_commands": list(profile.optional_commands),
                    "review_aids": list(profile.review_aids),
                }
            )
    selected_lanes.extend(concern_lanes)
    for lane in selected_lanes:
        lane["proof_kind"] = _proof_kind_for_lane(lane)
        lane["enough_proof"] = [
            str(
                _command_with_cli_invoke(
                    command=_proof_command_for_target(command=str(command), target_root=target_root),
                    cli_invoke=cli_invoke,
                )
            )
            for command in lane.get("enough_proof", [])
        ]
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

    executable_lanes = [
        lane for lane in selected_lanes if lane["id"] != cli_authority_lane and lane.get("proof_kind") in {"targeted-test", "full-test"}
    ]
    if len(executable_lanes) > 1:
        escalate_when.insert(0, str(_PROOF_SELECTION_RULES["cross_lane_escalation"]))

    optional_commands = [
        "agentic-workspace proof --target ./repo --current --format json",
        "agentic-workspace summary --format json",
    ]
    for concern_lane in concern_lanes:
        for command in concern_lane.get("optional_commands", []):
            if command not in optional_commands:
                optional_commands.append(str(command))
    optional_commands = [
        str(
            _command_with_cli_invoke(
                command=_proof_command_for_target(command=str(command), target_root=target_root),
                cli_invoke=cli_invoke,
            )
        )
        for command in optional_commands
    ]
    proof_selection = {
        "kind": "proof-selection/v1",
        "changed_paths": changed_paths,
        "selected_lanes": [
            {
                "id": lane["id"],
                "when": lane["when"],
                "required_commands": lane["enough_proof"],
                "proof_kind": lane.get("proof_kind", "targeted-test"),
                "proof_responsibility": lane.get("proof_responsibility", "local-closeout"),
                "execution_mode": lane.get("execution_mode", "parallel-ok"),
                "ci_relationship": lane.get("ci_relationship", ""),
                "recovery_signal": lane.get("recovery_signal", ""),
                **({"proof_profile": lane["proof_profile"]} if lane.get("proof_profile") else {}),
                **({"review_aids": lane["review_aids"]} if lane.get("review_aids") else {}),
                **({"subsystem": lane["subsystem"]} if lane.get("subsystem") else {}),
                **({"weak_agent_safe_routing": lane["weak_agent_safe_routing"]} if lane.get("weak_agent_safe_routing") else {}),
            }
            for lane in selected_lanes
        ],
        "required_commands": required_commands,
        "optional_commands": optional_commands,
        "validation_plan": _validation_plan_for_proof(
            selected_lanes=selected_lanes,
            optional_commands=optional_commands,
            target_root=target_root,
            cli_invoke=cli_invoke,
        ),
        "broaden_when": broaden_when,
        "escalate_when": escalate_when,
    }
    if routing_reductions:
        proof_selection["routing_reductions"] = routing_reductions
    if config is not None and target_root is not None and include_durable_intent:
        durable_intent = _intent_decision_projection(
            target_root=target_root,
            config=config,
            changed_paths=changed_paths,
            compact=True,
        )
        proof_selection["durable_intent"] = durable_intent
        if durable_intent.get("status") == "present":
            intent_effect = (
                "Relevant durable intent may add proof, review, or escalation expectations; inspect durable_intent before closeout."
            )
            if intent_effect not in proof_selection["escalate_when"]:
                proof_selection["escalate_when"].append(intent_effect)
    if subsystem_matches["matched_subsystems"]:
        proof_selection["subsystem_ownership"] = subsystem_matches
    if planning_assurance.get("status") == "present":
        gate_states = [
            _assurance_item_state(
                item_id=str(gate.get("id", "")),
                declared_status=str(gate.get("status", "missing")),
                blocking=bool(gate.get("blocking", False)),
                evidence=gate.get("evidence", []) if isinstance(gate.get("evidence", []), list) else [],
                reason=str(gate.get("reason", "")).strip() or None,
            )
            for gate in planning_assurance.get("control_gates", [])
            if isinstance(gate, dict)
        ]
        ref_states = [
            _assurance_item_state(
                item_id=ref,
                declared_status="present" if ref not in planning_assurance.get("missing_required_refs", []) else "missing",
                blocking=True,
                evidence=(
                    planning_assurance.get("traceability_refs", {}).get(ref, [])
                    if isinstance(planning_assurance.get("traceability_refs", {}), dict)
                    else []
                ),
            )
            for ref in planning_assurance.get("required_refs", [])
        ]
        profile_states = [
            {
                "id": str(profile_id),
                "state": "selected" if str(profile_id) not in missing_concern_profiles else "unavailable",
                "enforcement": "required",
                "trust": "satisfied" if str(profile_id) not in missing_concern_profiles else "blocking",
            }
            for profile_id in planning_assurance.get("proof_profiles", [])
        ]
        proof_evidence = _proof_execution_evidence_summary(
            declared=planning_assurance.get("proof_execution_evidence", []),
            required_commands=required_commands,
        )
        proof_selection["planning_assurance"] = {
            **planning_assurance,
            "missing_configured_proof_profiles": missing_concern_profiles,
            "trust_state": {
                "assurance_level": planning_assurance.get("adaptive_assurance", {}).get(
                    "level", config.assurance.default_level if config is not None else DEFAULT_ASSURANCE_LEVEL
                )
                if isinstance(planning_assurance.get("adaptive_assurance", {}), dict)
                else (config.assurance.default_level if config is not None else DEFAULT_ASSURANCE_LEVEL),
                "assurance_level_source": "explicit-slice-field"
                if isinstance(planning_assurance.get("adaptive_assurance", {}), dict)
                and "level" in planning_assurance.get("adaptive_assurance", {})
                else (config.assurance.default_level_source if config is not None else "product-default"),
                "gate_states": gate_states,
                "ref_states": ref_states,
                "proof_profile_states": profile_states,
                "proof_execution_evidence": proof_evidence,
                "overall": "blocking"
                if planning_assurance.get("closeout_status") == "blocked"
                or missing_concern_profiles
                or proof_evidence["lower_trust_required_count"]
                else "open",
            },
            "rule": (
                "Path lanes stay package-defined; concern profiles are host-configured and activated from active planning assurance fields."
            ),
        }
    surface_value_review = _surface_value_review_for_changed_paths(changed_paths=changed_paths, target_root=target_root)
    if surface_value_review["durable_surface_count"]:
        proof_selection["surface_value_review"] = surface_value_review
    direct_cli_review = _direct_cli_edit_review_for_changed_paths(changed_paths)
    if direct_cli_review["changed_paths"]:
        proof_selection["direct_cli_edit_review"] = direct_cli_review
    cli_authority_review = _cli_authority_review_for_changed_paths(changed_paths)
    if cli_authority_review["changed_paths"]:
        proof_selection["cli_authority_review"] = cli_authority_review
    return proof_selection


def _cli_authority_classification_for_path(changed_path: str) -> dict[str, Any] | None:
    for classification in _PROOF_SELECTION_RULES.get("cli_authority", {}).get("classifications", []):
        exact_matches = set(classification.get("exact", []))
        prefixes = tuple(classification.get("prefixes", []))
        if changed_path in exact_matches or changed_path.startswith(prefixes):
            return classification
    return None


def _cli_authority_review_for_changed_paths(changed_paths: list[str]) -> dict[str, Any]:
    classified_paths: list[dict[str, Any]] = []
    unresolved_paths: list[str] = []
    for path in changed_paths:
        classification = _cli_authority_classification_for_path(path)
        if not classification:
            continue
        role = str(classification["role"])
        source_contract = str(classification["source_contract"])
        regeneration_path = classification.get("regeneration_path")
        direct_edit_allowed = bool(classification["direct_edit_allowed"])
        has_required_projection_authority = role not in {"generator", "projection"} or bool(source_contract and regeneration_path)
        if role in {"generator", "projection"} and not has_required_projection_authority:
            unresolved_paths.append(path)
        classified_paths.append(
            {
                "path": path,
                "classification_id": classification["id"],
                "role": role,
                "direct_edit_allowed": direct_edit_allowed,
                "source_contract": source_contract,
                "generator_contract": classification.get("generator_contract"),
                "regeneration_path": regeneration_path,
                "edit_policy": classification["edit_policy"],
                "authority_ready": has_required_projection_authority,
            }
        )
    generated_or_projection = [item for item in classified_paths if item["role"] in {"generator", "projection"}]
    blocked_direct_edits = [item["path"] for item in generated_or_projection if not item["direct_edit_allowed"]]
    if unresolved_paths:
        status = "blocked-missing-authority"
    elif blocked_direct_edits:
        status = "blocked-direct-edit-route-to-source"
    elif classified_paths:
        status = "review-ready"
    else:
        status = "not-applicable"
    return {
        "kind": "cli-authority-review/v1",
        "changed_paths": [item["path"] for item in classified_paths],
        "status": status,
        "classifications": classified_paths,
        "blocked_direct_edit_paths": blocked_direct_edits,
        "unresolved_authority_paths": unresolved_paths,
        "rule": (
            "Generated or projection CLI paths are not direct-edit targets unless their source contract and regeneration path are named; "
            "hand-owned executable CLI paths still need the root CLI authority audit before interface authority changes."
        ),
        "authority_query": "agentic-workspace defaults --section root_cli_authority --format json",
    }


def _direct_cli_edit_review_for_changed_paths(changed_paths: list[str]) -> dict[str, Any]:
    cli_paths = [
        path
        for path in changed_paths
        if path == "src/agentic_workspace/cli.py"
        or path.endswith("/src/repo_planning_bootstrap/cli.py")
        or path.endswith("/src/repo_memory_bootstrap/cli.py")
    ]
    return {
        "kind": "direct-cli-edit-review/v1",
        "changed_paths": cli_paths,
        "status": "review-needed" if cli_paths else "not-applicable",
        "rule": (
            "Treat direct CLI edits as runtime-primitive work or migration exceptions; normal interface authoring belongs in "
            "command contracts, command-package IR, and generated outputs."
        ),
        "definition_owned_work": [
            "command identity and option semantics",
            "generated adapter/package metadata",
            "effect hints, operation refs, primitive refs, schema refs, and conformance refs",
        ],
        "allowed_direct_cli_work": [
            "runtime primitive implementation and live workspace inspection",
            "dispatch glue while a command is not yet covered by generated adapters",
            "urgent migration exceptions with proof output naming why definitions were insufficient",
        ],
        "proof_hint": (
            "When direct CLI edits accompany interface changes, include command-package IR/generator proof or split the runtime fix "
            "from definition work."
        ),
        "recovery_signal": (
            "Use proof output to decide whether the edit is allowed runtime work; route interface or generated-surface changes "
            "back to command contracts, command-package IR, and generated outputs."
        ),
    }


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
        elif _changed_path_is_git_deletion(target_root=target_root, changed_path=changed_path):
            result = "accepted"
            disposition = "removed durable surface"
            reason = "removing or compressing a durable surface follows the surface-value preference order"
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


def _changed_path_is_git_deletion(*, target_root: Path | None, changed_path: str) -> bool:
    if target_root is None:
        return False
    path = Path(changed_path)
    relative = path.as_posix() if not path.is_absolute() else ""
    if not relative:
        try:
            relative = path.relative_to(target_root).as_posix()
        except ValueError:
            return False
    for args in (("diff", "--name-status", "--cached", "--", relative), ("diff", "--name-status", "--", relative)):
        try:
            completed = subprocess.run(
                ["git", "-C", str(target_root), *args],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        except OSError:
            continue
        if completed.returncode == 0 and any(line.startswith("D\t") for line in completed.stdout.splitlines()):
            return True
    return False


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


def _normalized_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalise_subsystems(raw_subsystems: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_subsystems, list):
        return []
    subsystems: list[dict[str, Any]] = []
    for raw in raw_subsystems:
        if not isinstance(raw, dict):
            continue
        subsystem_id = str(raw.get("id", "")).strip()
        paths = [_normalize_repo_path(path) for path in _normalized_list(raw.get("paths"))]
        if not subsystem_id or not paths:
            continue
        subsystems.append(
            {
                "id": subsystem_id,
                "paths": paths,
                "owns": _normalized_list(raw.get("owns")),
                "does_not_own": _normalized_list(raw.get("does_not_own")),
                "proof": _normalized_list(raw.get("proof")),
                "escalate_when": _normalized_list(raw.get("escalate_when")),
                **({"summary": str(raw["summary"]).strip()} if str(raw.get("summary", "")).strip() else {}),
            }
        )
    return subsystems


def _load_ownership_subsystems(*, target_root: Path | None) -> list[dict[str, Any]]:
    if target_root is None:
        return []
    ledger_path = target_root / _defaults_payload()["ownership_mapping"]["ledger"]
    if not ledger_path.exists():
        return []
    try:
        payload = config_lib.load_toml_payload(path=ledger_path, surface_name=ledger_path.as_posix())
    except WorkspaceUsageError:
        return []
    return _normalise_subsystems(payload.get("subsystems"))


def _path_matches_subsystem_pattern(*, path: str, pattern: str) -> bool:
    normalized_path = _normalize_repo_path(path)
    normalized_pattern = _normalize_repo_path(pattern)
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3].rstrip("/")
        return normalized_path == prefix or normalized_path.startswith(f"{prefix}/")
    if normalized_pattern.endswith("/"):
        prefix = normalized_pattern.rstrip("/")
        return normalized_path == prefix or normalized_path.startswith(f"{prefix}/")
    return normalized_path == normalized_pattern or fnmatch.fnmatch(normalized_path, normalized_pattern)


def _subsystem_match_specificity(pattern: str) -> int:
    normalized = _normalize_repo_path(pattern)
    return len(normalized.replace("*", ""))


def _matching_subsystems_for_path(*, subsystems: list[dict[str, Any]], repo_path: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for subsystem in subsystems:
        matched_patterns = [
            pattern for pattern in subsystem.get("paths", []) if _path_matches_subsystem_pattern(path=repo_path, pattern=str(pattern))
        ]
        if not matched_patterns:
            continue
        best_pattern = max(matched_patterns, key=_subsystem_match_specificity)
        matches.append(
            {
                **subsystem,
                "matched_patterns": matched_patterns,
                "match_specificity": _subsystem_match_specificity(best_pattern),
            }
        )
    matches.sort(key=lambda entry: (-int(entry.get("match_specificity", 0)), str(entry.get("id", ""))))
    return matches


def _subsystem_matches_for_changed_paths(*, target_root: Path | None, changed_paths: list[str]) -> dict[str, Any]:
    subsystems = _load_ownership_subsystems(target_root=target_root)
    by_id: dict[str, dict[str, Any]] = {}
    for changed_path in changed_paths:
        for subsystem in _matching_subsystems_for_path(subsystems=subsystems, repo_path=changed_path):
            entry = by_id.setdefault(
                str(subsystem["id"]),
                {
                    "id": subsystem["id"],
                    "paths": subsystem.get("paths", []),
                    "owns": subsystem.get("owns", []),
                    "does_not_own": subsystem.get("does_not_own", []),
                    "proof": subsystem.get("proof", []),
                    "escalate_when": subsystem.get("escalate_when", []),
                    "matched_paths": [],
                    "matched_patterns": [],
                    "overlap_rank": len(by_id) + 1,
                },
            )
            if changed_path not in entry["matched_paths"]:
                entry["matched_paths"].append(changed_path)
            for pattern in subsystem.get("matched_patterns", []):
                if pattern not in entry["matched_patterns"]:
                    entry["matched_patterns"].append(pattern)
    return {
        "kind": "agentic-workspace/subsystem-ownership-selection/v1",
        "status": "matched" if by_id else ("no-subsystems-declared" if not subsystems else "no-match"),
        "subsystem_count": len(subsystems),
        "matched_count": len(by_id),
        "matched_subsystems": list(by_id.values()),
        "rule": "Optional host-repo subsystem ownership comes from .agentic-workspace/OWNERSHIP.toml [[subsystems]] entries and supplies path-scope, proof, and escalation hints.",
    }


def _ownership_answer_for_path(payload: dict[str, Any], *, repo_path: str) -> tuple[dict[str, Any], bool]:
    normalized = _normalize_repo_path(repo_path)
    subsystem_matches = _matching_subsystems_for_path(subsystems=payload.get("subsystems", []), repo_path=normalized)
    subsystem_projection = [
        {
            "id": subsystem.get("id"),
            "paths": subsystem.get("paths", []),
            "matched_patterns": subsystem.get("matched_patterns", []),
            "owns": subsystem.get("owns", []),
            "does_not_own": subsystem.get("does_not_own", []),
            "proof": subsystem.get("proof", []),
            "escalate_when": subsystem.get("escalate_when", []),
            "overlap_rank": index,
        }
        for index, subsystem in enumerate(subsystem_matches, start=1)
    ]

    def with_subsystems(answer: dict[str, Any]) -> dict[str, Any]:
        if subsystem_projection:
            answer["subsystems"] = subsystem_projection
            answer["primary_subsystem"] = subsystem_projection[0]
            answer["subsystem_overlap_count"] = len(subsystem_projection)
        return answer

    for entry in payload["authority_surfaces"]:
        surface = str(entry.get("surface", "")).rstrip("/")
        if surface == normalized:
            return (
                with_subsystems(
                    {
                        "path": normalized,
                        "owner": entry.get("owner"),
                        "ownership": entry.get("ownership"),
                        "authority": entry.get("authority"),
                        "surface": entry.get("surface"),
                        "summary": entry.get("summary"),
                        "matched_by": "authority_surface",
                    }
                ),
                True,
            )
    for entry in payload["module_roots"]:
        root_path = str(entry.get("path", "")).rstrip("/")
        if normalized == root_path or normalized.startswith(f"{root_path}/"):
            return (
                with_subsystems(
                    {
                        "path": normalized,
                        "owner": entry.get("module"),
                        "ownership": entry.get("ownership"),
                        "authority": "module_root",
                        "surface": entry.get("path"),
                        "uninstall_policy": entry.get("uninstall_policy"),
                        "matched_by": "module_root",
                    }
                ),
                True,
            )
    for entry in payload["managed_surfaces"]:
        surface = str(entry.get("path", ""))
        if fnmatch.fnmatch(normalized, surface):
            return (
                with_subsystems(
                    {
                        "path": normalized,
                        "owner": entry.get("module"),
                        "ownership": entry.get("ownership"),
                        "authority": entry.get("kind"),
                        "surface": entry.get("path"),
                        "uninstall_policy": entry.get("uninstall_policy"),
                        "matched_by": "managed_surface",
                    }
                ),
                True,
            )
    for entry in payload["fences"]:
        file_path = str(entry.get("file", "")).rstrip("/")
        if normalized == file_path:
            return (
                with_subsystems(
                    {
                        "path": normalized,
                        "owner": entry.get("module"),
                        "ownership": entry.get("ownership"),
                        "authority": "managed_fence",
                        "surface": entry.get("file"),
                        "fence": entry.get("name"),
                        "matched_by": "fence_file",
                    }
                ),
                True,
            )
    return (with_subsystems({"path": normalized, "matched_by": "subsystem"}), bool(subsystem_projection))


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


def _ownership_diagnostics(
    *,
    target_root: Path,
    authority_surfaces: list[dict[str, Any]],
) -> dict[str, Any]:
    def owner_for(concern: str, fallback: str) -> str:
        for entry in authority_surfaces:
            if str(entry.get("concern", "")) == concern:
                surface = str(entry.get("surface", "")).strip()
                owner = str(entry.get("owner", "")).strip()
                return f"{surface} ({owner})" if owner else surface
        return fallback

    def surface_owner(surface: str) -> dict[str, Any] | None:
        normalized = surface.rstrip("/")
        for entry in authority_surfaces:
            if str(entry.get("surface", "")).rstrip("/") == normalized:
                return entry
        return None

    def read_text(relative: str) -> str:
        path = target_root / relative
        if not path.exists() or not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ""

    def without_workspace_fence(text: str) -> str:
        updated, _changed = _remove_fenced_block(
            text=text,
            start_marker=WORKSPACE_WORKFLOW_MARKER_START,
            end_marker=WORKSPACE_WORKFLOW_MARKER_END,
        )
        return updated

    def add(
        *,
        finding_id: str,
        concern: str,
        status: str,
        suspected_surface: str | None = None,
        claimed_by: list[str] | None = None,
        expected_primary_owner: str,
        suggested_route: str,
        evidence: str,
        severity: str = "advisory",
    ) -> None:
        finding: dict[str, Any] = {
            "id": finding_id,
            "concern": concern,
            "status": status,
            "severity": severity,
            "expected_primary_owner": expected_primary_owner,
            "suggested_route": suggested_route,
            "evidence": evidence,
        }
        if suspected_surface:
            finding["suspected_drift_surface"] = suspected_surface
        if claimed_by:
            finding["claimed_by"] = claimed_by
        findings.append(finding)

    findings: list[dict[str, Any]] = []
    agents_text = without_workspace_fence(read_text("AGENTS.md"))
    config_text = read_text(WORKSPACE_CONFIG_PATH.as_posix())
    workflow_text = read_text(WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH.as_posix())
    workspace_workflow_text = read_text(".agentic-workspace/WORKFLOW.md")
    llms_text = read_text("llms.txt")

    active_state_markers = ("current task", "active task", "active execplan", "handoff", "next lane", "validation run")
    if any(marker in agents_text.lower() for marker in active_state_markers):
        add(
            finding_id="startup-adapter-active-state",
            concern="active execution state",
            status="suspected-drift",
            suspected_surface="AGENTS.md",
            expected_primary_owner=owner_for("compact-planning-state", ".agentic-workspace/planning/state.toml + execplans"),
            suggested_route="Move durable current-work and handoff detail into planning state, summary, or an execplan; keep AGENTS.md as an adapter.",
            evidence="startup adapter contains active-state or handoff language outside the managed workspace fence",
        )

    config_active_markers = ("current_task", "active_task", "active_execplan", "handoff", "next_action", "validation_run")
    if any(marker in config_text.lower() for marker in config_active_markers):
        add(
            finding_id="config-active-state",
            concern="active execution state",
            status="suspected-drift",
            suspected_surface=WORKSPACE_CONFIG_PATH.as_posix(),
            expected_primary_owner=owner_for("compact-planning-state", ".agentic-workspace/planning/state.toml + execplans"),
            suggested_route="Keep config for repo-owned policy; move current execution state or handoff details into Planning.",
            evidence="workspace config contains active-task or handoff-shaped keys",
        )

    policy_knobs = ("improvement_latitude", "optimization_bias", "safe_to_auto_run_commands", "[workflow_obligations.")
    if any(marker in workspace_workflow_text.lower() for marker in policy_knobs):
        add(
            finding_id="workflow-policy-knob",
            concern="repo-owned policy",
            status="suspected-drift",
            suspected_surface=".agentic-workspace/WORKFLOW.md",
            expected_primary_owner=owner_for("workspace-policy", WORKSPACE_CONFIG_PATH.as_posix()),
            suggested_route="Move repo-specific policy knobs into .agentic-workspace/config.toml; keep WORKFLOW.md as router guidance.",
            evidence="managed workflow router contains config-policy-shaped keys",
        )

    authoritative_claims: list[str] = []
    for surface, text in (
        ("AGENTS.md", agents_text),
        ("llms.txt", llms_text),
        (".agentic-workspace/WORKFLOW.md", workspace_workflow_text),
        (WORKSPACE_SYSTEM_INTENT_WORKFLOW_PATH.as_posix(), workflow_text),
    ):
        lowered = text.lower()
        if "canonical source" in lowered or "authoritative source" in lowered or "source of truth" in lowered:
            authoritative_claims.append(surface)
    if len(authoritative_claims) >= 2:
        add(
            finding_id="startup-authority-ambiguous",
            concern="startup routing",
            status="ambiguous-owner",
            claimed_by=authoritative_claims,
            expected_primary_owner="AGENTS.md as repo startup adapter; structured authority comes from config, ownership, start, and module reports",
            suggested_route="Keep startup files as adapters and move policy/state to the declared owner surface.",
            evidence="multiple startup or generated workflow surfaces claim canonical authority",
            severity="warning",
        )

    if (target_root / WORKSPACE_CONFIG_PATH).exists() and surface_owner(WORKSPACE_CONFIG_PATH.as_posix()) is None:
        add(
            finding_id="workspace-policy-missing-owner",
            concern="repo-owned policy",
            status="missing-owner",
            suspected_surface=WORKSPACE_CONFIG_PATH.as_posix(),
            expected_primary_owner=WORKSPACE_CONFIG_PATH.as_posix(),
            suggested_route="Declare workspace-policy ownership in .agentic-workspace/OWNERSHIP.toml so agents can route config edits correctly.",
            evidence="config.toml exists but the ownership ledger has no authority surface for it",
            severity="warning",
        )

    return {
        "kind": "agentic-workspace/ownership-diagnostics/v1",
        "status": "attention-needed" if findings else "clean",
        "finding_count": len(findings),
        "findings": findings,
        "rule": "Ledger-driven diagnostics flag likely separation-of-concerns drift and ambiguous authority; findings are advisory unless another invariant marks them invalid.",
        "detail_command": "agentic-workspace ownership --target ./repo --format json",
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


def _product_managed_enclave_payload(*, target_root: Path, ownership_payload: dict[str, Any]) -> dict[str, Any]:
    boundary_review = ownership_payload.get("boundary_review", {})
    package_owned = boundary_review.get("package_owned", {}) if isinstance(boundary_review, dict) else {}
    middle_ground = boundary_review.get("middle_ground", {}) if isinstance(boundary_review, dict) else {}
    module_roots = package_owned.get("module_roots", []) if isinstance(package_owned, dict) else []
    managed_surfaces = package_owned.get("managed_surfaces", []) if isinstance(package_owned, dict) else []
    managed_fences = middle_ground.get("managed_fences", []) if isinstance(middle_ground, dict) else []
    boundary_leaks = [
        surface
        for surface in managed_surfaces
        if isinstance(surface, dict)
        and not str(surface.get("surface", "")).startswith(".agentic-workspace/")
        and str(surface.get("ownership", "")) != "managed_fence"
    ]
    local_only_paths = [
        ".agentic-workspace/local/",
        ".agentic-workspace/local-only/",
        ".agentic-workspace/delegation-outcomes.local.json",
        WORKSPACE_LOCAL_CONFIG_PATH.as_posix(),
        WORKSPACE_LOCAL_MEMORY_DEFAULT_PATH.as_posix(),
        WORKSPACE_LOCAL_SCRATCH_ROOT_PATH.as_posix(),
    ]
    gitignore = target_root / ".gitignore"
    local_ignore_status = (
        "tracked-ignore-present"
        if gitignore.exists() and ".agentic-workspace/local/" in gitignore.read_text(encoding="utf-8")
        else "not-declared-in-gitignore"
    )
    return {
        "status": "attention-needed" if boundary_leaks or ownership_payload.get("warnings") else "clean",
        "managed_root": ".agentic-workspace/",
        "role": "product-managed enclave, not broad repo-owned startup input",
        "removability": {
            "rule": "remove managed files only; repo-owned files keep only explicit managed fences as removable package residue",
            "module_roots": module_roots,
            "managed_surfaces": managed_surfaces,
            "managed_fences": managed_fences,
            "would_affect": [
                ".agentic-workspace/ workspace, planning, memory, and system-intent managed payloads",
                "AGENTS.md managed workflow pointer fence only",
            ],
            "would_preserve": [
                "repo-owned startup instructions outside managed fences",
                "repo docs, source, tests, generated outputs, and ordinary project files",
            ],
        },
        "startup_quietness": {
            "status": "compact",
            "rule": "ordinary startup reads AGENTS.md and compact commands; broad enclave scans are only for selected ownership, report, or module operations",
            "ordinary_entrypoints": [
                "AGENTS.md",
                'agentic-workspace start --profile tiny --task "<task>" --format json',
                "agentic-workspace implement --profile tiny --changed <paths> --format json",
                "agentic-workspace summary --format json",
                "agentic-workspace preflight --format json for takeover/recovery",
            ],
        },
        "local_only_state": {
            "status": "non-authoritative",
            "paths": local_only_paths,
            "gitignore_status": local_ignore_status,
            "rule": "local-only state may tune local runtime behavior but must not become shared workflow, planning, Memory, or contract authority",
        },
        "boundary_leaks": boundary_leaks,
        "review_command": "agentic-workspace ownership --target ./repo --format json",
    }


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
    if payload["subsystems"]:
        print("Subsystems:")
        for entry in payload["subsystems"]:
            print(f"- {entry['id']}: {', '.join(entry.get('paths', []))}")
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
    diagnostics = payload["diagnostics"]
    print(f"Ownership diagnostics: {diagnostics['status']} ({diagnostics['finding_count']} findings)")
    for finding in diagnostics["findings"]:
        surface = finding.get("suspected_drift_surface") or ", ".join(finding.get("claimed_by", []))
        print(f"- {finding['concern']}: {finding['status']} at {surface}")
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
    subsystems: list[dict[str, Any]] = []

    if not ledger_path.exists():
        warnings.append(f"{defaults['ledger']}: ownership ledger missing")
    else:
        payload = config_lib.load_toml_payload(path=ledger_path, surface_name=ledger_path.as_posix())
        ownership_classes = {key: value for key, value in (payload.get("ownership_classes") or {}).items() if isinstance(value, dict)}
        module_roots = [entry for entry in (payload.get("module_roots") or []) if isinstance(entry, dict)]
        managed_surfaces = [entry for entry in (payload.get("managed_surfaces") or []) if isinstance(entry, dict)]
        fences = [entry for entry in (payload.get("fences") or []) if isinstance(entry, dict)]
        authority_surfaces = [entry for entry in (payload.get("authority_surfaces") or []) if isinstance(entry, dict)]
        subsystems = _normalise_subsystems(payload.get("subsystems"))
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
        "subsystems": subsystems,
        "boundary_review": _ownership_boundary_review(
            module_roots=module_roots,
            managed_surfaces=managed_surfaces,
            fences=fences,
            authority_surfaces=authority_surfaces,
        ),
        "diagnostics": _ownership_diagnostics(
            target_root=target_root,
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
                "freshness": _module_update_freshness_payload(
                    module_name=module_name,
                    sync_status=sync_status,
                    current_source=current_source,
                    policy=policy,
                    cli_invoke=config.cli_invoke,
                ),
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


def _sourced_value(value: Any, *, source: str) -> dict[str, Any]:
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
    local_override: Any | None = None,
) -> dict[str, Any]:
    lower_trust_profiles = [
        profile.get("name", "")
        for profile in profile_payloads
        if isinstance(profile, dict)
        and isinstance(profile.get("closeout_gate"), dict)
        and profile["closeout_gate"].get("trust") == "lower-trust"
    ]
    guardrail_defaults = defaults.get("delegated_run_guardrail", {})
    configured_profiles = sorted([str(profile.get("name", "")) for profile in profile_payloads if isinstance(profile, dict)])
    has_runtime_posture = bool(
        local_override
        and any(
            value is not None
            for value in (
                local_override.supports_internal_delegation,
                local_override.strong_planner_available,
                local_override.cheap_bounded_executor_available,
                local_override.prefer_internal_delegation_when_available,
            )
        )
    )
    return {
        "status": "present",
        "rule": guardrail_defaults.get("rule", ""),
        "required_preflight_checks": list(guardrail_defaults.get("required_preflight_checks", [])),
        "local_posture_effect": {
            "status": "configured" if configured_profiles or has_runtime_posture else "available-not-set",
            "advisory_only": True,
            "configured_profiles": [name for name in configured_profiles if name],
            "runtime_posture_configured": has_runtime_posture,
            "handoff_guidance": (
                "Use profile advisory and runtime_resolution to size handoff detail; keep local posture out of shared repo authority."
                if configured_profiles or has_runtime_posture
                else "No local delegation posture configured; use ordinary bounded handoff guidance."
            ),
            "proof_burden": (
                "lower-trust profiles require explicit execution residue and human review before closeout"
                if lower_trust_profiles
                else "normal bounded proof burden"
            ),
        },
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
    capability_mismatch = False
    required_action = "execute-with-normal-proof"
    overqualified_for_task = False
    hard_forbidden = False

    if execution_class and execution_class in profile.forbidden_task_classes:
        hard_forbidden = True
        capability_mismatch = True
        score -= 5
        required_action = "escalate-before-execution"
        reasons.append("target forbids this execution class")
    elif execution_class and execution_class in profile.safe_task_classes:
        score += 2
        reasons.append("target explicitly marks this execution class as safe")

    if recommended_strength:
        profile_rank = _strength_rank(profile.strength)
        required_rank = _strength_rank(recommended_strength)
        if profile_rank < required_rank:
            capability_mismatch = True
            score -= 3
            reasons.append("target strength is below the recommended strength")
            if profile.strength == "weak" and (
                recommended_strength == "strong" or execution_class in ("boundary-shaping", "reasoning-heavy")
            ):
                required_action = "escalate-before-execution"
                reasons.append("weak target must escalate before high-judgment execution")
            else:
                required_action = "review-before-execution"
        elif profile.strength == recommended_strength:
            score += 3
            reasons.append("target strength matches the recommended strength")
        else:
            overqualified_for_task = True
            score += 1
            reasons.append("target strength exceeds the recommended strength")
            if (
                not hard_forbidden
                and profile.strength == "strong"
                and recommended_strength == "weak"
                and execution_class == "mechanical-follow-through"
            ):
                required_action = "delegate-down-when-safe"
                reasons.append("strong target should down-route mechanical work when a cheaper fit is available")

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

    if profile.reasoning_profile != "unknown" and recommended_strength:
        reasoning_rank = {"weak": 1, "balanced": 2, "strong": 3}
        required_rank = {"weak": 1, "medium": 2, "strong": 3}.get(recommended_strength, 0)
        profile_reasoning_rank = reasoning_rank.get(profile.reasoning_profile, 0)
        if profile_reasoning_rank and required_rank and profile_reasoning_rank < required_rank:
            capability_mismatch = True
            score -= 2
            reasons.append("target reasoning profile is below the recommended strength")
            if recommended_strength == "strong":
                required_action = "escalate-before-execution"
        elif profile_reasoning_rank and required_rank and profile_reasoning_rank > required_rank:
            score += 1
            reasons.append("target reasoning profile exceeds the recommended strength")

    if profile.context_capacity == "small" and str(capability_posture.get("work shape", "")).strip() in ("lane", "epic"):
        capability_mismatch = True
        score -= 2
        reasons.append("target context capacity is too small for lane or epic shaped work")
        required_action = "escalate-before-execution"

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
        "capability_mismatch": capability_mismatch,
        "overqualified_for_task": overqualified_for_task,
        "required_action": required_action,
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
                "model_family": profile.model_family,
                "provider": profile.provider,
                "context_capacity": profile.context_capacity,
                "reasoning_profile": profile.reasoning_profile,
                "cost_class": profile.cost_class,
                "latency_class": profile.latency_class,
                "safe_task_classes": list(profile.safe_task_classes),
                "forbidden_task_classes": list(profile.forbidden_task_classes),
                "escalation_target": profile.escalation_target,
                "confidence_source": profile.confidence_source,
                "last_evaluation": profile.last_evaluation,
                "human_control_modes": list(profile.human_control_modes),
                "recommendation": rec["status"],
                "score": rec["score"],
                "reasons": rec["reasons"],
                "capability_mismatch": rec["capability_mismatch"],
                "overqualified_for_task": rec["overqualified_for_task"],
                "required_action": rec["required_action"],
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
    weak_target_mismatches = [
        p for p in profile_recommendations if p["strength"] == "weak" and p.get("required_action") == "escalate-before-execution"
    ]
    overqualified_strong_targets = [
        p for p in profile_recommendations if p["strength"] == "strong" and p.get("required_action") == "delegate-down-when-safe"
    ]
    cheaper_fit_targets = [
        p
        for p in profile_recommendations
        if p["strength"] in ("weak", "medium")
        and p["recommendation"] in ("recommended", "acceptable")
        and execution_class == "mechanical-follow-through"
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
        "self_assessment": _self_assessment_authority_payload(),
        "weak_target_guardrail": _weak_target_guardrail_payload(
            local_override=local_override,
            weak_target_mismatches=weak_target_mismatches,
        ),
        "downrouting_guardrail": _downrouting_guardrail_payload(
            local_override=local_override,
            overqualified_strong_targets=overqualified_strong_targets,
            cheaper_fit_targets=cheaper_fit_targets,
        ),
    }


def _self_assessment_authority_payload() -> dict[str, Any]:
    return {
        "authority": "advisory-only",
        "rule": (
            "A model's self-confidence or self-described capability may explain a route, but structural task signals, "
            "local target limits, proof burden, and human control remain higher authority."
        ),
        "may_influence": [
            "handoff detail",
            "review burden",
            "suggested confidence tuning",
            "whether to ask for stronger planning when structural signals are inconclusive",
        ],
        "cannot_override": [
            "forbidden_task_classes",
            "capability_mismatch",
            "proof_burden=high",
            "required_action=escalate-before-execution",
            "delegation.mode human control",
        ],
    }


def _weak_target_guardrail_payload(
    *,
    local_override: MixedAgentLocalOverride,
    weak_target_mismatches: list[dict[str, Any]],
) -> dict[str, Any]:
    delegation_control = _delegation_control_payload(local_override)
    effective_mode = delegation_control["effective_mode"]
    mode_actions = {
        "off": "do not delegate to the weak target; current executor must stay direct only if it can satisfy the task itself",
        "manual": "prepare a strong_handoff_packet and stop for human or runtime execution",
        "suggest": "recommend a stronger planner or compact handoff; do not execute the weak target automatically",
        "auto": "route to a stronger configured target when safety allows; otherwise stop with manual-handoff",
    }
    return {
        "status": "active" if weak_target_mismatches else "inactive",
        "rule": (
            "Weak targets may save tokens only when the task fits their advertised capability. "
            "For boundary-shaping, reasoning-heavy, or strong-strength work, a weak target below recommended strength "
            "must escalate before execution."
        ),
        "effective_mode": effective_mode,
        "mode_action": mode_actions.get(effective_mode, mode_actions["suggest"]),
        "quality_over_cost": "Token saving is valid only when it does not compromise capability fit, proof, or review trust.",
        "mismatched_targets": [
            {
                "name": str(item.get("name", "")),
                "strength": str(item.get("strength", "")),
                "required_action": str(item.get("required_action", "")),
                "reasons": list(item.get("reasons", [])),
            }
            for item in weak_target_mismatches
        ],
    }


def _downrouting_guardrail_payload(
    *,
    local_override: MixedAgentLocalOverride,
    overqualified_strong_targets: list[dict[str, Any]],
    cheaper_fit_targets: list[dict[str, Any]],
) -> dict[str, Any]:
    delegation_control = _delegation_control_payload(local_override)
    effective_mode = delegation_control["effective_mode"]
    active = bool(overqualified_strong_targets and cheaper_fit_targets)
    mode_actions = {
        "off": "stay direct; do not force delegation for cheap work",
        "manual": "prepare a compact handoff for the cheaper target and stop",
        "suggest": "recommend the cheaper bounded executor and keep the strong target as planner/reviewer fallback",
        "auto": "delegate to the cheaper bounded executor when safety allows; otherwise stay direct",
    }
    return {
        "status": "active" if active else "inactive",
        "rule": (
            "Strong targets should down-route mechanical-follow-through work when a configured cheaper target fits the task "
            "and validation remains clear. Strong reasoning remains the fallback for planning, review, or proof ambiguity."
        ),
        "effective_mode": effective_mode,
        "mode_action": mode_actions.get(effective_mode, mode_actions["suggest"]),
        "quality_over_cost": "Down-routing is valid only when it does not compromise capability fit, proof, or review trust.",
        "overqualified_targets": [
            {
                "name": str(item.get("name", "")),
                "strength": str(item.get("strength", "")),
                "required_action": str(item.get("required_action", "")),
                "reasons": list(item.get("reasons", [])),
            }
            for item in overqualified_strong_targets
        ],
        "cheaper_fit_targets": [
            {
                "name": str(item.get("name", "")),
                "strength": str(item.get("strength", "")),
                "recommendation": str(item.get("recommendation", "")),
                "score": item.get("score", 0),
            }
            for item in cheaper_fit_targets
        ],
    }


def _capability_handoff_packet_templates() -> dict[str, Any]:
    common_required = [
        "task_shape: direct, bounded, lane, or epic",
        "route_reason: why this target or escalation route fits better than direct execution",
        "inspected_context: exact files, commands, or planning state already inspected",
        "allowed_write_scope: paths or surfaces the receiver may edit",
        "proof_expectations: commands or checks that must remain true",
        "stop_conditions: when the receiver must stop instead of guessing",
        "return_contract: what evidence or answer the receiver must return",
    ]
    return {
        "rule": (
            "Use capability handoff packets when runtime_resolution exposes escalation, down-routing, or no-safe-route. "
            "Packets preserve quality first and token savings only when proof and scope remain safe."
        ),
        "common_required_fields": common_required,
        "packet_types": {
            "weak_target_escalation": {
                "use_when": "A weak or underfit target encounters boundary-shaping, reasoning-heavy, high-proof, or forbidden work.",
                "receiver": "strong planner, human, or configured escalation target",
                "must_not": "execute the overmatched target as executor of record",
            },
            "exploration_probe": {
                "use_when": "The current executor needs one bounded repo-inspection answer before planning, implementation, or validation can stay compact.",
                "receiver": "read-only explorer or cheaper inspection-capable target",
                "must_not": "edit files, decide product direction, or synthesize beyond the assigned question.",
            },
            "strong_target_downrouting": {
                "use_when": "A strong target is overqualified for mechanical-follow-through work and a cheaper configured target fits.",
                "receiver": "cheaper bounded executor with strong target retained as planner/reviewer fallback",
                "must_not": "down-route when proof is unclear or the task has unresolved judgment.",
            },
            "manual_human_clarification": {
                "use_when": "The next decision depends on human intent, ownership boundary, or acceptable autonomy.",
                "receiver": "human",
                "must_not": "substitute an agent-preferred outcome for the requested outcome.",
            },
            "strong_reviewer_fallback": {
                "use_when": "Implementation can proceed cheaply, but review or proof interpretation needs stronger reasoning.",
                "receiver": "strong reviewer",
                "must_not": "expand implementation scope during review without returning a new route decision.",
            },
            "no_safe_route": {
                "use_when": "No configured target can satisfy capability, proof, and human-control requirements.",
                "receiver": "current executor closeout or human triage",
                "must_not": "force delegation merely because a target exists.",
            },
        },
    }


def _ready_capability_handoff_packet(
    *,
    packet_type: str,
    mode: str,
    target: str | None,
    posture: dict[str, Any],
    runtime_resolution: dict[str, Any],
) -> dict[str, Any]:
    templates = _capability_handoff_packet_templates()
    packet_template = templates["packet_types"].get(packet_type, {})
    return {
        "kind": "agentic-workspace/capability-handoff-packet/v1",
        "packet_type": packet_type,
        "mode": mode,
        "target": target,
        "template": packet_template,
        "task_shape": posture.get("work_shape") or posture.get("posture", {}).get("work shape"),
        "route_reason": runtime_resolution.get("guidance"),
        "inspected_context": posture.get("inspection_evidence_required", []),
        "proof_expectations": posture.get("proof_burden"),
        "allowed_write_scope": "Use the active plan or implementer-context path boundaries; do not infer broader ownership.",
        "stop_conditions": [
            "capability mismatch remains unresolved",
            "proof burden is high and no stronger reviewer or proof route is available",
            "human-control mode does not permit execution",
            "the receiver would need to widen the requested outcome",
        ],
        "prompt": (
            "Answer or execute only the bounded packet. Preserve scope, proof, and human-control limits; quality fit outranks token saving."
        ),
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
                "model_family": profile.model_family,
                "provider": profile.provider,
                "context_capacity": profile.context_capacity,
                "reasoning_profile": profile.reasoning_profile,
                "cost_class": profile.cost_class,
                "latency_class": profile.latency_class,
                "safe_task_classes": list(profile.safe_task_classes),
                "forbidden_task_classes": list(profile.forbidden_task_classes),
                "escalation_target": profile.escalation_target,
                "confidence_source": profile.confidence_source,
                "last_evaluation": profile.last_evaluation,
                "human_control_modes": list(profile.human_control_modes),
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
            "supported_fields": ["workspace.improvement_latitude", "workspace.advanced_features"],
        },
        "local_override": {
            "path": WORKSPACE_LOCAL_CONFIG_PATH.as_posix(),
            "supported": defaults["local_override"]["supported"],
            "supported_fields": defaults["local_override"]["supported_fields"],
            "exists": local_override.exists,
            "applied": local_override.applied,
            "status": "applied" if local_override.applied else "available-not-set",
            "rule": "local-only machine/runtime posture; may not override repo-owned semantics",
        },
        "delegation_control": _delegation_control_payload(local_override),
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
                "delegation_targets.<target>.model_family",
                "delegation_targets.<target>.provider",
                "delegation_targets.<target>.context_capacity",
                "delegation_targets.<target>.reasoning_profile",
                "delegation_targets.<target>.cost_class",
                "delegation_targets.<target>.latency_class",
                "delegation_targets.<target>.safe_task_classes",
                "delegation_targets.<target>.forbidden_task_classes",
                "delegation_targets.<target>.escalation_target",
                "delegation_targets.<target>.confidence_source",
                "delegation_targets.<target>.last_evaluation",
                "delegation_targets.<target>.human_control_modes",
            ],
            "supported_strengths": list(SUPPORTED_DELEGATION_TARGET_STRENGTHS),
            "supported_locations": list(SUPPORTED_CAPABILITY_LOCATIONS),
            "supported_capability_classes": list(SUPPORTED_CAPABILITY_EXECUTION_CLASSES),
            "supported_execution_methods": list(SUPPORTED_DELEGATION_TARGET_EXECUTION_METHODS),
            "supported_context_capacities": list(SUPPORTED_DELEGATION_TARGET_CONTEXT_CAPACITIES),
            "supported_reasoning_profiles": list(SUPPORTED_DELEGATION_TARGET_REASONING_PROFILES),
            "supported_cost_classes": list(SUPPORTED_DELEGATION_TARGET_COST_CLASSES),
            "supported_latency_classes": list(SUPPORTED_DELEGATION_TARGET_LATENCY_CLASSES),
            "supported_human_control_modes": list(SUPPORTED_DELEGATION_CONTROL_MODES),
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
        "local_scratch": _local_scratch_payload(
            exists=(config.target_root / WORKSPACE_LOCAL_SCRATCH_ROOT_PATH).exists() if config.target_root is not None else False
        ),
        "agent_aid_storage": _agent_aid_storage_payload(target_root=config.target_root),
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
            "delegation_mode": _sourced_value(
                local_override.delegation_mode or "suggest",
                source="local-override" if local_override.delegation_mode is not None else "default",
            ),
            "clarification_mode": _sourced_value(
                local_override.clarification_mode or "suggest",
                source="local-override" if local_override.clarification_mode is not None else "default",
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
            local_override=local_override,
        ),
        "runtime_resolution": _runtime_resolution_payload(config=config),
        "strong_handoff_packet": _strong_handoff_packet_template(),
        "success_measures": defaults["success_measures"],
    }


def _config_payload(*, config: WorkspaceConfig) -> dict[str, Any]:
    assurance = config.assurance
    return {
        "target": config.target_root.as_posix() if config.target_root is not None else None,
        "invoked_cli_identity": _invoked_cli_identity_payload(target_root=config.target_root),
        "cli_compatibility": _cli_compatibility_payload(config=config),
        "config_path": config.path.as_posix() if config.path is not None else WORKSPACE_CONFIG_PATH.as_posix(),
        "exists": config.exists,
        "schema_version": config.schema_version,
        "edit_reference": {
            "kind": "agentic-workspace/managed-config-reference/v1",
            "owner": "repo-owned policy",
            "direct_edit_rule": "Edit directly only when changing repo-owned policy; use the config command for the resolved view.",
            "reference_doc": WORKSPACE_CONFIG_CONTRACT_DOC,
            "generated_reference_doc": WORKSPACE_CONFIG_REFERENCE_DOC,
            "source_schema": WORKSPACE_CONFIG_SOURCE_SCHEMA,
            "check_command": f"{config.cli_invoke} config --target . --profile tiny --format json",
            "managed_header": _managed_workspace_config_header(cli_invoke=config.cli_invoke).splitlines(),
        },
        "warnings": list(config.warnings),
        "config_enforcement": _config_enforcement_payload(config=config),
        "config_effect_audit": _config_effect_audit_payload(config=config),
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
            "advanced_features": list(config.advanced_features),
            "advanced_features_source": config.advanced_features_source,
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
            "supported_advanced_features": list(SUPPORTED_ADVANCED_FEATURES),
        },
        "update": {
            "wrapper_rule": "normal update execution stays behind agentic-workspace",
            "modules": _module_update_policy_payload(config=config, target_root=config.target_root),
        },
        "assurance": {
            "default_level": assurance.default_level,
            "default_level_source": assurance.default_level_source,
            "agent_may_escalate": assurance.agent_may_escalate,
            "agent_may_deescalate": assurance.agent_may_deescalate,
            "strict_closeout": assurance.strict_closeout,
            "supported_levels": list(SUPPORTED_ASSURANCE_LEVELS),
            "proof_profiles": [
                {
                    "id": profile.id,
                    "required_commands": list(profile.required_commands),
                    "optional_commands": list(profile.optional_commands),
                    "review_aids": list(profile.review_aids),
                }
                for profile in assurance.proof_profiles
            ],
            "test_data_policy": dict(assurance.test_data_policy),
            "decision_record_target": assurance.decision_record_target,
            "invariant_registry": assurance.invariant_registry,
            "risk_registry": assurance.risk_registry,
            "onboarding": _assurance_onboarding_payload(assurance=assurance),
            "rule": "Assurance config is generic host-owned routing for refs, proof profiles, gates, blockers, closeout, and review aids; it is not domain law.",
        },
        "mixed_agent": _mixed_agent_payload(config=config),
    }


def _compact_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    workspace = payload["workspace"]
    mixed_agent = payload["mixed_agent"]
    local_override = mixed_agent["local_override"]
    effective_posture = mixed_agent["effective_posture"]
    runtime_resolution = mixed_agent["runtime_resolution"]
    assurance = payload["assurance"]
    compact_obligations = [
        {
            "id": obligation["id"],
            "stage": obligation["stage"],
            "scope_tags": obligation["scope_tags"],
            "commands": obligation["commands"],
        }
        for obligation in workspace["workflow_obligations"]
    ]
    return {
        "kind": "agentic-workspace/config-compact/v1",
        "profile": "compact",
        "target": ".",
        "config_path": WORKSPACE_CONFIG_PATH.as_posix(),
        "exists": payload["exists"],
        "schema_version": payload["schema_version"],
        "warnings": payload["warnings"],
        "edit_reference": payload["edit_reference"],
        "config_effect_audit": {
            "status": payload["config_effect_audit"]["status"],
            "field_count_by_effect": payload["config_effect_audit"]["field_count_by_effect"],
            "agent_dependent_field_count": len(payload["config_effect_audit"]["agent_dependent_fields"]),
            "warning_count": len(payload["config_effect_audit"]["claimed_vs_actual_warnings"]),
            "detail_command": payload["config_effect_audit"]["detail_command"],
        },
        "workspace": {
            "default_preset": workspace["default_preset"],
            "agent_instructions_file": workspace["agent_instructions_file"],
            "workflow_artifact_profile": workspace["workflow_artifact_profile"],
            "improvement_latitude": workspace["improvement_latitude"],
            "improvement_latitude_source": workspace["improvement_latitude_source"],
            "optimization_bias": workspace["optimization_bias"],
            "optimization_bias_source": workspace["optimization_bias_source"],
            "cli_invoke": workspace["cli_invoke"],
            "workflow_obligations": compact_obligations,
            "system_intent_sources": workspace["system_intent"]["sources"],
        },
        "reporting_posture": {
            "status": "present",
            "summary": "Use this compact config payload as source evidence; do not read raw config files only to cite line numbers.",
            "effect": "Report the setting names and values that changed the closeout or handoff answer.",
            "repo_policy": {
                "improvement_latitude": workspace["improvement_latitude"],
                "improvement_latitude_source": workspace["improvement_latitude_source"],
                "optimization_bias": workspace["optimization_bias"],
                "optimization_bias_source": workspace["optimization_bias_source"],
                "workflow_obligation_ids": [obligation["id"] for obligation in compact_obligations],
            },
            "local_runtime": {
                "delegation_mode": effective_posture["delegation_mode"],
                "safe_to_auto_run_commands": effective_posture["safe_to_auto_run_commands"],
                "requires_human_verification_on_pr": effective_posture["requires_human_verification_on_pr"],
            },
            "citation_rule": "Final answers should cite repo-relative surfaces or setting names, not local absolute paths.",
        },
        "assurance": {
            "default_level": assurance["default_level"],
            "strict_closeout": assurance["strict_closeout"],
            "agent_may_escalate": assurance["agent_may_escalate"],
            "agent_may_deescalate": assurance["agent_may_deescalate"],
            "configured_proof_profile_count": len(assurance["proof_profiles"]),
        },
        "local_runtime": {
            "local_override_path": local_override["path"],
            "local_override_status": local_override["status"],
            "supports_internal_delegation": effective_posture["supports_internal_delegation"],
            "strong_planner_available": effective_posture["strong_planner_available"],
            "cheap_bounded_executor_available": effective_posture["cheap_bounded_executor_available"],
            "delegation_mode": effective_posture["delegation_mode"],
            "clarification_mode": effective_posture["clarification_mode"],
            "safe_to_auto_run_commands": effective_posture["safe_to_auto_run_commands"],
            "prefer_internal_delegation_when_available": effective_posture["prefer_internal_delegation_when_available"],
            "requires_human_verification_on_pr": effective_posture["requires_human_verification_on_pr"],
            "runtime_resolution": {
                "recommendation": runtime_resolution["recommendation"],
                "confidence": runtime_resolution["confidence"],
                "reasons": runtime_resolution["reasons"],
            },
        },
        "full_profile_command": f"{workspace['cli_invoke']} config --target . --profile full --format json",
    }


def _tiny_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    compact = _compact_config_payload(payload)
    workspace = compact["workspace"]
    local_runtime = compact["local_runtime"]
    reporting_posture = compact["reporting_posture"]
    return {
        "kind": "agentic-workspace/config-tiny/v1",
        "profile": "tiny",
        "target": compact["target"],
        "config_path": compact["config_path"],
        "exists": compact["exists"],
        "warnings": compact["warnings"],
        "reporting_posture": {
            "status": reporting_posture["status"],
            "effect": reporting_posture["effect"],
            "citation_rule": reporting_posture["citation_rule"],
        },
        "workspace": {
            "agent_instructions_file": workspace["agent_instructions_file"],
            "improvement_latitude": workspace["improvement_latitude"],
            "improvement_latitude_source": workspace["improvement_latitude_source"],
            "optimization_bias": workspace["optimization_bias"],
            "optimization_bias_source": workspace["optimization_bias_source"],
            "workflow_obligation_ids": reporting_posture["repo_policy"]["workflow_obligation_ids"],
            "cli_invoke": workspace["cli_invoke"],
        },
        "local_runtime": {
            "delegation_mode": local_runtime["delegation_mode"],
            "clarification_mode": local_runtime["clarification_mode"],
            "safe_to_auto_run_commands": local_runtime["safe_to_auto_run_commands"],
            "requires_human_verification_on_pr": local_runtime["requires_human_verification_on_pr"],
        },
        "next_detail": {
            "compact": f"{workspace['cli_invoke']} config --target . --profile compact --format json",
            "full": compact["full_profile_command"],
        },
    }


def _emit_config(*, format_name: str, config: WorkspaceConfig, profile: str = "full") -> None:
    full_payload = _config_payload(config=config)
    if profile == "tiny":
        payload = _tiny_config_payload(full_payload)
    elif profile == "compact":
        payload = _compact_config_payload(full_payload)
    else:
        payload = full_payload
    if format_name == "json":
        print(json.dumps(serialise_value(payload), indent=2))
        return
    if profile == "tiny":
        print(f"Target: {payload['target']}")
        print(f"Config path: {payload['config_path']}")
        print(f"Improvement latitude: {payload['workspace']['improvement_latitude']}")
        print(f"Optimization bias: {payload['workspace']['optimization_bias']}")
        print(f"Delegation mode: {payload['local_runtime']['delegation_mode']['value']}")
        print(f"Safe to auto-run commands: {payload['local_runtime']['safe_to_auto_run_commands']['value']}")
        print(f"Compact profile: {payload['next_detail']['compact']}")
        return
    if profile == "compact":
        print(f"Target: {payload['target']}")
        print(f"Config path: {payload['config_path']}")
        print(f"Exists: {payload['exists']}")
        print(f"Improvement latitude: {payload['workspace']['improvement_latitude']}")
        print(f"Optimization bias: {payload['workspace']['optimization_bias']}")
        print(f"Workflow obligations: {len(payload['workspace']['workflow_obligations'])} configured")
        print(f"Delegation mode: {payload['local_runtime']['delegation_mode']['value']}")
        print(f"Safe to auto-run commands: {payload['local_runtime']['safe_to_auto_run_commands']['value']}")
        print(f"Full profile: {payload['full_profile_command']}")
        return
    print(f"Target: {payload['target']}")
    print(f"Config path: {payload['config_path']}")
    print(f"Exists: {payload['exists']}")
    print(f"Reference: {payload['edit_reference']['reference_doc']}")
    print(f"Schema: {payload['edit_reference']['source_schema']}")
    print(f"Check command: {payload['edit_reference']['check_command']}")
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
    print(
        "Advanced features: "
        f"{', '.join(payload['workspace']['advanced_features']) or 'none'} "
        f"({payload['workspace']['advanced_features_source']})"
    )
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
        "subsystem_intent": _load_subsystem_intent(target_root=target_root),
        "decision_projection": _intent_decision_projection(target_root=target_root, config=config, compact=True),
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


def _module_update_freshness_payload(
    *,
    module_name: str,
    sync_status: str,
    current_source: dict[str, Any] | None,
    policy: ModuleUpdatePolicy,
    cli_invoke: str,
) -> dict[str, Any]:
    recorded_at = current_source.get("recorded_at") if isinstance(current_source, dict) else None
    status = "unknown"
    age_days: int | None = None
    reason = "module upgrade source metadata has no recorded_at timestamp"
    if sync_status == "missing":
        status = "unknown"
        reason = "module upgrade source metadata is missing"
    elif sync_status == "drift":
        status = "stale"
        reason = "module upgrade source metadata differs from the resolved workspace policy"
    elif isinstance(recorded_at, str) and recorded_at.strip():
        try:
            age_days = (date.today() - date.fromisoformat(recorded_at.strip())).days
            if age_days > policy.recommended_upgrade_after_days:
                status = "stale"
                reason = "module upgrade source metadata is older than recommended_upgrade_after_days"
            else:
                status = "fresh"
                reason = "module upgrade source metadata is within recommended_upgrade_after_days"
        except ValueError:
            status = "unknown"
            reason = "module upgrade source metadata recorded_at is not an ISO date"
    return {
        "status": status,
        "recorded_at": recorded_at,
        "age_days": age_days,
        "recommended_upgrade_after_days": policy.recommended_upgrade_after_days,
        "sync_status": sync_status,
        "reason": reason,
        "next_action": (
            {
                "action": "inspect-upgrade-plan",
                "command": f"{cli_invoke} upgrade --modules {module_name} --dry-run --format json",
                "run": f"{cli_invoke} upgrade --modules {module_name} --dry-run --format json",
                "risk": "read-only lifecycle inspection",
                "required_inputs": ["module", "resolved workspace policy"],
                "next_proof": "apply upgrade only after inspecting the dry-run lifecycle plan",
            }
            if status in {"stale", "unknown"}
            else None
        ),
    }


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
            name="workspace-core",
            registry_path=Path(".agentic-workspace/skills/REGISTRY.json"),
            skills_root=Path(".agentic-workspace/skills"),
            owner="agentic-workspace",
            source_kind="installed-workspace-skills",
            default_scope="bundled",
            default_stability="package-managed",
        ),
        SkillCatalogSource(
            name="planning-bundled",
            registry_path=Path(".agentic-workspace/planning/skills/REGISTRY.json"),
            skills_root=Path(".agentic-workspace/planning/skills"),
            owner="agentic-planning",
            source_kind="bundled-package-skills",
            default_scope="bundled",
            default_stability="package-managed",
        ),
        SkillCatalogSource(
            name="memory-core",
            registry_path=Path(".agentic-workspace/memory/skills/REGISTRY.json"),
            skills_root=Path(".agentic-workspace/memory/skills"),
            owner="agentic-memory",
            source_kind="installed-core-skills",
            default_scope="bundled",
            default_stability="package-managed",
        ),
        SkillCatalogSource(
            name="memory-bootstrap-temporary",
            registry_path=Path(".agentic-workspace/memory/bootstrap/skills/REGISTRY.json"),
            skills_root=Path(".agentic-workspace/memory/bootstrap/skills"),
            owner="agentic-memory",
            source_kind="temporary-memory-bootstrap-skills",
            default_scope="temporary-bootstrap",
            default_stability="temporary-bootstrap-workspace",
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
    if payload.get("agent_aid_recommendations"):
        print("Recommended agent aids:")
        for recommendation in payload["agent_aid_recommendations"]:
            print(f"- {recommendation['id']} ({recommendation['score']}): {recommendation['entrypoint']}")
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
    agent_aids, aid_warnings = _checked_in_agent_aid_entries(target_root=target_root)
    visible_agent_aids = [aid for aid in agent_aids if aid["status"] != "retired"]
    agent_aid_recommendations = _recommend_agent_aids(task_text=task_text, aids=visible_agent_aids) if task_text else []
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
        "agent_aids": visible_agent_aids,
        "agent_aid_recommendations": agent_aid_recommendations,
        "agent_aid_source": {
            "root": WORKSPACE_AGENT_AID_ROOT_PATH.as_posix(),
            "manifest_name": "manifest.json",
            "section_command": "agentic-workspace report --target ./repo --section agent_aids --format json",
            "retired_aids_excluded": True,
        },
        "warnings": warnings,
        "agent_aid_warnings": aid_warnings,
        "sources": sources,
    }


def _recommend_agent_aids(*, task_text: str, aids: list[dict[str, Any]]) -> list[dict[str, Any]]:
    task_tokens = set(_skill_match_tokens(task_text))
    task_text_normalized = " ".join(_skill_match_tokens(task_text))
    recommendations: list[dict[str, Any]] = []
    for aid in aids:
        score = 0
        reasons: list[str] = []
        searchable_values = [
            str(aid.get("id", "")),
            str(aid.get("type", "")),
            str(aid.get("entrypoint", "")),
            *[str(item) for item in aid.get("use_when", []) if isinstance(item, str)],
        ]
        for value in searchable_values:
            value_tokens = set(_skill_match_tokens(value))
            overlap = sorted(token for token in task_tokens & value_tokens if len(token) >= 4)
            if overlap:
                score += len(overlap)
                reasons.append(f"term overlap: {', '.join(overlap)}")
                break
        aid_id_phrase = " ".join(_skill_match_tokens(str(aid.get("id", ""))))
        if aid_id_phrase and aid_id_phrase in task_text_normalized:
            score += 6
            reasons.append(f"id match: {aid.get('id')}")
        if score > 0:
            recommendations.append({**aid, "score": score, "reasons": reasons})
    recommendations.sort(key=lambda item: (-int(item["score"]), str(item["id"])))
    return recommendations


def _discover_registered_skills(*, target_root: Path) -> tuple[list[RegisteredSkill], list[str], list[dict[str, str]]]:
    discovered: list[RegisteredSkill] = []
    warnings: list[str] = []
    sources: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for source in _skill_catalog_sources():
        registry_file = target_root / source.registry_path
        skills_root = target_root / source.skills_root
        package_registry_file = _package_skill_registry_file(source)
        source_state = "absent"
        if registry_file.exists():
            source_state = "registry"
            for skill in _load_registered_skills(source=source, registry_file=registry_file):
                key = (skill.skill_id, skill.path.as_posix())
                if key in seen:
                    continue
                seen.add(key)
                discovered.append(skill)
        elif package_registry_file is not None:
            source_state = "package-registry"
            for skill in _load_registered_skills(source=source, registry_file=package_registry_file):
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
        if registry_file.exists() or scanned_paths or package_registry_file is not None:
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


def _package_skill_registry_file(source: SkillCatalogSource) -> Path | None:
    if source.name != "planning-bundled":
        return None
    try:
        from repo_planning_bootstrap.installer import skills_root as planning_skills_root
    except ImportError:
        return None
    registry_file = planning_skills_root() / "REGISTRY.json"
    return registry_file if registry_file.exists() else None


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
    task_text_normalized = " ".join(_skill_match_tokens(task_text))
    if "setup" in task_text_lower:
        for skill in skills:
            if skill.skill_id == "workspace-setup-jumpstart":
                return [
                    SkillRecommendation(
                        skill=skill,
                        hint_score=18,
                        score=18,
                        reasons=("setup uses the workspace setup jumpstart route before any broader discovery",),
                    )
                ]
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

        matched_id = _matched_skill_id_phrase(skill=skill, task_text_normalized=task_text_normalized)
        if matched_id:
            score += 6
            hint_score += 6
            reasons.append(f"id match: {matched_id}")

        matched_phrases = _matched_skill_terms(
            terms=skill.activation_hints.phrases,
            task_text_lower=task_text_lower,
            task_text_normalized=task_text_normalized,
            task_tokens=task_tokens,
        )
        if matched_phrases:
            phrase_score = len(matched_phrases) * 6
            score += phrase_score
            hint_score += phrase_score
            reasons.append(f"phrase match: {', '.join(matched_phrases)}")

        for label, terms, weight in (
            ("verb", skill.activation_hints.verbs, 2),
            ("noun", skill.activation_hints.nouns, 3),
            ("context", skill.activation_hints.when, 2),
        ):
            matched = _matched_skill_terms(
                terms=terms,
                task_text_lower=task_text_lower,
                task_text_normalized=task_text_normalized,
                task_tokens=task_tokens,
            )
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


def _matched_skill_id_phrase(*, skill: RegisteredSkill, task_text_normalized: str) -> str:
    tokens = _skill_match_tokens(skill.skill_id)
    if len(tokens) < 2:
        return ""
    for size in range(len(tokens), 1, -1):
        phrase = " ".join(tokens[:size])
        if phrase in task_text_normalized:
            return phrase
    return ""


def _matched_skill_terms(
    *,
    terms: tuple[str, ...],
    task_text_lower: str,
    task_text_normalized: str,
    task_tokens: set[str],
) -> list[str]:
    matched = [
        term
        for term in terms
        if _skill_term_matches(
            term=term,
            task_text_lower=task_text_lower,
            task_text_normalized=task_text_normalized,
            task_tokens=task_tokens,
        )
    ]
    return sorted(dict.fromkeys(matched))


def _skill_term_matches(*, term: str, task_text_lower: str, task_text_normalized: str, task_tokens: set[str]) -> bool:
    term_tokens = _skill_match_tokens(term)
    normalised = " ".join(term_tokens)
    if not normalised:
        return False
    if " " in normalised:
        return (
            normalised in task_text_lower
            or normalised in task_text_normalized
            or all(_skill_token_matches(token=token, task_tokens=task_tokens) for token in term_tokens)
        )
    return _skill_token_matches(token=normalised, task_tokens=task_tokens)


def _skill_token_matches(*, token: str, task_tokens: set[str]) -> bool:
    if token in task_tokens:
        return True
    if token.endswith("s") and token[:-1] in task_tokens:
        return True
    if f"{token}s" in task_tokens:
        return True
    if token.endswith("e") and f"{token[:-1]}ion" in task_tokens:
        return True
    if token.endswith("ate") and f"{token[:-3]}ation" in task_tokens:
        return True
    return False


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
