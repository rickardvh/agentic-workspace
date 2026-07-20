"""Generated-surface trust runtime packet helpers.

This module owns generated-surface trust projections extracted from
``workspace_runtime_primitives`` while preserving the old private import names.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, overload

from agentic_workspace.config import DEFAULT_AGENT_INSTRUCTIONS_FILE
from agentic_workspace.contract_tooling import authority_markers_manifest, proof_selection_rules_manifest

_AUTHORITY_MARKERS = authority_markers_manifest()
_PROOF_SELECTION_RULES = proof_selection_rules_manifest()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _selector_tokens(select: str | None) -> list[str]:
    if not select:
        return []
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in select.split(","):
        token = raw.strip()
        if not token or token in seen:
            continue
        tokens.append(token)
        seen.add(token)
    return tokens


def _normalize_changed_paths(paths: list[str]) -> list[str]:
    normalized: list[str] = []
    for path_text in paths:
        for raw_part in str(path_text).split(","):
            stripped = raw_part.strip()
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


def _authority_marker_policy_by_id() -> dict[str, dict[str, Any]]:
    return {
        str(marker.get("id", "")): marker
        for marker in _list_payload(_AUTHORITY_MARKERS.get("markers"))
        if isinstance(marker, dict) and marker.get("id")
    }


def _authority_marker_canonical_source(*, marker: dict[str, Any], normalized: str) -> str:
    canonical_source = str(marker.get("canonical_source", "")).strip()
    if canonical_source:
        return canonical_source
    if normalized.startswith("src/agentic_workspace/contracts/schemas/"):
        return "src/agentic_workspace/contracts/schemas"
    if normalized.startswith("docs/reference/"):
        return "src/agentic_workspace/contracts/schemas"
    return ""


def _authority_marker_payload(*, marker_id: str, normalized: str) -> dict[str, Any]:
    marker = _authority_marker_policy_by_id()[marker_id]
    return {
        "path": normalized,
        "authority": marker["authority"],
        "canonical_source": _authority_marker_canonical_source(marker=marker, normalized=normalized),
        "safe_to_edit": marker["safe_to_edit"],
        "refresh_command": marker["refresh_command"],
    }


def _authority_marker_for_path(path_text: str, *, agent_instructions_file: str = DEFAULT_AGENT_INSTRUCTIONS_FILE) -> dict[str, Any]:
    normalized_paths = _normalize_changed_paths([path_text])
    normalized = normalized_paths[0] if normalized_paths else path_text
    if normalized == agent_instructions_file:
        return _authority_marker_payload(marker_id="root-agent-instructions", normalized=normalized)
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


def _cli_authority_classification_for_path(changed_path: str) -> dict[str, Any] | None:
    for classification in _list_payload(_as_dict(_PROOF_SELECTION_RULES.get("cli_authority")).get("classifications")):
        if not isinstance(classification, dict):
            continue
        exact_matches = set(classification.get("exact", []))
        prefixes = tuple(classification.get("prefixes", []))
        if changed_path in exact_matches or changed_path.startswith(prefixes):
            return classification
    return None


def _generated_surface_validation_command(*, path: str, proof: dict[str, Any]) -> str:
    commands = [str(command) for command in _list_payload(proof.get("required_commands")) if str(command).strip()]
    if path.startswith("docs/reference/"):
        return next((command for command in commands if "schema-reference-docs" in command), "make schema-reference-docs")
    if path.startswith("generated/") or path.startswith("command_generation/"):
        return next(
            (command for command in commands if "check_generated_command_packages.py" in command),
            "uv run python scripts/check/check_generated_command_packages.py",
        )
    return next(iter(commands), "")


def _generated_surface_source_status(*, target_root: Path, canonical_source: str) -> str:
    if not canonical_source:
        return "unknown"
    source_paths = [part.strip() for part in canonical_source.split("+") if part.strip()]
    existing: list[str] = []
    missing: list[str] = []
    for source_path in source_paths:
        if " " in source_path or not any(separator in source_path for separator in ("/", "\\")):
            continue
        if (target_root / source_path).exists():
            existing.append(source_path)
        else:
            missing.append(source_path)
    if missing:
        return "missing"
    if existing:
        return "present"
    return "not-checked"


@overload
def _command_with_cli_invoke(*, command: str, cli_invoke: str) -> str: ...


@overload
def _command_with_cli_invoke(*, command: None, cli_invoke: str) -> None: ...


def _command_with_cli_invoke(*, command: str | None, cli_invoke: str) -> str | None:
    if command is None:
        return None
    if command == "agentic-workspace" or command.startswith("agentic-workspace "):
        return f"{cli_invoke}{command.removeprefix('agentic-workspace')}"
    if command == "agentic-planning" or command.startswith("agentic-planning "):
        mapped = command.replace("agentic-planning ", "agentic-workspace planning ", 1)
        return _command_with_cli_invoke(command=mapped, cli_invoke=cli_invoke)
    if command == "agentic-memory" or command.startswith("agentic-memory "):
        mapped = command.replace("agentic-memory ", "agentic-workspace memory ", 1)
        return _command_with_cli_invoke(command=mapped, cli_invoke=cli_invoke)
    return command


def _generated_surface_trust_path_payload(*, target_root: Path, path: str, proof: dict[str, Any], cli_invoke: str) -> dict[str, Any] | None:
    def clean_text(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    normalized = path.replace("\\", "/").strip("/")
    classification = _cli_authority_classification_for_path(normalized)
    authority_marker = _authority_marker_for_path(normalized, agent_instructions_file=DEFAULT_AGENT_INSTRUCTIONS_FILE)
    is_schema_reference = normalized.startswith("docs/reference/")
    is_generated = normalized.startswith("generated/") or is_schema_reference
    if not is_generated and classification is None:
        return None
    role = str(classification.get("role", "generated-doc") if classification else "generated-doc" if is_schema_reference else "generated")
    canonical_source = clean_text(classification.get("source_contract") if classification else authority_marker.get("canonical_source"))
    refresh_command = clean_text(classification.get("regeneration_path") if classification else authority_marker.get("refresh_command"))
    direct_edit_allowed = bool(classification.get("direct_edit_allowed", False)) if classification else False
    direct_edit_policy = clean_text(classification.get("edit_policy") if classification else "")
    if is_schema_reference:
        canonical_source = "src/agentic_workspace/contracts/schemas"
        refresh_command = "make render-schema-reference"
        direct_edit_policy = "Do not hand-edit generated schema reference docs; edit the source schema and rerender."
    if not direct_edit_policy:
        direct_edit_policy = "Do not hand-edit generated surfaces when a canonical source or refresh command exists."
    validation_command = _generated_surface_validation_command(path=normalized, proof=proof)
    source_status = _generated_surface_source_status(target_root=target_root, canonical_source=canonical_source)
    freshness_status = "validation-required"
    if not refresh_command or source_status == "missing":
        freshness_status = "missing-source-or-refresh-command"
    refresh = _command_with_cli_invoke(command=refresh_command, cli_invoke=cli_invoke) if refresh_command else ""
    validation = _command_with_cli_invoke(command=validation_command, cli_invoke=cli_invoke) if validation_command else ""
    resolution_commands = list(dict.fromkeys(command for command in (refresh, validation) if command))
    return {
        "kind": "generated-surface-trust-item/v1",
        "path": normalized,
        "classification_id": str(classification.get("id", "")) if classification else "generated-reference-doc",
        "role": role,
        "canonical_source": canonical_source,
        "canonical_source_status": source_status,
        "freshness_status": freshness_status,
        "freshness_checked_by_implement": False,
        "refresh_command": refresh,
        "validation_command": validation,
        "direct_edit_allowed": direct_edit_allowed,
        "direct_edit_policy": direct_edit_policy,
        "action_effect": {
            "force": "required_before_claim" if not direct_edit_allowed or freshness_status != "validated" else "advisory",
            "allowed_now": "edit-canonical-source-refresh-and-validate-generated-surface",
            "blocked_until_reconciled": ["claim-generated-surface-fresh", "claim-task-complete"]
            if not direct_edit_allowed or freshness_status != "validated"
            else [],
            "claim_boundary": (
                "do-not-claim-generated-output-fresh-until-refresh-and-validation-pass"
                if refresh or validation
                else "do-not-claim-generated-output-fresh-until-canonical-source-or-refresh-route-is-restored"
            ),
            "resolution_selector": "generated_surface_trust",
            "resolution_command": resolution_commands[0] if resolution_commands else "",
            "resolution_commands": resolution_commands,
        },
    }


def _generated_surface_trust_payload(
    *, target_root: Path, changed_paths: list[str], proof: dict[str, Any], cli_invoke: str
) -> dict[str, Any]:
    items = [
        item
        for path in changed_paths
        for item in [_generated_surface_trust_path_payload(target_root=target_root, path=path, proof=proof, cli_invoke=cli_invoke)]
        if item is not None
    ]
    blocked_paths = [item["path"] for item in items if not item["direct_edit_allowed"]]
    resolution_commands = list(
        dict.fromkeys(
            command
            for item in items
            for command in _list_payload(_as_dict(item.get("action_effect")).get("resolution_commands"))
            if str(command).strip()
        )
    )
    action_effect = {
        "force": "required_before_claim" if items else "advisory",
        "allowed_now": "continue-implementation-but-refresh-generated-surfaces-before-claim" if items else "continue-implementation",
        "blocked_until_reconciled": ["claim-generated-surfaces-fresh", "claim-task-complete"] if items else [],
        "claim_boundary": (
            "generated-surface-freshness-must-be-reconciled-before-completion-claim" if items else "no-generated-surface-freshness-warning"
        ),
        "resolution_selector": "generated_surface_trust",
        "resolution_commands": resolution_commands,
    }
    return {
        "kind": "agentic-workspace/generated-surface-trust/v1",
        "status": "present" if items else "not-applicable",
        "changed_path_count": len(items),
        "items": items,
        "direct_edit_blocked_paths": blocked_paths,
        "action_effect": action_effect,
        "rule": (
            "Generated surfaces are derived artifacts. Edit the canonical source first, refresh the generated output, "
            "and run the validation command before trusting freshness."
        ),
        "detail_selector": "generated_surface_trust",
    }


def _selector_requests_generated_surface_trust(select: str | None) -> bool:
    return any(token == "generated_surface_trust" or token.startswith("generated_surface_trust.") for token in _selector_tokens(select))


def _generated_cli_freshness_payload(
    *,
    changed_paths: list[str],
    selected_lanes: list[dict[str, Any]],
    required_commands: list[str],
) -> dict[str, Any] | None:
    lane_ids = [str(lane.get("id", "")) for lane in selected_lanes if isinstance(lane, dict)]
    relevant_lane_ids = [
        lane_id
        for lane_id in lane_ids
        if lane_id in {"generated_command_packages", "cli_authority", "verification:generated_adapter_conformance"}
    ]
    related_commands = [
        command
        for command in required_commands
        if "check_generated_command_packages.py" in command or "generate_command_packages.py" in command
    ]
    if not relevant_lane_ids and not related_commands:
        return None
    freshness_check = "uv run python scripts/generate/generate_command_packages.py --check"
    refresh_command = "uv run python scripts/generate/generate_command_packages.py"
    has_typescript_change = any("/typescript/" in path.replace("\\", "/") for path in changed_paths)
    has_python_change = any("/python/" in path.replace("\\", "/") for path in changed_paths)
    preferred_validation_markers = (
        ("--require-node", "--conformance --require-node")
        if has_typescript_change and not has_python_change
        else ("--python-conformance", "--python-docker-conformance", "")
        if has_python_change and not has_typescript_change
        else ("--require-node", "--python-conformance", "")
    )

    def matches_preferred_marker(command: str, marker: str) -> bool:
        if "check_generated_command_packages.py" not in command:
            return False
        if not marker:
            return True
        if marker == "--require-node":
            return command.endswith("--require-node") and "--conformance" not in command
        return marker in command

    validation_command = next(
        (command for marker in preferred_validation_markers for command in related_commands if matches_preferred_marker(command, marker)),
        "uv run python scripts/check/check_generated_command_packages.py",
    )
    obligation = "required" if related_commands else "advisory"
    return {
        "kind": "agentic-workspace/generated-cli-freshness/v1",
        "status": obligation,
        "triggered_by": changed_paths,
        "selected_lanes": relevant_lane_ids,
        "freshness_check_command": freshness_check,
        "refresh_command": refresh_command,
        "validation_command": validation_command,
        "required_commands": related_commands,
        "obligation": obligation,
        "generated_target_parity": {
            "kind": "agentic-workspace/generated-target-parity/v1",
            "status": "required" if obligation == "required" else "advisory",
            "target_families": ["python", "typescript"],
            "freshness_evidence": [
                "scripts/generate/generate_command_packages.py --check compares rendered outputs for all generated Python and TypeScript package targets without writing files",
                "scripts/check/check_generated_command_packages.py performs static generated-package proof across Python and TypeScript surfaces",
            ],
            "stale_detection": {
                "python": "generated/*/python/** outputs must match command-generation render output",
                "typescript": "generated/*/typescript/** outputs must match command-generation render output",
            },
            "claim_rule": (
                "Do not claim generated CLI freshness from Python-only proof; relevant generated CLI proof must name "
                "both Python and TypeScript generated targets or record why one family is not applicable."
            ),
        },
        "rule": (
            "Generated CLI freshness is relevant only for generated command package surfaces. "
            "Run the check path before trusting generated CLI output; refresh only when the check reports stale output."
        ),
    }


def _tiny_surface_compatibility_review(changed_paths: list[str]) -> dict[str, Any]:
    risky_paths = [
        path
        for path in changed_paths
        if path
        in {
            "src/agentic_workspace/workspace_runtime_primitives.py",
            "src/agentic_workspace/contracts/schemas/startup_context.schema.json",
            "src/agentic_workspace/contracts/schemas/implementer_context.schema.json",
        }
        or path.startswith("tests/test_workspace_start_preflight_cli.py")
        or path.startswith("tests/test_workspace_implement_cli.py")
        or path.startswith("tests/test_workspace_summary_cli.py")
    ]
    if not risky_paths:
        return {"status": "not-applicable"}
    return {
        "kind": "agentic-workspace/tiny-surface-compatibility-review/v1",
        "status": "required",
        "changed_paths": risky_paths,
        "rule": "New facts usually belong behind selector, verbose, or nested context unless they are essential to the tiny next action.",
        "risk": "Tiny/default start, implement, preflight, and summary payloads are weak-agent startup contracts with size and shape budgets.",
        "expected_proof": [
            "focused tiny/default payload shape tests",
            "size-budget assertions when existing tests define one",
            "selector/full-surface assertion for any new diagnostic field",
        ],
    }
