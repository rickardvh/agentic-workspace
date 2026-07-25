"""Shared selector request validation for Agentic Workspace command surfaces."""

from __future__ import annotations

import copy
import json
from typing import Any

_MAX_SELECTOR_COUNT = 32
_MAX_SELECTOR_BYTES = 256
_MAX_SELECTOR_REQUEST_BYTES = 512
_MAX_SELECTOR_ERROR_ENVELOPE_BYTES = 6000
_MAX_SELECTOR_ERROR_ITEMS = 8
_SELECTOR_SUGGESTION_LIMIT = 1


_SELECTOR_DESCRIPTORS_BY_COMMAND: dict[str, tuple[str, ...]] = {
    "start": (
        "action_signals",
        "next_safe_action",
        "decision_packet",
        "communication_contract",
        "skills",
        "context",
        "context.primary_action",
        "context.route_decision",
        "workflow_sufficiency",
        "continuation_state",
        "current_decision",
        "message_economy",
        "evidence_bundle",
        "local_footprint",
        "installed_state_compatibility",
        "routine_work_context",
        "selector_inventory",
        "acceptance",
        "issue_reference_intent",
        "local_chat_checkpoint",
        "work_threads",
        "invoked_cli_identity",
        "active_state_summary",
        "immediate_next_allowed_action",
        "planning_safety_gate",
        "planning_route_decision",
        "task_posture_packet",
        "memory_decision_packet",
        "open_issue_intake",
        "next",
        "sufficiency",
        "proof_narrowness",
        "proof_route_strategy_decision",
        "proof_route_strategy_preservation",
        "proof_route_strategy_consumer_gate",
        "context_router.rule",
    ),
    "implement": (
        "next",
        "proof",
        "proof.proof_obligations",
        "proof.proof_route_maintenance",
        "proof.proof_route_strategy_preservation",
        "proof.proof_route_strategy_claim_gate",
        "proof_route_strategy_consumer_gate",
        "proof.runtime_source_edit_review",
        "proof.runtime_symbol_working_set",
        "proof_route_strategy_preservation",
        "context",
        "context.delegation_decision",
        "context.delegation_decision.required_next_action",
        "context.delegation_decision.delegation_next_step.must_report_if_not_run",
        "context.delegation_decision.effort_guidance.cost_posture",
        "context.plan_delegation_packet",
        "context.workflow_sufficiency",
        "context.scope",
        "context.guidance",
        "task_contract",
        "change_impact",
        "generated_surface_trust",
        "routine_work_context",
        "reuse_pressure",
        "architecture_principles",
        "assurance_requirements",
        "verification",
        "requirement_grounding",
        "plan_delegation_packet",
        "test_strategy_check",
        "active_intent_contract",
        "intent_satisfaction_matrix",
        "selector_inventory",
        "completion_options",
        "decision_point_intent_confirmation",
        "planning_safety_gate",
        "work_threads",
    ),
    "summary": (
        "todo",
        "todo.active_count",
        "target_root",
        "planning_revision",
        "planning_record",
        "execplans",
        "planning_surface_health",
        "execution_readiness",
        "current_execution_pressure",
        "continuation_view",
        "fresh_session_digest",
        "decision_packet",
        "decision_point_carry_status",
        "planning_route_decision",
        "closeout_trust_inspection",
        "decomposition",
        "lanes",
        "residue_governance",
        "roadmap",
        "detail_commands",
        "warning_count",
        "memory_consult",
        "selector_inventory",
    ),
    "proof": (
        "proof_route_strategy_decision",
        "proof_route_escalation_gate",
        "proof_route_strategy_preservation",
        "proof_route_strategy_claim_gate",
        "proof_route_strategy_consumer_gate",
        "proof_receipt_reconciliation",
        "proof_receipt_bridge",
        "proof_closeout_summary",
        "proof_narrowness",
        "proof_decision",
        "proof_route_maintenance",
        "proof_next_decision",
        "proof_obligations",
        "architecture_principles",
        "verification",
        "requirement_grounding",
        "test_strategy_check",
        "validation_plan",
        "generated_cli_freshness",
        "cli_authority_review",
        "required_commands",
        "selected_lanes",
        "selected_commands",
        "manual_verification",
        "next",
        "sufficiency",
        "route_refinement_required",
        "focused_route_coverage_audit",
        "release_proof_profile",
        "domain_proof_route_inventory_audit",
        "completion_options",
        "selector_inventory",
    ),
    "report": (
        "kind",
        "status",
        "answer",
        "report",
        "output_contract",
        "workflow_obligations",
        "repo_friction",
        "decision_packet",
        "selector_inventory",
    ),
    "config": (
        "workspace",
        "workspace.enabled",
        "workspace.enabled_modules",
        "workspace.improvement_latitude",
        "workspace.optimization_bias",
        "workspace.optimization_bias_source",
        "workspace.workflow_obligations",
        "warnings",
        "target",
        "config_path",
        "modules",
        "mixed_agent",
        "mixed_agent.runtime_resolution",
        "assurance",
        "config_enforcement",
        "config_effect_audit",
        "cli_compatibility",
        "selector_inventory",
    ),
    "doctor": (
        "command",
        "target",
        "health",
        "warnings",
        "warnings_count",
        "needs_review_count",
        "repair_actions_count",
        "manual_review_actions_count",
        "next_action",
        "installed_modules",
        "reports",
        "repair_plan",
        "actionability",
        "installed_state_summary",
        "installed_state_compatibility",
        "payload_closure_summary",
        "payload_closure_plan",
        "decision_point_carry_status",
        "selector_inventory",
    ),
    "status": (
        "command",
        "target",
        "health",
        "warnings",
        "warnings_count",
        "needs_review_count",
        "repair_actions_count",
        "manual_review_actions_count",
        "next_action",
        "installed_modules",
        "reports",
        "repair_plan",
        "actionability",
        "installed_state_summary",
        "payload_closure_summary",
        "payload_closure_plan",
        "decision_point_carry_status",
        "selector_inventory",
    ),
    "defaults": (
        "kind",
        "answer",
        "answer.command",
        "section",
        "sections",
        "startup",
        "startup.canonical_doc",
        "root_cli_authority",
        "root_cli_authority.command",
        "workspace",
        "proof_selection",
        "improvement_intake",
        "optimization_bias",
        "selector_inventory",
    ),
}

_KNOWN_OPTIONAL_SELECTORS_BY_COMMAND: dict[str, set[str]] = {
    "start": {"issue_reference_intent"},
}

_DEPRECATED_SELECTOR_REPLACEMENTS_BY_COMMAND: dict[str, dict[str, str]] = {
    "config": {
        "workspace.feature_tier": "workspace.enabled_modules",
    },
}


def _selector_tokens(select: Any) -> list[str]:
    tokens, _ = _selector_request(select=select, source_command="")
    return tokens


def _selector_request(*, select: Any, source_command: str) -> tuple[list[str], dict[str, Any] | None]:
    if not select:
        return ([], None)
    tokens: list[str] = []
    seen: set[str] = set()
    requested_count = 0
    selector_request_bytes = 0
    raw_selectors = select if isinstance(select, (list, tuple, set)) else [select]
    for raw_selector in raw_selectors:
        for raw in str(raw_selector).split(","):
            token = raw.strip()
            if not token:
                continue
            requested_count += 1
            token_bytes = len(token.encode("utf-8", errors="replace"))
            if requested_count > _MAX_SELECTOR_COUNT:
                return (
                    tokens,
                    _selector_request_validation_error(
                        source_command=source_command,
                        reason="too-many-selectors",
                        selectors=tokens,
                        requested_selector_count=requested_count,
                        selector_request_bytes=selector_request_bytes,
                        selector_index=requested_count - 1,
                        offending_selector=token,
                    ),
                )
            if token_bytes > _MAX_SELECTOR_BYTES:
                return (
                    tokens,
                    _selector_request_validation_error(
                        source_command=source_command,
                        reason="selector-too-long",
                        selectors=tokens,
                        requested_selector_count=requested_count,
                        selector_request_bytes=selector_request_bytes + token_bytes,
                        selector_index=requested_count - 1,
                        selector_bytes=token_bytes,
                        offending_selector=token,
                    ),
                )
            if selector_request_bytes + token_bytes > _MAX_SELECTOR_REQUEST_BYTES:
                return (
                    tokens,
                    _selector_request_validation_error(
                        source_command=source_command,
                        reason="selector-request-too-large",
                        selectors=tokens,
                        requested_selector_count=requested_count,
                        selector_request_bytes=selector_request_bytes + token_bytes,
                        selector_index=requested_count - 1,
                        offending_selector=token,
                    ),
                )
            selector_request_bytes += token_bytes
            if token in seen:
                continue
            tokens.append(token)
            seen.add(token)
    return (tokens, None)


def _field_by_path(payload: Any, path: str) -> tuple[bool, Any]:
    current = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        if isinstance(current, list):
            try:
                current = current[int(part)]
                continue
            except (ValueError, IndexError):
                return (False, None)
        return (False, None)
    return (True, copy.deepcopy(current))


def _field_path_exists(payload: Any, path: str) -> bool:
    current = payload
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        if isinstance(current, list):
            try:
                current = current[int(part)]
                continue
            except (ValueError, IndexError):
                return False
        return False
    return True


def _bounded_selector_descriptor_for_payload(payload: dict[str, Any]) -> list[str]:
    selectors: list[str] = []

    def visit(value: Any, prefix: str = "") -> None:
        if not isinstance(value, dict):
            return
        for key, nested in value.items():
            if not isinstance(key, str) or not key.strip():
                continue
            selector = f"{prefix}.{key}" if prefix else key
            selectors.append(selector)
            if isinstance(nested, dict):
                visit(nested, selector)

    visit(payload)
    return selectors


def _selector_descriptor_for_command(source_command: str) -> list[str]:
    return list(_SELECTOR_DESCRIPTORS_BY_COMMAND.get(source_command, ()))


def _selector_inventory_command(source_command: str) -> str:
    return f"agentic-workspace {source_command} --target . --select selector_inventory --format json"


def _known_optional_selector_absent(*, source_command: str, selector: str) -> bool:
    known = _KNOWN_OPTIONAL_SELECTORS_BY_COMMAND.get(source_command, set())
    return selector in known


def _replacement_for_deprecated_selector(*, source_command: str, selector: str) -> str | None:
    return _DEPRECATED_SELECTOR_REPLACEMENTS_BY_COMMAND.get(source_command, {}).get(selector)


def _declared_selector_for_command(*, source_command: str, selector: str) -> bool:
    available = _selector_descriptor_for_command(source_command)
    return selector in available


def _selector_suggestions(*, unknown: str, available: list[str], limit: int = _SELECTOR_SUGGESTION_LIMIT) -> list[str]:
    unknown_root = unknown.split(".", 1)[0]
    suggestions: list[str] = []
    for selector in available:
        if selector == unknown:
            continue
        selector_root = selector.split(".", 1)[0]
        if selector_root == unknown_root or selector.startswith(unknown) or unknown.startswith(selector_root):
            suggestions.append(selector)
        if len(suggestions) >= limit:
            break
    return suggestions


def _selector_replacements_payload(*, source_command: str, selectors: list[str]) -> dict[str, str]:
    replacements: dict[str, str] = {}
    for selector in selectors:
        replacement = _replacement_for_deprecated_selector(source_command=source_command, selector=selector)
        if replacement:
            replacements[selector] = replacement
        if len(replacements) >= _MAX_SELECTOR_ERROR_ITEMS:
            break
    return replacements


def _selector_validation_error_from_available(
    *, available: list[str], selectors: list[str], missing: list[str], source_command: str
) -> dict[str, Any]:
    sample = list(dict.fromkeys(selector for selector in available if isinstance(selector, str) and selector.strip()))[:8]
    bounded_selectors = selectors[:_MAX_SELECTOR_ERROR_ITEMS]
    bounded_missing = missing[:_MAX_SELECTOR_ERROR_ITEMS]
    suggestions = {
        selector: matches for selector in bounded_missing if (matches := _selector_suggestions(unknown=selector, available=available))
    }
    replacement_selectors = _selector_replacements_payload(source_command=source_command, selectors=missing)
    inventory_command = _selector_inventory_command(source_command)
    payload: dict[str, Any] = {
        "kind": "agentic-workspace/selector-validation-error/v1",
        "status": "invalid-selector",
        "source_command": source_command,
        "requested_selectors": bounded_selectors,
        "requested_selector_count": len(selectors),
        "requested_selector_omitted_count": max(0, len(selectors) - len(bounded_selectors)),
        "unknown_selectors": bounded_missing,
        "unknown_selector_count": len(missing),
        "unknown_selector_omitted_count": max(0, len(missing) - len(bounded_missing)),
        "selector_inventory": {
            "status": "omitted-from-validation-error",
            "available_count": len(available),
            "sample": sample,
            "sample_limit": 8,
            "discovery_command": inventory_command,
            "inventory_command": inventory_command,
            "absence_state": "hidden_behind_detail_route",
            "rule": "Unknown selectors return a bounded validation envelope; full selector inventory is available only through an explicit detail route.",
        },
        "suggestions": suggestions,
        "selector_budget": _selector_budget_payload(),
        "validation_rule": "Selector requests are exact: nested selectors must be declared before payload construction.",
    }
    if replacement_selectors:
        payload["deprecated_selectors"] = list(replacement_selectors)
        payload["replacement_selectors"] = replacement_selectors
        payload["replacement_rule"] = "Deprecated selectors are rejected atomically with a bounded replacement hint."
    return _fit_selector_error_envelope(payload)


def _selector_budget_payload() -> dict[str, int]:
    return {
        "max_selectors": _MAX_SELECTOR_COUNT,
        "max_selector_bytes": _MAX_SELECTOR_BYTES,
        "max_selector_request_bytes": _MAX_SELECTOR_REQUEST_BYTES,
        "max_error_envelope_bytes": _MAX_SELECTOR_ERROR_ENVELOPE_BYTES,
        "max_error_items": _MAX_SELECTOR_ERROR_ITEMS,
    }


def _selector_request_validation_error(
    *,
    source_command: str,
    reason: str,
    selectors: list[str],
    requested_selector_count: int,
    selector_request_bytes: int,
    selector_index: int | None = None,
    selector_bytes: int | None = None,
    offending_selector: str = "",
) -> dict[str, Any]:
    inventory_command = _selector_inventory_command(source_command)
    payload: dict[str, Any] = {
        "kind": "agentic-workspace/selector-validation-error/v1",
        "status": "invalid-selector-request",
        "source_command": source_command,
        "reason": reason,
        "requested_selectors": selectors[:_MAX_SELECTOR_ERROR_ITEMS],
        "requested_selector_count": requested_selector_count,
        "requested_selector_omitted_count": max(0, requested_selector_count - _MAX_SELECTOR_ERROR_ITEMS),
        "selector_request_bytes": selector_request_bytes,
        "selector_inventory": {
            "status": "omitted-from-validation-error",
            "inventory_command": inventory_command,
            "discovery_command": inventory_command,
            "rule": "Selector request limits are enforced before command payload construction; use the inventory route for valid selectors.",
        },
        "selector_budget": _selector_budget_payload(),
        "validation_rule": "Selector requests are bounded before descriptor lookup or payload construction.",
    }
    if selector_index is not None:
        payload["selector_index"] = selector_index
        payload["limit_contributor"] = "selector_index"
    if selector_bytes is not None:
        payload["selector_bytes"] = selector_bytes
        payload["limit_contributor"] = "selector_bytes"
    if offending_selector:
        payload["offending_selector"] = offending_selector[:120]
    if reason == "selector-request-too-large":
        payload["limit_contributor"] = "selector_request_bytes"
    if reason == "too-many-selectors":
        payload["limit_contributor"] = "requested_selector_count"
    return _fit_selector_error_envelope(payload)


def _fit_selector_error_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    if _selector_error_envelope_bytes(payload) <= _MAX_SELECTOR_ERROR_ENVELOPE_BYTES:
        return payload
    payload["suggestions"] = {}
    if _selector_error_envelope_bytes(payload) <= _MAX_SELECTOR_ERROR_ENVELOPE_BYTES:
        return payload
    payload["requested_selectors"] = payload.get("requested_selectors", [])[:3]
    payload["unknown_selectors"] = payload.get("unknown_selectors", [])[:3]
    inventory = payload.get("selector_inventory")
    if isinstance(inventory, dict):
        inventory["sample"] = inventory.get("sample", [])[:3]
    if _selector_error_envelope_bytes(payload) <= _MAX_SELECTOR_ERROR_ENVELOPE_BYTES:
        return payload
    payload["requested_selectors"] = []
    payload["unknown_selectors"] = []
    if isinstance(inventory, dict):
        inventory["sample"] = []
    payload["truncated_to_budget"] = True
    return payload


def _selector_error_envelope_bytes(payload: dict[str, Any]) -> int:
    rendered = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return len(rendered.encode("utf-8"))


def _selector_validation_error(*, payload: dict[str, Any], selectors: list[str], missing: list[str], source_command: str) -> dict[str, Any]:
    return _selector_validation_error_from_available(
        available=_bounded_selector_descriptor_for_payload(payload),
        selectors=selectors,
        missing=missing,
        source_command=source_command,
    )


def _selector_inventory_value(*, source_command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    available = _selector_descriptor_for_command(source_command)
    if not available and payload is not None:
        available = _bounded_selector_descriptor_for_payload(payload)
    return {
        "kind": "agentic-workspace/selector-inventory/v1",
        "source_command": source_command,
        "available_count": len(available),
        "selectors": available,
        "rule": "Explicit selector inventory is available through --select selector_inventory; validation errors include only a bounded sample.",
    }


def _selected_payload_for_values(*, values: dict[str, Any], source_command: str, missing: list[str] | None = None) -> dict[str, Any]:
    selected_payload_paths = {
        selector: f"values.{selector}" if selector.isidentifier() else f"values[{json.dumps(selector)}]" for selector in values
    }
    selected: dict[str, Any] = {
        "kind": "agentic-workspace/selected-output/v1",
        "source_command": source_command,
        "values": values,
        "payload_locations": {
            "kind": "agentic-workspace/output-wrapper-locations/v1",
            "primary_payload_field": "values",
            "selected_payload_paths": selected_payload_paths,
            "rule": "Selected field output stores payloads under values keyed by the selector string; compact report/proof answers store their payload under answer.",
        },
    }
    if missing:
        selected["missing"] = missing
    return selected


def _selector_inventory_selected_payload(*, select: str | None, source_command: str) -> dict[str, Any] | None:
    selectors, request_error = _selector_request(select=select, source_command=source_command)
    if request_error is not None:
        return request_error
    if selectors != ["selector_inventory"]:
        return None
    return _selected_payload_for_values(
        values={"selector_inventory": _selector_inventory_value(source_command=source_command)},
        source_command=source_command,
    )


def _selector_prevalidation_error(*, select: str | None, source_command: str) -> dict[str, Any] | None:
    selectors, request_error = _selector_request(select=select, source_command=source_command)
    if request_error is not None:
        return request_error
    if not selectors:
        return None
    available = _selector_descriptor_for_command(source_command)
    if not available:
        return None
    unknown = []
    for selector in selectors:
        if selector in available:
            continue
        if _known_optional_selector_absent(source_command=source_command, selector=selector):
            continue
        unknown.append(selector)
    if not unknown:
        return None
    return _selector_validation_error_from_available(
        available=available,
        selectors=selectors,
        missing=unknown,
        source_command=source_command,
    )


def _select_payload_fields(payload: dict[str, Any], *, select: str | None, source_command: str) -> dict[str, Any]:
    selectors, request_error = _selector_request(select=select, source_command=source_command)
    if request_error is not None:
        return request_error
    unknown: list[str] = []
    missing: list[str] = []
    for selector in selectors:
        if selector == "selector_inventory":
            continue
        if _field_path_exists(payload, selector):
            continue
        if _known_optional_selector_absent(source_command=source_command, selector=selector) or _declared_selector_for_command(
            source_command=source_command, selector=selector
        ):
            missing.append(selector)
        else:
            unknown.append(selector)
    if unknown:
        return _selector_validation_error(payload=payload, selectors=selectors, missing=unknown, source_command=source_command)
    values: dict[str, Any] = {}
    for selector in selectors:
        if selector == "selector_inventory":
            values[selector] = _selector_inventory_value(source_command=source_command, payload=payload)
            continue
        found, value = _field_by_path(payload, selector)
        if found:
            values[selector] = value
    return _selected_payload_for_values(values=values, source_command=source_command, missing=missing)
