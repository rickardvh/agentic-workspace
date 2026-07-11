"""Proof, verification, and closeout runtime packet builders.

This module owns proof and closeout runtime packet helpers while the old
monolith keeps compatibility re-exports for legacy private import names.
"""

from __future__ import annotations

import copy
import fnmatch
import hashlib
import json
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

from repo_verification_bootstrap.runtime_primitives import (
    VerificationUsageError,
)
from repo_verification_bootstrap.runtime_primitives import (
    verification_report_payload as verification_module_report_payload,
)

from agentic_workspace import config as config_lib
from agentic_workspace._schema import ModuleDescriptor
from agentic_workspace.config import DEFAULT_ASSURANCE_LEVEL, DEFAULT_CLI_INVOKE, WorkspaceConfig, WorkspaceUsageError
from agentic_workspace.current_work_context import resolve_current_work_context
from agentic_workspace.runtime_source_review import runtime_source_edit_review_for_changed_paths
from agentic_workspace.runtime_symbol_working_set import runtime_symbol_working_set_for_changed_paths
from agentic_workspace.workspace_runtime_core import (
    _PROOF_EXECUTION_STATUSES,
    _PROOF_SELECTION_RULES,
    PROOF_RECEIPT_HISTORY_RELATIVE_PATH,
    PROOF_RECEIPT_RELATIVE_PATH,
    PROOF_ROUTE_HINTS_PATH,
    _active_planning_assurance_for_proof,
    _adapt_make_proof_command_for_target,
    _applicable_intent_status_payload,
    _apply_learned_route_hints_to_capabilities,
    _architecture_principles_payload,
    _assurance_item_state,
    _assurance_requirements_report_payload,
    _assurance_requirements_with_verification,
    _authority_boundary_payload,
    _changed_path_exists,
    _cli_authority_review_for_changed_paths,
    _closeout_intent_evidence_payload,
    _closeout_report_adoption_payload,
    _closeout_report_completeness_payload,
    _closeout_report_decision_review_payload,
    _closeout_report_final_response_rendering_payload,
    _closeout_report_profile_policy_payload,
    _closeout_report_review_compression_payload,
    _closeout_report_selected_review_mode,
    _closeout_report_traceability_rows,
    _completion_gate_payload,
    _confirm_learned_route_hints,
    _decision_point_source_revision_status,
    _dedupe,
    _defaults_payload,
    _direct_cli_edit_review_for_changed_paths,
    _docs_only_reduction_lane,
    _guidance_with_cli_invoke,
    _host_repo_learning_posture_payload,
    _intent_decision_projection,
    _intent_proof_prompt_payload,
    _issue_scope_evidence_payload,
    _lane_execution_metadata,
    _learned_proof_lanes_for_changed_paths,
    _learned_route_reliance_payload,
    _load_decision_point_forecast,
    _load_proof_route_hints,
    _load_workspace_config,
    _make_targets_without_negative_routes,
    _makefile_targets,
    _manual_verification_templates_for_intents,
    _missing_repo_path_references_in_command,
    _ordered_module_names,
    _package_json_scripts,
    _package_scripts_without_negative_routes,
    _parent_intent_status_payload,
    _project_roots_for_changed_paths,
    _proof_adequacy_payload,
    _proof_command_for_target,
    _proof_command_tier,
    _proof_command_tiers,
    _proof_completion_options,
    _proof_confidence_payload,
    _proof_execution_evidence_summary,
    _proof_intent_for_lane,
    _proof_kind_for_lane,
    _proof_next_decision_payload,
    _proof_route_decision_payload,
    _proof_route_explanation_payload,
    _proof_route_source_for_lane,
    _record_decision_point_confirmation,
    _requirement_grounding_payload,
    _routine_work_context_payload,
    _run_lifecycle_command,
    _shell_quote,
    _skill_behavior_impact_review_for_changed_paths,
    _split_validation_command,
    _subsystem_matches_for_changed_paths,
    _supplemental_proof_lanes_for_changed_paths,
    _surface_value_review_for_changed_paths,
    _target_proof_capabilities,
    _test_strategy_check_payload,
    _tiny_action_effect,
    _tiny_required_proof_commands,
    _tiny_workflow_sufficiency,
    _transient_validation_retry_guidance,
    _validation_plan_for_proof,
    _workflow_obligation_closeout_contract_payload,
    _workflow_obligations_report_payload,
    _workflow_sufficiency_payload,
)
from agentic_workspace.workspace_runtime_generated_surface import (
    _as_dict,
    _cli_authority_classification_for_path,
    _command_with_cli_invoke,
    _generated_cli_freshness_payload,
    _list_payload,
    _tiny_surface_compatibility_review,
)
from agentic_workspace.workspace_runtime_planning import _active_planning_record_for_report_section


def _proof_lifecycle_command(*args: Any, **kwargs: Any) -> dict[str, Any]:
    generated_cli: Any = None
    try:
        from generated.workspace.python import cli as generated_cli
    except Exception:
        pass
    if generated_cli is not None:
        patched = getattr(generated_cli, "_run_lifecycle_command", None)
        if patched is not None and patched is not _run_lifecycle_command:
            return patched(*args, **kwargs)
    return _run_lifecycle_command(*args, **kwargs)


def _verification_report_payload(
    *,
    target_root: Path | None,
    changed_paths: list[str] | None = None,
    task_text: str | None = None,
    active_planning_record: dict[str, Any] | None = None,
    assurance_requirements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return verification_module_report_payload(
            target_root=target_root,
            changed_paths=changed_paths,
            task_text=task_text,
            active_planning_record=active_planning_record,
            assurance_requirements=assurance_requirements,
        )
    except VerificationUsageError as exc:
        raise WorkspaceUsageError(str(exc)) from exc


def _compact_tiny_intent_proof(intent_proof: Any) -> dict[str, Any]:
    if not isinstance(intent_proof, dict):
        return {}
    compact = dict(intent_proof)
    compact.pop("behavior_preservation_prompt", None)
    compact.pop("rule", None)
    for key in ("intended_behavior", "unproven_after_tests"):
        if compact.get(key) == []:
            compact.pop(key, None)
    return compact


def _compact_tiny_proof_narrowness(value: Any) -> dict[str, Any]:
    packet = value if isinstance(value, dict) else {}
    if not packet:
        return {}
    required_items = [item for item in _list_payload(packet.get("required")) if isinstance(item, dict)]
    trigger_items = [item for item in _list_payload(packet.get("expansion_triggers")) if isinstance(item, dict)]
    first_required = required_items[0] if required_items else {}
    first_trigger = trigger_items[0] if trigger_items else {}
    compact = {
        "status": packet.get("status", "unknown"),
        "expansion_trigger_lane": str(first_trigger.get("lane", "")) if first_trigger.get("lane") else "",
        "broad_suite_boundary_status": _as_dict(packet.get("broad_suite_boundary")).get("status", ""),
    }
    if first_required and packet.get("status") != "broad_required":
        compact["required_reason_sample"] = {
            "why_required": str(first_required.get("why_required", "")),
            "acceptance_boundary": first_required.get("acceptance_boundary", True),
        }
    return {key: payload for key, payload in compact.items() if payload not in ("", [], {}, None)}


def _include_tiny_proof_narrowness(value: Any) -> bool:
    packet = value if isinstance(value, dict) else {}
    status = str(packet.get("status", ""))
    if status == "broad_required":
        return True
    if status != "narrow_required":
        return False
    return any(
        isinstance(item, dict) and str(item.get("proof_kind", "")) != "diff-review" for item in _list_payload(packet.get("required"))
    )


def _compact_tiny_high_risk_overlay(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("status") != "active":
        return {}
    active = _as_dict(value.get("active"))
    return {
        "status": value.get("status"),
        "active_count": value.get("active_count", 0),
        "sections": {section: len(_list_payload(items)) for section, items in active.items() if _list_payload(items)},
        "authority_boundary": _as_dict(value.get("authority_boundary")).get("rule", ""),
        "detail_selector": "high_risk_overlay",
    }


def _compact_tiny_local_overlay(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("status") != "active":
        return {}
    active = _as_dict(value.get("active"))
    return {
        "status": value.get("status"),
        "active_count": value.get("active_count", 0),
        "ordinary_guidance_count": len(_list_payload(active.get("guidance"))),
        "authority_boundary": _as_dict(value.get("authority_boundary")).get("rule", ""),
        "detail_selector": "local_overlay",
    }


def _compact_tiny_proof_closeout_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    route = _as_dict(value.get("route"))
    sufficiency = _as_dict(value.get("sufficiency"))
    receipt_bridge = _as_dict(value.get("receipt_bridge"))
    route_maturity_detail = _as_dict(value.get("route_maturity"))
    changed_paths = [str(item) for item in _list_payload(value.get("changed_paths"))][:5]
    gap_count = len(_list_payload(value.get("remaining_gaps")))
    proof_count = len(_list_payload(value.get("proof_results")))
    route_name = str(route.get("name") or "none")
    route_maturity = str(route.get("maturity") or "unknown")
    route_source = str(route.get("source") or "unknown")
    human_summary = _short_tiny_text(
        f"Route {route_name} from {route_source} ({route_maturity}); proof_results={proof_count}; remaining_gaps={gap_count}.",
        limit=180,
    )
    compact_route_maturity = {"status": route_maturity_detail.get("status", "")}
    advisory_count = len(_list_payload(route_maturity_detail.get("advisories")))
    blocker_count = len(_list_payload(route_maturity_detail.get("blockers")))
    if advisory_count:
        compact_route_maturity["advisory_count"] = advisory_count
    if blocker_count:
        compact_route_maturity["blocker_count"] = blocker_count
    return {
        "kind": value.get("kind", "agentic-workspace/proof-closeout-summary/v1"),
        "status": value.get("status", ""),
        "changed_paths": changed_paths,
        "route": {key: route.get(key, "") for key in ("name", "maturity") if route.get(key)},
        "proof_result_count": proof_count,
        "remaining_gap_count": gap_count,
        "receipt_bridge": {
            key: receipt_bridge.get(key) for key in ("status", "missing_receipt_count", "detail_selector") if key in receipt_bridge
        },
        **({"route_maturity": compact_route_maturity} if compact_route_maturity["status"] not in {"", "not-applicable"} else {}),
        "sufficiency": {key: sufficiency.get(key, "") for key in ("status",) if sufficiency.get(key)},
        "human_summary": human_summary,
        "detail_selector": "proof_closeout_summary",
    }


def _compact_tiny_learned_proof_route_model(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    selected_routes = [
        {
            key: route.get(key)
            for key in ("id", "route_class", "maturity", "selected", "scope", "proof_classes", "override_semantics")
            if key in route
        }
        for route in _list_payload(value.get("selected_routes"))[:4]
        if isinstance(route, dict)
    ]
    fallback = _as_dict(value.get("fallback"))
    return {
        "kind": value.get("kind", "learned-proof-route-model/v1"),
        "status": value.get("status", "absent"),
        "route_classes": _list_payload(value.get("route_classes")),
        "selected_route_count": value.get("selected_route_count", 0),
        "selected_routes": selected_routes,
        "fallback": {key: fallback.get(key) for key in ("status", "reason", "manual_verification_required") if key in fallback},
        "proof_class_vocabulary": _list_payload(value.get("proof_class_vocabulary")),
        "override_rule": value.get("override_rule", ""),
        "repo_neutrality_rule": value.get("repo_neutrality_rule", ""),
        "detail_selector": "learned_proof_route_model",
    }


def _short_tiny_text(value: str, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 3)].rstrip()}..."


def _tiny_proof_payload(payload: dict[str, Any], *, cli_invoke: str = DEFAULT_CLI_INVOKE) -> dict[str, Any]:
    if payload.get("profile") == "compact-contract-answer/v1":
        answer = payload.get("answer", {})
        tiny_required_commands = _tiny_required_proof_commands(answer) if isinstance(answer, dict) else []
        include_intent_proof = False
        if isinstance(answer, dict) and answer.get("intent_proof"):
            required_for_intent = tiny_required_commands
            include_intent_proof = not required_for_intent or not all(command.startswith("git diff --") for command in required_for_intent)
        if isinstance(answer, dict) and isinstance(answer.get("proof_next_decision"), dict):
            next_decision = dict(answer["proof_next_decision"])
            next_decision["required_commands"] = tiny_required_commands
            next_decision.setdefault("target", payload.get("target"))
            next_decision.setdefault("selector", payload.get("selector", {}))
            next_decision.setdefault("sufficiency", _tiny_workflow_sufficiency(answer.get("sufficiency", {})))
            if answer.get("proof_route_decision"):
                route_decision = dict(answer["proof_route_decision"])
                route_decision.pop("next_action", None)
                route_decision.pop("required_commands", None)
                next_decision["proof_route_selection"] = route_decision
            if answer.get("proof_command_adjustments"):
                next_decision["proof_command_adjustments"] = answer["proof_command_adjustments"]
            if answer.get("proof_closeout_summary"):
                next_decision["proof_closeout_summary"] = _compact_tiny_proof_closeout_summary(answer["proof_closeout_summary"])
            if answer.get("learned_proof_route_model"):
                learned_route_model = _compact_tiny_learned_proof_route_model(answer["learned_proof_route_model"])
                if learned_route_model.get("status") != "absent":
                    next_decision["learned_proof_route_model"] = learned_route_model
            if answer.get("unavailable_proof_commands"):
                next_decision["unavailable_proof_commands"] = answer["unavailable_proof_commands"]
            if answer.get("target_proof_capabilities") and (
                answer.get("proof_command_adjustments") or answer.get("unavailable_proof_commands")
            ):
                next_decision["target_proof_capabilities"] = answer["target_proof_capabilities"]
            if answer.get("proof_strategy") and (answer.get("proof_command_adjustments") or answer.get("unavailable_proof_commands")):
                next_decision["proof_strategy"] = {
                    "kind": answer.get("proof_strategy", {}).get("kind"),
                    "selection_order": answer.get("proof_strategy", {}).get("selection_order", []),
                }
            next_decision["detail_command_template"] = _command_template_payload(
                command=next_decision.get(
                    "detail_command",
                    _command_with_cli_invoke(
                        command="agentic-workspace proof --verbose --changed <paths> --format json",
                        cli_invoke=cli_invoke,
                    ),
                ),
                placeholders={"paths": _list_payload(payload.get("selector", {}).get("changed"))},
                purpose="verbose proof drill-down after substituting the actual changed paths",
            )
            if include_intent_proof:
                next_decision["intent_proof"] = _compact_tiny_intent_proof(answer["intent_proof"])
            raw_proof_narrowness = answer.get("proof_narrowness")
            proof_narrowness = (
                _compact_tiny_proof_narrowness(raw_proof_narrowness) if _include_tiny_proof_narrowness(raw_proof_narrowness) else {}
            )
            if proof_narrowness:
                next_decision["proof_narrowness"] = proof_narrowness
            local_overlay = _compact_tiny_local_overlay(answer.get("local_overlay"))
            if local_overlay:
                next_decision["local_overlay"] = local_overlay
            high_risk_overlay = _compact_tiny_high_risk_overlay(answer.get("high_risk_overlay"))
            if high_risk_overlay:
                next_decision["high_risk_overlay"] = high_risk_overlay
            next_decision.setdefault(
                "detail_command",
                _command_with_cli_invoke(
                    command="agentic-workspace proof --verbose --changed <paths> --format json", cli_invoke=cli_invoke
                ),
            )
            next_decision = _guidance_with_cli_invoke(value=next_decision, cli_invoke=cli_invoke)
            return next_decision
        required_commands = tiny_required_commands
        validation_plan = answer.get("validation_plan", {}) if isinstance(answer, dict) else {}
        primary = validation_plan.get("primary_next_action") if isinstance(validation_plan, dict) else None
        if isinstance(answer, dict) and (not required_commands) and answer.get("unavailable_proof_commands"):
            primary = {"action": "select-proof-scope", "command": None, "run": None, "required": False}
        elif not isinstance(primary, dict):
            primary = {
                "action": "run-validation-command" if required_commands else "select-proof-scope",
                "command": required_commands[0] if required_commands else None,
                "run": required_commands[0] if required_commands else None,
            }
        surface_value = answer.get("surface_value_review") if isinstance(answer, dict) else None
        warnings: list[dict[str, Any]] = []
        if isinstance(surface_value, dict) and surface_value.get("status") in {"blocked", "needs-review"}:
            warnings.append({"status": surface_value.get("status"), "summary": surface_value.get("summary") or surface_value.get("rule")})
        high_risk_overlay = _compact_tiny_high_risk_overlay(answer.get("high_risk_overlay") if isinstance(answer, dict) else {})
        local_overlay = _compact_tiny_local_overlay(answer.get("local_overlay") if isinstance(answer, dict) else {})
        next_payload = {
            "kind": "proof-next-decision/v1",
            "target": payload.get("target"),
            "selector": payload.get("selector", {}),
            "sufficiency": _tiny_workflow_sufficiency(answer.get("sufficiency", {})) if isinstance(answer, dict) else {},
            "next": {
                "action": primary.get("action", "run-validation-command"),
                "command": primary.get("command"),
                "run": primary.get("run"),
                "required": primary.get("required", bool(required_commands)),
            },
            "required_commands": required_commands,
            **({"intent_proof": _compact_tiny_intent_proof(answer["intent_proof"])} if include_intent_proof else {}),
            **(
                {"proof_narrowness": _compact_tiny_proof_narrowness(answer.get("proof_narrowness"))}
                if isinstance(answer, dict)
                and answer.get("proof_narrowness")
                and _include_tiny_proof_narrowness(answer.get("proof_narrowness"))
                else {}
            ),
            **({"local_overlay": local_overlay} if local_overlay else {}),
            **({"high_risk_overlay": high_risk_overlay} if high_risk_overlay else {}),
            **(
                {"proof_command_adjustments": answer["proof_command_adjustments"]}
                if isinstance(answer, dict) and answer.get("proof_command_adjustments")
                else {}
            ),
            **(
                {"unavailable_proof_commands": answer["unavailable_proof_commands"]}
                if isinstance(answer, dict) and answer.get("unavailable_proof_commands")
                else {}
            ),
            **(
                {
                    "proof_strategy": {
                        "kind": answer.get("proof_strategy", {}).get("kind"),
                        "selection_order": answer.get("proof_strategy", {}).get("selection_order", []),
                    }
                }
                if isinstance(answer, dict)
                and answer.get("proof_strategy")
                and (answer.get("proof_command_adjustments") or answer.get("unavailable_proof_commands"))
                else {}
            ),
            **(
                {"target_proof_capabilities": answer["target_proof_capabilities"]}
                if isinstance(answer, dict)
                and answer.get("target_proof_capabilities")
                and (answer.get("proof_command_adjustments") or answer.get("unavailable_proof_commands"))
                else {}
            ),
            **(
                {"manual_verification": answer["manual_verification"]}
                if isinstance(answer, dict) and answer.get("manual_verification")
                else {}
            ),
            "warnings": warnings,
            "detail_command": _command_with_cli_invoke(
                command="agentic-workspace proof --verbose --changed <paths> --format json", cli_invoke=cli_invoke
            ),
            "detail_command_template": _command_template_payload(
                command=_command_with_cli_invoke(
                    command="agentic-workspace proof --verbose --changed <paths> --format json",
                    cli_invoke=cli_invoke,
                ),
                placeholders={"paths": _list_payload(payload.get("selector", {}).get("changed"))},
                purpose="verbose proof drill-down after substituting the actual changed paths",
            ),
        }
        return _guidance_with_cli_invoke(value=next_payload, cli_invoke=cli_invoke)
    return {
        "kind": "proof-next-decision/v1",
        "target": payload.get("target"),
        "selector": {},
        "next": {
            "action": "select-proof-scope",
            "command": None,
            "run": None,
            "required": False,
        },
        "command_template": _command_template_payload(
            command=_command_with_cli_invoke(command="agentic-workspace proof --changed <paths> --format json", cli_invoke=cli_invoke),
            placeholders={"paths": []},
            purpose="proof selection after changed paths are known",
        ),
        "required_commands": [],
        "warnings": [],
        "detail_command": _command_with_cli_invoke(command="agentic-workspace proof --verbose --format json", cli_invoke=cli_invoke),
    }


def _command_template_payload(*, command: Any, placeholders: dict[str, Any], purpose: str) -> dict[str, Any]:
    template = str(command or "").strip()
    return {
        "kind": "agentic-workspace/command-template/v1",
        "template": template,
        "runnable": False,
        "placeholders": placeholders,
        "instantiation_required": [name for name, value in placeholders.items() if value in (None, "", [])],
        "purpose": purpose,
        "rule": "Substitute placeholders before running.",
    }


def _proof_receipt_passed(result: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(result or "").strip().lower()).strip("-")
    return normalized in {"pass", "passed", "success", "succeeded", "ok", "green"}


def _proof_receipt_failed(result: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(result or "").strip().lower()).strip("-")
    if normalized in {"fail", "failed", "failure", "error", "errored", "timeout", "timed-out", "cancelled", "canceled"}:
        return True
    return bool(set(normalized.split("-")) & {"fail", "failed", "failure", "error", "errored", "timeout", "cancelled", "canceled"})


def _proof_receipt_summary(receipt: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "command": str(receipt.get("command") or "").strip(),
        "result": str(receipt.get("result") or "").strip(),
        "changed_paths": [str(path).strip() for path in _list_payload(receipt.get("changed_paths")) if str(path).strip()],
        "recorded_at": receipt.get("recorded_at", ""),
        "plan_id": receipt.get("plan_id", ""),
    }
    proof_commands = [str(command).strip() for command in _list_payload(receipt.get("proof_commands")) if str(command).strip()]
    if proof_commands:
        summary["proof_commands"] = proof_commands
    for key in ("selected_proof_id", "selected_proof_fingerprint"):
        value = str(receipt.get(key) or "").strip()
        if value:
            summary[key] = value
    return summary


def _proof_receipt_identity(receipt: dict[str, Any]) -> str:
    return json.dumps(_proof_receipt_summary(receipt), sort_keys=True, ensure_ascii=True)


def _read_proof_receipt_records(target_root: Path) -> tuple[list[dict[str, Any]] | None, dict[str, Any], str]:
    receipt_path = target_root / PROOF_RECEIPT_RELATIVE_PATH
    history_path = target_root / PROOF_RECEIPT_HISTORY_RELATIVE_PATH
    records: list[dict[str, Any]] = []
    latest_receipt: dict[str, Any] = {}
    seen: set[str] = set()

    def add_record(receipt: Any) -> None:
        if not isinstance(receipt, dict):
            return
        identity = _proof_receipt_identity(receipt)
        if identity in seen:
            return
        seen.add(identity)
        records.append(receipt)

    if receipt_path.is_file():
        try:
            loaded = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return None, {}, f"latest receipt could not be read as JSON: {exc}"
        if isinstance(loaded, dict):
            latest_receipt = loaded
            add_record(loaded)
        else:
            return None, {}, "latest receipt is not a JSON object"

    if history_path.is_file():
        try:
            lines = history_path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            return None, latest_receipt, f"receipt history could not be read: {exc}"
        for index, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError as exc:
                return None, latest_receipt, f"receipt history line {index} could not be read as JSON: {exc}"
            if not isinstance(loaded, dict):
                return None, latest_receipt, f"receipt history line {index} is not a JSON object"
            add_record(loaded)

    records.sort(key=lambda item: str(item.get("recorded_at") or ""), reverse=True)
    return records, latest_receipt, ""


def _proof_receipt_path_scope_matches(*, receipt: dict[str, Any], changed_paths: list[str]) -> bool:
    receipt_paths = [str(path).strip() for path in _list_payload(receipt.get("changed_paths")) if str(path).strip()]
    normalized_changed_paths = [str(path).strip() for path in changed_paths if str(path).strip()]
    return set(normalized_changed_paths).issubset(set(receipt_paths)) if normalized_changed_paths else True


def _selected_proof_identity(required_commands: list[str]) -> dict[str, Any]:
    normalized = [str(command).strip() for command in required_commands if str(command).strip()]
    digest = hashlib.sha256(json.dumps(normalized, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()
    return {
        "kind": "agentic-workspace/selected-proof-identity/v1",
        "id": f"selected-proof:{digest[:16]}",
        "fingerprint": digest,
        "command_count": len(normalized),
    }


def _proof_receipt_aggregate_matches(*, receipt: dict[str, Any], required_commands: list[str]) -> tuple[bool, str]:
    required = [str(command).strip() for command in required_commands if str(command).strip()]
    if not required:
        return False, "no selected commands require aggregate proof"
    identity = _selected_proof_identity(required)
    receipt_fingerprint = str(receipt.get("selected_proof_fingerprint") or "").strip()
    if receipt_fingerprint and receipt_fingerprint == identity["fingerprint"]:
        return True, "selected proof fingerprint accepted"
    receipt_id = str(receipt.get("selected_proof_id") or "").strip()
    if receipt_id and receipt_id == identity["id"]:
        return True, "selected proof id accepted"
    proof_commands = [str(command).strip() for command in _list_payload(receipt.get("proof_commands")) if str(command).strip()]
    if proof_commands and set(required).issubset(set(proof_commands)):
        return True, "aggregate proof_commands receipt accepted"
    return False, "receipt is not for this selected proof set"


def _proof_requirement_tier_for_command(command: str, *, selected: dict[str, Any]) -> str:
    tier = _proof_command_tier(command, lane=str(selected.get("lane", "")))
    if tier == "environmental":
        return "optional_environmental"
    if tier == "manual_review":
        return "manual_required"
    return "selected_required"


def _proof_receipt_blocking_commands(*, required_commands: list[str], selected_commands: list[dict[str, Any]]) -> list[str]:
    selected_by_text = {str(command.get("command", "")): command for command in selected_commands if isinstance(command, dict)}
    blocking: list[str] = []
    for command in required_commands:
        text = str(command).strip()
        if not text:
            continue
        tier = _proof_requirement_tier_for_command(text, selected=selected_by_text.get(text, {}))
        if tier == "optional_environmental":
            continue
        blocking.append(text)
    return blocking


def _proof_requirement_tiers_payload(
    *,
    selected_commands: list[dict[str, Any]],
    required_commands: list[str],
    optional_commands: list[str],
    manual_proof_obligations: list[dict[str, Any]],
    unavailable_commands: list[dict[str, Any]],
    host_policy_blocked_commands: list[dict[str, Any]],
) -> dict[str, Any]:
    selected_by_text = {str(command.get("command", "")): command for command in selected_commands if isinstance(command, dict)}
    categories: dict[str, list[dict[str, Any]]] = {
        "selected_required": [],
        "manual_required": [],
        "recommended_confidence": [],
        "optional_environmental": [],
        "not_selected": [],
    }
    for command in required_commands:
        text = str(command).strip()
        if not text:
            continue
        selected = selected_by_text.get(text, {})
        requirement_tier = _proof_requirement_tier_for_command(text, selected=selected)
        categories.setdefault(requirement_tier, []).append(
            {
                "command": text,
                "lane": str(selected.get("lane", "")),
                "blocking": requirement_tier in {"selected_required", "manual_required"},
                "receipt_required": requirement_tier == "selected_required",
                "reason": "environmental proof is surfaced as non-blocking context"
                if requirement_tier == "optional_environmental"
                else "selected proof blocks closeout until executed or reconciled",
            }
        )
    for item in manual_proof_obligations:
        if isinstance(item, dict):
            categories["manual_required"].append(
                {
                    "id": str(item.get("id", "")),
                    "blocking": bool(item.get("required", True)),
                    "receipt_required": False,
                    "reason": "manual proof obligation must be recorded outside executable receipt matching",
                }
            )
    for command in optional_commands:
        text = str(command).strip()
        if text and text not in {item.get("command") for item in categories["selected_required"]}:
            categories["recommended_confidence"].append(
                {"command": text, "blocking": False, "receipt_required": False, "reason": "recommended confidence check"}
            )
    for command in [*unavailable_commands, *host_policy_blocked_commands]:
        if isinstance(command, dict):
            categories["manual_required"].append(
                {
                    "command": str(command.get("command", "")),
                    "lane": str(command.get("lane", "")),
                    "blocking": True,
                    "receipt_required": False,
                    "reason": str(command.get("reason", "")) or "selected proof is unavailable or blocked",
                }
            )
    counts = {key: len(value) for key, value in categories.items()}
    blocking_count = sum(1 for items in categories.values() for item in items if item.get("blocking"))
    return {
        "kind": "agentic-workspace/proof-requirement-tiers/v1",
        "status": "present" if any(counts.values()) else "empty",
        "counts": counts,
        "blocking_count": blocking_count,
        "categories": categories,
        "blocking_rule": (
            "Closeout blocks on selected_required and manual_required proof. Recommended confidence, optional "
            "environmental, and not-selected proof remain visible without inflating missing receipt counts."
        ),
    }


def _proof_receipt_reconciliation_payload(
    *,
    target_root: Path | None,
    required_commands: list[str],
    changed_paths: list[str],
    selected_commands: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    blocking_commands = _proof_receipt_blocking_commands(
        required_commands=required_commands,
        selected_commands=selected_commands or [],
    )
    selected_identity = _selected_proof_identity(blocking_commands)
    command_states: list[dict[str, Any]] = []
    base = {
        "kind": "agentic-workspace/proof-receipt-reconciliation/v1",
        "receipt_path": PROOF_RECEIPT_RELATIVE_PATH.as_posix(),
        "receipt_history_path": PROOF_RECEIPT_HISTORY_RELATIVE_PATH.as_posix(),
        "selected_command_count": len(required_commands),
        "required_command_count": len(blocking_commands),
        "non_blocking_selected_count": max(0, len(required_commands) - len(blocking_commands)),
        "selected_proof_identity": selected_identity,
        "rule": (
            "Receipts are accepted only for exact command matches, compatible changed-path scope, and passed results; "
            "aggregate receipts may satisfy the selected proof set when they carry matching selected proof identity or "
            "proof_commands. Optional/environmental proof is reported outside the blocking receipt count."
        ),
    }
    if target_root is None:
        return {
            **base,
            "status": "unavailable",
            "reason": "target root unavailable",
            "commands": [
                {"command": command, "evidence_state": "not-run-or-not-recorded", "diagnostic": "not run or not recorded"}
                for command in blocking_commands
            ],
        }
    receipt_records, latest_receipt, read_error = _read_proof_receipt_records(target_root)
    if receipt_records is None:
        return {
            **base,
            "status": "untrusted-record",
            "reason": read_error,
            "commands": [
                {"command": command, "evidence_state": "record-stale-untrusted", "diagnostic": "record unreadable or untrusted"}
                for command in blocking_commands
            ],
        }
    if not receipt_records:
        return {
            **base,
            "status": "not-recorded",
            "commands": [
                {"command": command, "evidence_state": "not-run-or-not-recorded", "diagnostic": "not run or not recorded"}
                for command in blocking_commands
            ],
        }
    aggregate_receipts = [
        receipt
        for receipt in receipt_records
        if _proof_receipt_passed(str(receipt.get("result") or ""))
        and _proof_receipt_path_scope_matches(receipt=receipt, changed_paths=changed_paths)
        and _proof_receipt_aggregate_matches(receipt=receipt, required_commands=blocking_commands)[0]
    ]
    aggregate_receipt = aggregate_receipts[0] if aggregate_receipts else None
    aggregate_match_reason = (
        _proof_receipt_aggregate_matches(receipt=aggregate_receipt, required_commands=blocking_commands)[1]
        if aggregate_receipt is not None
        else ""
    )
    for command in blocking_commands:
        state: dict[str, Any]
        command_receipts = [receipt for receipt in receipt_records if str(receipt.get("command") or "").strip() == command]
        scoped_receipts = [
            receipt for receipt in command_receipts if _proof_receipt_path_scope_matches(receipt=receipt, changed_paths=changed_paths)
        ]
        accepted_receipt = next(
            (receipt for receipt in scoped_receipts if _proof_receipt_passed(str(receipt.get("result") or ""))),
            None,
        )
        failed_receipt = next(
            (receipt for receipt in scoped_receipts if _proof_receipt_failed(str(receipt.get("result") or ""))),
            None,
        )
        if accepted_receipt is not None:
            state = {
                "command": command,
                "evidence_state": "accepted",
                "diagnostic": "passed receipt accepted",
                "receipt": _proof_receipt_summary(accepted_receipt),
            }
        elif aggregate_receipt is not None:
            state = {
                "command": command,
                "evidence_state": "accepted",
                "diagnostic": aggregate_match_reason,
                "receipt": _proof_receipt_summary(aggregate_receipt),
                "receipt_match": "aggregate-selected-proof",
            }
        elif failed_receipt is not None:
            state = {
                "command": command,
                "evidence_state": "recorded-failed",
                "diagnostic": "run and recorded as failed",
                "receipt": _proof_receipt_summary(failed_receipt),
            }
        elif command_receipts and not scoped_receipts:
            state = {
                "command": command,
                "evidence_state": "record-stale-untrusted",
                "diagnostic": "record stale or untrusted for this changed-path scope",
            }
        elif command_receipts:
            state = {
                "command": command,
                "evidence_state": "record-stale-untrusted",
                "diagnostic": "receipt result is not a recognized pass/fail state",
            }
        else:
            state = {
                "command": command,
                "evidence_state": "run-but-not-recorded",
                "diagnostic": "run but not recorded for this selected command",
            }
        state["required"] = True
        state["blocking"] = True
        state["proof_requirement_tier"] = "selected_required"
        command_states.append(state)
    accepted_count = sum(1 for state in command_states if state.get("evidence_state") == "accepted")
    return {
        **base,
        "status": "accepted" if command_states and accepted_count == len(command_states) else "attention",
        "accepted_count": accepted_count,
        "receipt": _proof_receipt_summary(latest_receipt),
        "receipt_history": {
            "path": PROOF_RECEIPT_HISTORY_RELATIVE_PATH.as_posix(),
            "record_count": len(receipt_records),
            "accepted_record_count": accepted_count,
            "rule": "Each selected command may be reconciled against any trusted receipt in the current proof boundary.",
        },
        "commands": command_states,
    }


def _proof_receipt_bridge_payload(
    *,
    changed_paths: list[str],
    proof_receipt_reconciliation: dict[str, Any],
    cli_invoke: str,
) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    changed_args = " ".join(_shell_quote(path) for path in changed_paths)
    changed_part = f" --changed {changed_args}" if changed_args else ""
    for item in _list_payload(proof_receipt_reconciliation.get("commands")):
        if not isinstance(item, dict):
            continue
        evidence_state = str(item.get("evidence_state", "")).strip()
        if evidence_state == "accepted":
            continue
        command = str(item.get("command", "")).strip()
        if not command:
            continue
        placeholders = sorted(set(re.findall(r"<[^>]+>", command)))
        action: dict[str, Any] = {
            "kind": "agentic-workspace/proof-receipt-bridge-action/v1",
            "command": command,
            "receipt_state": evidence_state or "not-recorded",
            "diagnostic": str(item.get("diagnostic", "")),
            "result_options": ["passed", "failed", "skipped", "waived"],
            "after_running": "Record the actual result only after executing or deliberately classifying this selected proof command.",
        }
        if placeholders:
            action.update(
                {
                    "status": "instantiate-before-recording",
                    "placeholders": placeholders,
                    "next_action": "instantiate placeholders, run the concrete command, then record the actual result",
                    "recording_rule": "Substitute placeholders and run the concrete command before recording a receipt.",
                }
            )
        else:
            action["status"] = "ready-to-record-after-run"
            record_passed_command = _command_with_cli_invoke(
                command=(
                    "agentic-workspace proof --target ."
                    f"{changed_part} --record-receipt --receipt-command {_shell_quote(command)} --receipt-result passed --format json"
                ),
                cli_invoke=cli_invoke,
            )
            action["next_action"] = "record the actual proof result after this concrete command has run"
            action["recording_command"] = record_passed_command
            action["record_passed_command"] = record_passed_command
        actions.append(action)
    ready_actions = [action for action in actions if action.get("status") == "ready-to-record-after-run"]
    template_actions = [action for action in actions if action.get("status") == "instantiate-before-recording"]
    next_ready_command = str(ready_actions[0].get("recording_command", "")) if ready_actions else ""
    return {
        "kind": "agentic-workspace/proof-receipt-bridge/v1",
        "status": "action-required" if actions else "complete",
        "missing_receipt_count": len(actions),
        "ready_to_record_count": len(ready_actions),
        "template_blocked_count": len(template_actions),
        "next_action": "record the first concrete proof receipt"
        if ready_actions
        else "instantiate template proof commands before recording"
        if template_actions
        else "no receipt action required",
        "next_recording_command": next_ready_command,
        "receipt_path": str(proof_receipt_reconciliation.get("receipt_path", PROOF_RECEIPT_RELATIVE_PATH.as_posix())),
        "history_path": str(proof_receipt_reconciliation.get("receipt_history_path", PROOF_RECEIPT_HISTORY_RELATIVE_PATH.as_posix())),
        "actions": actions,
        "rule": (
            "This bridge supplies explicit receipt commands for selected proof only; it does not infer execution success "
            "from shell history or prose. Record the actual result after running the command."
        ),
    }


def _active_planning_record_for_proof(*, target_root: Path) -> dict[str, Any]:
    state_path = target_root / ".agentic-workspace" / "planning" / "state.toml"
    try:
        state = tomllib.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {"status": "unavailable", "reason": "planning state unavailable"}
    todo = state.get("todo", {})
    active_items = todo.get("active_items", []) if isinstance(todo, dict) else []
    active_item = next((item for item in active_items if isinstance(item, dict)), None)
    if not isinstance(active_item, dict):
        return {"status": "unavailable", "reason": "no active planning item"}
    surface = str(active_item.get("surface") or "").strip()
    record_path = target_root / surface if surface else None
    raw_record: dict[str, Any] = {}
    if record_path is not None and record_path.is_file() and record_path.suffix == ".json":
        try:
            loaded_record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded_record = {}
        raw_record = loaded_record if isinstance(loaded_record, dict) else {}
    canonical = raw_record.get("canonical_core", {}) if isinstance(raw_record.get("canonical_core"), dict) else {}
    machine = raw_record.get("machine_readable_contract", {}) if isinstance(raw_record.get("machine_readable_contract"), dict) else {}
    execution = machine.get("execution", {}) if isinstance(machine.get("execution"), dict) else {}
    proof_expectations = _list_payload(canonical.get("proof_expectations")) or _list_payload(active_item.get("proof"))
    validation_commands = _list_payload(raw_record.get("validation_commands")) or _list_payload(execution.get("proof"))
    return {
        "status": "present",
        "task": {"id": active_item.get("id", ""), "title": active_item.get("title", ""), "surface": surface},
        "validation_commands": validation_commands,
        "proof_expectations": proof_expectations,
        "adaptive_assurance": raw_record.get("adaptive_assurance", {}),
        "traceability_refs": raw_record.get("traceability_refs", {}),
        "control_gates": raw_record.get("control_gates", []),
        "implementation_blockers": raw_record.get("implementation_blockers", []),
        "risk_registry_refs": raw_record.get("risk_registry_refs", []),
        "invariant_refs": raw_record.get("invariant_refs", []),
        "test_data_policy": raw_record.get("test_data_policy", {}),
        "layer_scaffold": raw_record.get("layer_scaffold", {}),
        "architecture_decision_promotion": raw_record.get("architecture_decision_promotion", {}),
        "threat_failure_aids": raw_record.get("threat_failure_aids", []),
        "proof_report": raw_record.get("proof_report", {}),
    }


def _tiny_proof_obligations_payload(value: dict[str, Any], *, required_commands: list[str] | None = None) -> dict[str, Any]:
    required = value.get("required_proof", {}) if isinstance(value.get("required_proof"), dict) else {}
    recommended = value.get("recommended_confidence_checks", {}) if isinstance(value.get("recommended_confidence_checks"), dict) else {}
    visible_required_commands = list(required_commands) if required_commands is not None else required.get("commands", [])
    manual_obligations = [item for item in required.get("manual_obligations", []) if isinstance(item, dict) and item.get("required")]
    compact_manual_obligations = [
        {
            "id": str(item.get("id", "")),
            "status": str(item.get("status", "")),
            "missing_evidence": item.get("missing_evidence", []),
            "reference_material": item.get("reference_material", []),
            "claim_boundary": str(item.get("claim_boundary", "")),
            "resolution": {
                "inspect": item.get("reference_material", []) or item.get("missing_evidence", []),
                "record": item.get("missing_evidence", []) or ["manual_review_result"],
                "detail_selector": "proof.proof_obligations.required_proof.manual_obligations",
                "closeout_format": "manual obligation <id>: inspected <refs>; recorded <evidence>; claim boundary <claim_boundary>",
            },
        }
        for item in manual_obligations
    ]
    manual_obligation_projection: dict[str, Any]
    if len(compact_manual_obligations) <= 3:
        manual_obligation_projection = {"manual_obligations": compact_manual_obligations}
    else:
        manual_obligation_projection = {
            "manual_obligation_ids": [str(item.get("id", "")) for item in manual_obligations[:4] if str(item.get("id", "")).strip()],
            "manual_obligations_detail_selector": "proof.proof_obligations.required_proof.manual_obligations",
            "manual_obligation_record_shape": {
                "inspect": "reference_material or the affected surface named by the obligation",
                "record": "missing_evidence item plus review result",
                "detail_selector": "proof.proof_obligations.required_proof.manual_obligations",
                "closeout_format": "manual obligation <id>: inspected <refs>; recorded <evidence>; claim boundary <claim_boundary>",
            },
        }
    return {
        "kind": value.get("kind", "agentic-workspace/proof-obligations/v1"),
        "required_proof": {
            "status": required.get("status", "unknown"),
            "commands": visible_required_commands,
            "manual_verification_required": bool(required.get("manual_verification_required", False)),
            "manual_obligation_count": int(required.get("manual_obligation_count", 0) or 0),
            **manual_obligation_projection,
            "action_effect": _tiny_action_effect(
                required.get("action_effect", {}), include_allowed=False, include_resolution_commands=False
            ),
        },
        "recommended_confidence_checks": {
            "status": recommended.get("status", "unknown"),
            **({"commands": recommended.get("commands", [])} if required_commands is None else {}),
            "rule": recommended.get("rule", ""),
        },
        "completion_claim_rule": value.get("completion_claim_rule", ""),
    }


def _closeout_ready_phase_answer_payload(
    *,
    completion_gate: dict[str, Any],
    proof_execution: dict[str, Any],
    planning_evidence: dict[str, Any],
    installed_state_residue: dict[str, Any],
    workflow_compliance_summary: dict[str, Any],
    detail_commands: dict[str, str],
) -> dict[str, Any]:
    claim_authorization = _as_dict(completion_gate.get("claim_authorization"))
    allowed_claim_classes = [
        str(item).strip() for item in _list_payload(claim_authorization.get("allowed_claim_classes")) if str(item).strip()
    ]
    blocked_claim_classes = [
        str(item).strip() for item in _list_payload(claim_authorization.get("blocked_claim_classes")) if str(item).strip()
    ]
    closure_actions = [dict(item) for item in _list_payload(claim_authorization.get("closure_actions")) if isinstance(item, dict)]
    closure_keyword_guard = _as_dict(claim_authorization.get("closure_keyword_guard"))
    unsafe_closure_actions: list[dict[str, Any]] = [
        {
            "kind": str(action.get("kind") or "closure_action"),
            "target": str(action.get("target") or ""),
            "reason": str(action.get("reason") or "closure action is not authorized by closeout claim authorization"),
        }
        for action in closure_actions
        if action.get("authorized") is not True
    ]
    for target in _list_payload(closure_keyword_guard.get("targets")):
        if not isinstance(target, dict) or str(target.get("status") or "") != "blocked":
            continue
        unsafe_closure_actions.append(
            {
                "kind": "closure_keyword",
                "target": str(target.get("target") or ""),
                "reason": str(closure_keyword_guard.get("rule") or "closure keywords are blocked for this target"),
                "unsafe_examples": _list_payload(target.get("unsafe_examples")),
                "safe_reference": str(target.get("safe_reference") or ""),
            }
        )

    claim_rank = {
        "none": 0,
        "partial_progress": 1,
        "slice_complete": 2,
        "lane_complete": 3,
        "parent_complete": 4,
        "full_intent_complete": 5,
        "issue_closure": 6,
    }
    strongest_safe_claim = "none"
    for claim_class in allowed_claim_classes:
        if claim_rank.get(claim_class, 0) > claim_rank.get(strongest_safe_claim, 0):
            strongest_safe_claim = claim_class

    proof_status = str(proof_execution.get("status") or "unknown").strip() or "unknown"
    proof_state = "satisfied" if proof_status in {"recorded", "passed", "satisfied"} else "missing-or-unknown"
    planning_state = str(planning_evidence.get("state") or "absent").strip() or "absent"
    payload_status = str(installed_state_residue.get("status") or "unknown").strip() or "unknown"
    payload_effect = str(installed_state_residue.get("current_task_proof_effect") or "").strip()
    workflow_status = str(workflow_compliance_summary.get("status") or "unknown").strip() or "unknown"
    dogfooding_command = detail_commands.get(
        "dogfooding_signal_status",
        "agentic-workspace report --target ./repo --section dogfooding_signal_status --format json",
    )
    dogfooding_status = {
        "status": "not-inspected",
        "source": "dogfooding_signal_status",
        "detail_selector": "dogfooding_signal_status",
        "detail_command": dogfooding_command,
        "claim_boundary": (
            "Treat missing dogfooding disposition as unresolved for broad closeout; inspect or record no-signal/dismissed/routed state."
        ),
    }

    remaining_actions: list[dict[str, Any]] = []

    def add_remaining(action_id: str, status: str, summary: str, selector: str, command: str = "") -> None:
        remaining_actions.append(
            {
                "id": action_id,
                "status": status,
                "summary": summary,
                "detail_selector": selector,
                **({"command": command} if command else {}),
            }
        )

    if proof_state != "satisfied":
        add_remaining(
            "proof",
            proof_status,
            "Proof execution is not recorded as satisfied for this closeout claim.",
            "closeout_report.validation",
            detail_commands.get("closeout_trust", ""),
        )
    if payload_status in {"current_task_blocking", "payload-upgrade-required", "blocked", "unknown"} or payload_effect == "blocking":
        add_remaining(
            "payload",
            payload_status,
            "Installed payload state is missing, unknown, or claim-relevant before broad closeout.",
            "closeout_report.installed_state_residue",
        )
    if workflow_status in {"attention", "unknown"}:
        add_remaining(
            "workflow",
            workflow_status,
            "Workflow compliance has unresolved or unknown closeout evidence.",
            "closeout_report.gaps_and_residual_risk.workflow_trust_impact",
            detail_commands.get("workflow_compliance_summary", ""),
        )
    add_remaining(
        "dogfooding",
        dogfooding_status["status"],
        "Dogfooding disposition is not included in this closeout report packet; inspect the dedicated selector.",
        "dogfooding_signal_status",
        dogfooding_command,
    )
    if strongest_safe_claim == "none" or blocked_claim_classes:
        add_remaining(
            "claim_authorization",
            str(completion_gate.get("status") or "unknown"),
            "Completion claim classes are blocked or limited by claim authorization.",
            "closeout_report.completion_gate.claim_authorization",
        )
    if unsafe_closure_actions:
        add_remaining(
            "closure_actions",
            "blocked",
            "One or more closure actions or closure keywords are unsafe for the current claim boundary.",
            "closeout_report.closeout_ready.unsafe_closure_actions",
        )

    status = "ready"
    if any(item["id"] in {"proof", "payload", "claim_authorization", "closure_actions"} for item in remaining_actions):
        status = "blocked"
    elif remaining_actions:
        status = "review-required"

    return {
        "kind": "agentic-workspace/closeout-ready-phase-answer/v1",
        "status": status,
        "phase_question": "What proof remains, what residue matters, and what can safely be claimed now?",
        "strongest_safe_claim": strongest_safe_claim,
        "proof_status": {
            "status": proof_status,
            "state": proof_state,
            "proof": proof_execution.get("proof", ""),
            "source_field": proof_execution.get("source_field", ""),
        },
        "planning_owner": {
            "state": planning_state,
            "authority": planning_evidence.get("authority", ""),
            "source": planning_evidence.get("source", {}),
            "rule": planning_evidence.get("rule", ""),
        },
        "payload_status": {
            "status": payload_status,
            "current_task_proof_effect": payload_effect or "unknown",
            "claim_boundary": _as_dict(installed_state_residue.get("triage")).get(
                "claim_boundary", installed_state_residue.get("claim_boundary", "")
            ),
        },
        "dogfooding_status": dogfooding_status,
        "claim_authorization": {
            "allowed_claim_classes": allowed_claim_classes,
            "blocked_claim_classes": blocked_claim_classes,
            "closure_actions": closure_actions,
            "closure_keyword_guard": closure_keyword_guard,
        },
        "unsafe_closure_actions": unsafe_closure_actions,
        "remaining_actions": remaining_actions,
        "remaining_action_count": len(remaining_actions),
        "drilldowns": {
            "closeout_report": detail_commands.get("closeout_report", ""),
            "closeout_trust": detail_commands.get("closeout_trust", ""),
            "completion_contract": detail_commands.get("completion_contract", ""),
            "workflow_compliance_summary": detail_commands.get("workflow_compliance_summary", ""),
            "dogfooding_signal_status": dogfooding_command,
        },
        "conservative_unknown_rule": (
            "Unknown, stale, or omitted evidence stays visible as remaining action and must not be promoted into a completion or closure claim."
        ),
        "boundary": (
            "This packet composes existing closeout/proof/planning/payload/dogfooding/claim signals; detailed selectors remain canonical."
        ),
    }


def _closeout_report_payload(
    *,
    active_planning_record: dict[str, Any],
    closeout_trust: dict[str, Any],
    completion_contract: dict[str, Any],
    workflow_compliance_summary: dict[str, Any],
    verification: dict[str, Any],
    architecture_principles: dict[str, Any] | None = None,
    installed_state_closeout_residue: dict[str, Any] | None = None,
    config: WorkspaceConfig,
) -> dict[str, Any]:
    active_planning_record = active_planning_record if isinstance(active_planning_record, dict) else {}
    closeout_trust = closeout_trust if isinstance(closeout_trust, dict) else {}
    completion_contract = completion_contract if isinstance(completion_contract, dict) else {}
    verification = verification if isinstance(verification, dict) else {}
    architecture_principles = architecture_principles if isinstance(architecture_principles, dict) else {}
    installed_state_closeout_residue = installed_state_closeout_residue if isinstance(installed_state_closeout_residue, dict) else {}
    execution = _as_dict(active_planning_record.get("execution_run"))
    proof_report = _as_dict(active_planning_record.get("proof_report"))
    closure_check = _as_dict(active_planning_record.get("closure_check"))
    delegated = _as_dict(active_planning_record.get("delegated_judgment"))
    evidence_source = _as_dict(active_planning_record.get("_closeout_evidence_source"))
    default_evidence_authority = "active-planning-evidence" if active_planning_record else ""
    evidence_authority = str(evidence_source.get("authority") or default_evidence_authority).strip()
    evidence_is_archived = evidence_authority == "archived-planning-evidence"
    evidence_is_retained = evidence_authority == "retained-closeout-evidence"
    evidence_state = (
        "retained" if evidence_is_retained else "archived" if evidence_is_archived else "active" if active_planning_record else "absent"
    )
    intent_check = _as_dict(closeout_trust.get("intent_satisfaction_check"))
    completion_boundary = _as_dict(completion_contract.get("completion_boundary"))
    traceability_rows = _closeout_report_traceability_rows(
        active_planning_record=active_planning_record,
        closeout_trust=closeout_trust,
        completion_contract=completion_contract,
        verification=verification,
    )
    completeness = _closeout_report_completeness_payload(
        active_planning_record=active_planning_record,
        closeout_trust=closeout_trust,
        completion_contract=completion_contract,
        traceability_rows=traceability_rows,
        verification=verification,
        assurance_requirements=_as_dict(closeout_trust.get("assurance_requirements")),
    )
    profile_policy = _closeout_report_profile_policy_payload(
        closeout_trust=closeout_trust,
        completion_contract=completion_contract,
        verification=verification,
        completeness=completeness,
        config=config,
        cli_invoke=config.cli_invoke,
    )
    trust = str(closeout_trust.get("trust", "unknown"))
    if profile_policy["selected_profile"] == "audit" and completeness["status"] != "complete":
        trust = "lower-trust"
    raw_completion_options = [item for item in _list_payload(closeout_trust.get("completion_options")) if isinstance(item, dict)]
    options = {str(item.get("id", "")): item for item in raw_completion_options}
    next_action = (
        closeout_trust.get("recommended_next_action")
        or _as_dict(closeout_trust.get("terminal_action")).get("recommended_next_action")
        or "Use the closeout report evidence before making a final completion claim."
    )
    work_completed = str(execution.get("what happened") or execution.get("summary") or "").strip()
    requested_outcome = str(
        delegated.get("requested outcome") or delegated.get("requested_outcome") or completion_contract.get("must_be_true") or ""
    ).strip()
    intent_evidence = _closeout_intent_evidence_payload(
        active_planning_record=active_planning_record,
        evidence_state=evidence_state,
        requested_outcome=requested_outcome,
        intent_check=intent_check,
    )
    parent_intent_status = _parent_intent_status_payload(
        active_planning_record=active_planning_record,
        intent_check=intent_check,
        completion_boundary=completion_boundary,
    )
    applicable_intent_status = _applicable_intent_status_payload(
        active_planning_record=active_planning_record,
        verification=verification,
        assurance_requirements=_as_dict(closeout_trust.get("assurance_requirements")),
    )
    architecture_closeout = _as_dict(architecture_principles.get("closeout"))

    def meaningful_closeout_text(value: Any) -> str:
        text = str(value or "").strip()
        return "" if text.lower() in {"", "none", "null", "unknown", "pending", "not-run-yet"} else text

    changed_surfaces = str(execution.get("changed surfaces") or "").strip()
    raw_proof_report_validation = str(proof_report.get("validation proof") or "").strip()
    raw_execution_validation = str(execution.get("validations run") or "").strip()
    proof_report_validation = meaningful_closeout_text(raw_proof_report_validation)
    validation_proof = str(
        proof_report_validation or meaningful_closeout_text(raw_execution_validation) or raw_proof_report_validation
    ).strip()
    proof_achieved_now = str(proof_report.get("proof achieved now") or "").strip()
    proof_execution_recorded = bool(proof_report_validation) or meaningful_closeout_text(proof_achieved_now).lower().startswith(
        ("yes", "passed", "satisfied", "complete")
    )
    validation_proof_blocker = "intent_satisfaction.closure_scope.validation_proof"
    proof_execution = {
        "kind": "agentic-workspace/closeout-proof-execution/v1",
        "status": "recorded" if proof_execution_recorded else "missing",
        "proof": validation_proof,
        "proof_achieved_now": proof_achieved_now,
        "source_field": (
            "planning.closeout_evidence.proof_report.validation proof"
            if evidence_is_retained
            else "planning.archive.execplan.proof_report.validation proof"
            if evidence_is_archived
            else "planning.active.planning_record.proof_report.validation proof"
        ),
        "claim_boundary": "proof execution only",
        "confidence_boundary": (
            "Recorded proof execution satisfies the validation-proof reporting blocker, but structured intent-proof "
            "confidence remains separate and must not be inferred from free-form proof text."
        ),
        "rule": "Proof execution records that validation was reported; proof_confidence reports structured claim support.",
    }
    completion_options = copy.deepcopy(raw_completion_options)
    option_blockers: dict[str, list[str]] = {}
    parent_status_value = str(parent_intent_status.get("status") or "").strip()
    if parent_status_value and parent_status_value not in {"satisfied", "guidance-only", "not-recorded"}:
        option_blockers.setdefault("claim-work-complete", []).append("parent_intent_status")
        option_blockers.setdefault("close-parent-lane", []).append("parent_intent_status")
    if applicable_intent_status.get("closeout_blocked"):
        blocked_claims = [
            str(item).strip() for item in _list_payload(applicable_intent_status.get("blocked_claims")) if str(item).strip()
        ] or ["claim-work-complete", "close-parent-lane"]
        for claim in blocked_claims:
            option_blockers.setdefault(claim, []).append("applicable_intent_status")
    if architecture_closeout.get("required_claim"):
        option_blockers.setdefault("claim-work-complete", []).append("architecture_principles_status")
    for option in completion_options:
        blockers_for_option = _dedupe([*(_list_payload(option.get("blocking_fields"))), *option_blockers.get(str(option.get("id")), [])])
        if proof_execution_recorded:
            blockers_for_option = [blocker for blocker in blockers_for_option if str(blocker) != validation_proof_blocker]
        if not blockers_for_option:
            option.pop("blocking_fields", None)
            continue
        option["blocking_fields"] = blockers_for_option
        if str(option.get("id")) in option_blockers:
            option["allowed"] = False
            option["why"] = "completion claim is blocked until parent/applicable intent evidence is reconciled"
    completion_decision = str(completion_contract.get("completion_decision", "unknown"))
    proof_confidence = _as_dict(closeout_trust.get("proof_confidence"))
    behavior_preservation = _as_dict(proof_confidence.get("behavior_preservation"))
    residual_risk = str(proof_confidence.get("residual_risk", ""))
    completion_gate = _as_dict(closeout_trust.get("completion_gate"))
    if not completion_gate:
        completion_gate = _completion_gate_payload(
            active_planning_record=active_planning_record,
            intent_check=intent_check,
            acceptance_reconciliation=_as_dict(closeout_trust.get("acceptance_criteria_reconciliation")),
            intent_proof_check=_as_dict(closeout_trust.get("intent_proof_check")),
            parent_intent_status=parent_intent_status,
            applicable_intent_status=applicable_intent_status,
            durable_residue_action=_as_dict(closeout_trust.get("durable_residue_action")),
        )
    task_posture_followthrough = _as_dict(completion_gate.get("task_posture_followthrough"))
    first_blocking_option = next((item for item in completion_options if item.get("allowed") is False and item.get("blocking_fields")), {})
    blockers = first_blocking_option.get("blocking_fields", [])
    workflow_obligation_contract = _workflow_obligation_closeout_contract_payload(
        config=config,
        active_planning_record=active_planning_record,
    )
    decision_review = _closeout_report_decision_review_payload(
        active_planning_record=active_planning_record,
        proof_report=proof_report,
    )
    selected_review_mode = _closeout_report_selected_review_mode(
        profile_policy=profile_policy,
        trust=trust,
        completeness=completeness,
        decision_review=decision_review,
        behavior_preservation=behavior_preservation,
    )
    final_response_rendering = _closeout_report_final_response_rendering_payload(
        status="present" if active_planning_record else "guidance-only",
        profile_policy=profile_policy,
        trust=trust,
        work_completed=work_completed,
        requested_outcome=requested_outcome,
        changed_surfaces=changed_surfaces,
        validation_proof=validation_proof,
        completion_decision=completion_decision,
        completion_boundary=completion_boundary,
        completion_options=completion_options,
        completeness=completeness,
        residual_risk=residual_risk,
        blockers=blockers if isinstance(blockers, list) else [],
        next_action=str(next_action),
        decision_review=decision_review,
        behavior_preservation=behavior_preservation,
        parent_intent_status=parent_intent_status,
        applicable_intent_status=applicable_intent_status,
        workflow_obligation_contract=workflow_obligation_contract,
        completion_gate=completion_gate,
        review_mode=selected_review_mode,
    )
    detail_commands = {
        "closeout_report": str(profile_policy.get("next_command", "")),
        "closeout_trust": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section closeout_trust --format json",
            cli_invoke=config.cli_invoke,
        ),
        "completion_contract": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section completion_contract --format json",
            cli_invoke=config.cli_invoke,
        ),
        "decision_pressure": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section decision_pressure --format json",
            cli_invoke=config.cli_invoke,
        ),
        "workflow_compliance_summary": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section workflow_compliance_summary --format json",
            cli_invoke=config.cli_invoke,
        ),
        "dogfooding_signal_status": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section dogfooding_signal_status --format json",
            cli_invoke=config.cli_invoke,
        ),
    }
    follow_up_owner = str(
        _as_dict(options.get("keep-parent-open")).get("owner") or completion_boundary.get("required_follow_up_owner") or ""
    ).strip()
    review_compression = _closeout_report_review_compression_payload(
        profile_policy=profile_policy,
        trust=trust,
        completeness=completeness,
        decision_review=decision_review,
        behavior_preservation=behavior_preservation,
        residual_risk=residual_risk,
        follow_up_owner=follow_up_owner,
        detail_commands=detail_commands,
    )
    closeout_adoption = _closeout_report_adoption_payload(
        profile_policy=profile_policy,
        final_response_rendering=final_response_rendering,
        decision_review=decision_review,
        review_compression=review_compression,
    )
    closeout_authority_boundary = _authority_boundary_payload(
        surface="closeout_report",
        enforced_by_aw=[str(blocker) for blocker in blockers] if isinstance(blockers, list) else [],
        observed_by_aw=[
            f"planning_evidence_state={evidence_state}",
            f"selected_profile={profile_policy['selected_profile']}",
            f"trust={trust}",
            f"completion_decision={completion_decision}",
            f"workflow_obligation_required_count={workflow_obligation_contract['required_count']}",
        ],
        recommended_by_aw=[str(next_action), profile_policy["next_command"]],
        proof_hints=[validation_proof],
        agent_owned_decisions=[
            "final user-facing wording",
            "whether proof and acceptance justify a completion claim",
            "which caveats are material enough to include in chat",
        ],
        human_owned_decisions=["acceptance of residual intent or follow-up ownership when the report names open residue"],
        rule=(
            "closeout_report renders derived evidence and gates; it must not be described as AW making the agent's "
            "semantic completion judgment."
        ),
    )
    planning_evidence = {
        "authority": evidence_authority or "no-planning-evidence",
        "source": evidence_source,
        "state": evidence_state,
        "rule": "Retained or archived evidence may explain the just-finished lane, but only active Planning state can govern current work.",
    }
    closeout_ready = _closeout_ready_phase_answer_payload(
        completion_gate=completion_gate,
        proof_execution=proof_execution,
        planning_evidence=planning_evidence,
        installed_state_residue=installed_state_closeout_residue,
        workflow_compliance_summary=workflow_compliance_summary,
        detail_commands=detail_commands,
    )
    return {
        "kind": "agentic-workspace/closeout-report/v1",
        "status": "present" if active_planning_record else "guidance-only",
        "authority": "derived-projection",
        "authority_boundary": closeout_authority_boundary,
        "planning_evidence": planning_evidence,
        "closeout_ready": closeout_ready,
        "profile": profile_policy["selected_profile"],
        "profile_policy": profile_policy,
        "trust": trust,
        "work_completed": work_completed,
        "interpreted_intent": {
            "requested_outcome": requested_outcome,
            "intent_evidence": intent_evidence,
            "intent_satisfaction": {
                key: intent_check.get(key)
                for key in ("status", "trust", "required_follow_on", "continuation_surface")
                if key in intent_check
            },
            "closure_decision": str(closure_check.get("closure decision") or closure_check.get("closure_decision") or "").strip(),
        },
        "intent_evidence": intent_evidence,
        "parent_intent_status": parent_intent_status,
        "applicable_intent_status": applicable_intent_status,
        "architecture_principles_status": architecture_principles,
        "installed_state_residue": installed_state_closeout_residue,
        "changes": {
            "changed_surfaces": changed_surfaces,
            "scope_touched": str(execution.get("scope touched") or "").strip(),
            "source": "planning.closeout_evidence.execution_run"
            if evidence_is_retained
            else "planning.archive.execplan.execution_run"
            if evidence_is_archived
            else "planning.active.planning_record.execution_run",
        },
        "validation": {
            "proof": validation_proof,
            "proof_achieved_now": proof_achieved_now,
            "proof_execution": proof_execution,
            "proof_confidence": closeout_trust.get("proof_confidence", {}),
            "behavior_preservation": behavior_preservation,
        },
        "gaps_and_residual_risk": {
            "completion_blockers": blockers,
            "completion_gate": completion_gate,
            "task_posture_followthrough": task_posture_followthrough,
            "residual_risk": residual_risk,
            "durable_residue_action": closeout_trust.get("durable_residue_action", {}),
            "installed_state_residue": installed_state_closeout_residue,
            "workflow_trust_impact": workflow_compliance_summary.get("trust_impact", "unknown")
            if isinstance(workflow_compliance_summary, dict)
            else "unknown",
        },
        "workflow_obligation_contract": workflow_obligation_contract,
        "completion_gate": completion_gate,
        "task_posture_followthrough": task_posture_followthrough,
        "closure_boundary": {
            "completion_decision": completion_contract.get("completion_decision", "unknown"),
            "decision_reasons": completion_contract.get("decision_reasons", []),
            "completion_boundary": completion_boundary,
            "terminal_action": closeout_trust.get("terminal_action", {}),
            "completion_options": completion_options,
        },
        "traceability": {
            "status": "present",
            "row_count": len(traceability_rows),
            "rows": traceability_rows,
        },
        "completeness": completeness,
        "decision_review": decision_review,
        "review_compression": review_compression,
        "closeout_adoption": closeout_adoption,
        "final_response_rendering": final_response_rendering,
        "next_action": {
            "summary": next_action,
            "command": profile_policy["next_command"],
            "run": profile_policy["next_command"],
        },
        "detail_commands": detail_commands,
        "source_fields": [
            "planning.closeout_evidence.execution_run"
            if evidence_is_retained
            else "planning.archive.execplan.execution_run"
            if evidence_is_archived
            else "planning.active.planning_record.execution_run",
            "planning.closeout_evidence.proof_report"
            if evidence_is_retained
            else "planning.archive.execplan.proof_report"
            if evidence_is_archived
            else "planning.active.planning_record.proof_report",
            "planning.closeout_evidence.closure_check"
            if evidence_is_retained
            else "planning.archive.execplan.closure_check"
            if evidence_is_archived
            else "planning.active.planning_record.closure_check",
            "report.closeout_trust",
            "report.completion_contract",
            "report.verification",
            "report.architecture_principles",
        ],
        "boundary": (
            "This report is derived operator-facing presentation. It stores no execution state, does not decide proof, "
            "and does not replace Planning, Verification, or closeout_trust as canonical owners."
        ),
    }


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
        config = config_lib.load_workspace_config(target_root=target_root, valid_presets=set(descriptors))
        status_payload = _proof_lifecycle_command(
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
        doctor_payload = _proof_lifecycle_command(
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


def _release_ownership_payload(target_root: Path | None) -> dict[str, Any]:
    if target_root is None:
        return {}
    path = target_root / ".github" / "release-ownership.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _coordinated_release_proof_lane(*, target_root: Path | None, changed_paths: list[str]) -> dict[str, Any] | None:
    ownership = _release_ownership_payload(target_root)
    if not ownership:
        return None
    release_version_paths = {
        str(path).strip() for path in _list_payload(ownership.get("release_commit_allowed_paths")) if str(path).strip()
    }
    release_surface_exact = {
        str(ownership.get("canonical_version_source") or "").strip(),
        ".github/release-ownership.json",
        ".github/workflows/pr-semver-label.yml",
        ".github/workflows/release-from-semver-label.yml",
        ".github/workflows/release.yml",
        "docs/release-and-versioning.md",
        "tests/test_release_workflows.py",
    }
    release_surface_exact = {path for path in release_surface_exact if path}
    release_surface_prefixes = ("scripts/release/",)
    matched = [
        path
        for path in changed_paths
        if path in release_version_paths or path in release_surface_exact or path.startswith(release_surface_prefixes)
    ]
    if not matched:
        return None
    return {
        "id": "coordinated_release_proof",
        "when": "changed paths touch release-owned coordinated version or release workflow surfaces",
        "enough_proof": [
            "make test-workspace",
            "make lint-workspace",
            "make test-memory",
            "make lint-memory",
            "make test-planning",
            "make lint-planning",
            "make typecheck-planning",
            "make test-verification",
            "make lint-verification",
            "uv run python scripts/check/check_generated_command_packages.py",
            "uv run python scripts/check/run_operation_conformance_tests.py --target all",
            "uv run python scripts/run_agentic_workspace.py defaults --section root_cli_authority --format json",
            "uv run pytest tests/test_release_workflows.py -q",
        ],
        "proof_kind": "full-test",
        "proof_responsibility": "local-closeout",
        "execution_mode": "serial-recommended",
        "ci_relationship": "Release CI may repeat coordinated proof; local closeout should show the grouped release proof rationale before claiming release readiness.",
        "recovery_signal": "Release-owned version or workflow changes need coordinated package, generated-surface, conformance, and release-authority proof.",
        "matched_paths": matched,
        "release_model": str(ownership.get("release_model", "coordinated-workspace")),
        "release_ownership_path": ".github/release-ownership.json",
    }


def _runtime_mirror_consistency_proof_lane(*, changed_paths: list[str]) -> dict[str, Any] | None:
    matched_paths = [
        path
        for path in changed_paths
        if path
        in {
            "src/agentic_workspace/workspace_runtime_core.py",
            "src/agentic_workspace/workspace_runtime_primitives.py",
        }
    ]
    if not matched_paths:
        return None
    return {
        "id": "runtime_mirror_consistency",
        "when": "changed path edits mirrored runtime packet surfaces",
        "enough_proof": [
            "uv run python scripts/run_agentic_workspace.py report --target . --section runtime_mirror_consistency --format json"
        ],
        "recovery_signal": "runtime mirror mismatches should block closeout until core and primitives expose the same packet shape",
        "proof_kind": "targeted-static-check",
        "proof_responsibility": "local-closeout",
        "matched_paths": matched_paths,
    }


def _release_group_command(command: str) -> str:
    text = command.lower()
    if "test-memory" in text or "lint-memory" in text or "packages/memory" in text:
        return "memory-package"
    if "test-planning" in text or "lint-planning" in text or "typecheck-planning" in text or "packages/planning" in text:
        return "planning-package"
    if "test-verification" in text or "lint-verification" in text or "packages/verification" in text:
        return "verification-package"
    if "check_generated_command_packages.py" in text or "generate_command_packages.py" in text:
        return "generated-command-package-freshness"
    if "run_operation_conformance_tests.py" in text:
        return "operation-conformance"
    if "defaults --section root_cli_authority" in text or "test_release_workflows.py" in text:
        return "release-defaults-version-authority"
    return "workspace-runtime"


def _release_proof_profile_payload(
    *, changed_paths: list[str], selected_lanes: list[dict[str, Any]], required_commands: list[str]
) -> dict[str, Any] | None:
    release_lane = next((lane for lane in selected_lanes if str(lane.get("id", "")) == "coordinated_release_proof"), None)
    if release_lane is None:
        return None
    group_order = [
        "workspace-runtime",
        "memory-package",
        "planning-package",
        "verification-package",
        "generated-command-package-freshness",
        "operation-conformance",
        "release-defaults-version-authority",
    ]
    group_metadata = {
        "workspace-runtime": ("Workspace runtime behavior", "behavioral"),
        "memory-package": ("Memory package behavior", "behavioral"),
        "planning-package": ("Planning package behavior", "behavioral"),
        "verification-package": ("Verification package behavior", "behavioral"),
        "generated-command-package-freshness": ("Generated command package freshness/parity", "freshness-parity"),
        "operation-conformance": ("Operation conformance", "behavioral"),
        "release-defaults-version-authority": ("Release/defaults/version authority", "release-authority"),
    }
    grouped: dict[str, list[str]] = {group_id: [] for group_id in group_order}
    for command in required_commands:
        group_id = _release_group_command(str(command))
        if group_id in grouped and command not in grouped[group_id]:
            grouped[group_id].append(str(command))
    groups = []
    for group_id in group_order:
        title, proof_purpose = group_metadata[group_id]
        commands = grouped[group_id]
        groups.append(
            {
                "id": group_id,
                "title": title,
                "status": "required" if commands else "unavailable",
                "obligation": "required",
                "proof_purpose": proof_purpose,
                "commands": commands,
                "claim_supported": (
                    "coordinated release proof remains legible for this protected surface"
                    if commands
                    else "release proof is missing selected commands for this protected surface"
                ),
            }
        )
    return {
        "kind": "agentic-workspace/release-proof-profile/v1",
        "id": "coordinated-release-proof",
        "status": "required",
        "release_model": str(release_lane.get("release_model", "coordinated-workspace")),
        "matched_paths": list(release_lane.get("matched_paths", [])),
        "triggered_by": changed_paths,
        "release_ownership_path": str(release_lane.get("release_ownership_path", ".github/release-ownership.json")),
        "groups": groups,
        "rule": (
            "This profile explains why coordinated release proof is broad; it groups selected required commands by "
            "protected release surface and proof purpose without relaxing required_commands."
        ),
    }


def _proof_route_authority_for_lane(*, lane: dict[str, Any], route_source: str, learned_confirmed: bool = False) -> dict[str, Any]:
    lane_id = str(lane.get("id", ""))
    if lane.get("learned_route"):
        authority = "repo-learned-route-table"
        fallback_status = "repo-learned-confirmed"
        route = lane.get("learned_route", {}) if isinstance(lane.get("learned_route"), dict) else {}
        surface = str(route.get("source_path") or ".agentic-workspace/proof-route-hints.json")
    elif learned_confirmed:
        authority = "agent-learned-confirmed-route"
        fallback_status = "confirmed-repo-knowledge"
        surface = str(lane.get("authority_surface", ".agentic-workspace/memory/repo"))
    elif lane.get("domain_lane"):
        authority = "repo-owned-domain-proof-lane"
        fallback_status = "repo-confirmed"
        surface = ".agentic-workspace/config.toml [assurance.domain_proof_lanes]"
    elif lane.get("local_overlay"):
        authority = "local-only-high-risk-profile"
        fallback_status = "local-only"
        surface = ".agentic-workspace/config.local.toml [local_overlay.high_risk]"
    elif lane.get("proof_profile") or lane.get("requirement_id") or lane.get("subsystem"):
        authority = "repo-owned-proof-policy"
        fallback_status = "repo-confirmed"
        surface = ".agentic-workspace/config.toml"
    elif lane_id.startswith("verification:"):
        authority = "verification-manual-protocol"
        fallback_status = "repo-confirmed"
        surface = ".agentic-workspace/verification/manifest.toml"
    elif route_source == "manual-fallback":
        authority = "generic-manual-fallback"
        fallback_status = "fallback"
        surface = "package fallback"
    elif route_source == "live-adapted-target-capability":
        authority = "live-target-capability"
        fallback_status = "candidate-live-confirmed"
        surface = "target repo command discovery"
    elif lane_id.startswith("subsystem:"):
        authority = "repo-owned-subsystem-route"
        fallback_status = "repo-confirmed"
        surface = ".agentic-workspace/OWNERSHIP.toml"
    else:
        authority = "package-seed-or-default-route"
        fallback_status = "seed-fallback"
        surface = "package proof defaults"
    promotion_candidate = fallback_status in {"seed-fallback", "fallback", "candidate-live-confirmed"}
    return {
        "kind": "proof-route-authority/v1",
        "authority": authority,
        "fallback_status": fallback_status,
        "route_source": route_source,
        "authority_surface": surface,
        "promotion_candidate": promotion_candidate,
        "maintenance_target": ".agentic-workspace/proof-route-hints.json" if promotion_candidate else surface,
        "rule": "Prefer confirmed repo/agent-learned/Verification proof knowledge over package defaults and generic fallbacks.",
    }


def _proof_route_precedence_payload(*, selected_commands: list[dict[str, Any]]) -> dict[str, Any]:
    priority = {
        "host-configured-proof-profile": 100,
        "host-declared-domain-proof-lane": 98,
        "host-configured-subsystem": 95,
        "repo-learned-proof-route": 90,
        "verification-manual-protocol": 85,
        "local-only-high-risk-overlay": 75,
        "live-adapted-target-capability": 60,
        "live-confirmed-proof-rule": 40,
        "manual-fallback": 20,
    }
    by_command: dict[str, list[dict[str, Any]]] = {}
    for command in selected_commands:
        if not isinstance(command, dict):
            continue
        command_text = str(command.get("command", "")).strip()
        if not command_text:
            continue
        by_command.setdefault(command_text, []).append(command)
    competing: list[dict[str, Any]] = []
    for command_text, matches in by_command.items():
        if len(matches) < 2:
            continue
        ordered = sorted(
            matches,
            key=lambda item: (
                priority.get(str(item.get("selected_from", "")), 0),
                1
                if str(item.get("fallback_status", "")) in {"repo-confirmed", "repo-learned-confirmed", "confirmed-repo-knowledge"}
                else 0,
            ),
            reverse=True,
        )
        winner = ordered[0]
        competing.append(
            {
                "kind": "proof-route-precedence-case/v1",
                "command": command_text,
                "winner": {
                    "lane": str(winner.get("lane", "")),
                    "route_source": str(winner.get("selected_from", "")),
                    "route_authority": str(winner.get("route_authority", "")),
                    "authority_surface": str(winner.get("authority_surface", "")),
                },
                "overridden": [
                    {
                        "lane": str(item.get("lane", "")),
                        "route_source": str(item.get("selected_from", "")),
                        "route_authority": str(item.get("route_authority", "")),
                        "authority_surface": str(item.get("authority_surface", "")),
                    }
                    for item in ordered[1:]
                ],
            }
        )
    return {
        "kind": "proof-route-precedence/v1",
        "status": "competing-routes" if competing else "no-competition",
        "priority_order": [
            "host-configured-proof-profile",
            "host-declared-domain-proof-lane",
            "host-configured-subsystem",
            "repo-learned-proof-route",
            "verification-manual-protocol",
            "live-adapted-target-capability",
            "live-confirmed-proof-rule",
            "manual-fallback",
        ],
        "cases": competing,
        "rule": "When the same command is selected from multiple sources, repo-owned and learned authority should be visible and preferred over package defaults.",
    }


def _local_overlay_item_matches(*, item: dict[str, Any], changed_paths: list[str], task_text: str | None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    path_patterns = [str(pattern).strip() for pattern in _list_payload(item.get("applies_to_paths")) if str(pattern).strip()]
    for changed_path in changed_paths:
        for pattern in path_patterns:
            if fnmatch.fnmatch(changed_path, pattern):
                reasons.append(f"path:{changed_path} matches {pattern}")
                break
    normalized_task = (task_text or "").lower()
    for marker in [str(marker).strip() for marker in _list_payload(item.get("applies_to_task_markers")) if str(marker).strip()]:
        if marker.lower() in normalized_task:
            reasons.append(f"task-marker:{marker}")
    return (bool(reasons), reasons)


def _local_high_risk_overlay_for_work(
    *, config: WorkspaceConfig | None, changed_paths: list[str], task_text: str | None, cli_invoke: str = DEFAULT_CLI_INVOKE
) -> dict[str, Any]:
    overlay = config.local_override.high_risk_overlay if config is not None else {}
    if not isinstance(overlay, dict) or overlay.get("status") != "configured":
        return {
            "kind": "agentic-workspace/local-high-risk-overlay/v1",
            "status": "absent",
            "active_count": 0,
            "detail_command": _command_with_cli_invoke(
                command="agentic-workspace report --target ./repo --section local_high_risk_overlay --format json",
                cli_invoke=cli_invoke,
            ),
        }
    sections = _as_dict(overlay.get("sections"))
    active_by_section: dict[str, list[dict[str, Any]]] = {}
    for section, raw_items in sections.items():
        active_items: list[dict[str, Any]] = []
        for raw_item in _list_payload(raw_items):
            if not isinstance(raw_item, dict):
                continue
            matched, reasons = _local_overlay_item_matches(item=raw_item, changed_paths=changed_paths, task_text=task_text)
            if not matched:
                continue
            item = dict(raw_item)
            item["matched_because"] = reasons
            item["provenance"] = {
                "source_layer": item.get("source_layer", "local-config"),
                "surface": item.get("surface", ".agentic-workspace/config.local.toml [local_overlay.high_risk]"),
                "authority": "local-only-overlay",
                "shared_repo_policy": False,
            }
            active_items.append(item)
        active_by_section[str(section)] = active_items
    active_count = sum(len(items) for items in active_by_section.values())
    return {
        "kind": "agentic-workspace/local-high-risk-overlay/v1",
        "status": "active" if active_count else "configured-no-match",
        "configured_count": int(overlay.get("item_count", 0) or 0),
        "active_count": active_count,
        "changed_paths": changed_paths,
        "active": active_by_section,
        "warnings": _list_payload(overlay.get("warnings")),
        "authority_boundary": {
            "kind": "agentic-workspace/authority-boundary/v1",
            "surface": "local_high_risk_overlay",
            "authority_class": "local-advisory",
            "observed_by_aw": ["local config overlay declarations", "changed-path/task-marker match facts"],
            "recommended_by_aw": ["carry matched local guardrails into proof and closeout claims"],
            "agent_owned_decisions": ["semantic applicability", "whether proof and review evidence satisfy the requested task"],
            "human_owned_decisions": ["host policy acceptance", "security/legal review", "local override trust"],
            "rule": "Local-only overlays may shape this checkout's workflow but never become checked-in host policy or certification.",
        },
        "detail_command": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section local_high_risk_overlay --format json",
            cli_invoke=cli_invoke,
        ),
    }


def _local_overlay_for_work(
    *, config: WorkspaceConfig | None, changed_paths: list[str], task_text: str | None, cli_invoke: str = DEFAULT_CLI_INVOKE
) -> dict[str, Any]:
    overlay = config.local_override.local_overlay if config is not None else {}
    if not isinstance(overlay, dict) or overlay.get("status") != "configured":
        return {
            "kind": "agentic-workspace/local-overlay/v1",
            "status": "absent",
            "active_count": 0,
            "detail_command": _command_with_cli_invoke(
                command="agentic-workspace report --target ./repo --section local_overlay --format json",
                cli_invoke=cli_invoke,
            ),
        }
    sections = _as_dict(overlay.get("sections"))
    active_guidance: list[dict[str, Any]] = []
    for raw_item in _list_payload(sections.get("guidance")):
        if not isinstance(raw_item, dict):
            continue
        matched, reasons = _local_overlay_item_matches(item=raw_item, changed_paths=changed_paths, task_text=task_text)
        if not matched:
            continue
        item = dict(raw_item)
        item["matched_because"] = reasons
        item["provenance"] = {
            "source_layer": item.get("source_layer", "local-config"),
            "surface": item.get("surface", ".agentic-workspace/config.local.toml [local_overlay.guidance]"),
            "authority": "local-only-overlay",
            "shared_repo_policy": False,
        }
        active_guidance.append(item)
    active_count = len(active_guidance)
    return {
        "kind": "agentic-workspace/local-overlay/v1",
        "status": "active" if active_count else "configured-no-match",
        "configured_count": int(overlay.get("item_count", 0) or 0),
        "ordinary_guidance_count": int(overlay.get("ordinary_guidance_count", 0) or 0),
        "high_risk_profile_count": int(overlay.get("high_risk_profile_count", 0) or 0),
        "active_count": active_count,
        "changed_paths": changed_paths,
        "active": {"guidance": active_guidance},
        "warnings": _list_payload(overlay.get("warnings")),
        "authority_boundary": {
            "kind": "agentic-workspace/authority-boundary/v1",
            "surface": "local_overlay",
            "authority_class": "local-advisory",
            "observed_by_aw": ["local overlay declarations", "changed-path/task-marker match facts"],
            "recommended_by_aw": ["carry matched local guidance into workflow choices"],
            "agent_owned_decisions": ["semantic applicability", "whether local guidance is sufficient or only advisory"],
            "human_owned_decisions": ["host policy acceptance", "local override trust"],
            "rule": "Local overlays may shape this checkout's workflow but never become checked-in host policy or certification.",
        },
        "detail_command": _command_with_cli_invoke(
            command="agentic-workspace report --target ./repo --section local_overlay --format json",
            cli_invoke=cli_invoke,
        ),
    }


def _local_overlay_lanes(overlay: dict[str, Any]) -> list[dict[str, Any]]:
    if overlay.get("status") != "active":
        return []
    active = _as_dict(overlay.get("active"))
    lanes: list[dict[str, Any]] = []
    for item in _list_payload(active.get("source_maps")):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            continue
        lanes.append(
            {
                "id": f"local-overlay-source:{item_id}",
                "when": "local-only high-risk overlay source map matched changed paths or task markers",
                "enough_proof": _list_payload(item.get("required_commands")),
                "manual_evidence": _list_payload(item.get("manual_evidence")) or _list_payload(item.get("required_sources")),
                "review_aids": _list_payload(item.get("review_aids")),
                "proof_profile": next(iter(_list_payload(item.get("proof_profiles"))), ""),
                "authority_refs": _list_payload(item.get("authority_refs")) or _list_payload(item.get("required_sources")),
                "claim_boundary": str(item.get("claim_boundary") or ""),
                "local_overlay": {
                    "section": "source_maps",
                    "id": item_id,
                    "source_layer": item.get("source_layer"),
                    "impact": item.get("impact"),
                    "matched_because": _list_payload(item.get("matched_because")),
                },
                "proof_responsibility": "local-closeout",
                "execution_mode": "serial-recommended",
                "recovery_signal": "local source-of-truth mapping must be considered before high-risk closeout claims",
            }
        )
    for item in _list_payload(active.get("validation_profiles")):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            continue
        lanes.append(
            {
                "id": f"local-overlay-validation:{item_id}",
                "when": "local-only validation profile matched changed paths or task markers",
                "enough_proof": _list_payload(item.get("required_commands")),
                "manual_evidence": _list_payload(item.get("manual_checks")),
                "optional_commands": _list_payload(item.get("optional_commands")),
                "review_aids": _list_payload(item.get("manual_checks")),
                "proof_profile": next(iter(_list_payload(item.get("proof_profiles"))), ""),
                "authority_refs": _list_payload(item.get("authority_refs")),
                "claim_boundary": str(item.get("claim_boundary") or ""),
                "validation_profile": {
                    "id": item_id,
                    "category": item.get("category"),
                    "unavailable_routes": _list_payload(item.get("unavailable_routes")),
                    "source_layer": item.get("source_layer"),
                    "impact": item.get("impact"),
                    "matched_because": _list_payload(item.get("matched_because")),
                },
                "proof_responsibility": "local-closeout",
                "execution_mode": "serial-recommended",
                "recovery_signal": "matched local validation profile must be resolved or consciously substituted before closeout",
            }
        )
    return lanes


def _local_overlay_claim_effects(overlay: dict[str, Any]) -> dict[str, Any]:
    if overlay.get("status") != "active":
        return {"status": overlay.get("status", "absent"), "blockers": [], "warnings": []}
    active = _as_dict(overlay.get("active"))
    blockers: list[str] = []
    warnings: list[str] = []
    ci_items: list[dict[str, Any]] = []
    unresolved_items: list[dict[str, Any]] = []
    guardrail_items: list[dict[str, Any]] = []
    template_items: list[dict[str, Any]] = []
    for item in _list_payload(active.get("ci_validation")):
        if not isinstance(item, dict):
            continue
        ci_items.append(item)
        state = str(item.get("validation_state") or "ci_unavailable")
        policy = str(item.get("local_substitute_policy") or "insufficient")
        if state in {"ci_failed", "ci_pending", "ci_unavailable", "quota_exhausted", "logs_unavailable"}:
            blockers.append(f"validation-state:{state}")
        if policy in {"insufficient", "human-review-only"}:
            blockers.append(f"local-substitute-policy:{policy}")
        elif policy == "advisory":
            warnings.append("local substitute validation is advisory only")
    for item in _list_payload(active.get("unresolved_questions")):
        if not isinstance(item, dict):
            continue
        unresolved_items.append(item)
        category = str(item.get("category") or "safe-follow-up")
        if category in {"merge-blocker", "release-blocker", "human-review-required"}:
            blockers.append(f"unresolved-question:{category}")
        elif category == "intentionally-deferred":
            warnings.append("unresolved question intentionally deferred with owner")
    for item in _list_payload(active.get("guardrails")):
        if not isinstance(item, dict):
            continue
        guardrail_items.append(item)
        impact = str(item.get("impact") or "advisory")
        if impact in {"blocking", "human-review-only", "claim-limiting"}:
            blockers.append(f"guardrail:{impact}")
    for item in _list_payload(active.get("templates")):
        if not isinstance(item, dict):
            continue
        template_items.append(item)
        state = str(item.get("state") or "")
        if state in {"missing", "ambiguous", "unsupported"}:
            blockers.append(f"template-preservation:{state}")
    return {
        "status": "attention" if blockers else "advisory" if warnings else "clear",
        "blockers": _dedupe(blockers),
        "warnings": _dedupe(warnings),
        "ci_validation": ci_items,
        "unresolved_questions": unresolved_items,
        "guardrails": guardrail_items,
        "templates": template_items,
    }


def _manual_proof_obligations_payload(*, verification: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(verification, dict):
        return []
    evidence_by_protocol = {
        str(item.get("protocol_id", "")): item
        for item in _list_payload(verification.get("evidence_status"))
        if isinstance(item, dict) and str(item.get("protocol_id", "")).strip()
    }
    routes_by_protocol: dict[str, list[dict[str, Any]]] = {}
    for route in _list_payload(verification.get("active_proof_routes")):
        if not isinstance(route, dict):
            continue
        for protocol_ref in _list_payload(route.get("protocol_refs")):
            routes_by_protocol.setdefault(str(protocol_ref), []).append(route)
    obligations: list[dict[str, Any]] = []
    for protocol in _list_payload(verification.get("active_protocols")):
        if not isinstance(protocol, dict):
            continue
        protocol_id = str(protocol.get("id", "")).strip()
        if not protocol_id:
            continue
        status = evidence_by_protocol.get(protocol_id, {})
        expected = [
            str(item).strip()
            for item in _list_payload(status.get("expected_evidence") or protocol.get("expected_evidence"))
            if str(item).strip()
        ]
        missing = [str(item).strip() for item in _list_payload(status.get("missing_evidence")) if str(item).strip()]
        stale = [str(item).strip() for item in _list_payload(status.get("stale_expected_evidence")) if str(item).strip()]
        protocol_routes = routes_by_protocol.get(protocol_id, [])
        review_aids = _dedupe(
            [str(item).strip() for item in _list_payload(protocol.get("review_aids")) if str(item).strip()]
            + [str(item).strip() for route in protocol_routes for item in _list_payload(route.get("review_aids")) if str(item).strip()]
        )
        steps = [str(item).strip() for item in _list_payload(protocol.get("steps")) if str(item).strip()]
        authority_refs = [str(item).strip() for item in _list_payload(protocol.get("authority_refs")) if str(item).strip()]
        if not (expected or missing or stale or review_aids or steps or authority_refs):
            continue
        required = bool(missing or stale or expected)
        obligations.append(
            {
                "kind": "manual-proof-obligation/v1",
                "id": f"verification:{protocol_id}",
                "status": "missing-evidence" if missing else "stale-evidence" if stale else "satisfied" if expected else "review",
                "required": required,
                "protocol_id": protocol_id,
                "title": str(protocol.get("title", "")),
                "purpose": str(protocol.get("purpose", "")),
                "review_owner": str(protocol.get("review_owner") or protocol.get("ownerless_reason") or ""),
                "expected_evidence": expected,
                "missing_evidence": missing,
                "stale_evidence": stale,
                "steps": steps,
                "reference_material": authority_refs,
                "review_aids": review_aids,
                "proof_route_ids": [str(route.get("id")) for route in protocol_routes if route.get("id")],
                "authority": _proof_route_authority_for_lane(
                    lane={"id": f"verification:{protocol_id}"}, route_source="verification-manual-protocol"
                ),
                "claim_boundary": (
                    "completion-claims-qualified-until-manual-evidence-recorded-or-waived"
                    if required
                    else "manual-verification-evidence-present-or-review-only"
                ),
            }
        )
    return obligations


def _proof_route_maintenance_payload(
    *,
    selected_lanes: list[dict[str, Any]],
    selected_commands: list[dict[str, Any]],
    learned_route_hints: dict[str, Any],
    manual_proof_obligations: list[dict[str, Any]],
) -> dict[str, Any]:
    stale_hints = [hint for hint in _list_payload(learned_route_hints.get("stale")) if isinstance(hint, dict)]
    invalid_hints = [hint for hint in _list_payload(learned_route_hints.get("invalid")) if isinstance(hint, dict)]
    fallback_commands = [
        command
        for command in selected_commands
        if isinstance(command, dict)
        and str(command.get("fallback_status", "")) in {"seed-fallback", "fallback", "candidate-live-confirmed"}
    ]
    manual_missing = [item for item in manual_proof_obligations if isinstance(item, dict) and item.get("required")]
    suggestions: list[dict[str, Any]] = []
    route_hints_status = str(learned_route_hints.get("status") or "unavailable")
    route_hints_surface = PROOF_ROUTE_HINTS_PATH.as_posix()
    route_hints_surface_contract = {
        "kind": "proof-route-hints-surface-contract/v1",
        "surface": route_hints_surface,
        "surface_status": "present" if route_hints_status == "loaded" else "absent",
        "owner": "repo",
        "schema": "agentic-workspace/proof-route-hints/v1",
        "schema_path": "src/agentic_workspace/contracts/schemas/proof_route_hints.schema.json",
        "create_when": "only after repeated fallback reliance or explicit setup/adopt proof-route learning needs durable capture",
        "authority_boundary": "advisory route memory; configured proof policy and live target capabilities remain primary",
    }

    def attach_route_hints_contract(suggestion: dict[str, Any]) -> dict[str, Any]:
        if suggestion.get("target_surface") == route_hints_surface:
            suggestion = {
                **suggestion,
                "target_surface_status": route_hints_surface_contract["surface_status"],
                "target_surface_contract": route_hints_surface_contract,
            }
        return suggestion

    for command in fallback_commands:
        command_text = str(command.get("command", ""))
        reason = (
            "new target proof capability needs route-table promotion"
            if str(command.get("fallback_status", "")) == "candidate-live-confirmed"
            else "selected proof relies on fallback or seed route"
        )
        suggestions.append(
            attach_route_hints_contract(
                {
                    "kind": "proof-route-maintenance-suggestion/v1",
                    "reason": reason,
                    "route_id": f"promote-{str(command.get('lane', 'proof-route')).replace(':', '-')}",
                    "matcher": {"selected_lane": str(command.get("lane", ""))},
                    "command": command_text,
                    "target_surface": ".agentic-workspace/proof-route-hints.json",
                    "source_observation": str(command.get("selected_from", "")),
                    "recommended_state": "confirmed",
                }
            )
        )
        if str(command.get("ci_relationship", "")).strip():
            suggestions.append(
                attach_route_hints_contract(
                    {
                        "kind": "proof-route-maintenance-suggestion/v1",
                        "reason": "CI-learned proof gap should be captured as repo route authority",
                        "route_id": f"ci-gap-{str(command.get('lane', 'proof-route')).replace(':', '-')}",
                        "matcher": {
                            "selected_lane": str(command.get("lane", "")),
                            "ci_relationship": str(command.get("ci_relationship", "")),
                        },
                        "command": command_text,
                        "target_surface": ".agentic-workspace/proof-route-hints.json",
                        "source_observation": str(command.get("selected_from", "")),
                        "recommended_state": "confirmed-with-ci-provenance",
                    }
                )
            )
    for hint in stale_hints:
        suggestions.append(
            attach_route_hints_contract(
                {
                    "kind": "proof-route-maintenance-suggestion/v1",
                    "reason": "learned proof route is stale or unavailable",
                    "route_id": str(hint.get("id", "")),
                    "matcher": {"scope": str(hint.get("scope", "")), "intent_type": str(hint.get("intent_type", ""))},
                    "command": str(hint.get("candidate_command", "")),
                    "target_surface": str(hint.get("source_path") or ".agentic-workspace/proof-route-hints.json"),
                    "source_observation": str(hint.get("confirmation", "stale-or-unavailable")),
                    "recommended_state": "negative-or-superseded-or-reconfirmed",
                }
            )
        )
    for hint in invalid_hints:
        suggestions.append(
            attach_route_hints_contract(
                {
                    "kind": "proof-route-maintenance-suggestion/v1",
                    "reason": "learned proof route lacks authority metadata",
                    "route_id": str(hint.get("id", "")),
                    "matcher": {"missing_fields": ", ".join(str(item) for item in _list_payload(hint.get("missing_fields")))},
                    "command": str(hint.get("candidate_command", "")),
                    "target_surface": str(hint.get("source_path") or ".agentic-workspace/proof-route-hints.json"),
                    "source_observation": str(hint.get("recovery", "")),
                    "recommended_state": "recapture-with-authority",
                }
            )
        )
    for obligation in manual_missing:
        suggestions.append(
            {
                "kind": "proof-route-maintenance-suggestion/v1",
                "reason": "manual Verification evidence is required or missing",
                "route_id": str(obligation.get("id", "")),
                "matcher": {"protocol_id": str(obligation.get("protocol_id", ""))},
                "manual_evidence": ", ".join(str(item) for item in _list_payload(obligation.get("missing_evidence"))),
                "target_surface": ".agentic-workspace/verification/manifest.toml",
                "source_observation": "active verification protocol selected manual proof",
                "recommended_state": "record-evidence-or-waive",
            }
        )
    material = bool(stale_hints or invalid_hints or manual_missing)
    fallback_count = len(fallback_commands)
    new_capability_count = sum(1 for command in fallback_commands if str(command.get("fallback_status", "")) == "candidate-live-confirmed")
    ci_gap_count = sum(1 for command in fallback_commands if str(command.get("ci_relationship", "")).strip())
    return {
        "kind": "proof-route-maintenance/v1",
        "status": "attention" if material else "promotion-available" if fallback_count else "quiet",
        "material_to_current_work": material,
        "fallback_selected_count": fallback_count,
        "new_capability_candidate_count": new_capability_count,
        "ci_gap_candidate_count": ci_gap_count,
        "stale_route_count": len(stale_hints),
        "invalid_authority_count": len(invalid_hints),
        "manual_obligation_count": len(manual_missing),
        "route_hints_surface_contract": route_hints_surface_contract,
        "suggested_updates": suggestions,
        "closeout_rule": (
            "Stale, invalid, or missing manual proof routes require closeout disclosure or durable routing."
            if material
            else "Fallback proof routes may be promoted when repeated, but do not block this closeout by themselves."
        ),
        "rule": "Agents may spend cheap maintenance effort to preserve proof knowledge and avoid repeated rediscovery.",
    }


def _proof_obligations_payload(
    *,
    required_commands: list[str],
    optional_commands: list[str],
    manual_verification: dict[str, Any] | None,
    selected_commands: list[dict[str, Any]] | None = None,
    manual_proof_obligations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    manual_obligations = [item for item in manual_proof_obligations or [] if isinstance(item, dict)]
    required_manual_obligations = [item for item in manual_obligations if item.get("required")]
    manual_required = manual_verification is not None or bool(required_manual_obligations)
    manual_status = manual_verification.get("status") if manual_verification is not None else "not-needed"
    authority_by_command = {str(item.get("command", "")): item for item in selected_commands or []}
    command_authority = []
    for command in required_commands:
        selected = authority_by_command.get(str(command), {})
        command_authority.append(
            {
                "command": str(command),
                "authority_source": str(selected.get("selected_from") or selected.get("lane") or "proof-route-selection"),
                "route_authority": str(selected.get("route_authority") or ""),
                "fallback_status": str(selected.get("fallback_status") or ""),
                "authority_surface": str(selected.get("authority_surface") or ""),
                "lane": str(selected.get("lane") or ""),
                "intent_type": str(selected.get("intent_type") or ""),
                "rule": "Authority describes why AW surfaced the command; the agent still owns proof sufficiency.",
            }
        )
    proof_required = bool(required_commands or manual_required)
    return {
        "kind": "agentic-workspace/proof-obligations/v1",
        "status": "required-proof-selected" if required_commands else "manual-proof-required" if manual_required else "no-required-proof",
        "required_proof": {
            "kind": "agentic-workspace/required-proof/v1",
            "status": "required" if required_commands or manual_required else "not-selected",
            "commands": required_commands,
            "command_authority": command_authority,
            "manual_verification_required": manual_required,
            "manual_verification_status": manual_status,
            "manual_obligations": manual_obligations,
            "manual_obligation_count": len(required_manual_obligations),
            "source_field": "required_commands",
            "action_effect": {
                "force": "required_before_claim" if proof_required else "advisory",
                "allowed_now": "continue-implementation-and-run-required-proof" if proof_required else "continue-implementation",
                "blocked_until_reconciled": ["claim-task-complete"] if proof_required else [],
                "claim_boundary": (
                    "completion-claims-blocked-until-required-proof-passes-or-manual-verification-is-recorded"
                    if proof_required
                    else "no-required-proof-selected"
                ),
                "resolution_selector": "proof.proof_obligations.required_proof",
                "resolution_commands": required_commands,
            },
            "rule": (
                "These commands, or required manual verification when commands are unavailable, are the proof gate for completion claims."
            ),
        },
        "recommended_confidence_checks": {
            "kind": "agentic-workspace/recommended-confidence-checks/v1",
            "status": "available" if optional_commands else "not-selected",
            "commands": optional_commands,
            "source_field": "optional_commands",
            "rule": "Recommended checks may refresh state or raise confidence, but they do not replace or relax required proof.",
        },
        "agent_selected_extra_validation": {
            "kind": "agentic-workspace/agent-selected-extra-validation/v1",
            "status": "agent-owned",
            "commands": [],
            "examples": [
                "rerun a focused failing test after the fix",
                "inspect the final diff against requested acceptance",
                "add task-specific validation when failures or risk expose an unproven behavior",
            ],
            "rule": "The agent may add validation when task intent, failures, or risk warrant it; AW does not pre-claim that extra work is mandatory.",
        },
        "completion_claim_rule": (
            "Completion claims remain blocked until required proof passes or required manual verification is recorded, "
            "then acceptance and residue are reconciled."
        ),
        "compatibility": {
            "required_commands": "unchanged hard-gate field for existing callers",
            "optional_commands": "unchanged advisory confidence-check field for existing callers",
        },
    }


def _lane_activation_summary(lane: dict[str, Any]) -> str:
    applies_because = _list_payload(lane.get("applies_because"))
    if applies_because:
        return str(applies_because[0])
    when = _list_payload(lane.get("when"))
    if when:
        return str(when[0])
    matched_paths = _list_payload(lane.get("matched_paths"))
    if matched_paths:
        return "changed path matched " + ", ".join(str(path) for path in matched_paths[:3])
    return "selected by changed-path proof routing"


def _proof_narrowness_payload(
    *,
    selected_lanes: list[dict[str, Any]],
    selected_commands: list[dict[str, Any]],
    required_commands: list[str],
    optional_commands: list[str],
    broaden_when: list[str],
    escalate_when: list[str],
    manual_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    lane_by_id = {str(lane.get("id", "")): lane for lane in selected_lanes}
    broad_acceptance_lanes = {str(lane_id) for lane_id in _list_payload(_PROOF_SELECTION_RULES.get("broad_acceptance_lanes"))}
    command_tiers = _proof_command_tiers(selected_commands=selected_commands, required_commands=required_commands)
    tier_by_command = {
        str(item.get("command", "")): str(tier.get("id", ""))
        for tier in _list_payload(command_tiers.get("tiers"))
        if isinstance(tier, dict)
        for item in _list_payload(tier.get("commands"))
        if isinstance(item, dict)
    }
    required: list[dict[str, Any]] = []
    for command in selected_commands:
        command_text = str(command.get("command", ""))
        if command_text not in required_commands:
            continue
        lane_id = str(command.get("lane", ""))
        lane = lane_by_id.get(lane_id, {})
        proof_kind = str(lane.get("proof_kind") or command.get("proof_kind") or "")
        command_tier = tier_by_command.get(command_text, "")
        required.append(
            {
                "command": command_text,
                "lane": lane_id,
                "proof_kind": proof_kind,
                "command_tier": command_tier,
                "why_required": _lane_activation_summary(lane),
                "authority": str(command.get("route_authority") or command.get("selected_from") or "proof-route-selection"),
                "acceptance_boundary": True,
                "claim_boundary": "Required proof must pass or be explicitly reconciled before completion is claimed.",
            }
        )
    optional = [
        {
            "command": str(command),
            "why_optional": "Confidence or orientation check; not selected as the completion proof gate for these changed paths.",
            "acceptance_boundary": False,
        }
        for command in optional_commands
    ]
    expansion_triggers: list[dict[str, Any]] = []
    for lane in selected_lanes:
        lane_id = str(lane.get("id", ""))
        proof_kind = str(lane.get("proof_kind", ""))
        if proof_kind == "full-test" or lane_id in broad_acceptance_lanes:
            expansion_triggers.append(
                {
                    "trigger": "selected lane requires broad proof",
                    "lane": lane_id,
                    "why": _lane_activation_summary(lane),
                    "effect": "broad proof is part of required_commands, not optional confidence",
                }
            )
    for condition in broaden_when:
        expansion_triggers.append({"trigger": "broaden_when", "why": str(condition), "effect": "broaden proof before closeout"})
    for condition in escalate_when:
        expansion_triggers.append({"trigger": "escalate_when", "why": str(condition), "effect": "escalate proof or review before closeout"})
    broad_required = (
        any(item.get("proof_kind") == "full-test" for item in required)
        or any(item.get("command_tier") in {"generated_contract", "environmental"} for item in required)
        or any(item.get("lane") in broad_acceptance_lanes for item in required)
    )
    if manual_verification is not None and not required_commands:
        status = "manual_required"
    elif broad_required:
        status = "broad_required"
    elif required_commands:
        status = "narrow_required"
    else:
        status = "no_required_proof"
    return {
        "kind": "agentic-workspace/proof-narrowness/v1",
        "status": status,
        "required_command_count": len(required_commands),
        "required": required,
        "optional_confidence_check_count": len(optional_commands),
        "optional_confidence_checks": optional,
        "expansion_triggers": expansion_triggers,
        "broad_suite_boundary": {
            "status": "required_acceptance_boundary" if broad_required else "not_required_acceptance_boundary",
            "rule": (
                "Broad suite results are part of the acceptance boundary only when selected as required proof before validation runs; "
                "otherwise they are confidence evidence the final report may mention without treating them as required."
            ),
        },
        "final_report_rule": (
            "Report required proof as the acceptance boundary. Report optional checks as confidence or residue unless a visible trigger "
            "promoted them to required proof before they ran."
        ),
    }


def _host_domain_proof_lanes_for_changed_paths(
    *,
    config: WorkspaceConfig | None,
    changed_paths: list[str],
    task_text: str | None,
) -> list[dict[str, Any]]:
    if config is None:
        return []
    haystack = (task_text or "").lower()
    lanes: list[dict[str, Any]] = []
    for lane in config.assurance.domain_proof_lanes:
        path_matches = [
            {"path": path, "pattern": pattern}
            for pattern in lane.applies_to_paths
            for path in changed_paths
            if fnmatch.fnmatch(path, pattern)
        ]
        task_matches = [marker for marker in lane.applies_to_task_markers if marker.lower() in haystack]
        if not (path_matches or task_matches):
            continue
        lanes.append(
            {
                "id": f"domain:{lane.id}",
                "when": "matched host-declared domain proof lane",
                "enough_proof": list(lane.commands),
                "recovery_signal": (
                    "missing or failing host domain proof should block broad closeout until resolved, manually evidenced, or explicitly waived"
                ),
                "proof_kind": "targeted-test" if lane.commands else "manual-verification",
                "proof_responsibility": "local-closeout",
                "execution_mode": "serial-recommended",
                "domain_lane": {
                    "id": lane.id,
                    "purpose": lane.purpose,
                    "source": ".agentic-workspace/config.toml [assurance.domain_proof_lanes]",
                    "owner": lane.owner or "",
                    "matched_paths": path_matches,
                    "matched_task_markers": task_matches,
                    "manual_evidence": list(lane.manual_evidence),
                    "evidence_concepts": list(lane.evidence_concepts),
                    "assurance_requirement_refs": list(lane.assurance_requirement_refs),
                    "proof_profiles": list(lane.proof_profiles),
                    "authority_refs": list(lane.authority_refs),
                    "escalation": list(lane.escalation),
                    "claim_boundary": lane.claim_boundary or "domain-proof-required-before-full-completion-claim",
                    "notes": lane.notes or "",
                },
                "matched_paths": [match["path"] for match in path_matches],
                "review_aids": list(lane.review_aids),
                "manual_evidence": list(lane.manual_evidence),
                "evidence_concepts": list(lane.evidence_concepts),
                "assurance_requirement_refs": list(lane.assurance_requirement_refs),
                "proof_profiles": list(lane.proof_profiles),
                "authority_refs": list(lane.authority_refs),
                "claim_boundary": lane.claim_boundary or "domain-proof-required-before-full-completion-claim",
                "escalate_when": list(lane.escalation),
            }
        )
    return lanes


def _domain_manual_proof_obligations(domain_lanes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    for lane in domain_lanes:
        manual_evidence = [str(item).strip() for item in _list_payload(lane.get("manual_evidence")) if str(item).strip()]
        review_aids = [str(item).strip() for item in _list_payload(lane.get("review_aids")) if str(item).strip()]
        if not (manual_evidence or review_aids):
            continue
        domain = lane.get("domain_lane", {}) if isinstance(lane.get("domain_lane"), dict) else {}
        lane_id = str(lane.get("id", ""))
        obligations.append(
            {
                "kind": "manual-proof-obligation/v1",
                "id": lane_id,
                "status": "missing-evidence" if manual_evidence else "review",
                "required": bool(manual_evidence),
                "protocol_id": "",
                "title": str(domain.get("purpose") or lane_id),
                "purpose": str(domain.get("purpose") or "Host-declared domain proof lane"),
                "review_owner": str(domain.get("owner") or ""),
                "expected_evidence": manual_evidence,
                **(
                    {"expected_evidence_concepts": lane["evidence_concept_usage"]}
                    if isinstance(lane.get("evidence_concept_usage"), dict)
                    else {}
                ),
                "missing_evidence": manual_evidence,
                "stale_evidence": [],
                "steps": [],
                "reference_material": _list_payload(domain.get("authority_refs")),
                "review_aids": review_aids,
                "proof_route_ids": [lane_id],
                "authority": _proof_route_authority_for_lane(lane=lane, route_source="host-declared-domain-proof-lane"),
                "claim_boundary": str(lane.get("claim_boundary") or "domain-proof-required-before-full-completion-claim"),
            }
        )
    return obligations


def _evidence_concept_usage_for_labels(*, labels: list[str], verification: dict[str, Any]) -> dict[str, Any]:
    concepts = verification.get("evidence_concepts", {}) if isinstance(verification, dict) else {}
    concepts = concepts if isinstance(concepts, dict) else {}
    core_by_id = {
        str(item.get("id", "")).strip(): item
        for item in _list_payload(concepts.get("core"))
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    declared = concepts.get("declared_host_by_id", {})
    declared = declared if isinstance(declared, dict) else {}
    used: list[dict[str, Any]] = []
    degraded: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_label in labels:
        label = str(raw_label).strip()
        if not label or label in seen:
            continue
        seen.add(label)
        if label in core_by_id:
            used.append(dict(core_by_id[label]))
        elif label.startswith("host:") and label in declared and isinstance(declared[label], dict):
            used.append(dict(declared[label]))
        elif label.startswith("host:"):
            degraded.append(
                {
                    "id": label,
                    "state": "undeclared-host-concept",
                    "reason": "Declare this host evidence concept under .agentic-workspace/verification/manifest.toml [evidence_concepts] before relying on it for proof or closeout output.",
                }
            )
        else:
            degraded.append(
                {
                    "id": label,
                    "state": "legacy-unclassified-label",
                    "reason": "Use a core concept or a declared host:<term> concept for machine-readable proof semantics.",
                }
            )
    return {
        "used": used,
        "degraded": degraded,
        "status": "attention" if degraded else "declared" if used else "none",
    }


def _annotate_domain_lane_evidence_concepts(*, domain_lanes: list[dict[str, Any]], verification: dict[str, Any]) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for lane in domain_lanes:
        manual_evidence = [str(item).strip() for item in _list_payload(lane.get("manual_evidence")) if str(item).strip()]
        evidence_concepts = [str(item).strip() for item in _list_payload(lane.get("evidence_concepts")) if str(item).strip()]
        usage = _evidence_concept_usage_for_labels(labels=[*manual_evidence, *evidence_concepts], verification=verification)
        next_lane = {**lane, "evidence_concept_usage": usage}
        if isinstance(next_lane.get("domain_lane"), dict):
            next_lane["domain_lane"] = {**next_lane["domain_lane"], "evidence_concept_usage": usage}
        annotated.append(next_lane)
    return annotated


def _degraded_domain_lane_evidence_concepts(domain_lanes: list[dict[str, Any]]) -> list[dict[str, str]]:
    degraded: list[dict[str, str]] = []
    for lane in domain_lanes:
        usage = lane.get("evidence_concept_usage", {})
        usage = usage if isinstance(usage, dict) else {}
        for item in _list_payload(usage.get("degraded")):
            if not isinstance(item, dict):
                continue
            degraded.append(
                {
                    "lane": str(lane.get("id", "")),
                    "id": str(item.get("id", "")),
                    "state": str(item.get("state", "")),
                    "reason": str(item.get("reason", "")),
                }
            )
    return degraded


def _host_closeout_posture_packet(
    *,
    config: WorkspaceConfig | None,
    changed_paths: list[str],
    task_text: str | None,
    selected_lanes: list[dict[str, Any]],
    active_assurance_requirements: dict[str, Any],
) -> dict[str, Any]:
    configured = list(config.assurance.closeout_postures) if config is not None else []
    if not configured:
        return {
            "kind": "agentic-workspace/high-assurance-closeout-posture/v1",
            "status": "not-configured",
            "configured_count": 0,
            "matched_count": 0,
            "matched_postures": [],
        }
    haystack = (task_text or "").lower()
    selected_profiles = {
        str(item).strip()
        for lane in selected_lanes
        for item in [lane.get("proof_profile"), *_list_payload(lane.get("proof_profiles"))]
        if str(item).strip()
    }
    active_requirements = [item for item in _list_payload(active_assurance_requirements.get("active")) if isinstance(item, dict)]
    active_requirement_ids = {
        str(item.get("id") or item.get("requirement_id") or "").strip() for item in active_requirements if str(item).strip()
    }
    active_requirement_profiles = {
        str(item.get("proof_profile") or "").strip() for item in active_requirements if str(item.get("proof_profile") or "").strip()
    }
    selected_profiles.update(active_requirement_profiles)
    evidence_by_requirement: dict[str, set[str]] = {}
    for status in _list_payload(active_assurance_requirements.get("evidence_status")):
        if not isinstance(status, dict):
            continue
        requirement_id = str(status.get("requirement_id") or "").strip()
        if not requirement_id:
            continue
        evidence_by_requirement.setdefault(requirement_id, set()).update(
            str(item).strip() for item in _list_payload(status.get("evidence_present")) if str(item).strip()
        )
    matched_postures: list[dict[str, Any]] = []
    for posture in configured:
        path_matches = [
            {"path": path, "pattern": pattern}
            for pattern in posture.applies_to_paths
            for path in changed_paths
            if fnmatch.fnmatch(path, pattern)
        ]
        task_matches = [marker for marker in posture.applies_to_task_markers if marker.lower() in haystack]
        requirement_matches = sorted(set(posture.assurance_requirement_refs) & active_requirement_ids)
        proof_profile_matches = sorted(set(posture.proof_profiles) & selected_profiles)
        if not (path_matches or task_matches or requirement_matches or proof_profile_matches):
            continue
        evidence_present = sorted(
            {
                evidence
                for requirement_id in requirement_matches
                for evidence in evidence_by_requirement.get(requirement_id, set())
                if evidence
            }
        )
        required_evidence = [str(item).strip() for item in posture.required_evidence if str(item).strip()]
        missing_evidence = [item for item in required_evidence if item not in evidence_present]
        matched_postures.append(
            {
                "id": posture.id,
                "purpose": posture.purpose,
                "source": ".agentic-workspace/config.toml [assurance.closeout_postures]",
                "matched_paths": path_matches,
                "matched_task_markers": task_matches,
                "matched_assurance_requirement_refs": requirement_matches,
                "matched_proof_profiles": proof_profile_matches,
                "required_evidence": required_evidence,
                "evidence_present": evidence_present,
                "missing_evidence": missing_evidence,
                "review_owner": posture.review_owner or "",
                "authority_refs": list(posture.authority_refs),
                "claim_boundary": posture.claim_boundary or "high-assurance-closeout-posture-required-before-full-claim",
                "uncertainty": posture.uncertainty or "",
                "human_waiver_refs": list(posture.human_waiver_refs),
                "certification_limits": list(posture.certification_limits),
                "notes": posture.notes or "",
            }
        )
    missing_evidence = _dedupe(
        [str(item).strip() for posture in matched_postures for item in _list_payload(posture.get("missing_evidence")) if str(item).strip()]
    )
    human_waiver_refs = _dedupe(
        [str(item).strip() for posture in matched_postures for item in _list_payload(posture.get("human_waiver_refs")) if str(item).strip()]
    )
    uncertainty = _dedupe([str(posture.get("uncertainty")).strip() for posture in matched_postures if posture.get("uncertainty")])
    status = "not-applicable"
    if matched_postures:
        status = "human-waiver-required" if human_waiver_refs or uncertainty else "missing-proof" if missing_evidence else "applicable"
    return {
        "kind": "agentic-workspace/high-assurance-closeout-posture/v1",
        "status": status,
        "configured_count": len(configured),
        "matched_count": len(matched_postures),
        "matched_postures": matched_postures,
        "missing_evidence": missing_evidence,
        "human_waiver_refs": human_waiver_refs,
        "uncertainty": uncertainty,
        "claim_boundaries": _dedupe(
            [str(posture.get("claim_boundary")).strip() for posture in matched_postures if str(posture.get("claim_boundary") or "").strip()]
        ),
        "certification_limits": _dedupe(
            [
                str(item).strip()
                for posture in matched_postures
                for item in _list_payload(posture.get("certification_limits"))
                if str(item).strip()
            ]
        ),
        "does_not_certify": ["legal correctness", "security correctness", "compliance correctness"],
        "rule": "Host-declared postures project closeout boundaries and evidence expectations; they do not certify domain correctness.",
    }


def _proof_decision_packet(
    *,
    changed_paths: list[str],
    selected_lanes: list[dict[str, Any]],
    selected_commands: list[dict[str, Any]],
    required_commands: list[str],
    manual_proof_obligations: list[dict[str, Any]],
    manual_verification: dict[str, Any] | None,
    unavailable_commands: list[dict[str, Any]],
    host_policy_blocked_commands: list[dict[str, str]],
    active_assurance_requirements: dict[str, Any],
    verification: dict[str, Any],
    architecture_principles: dict[str, Any],
    high_assurance_closeout_posture: dict[str, Any],
    test_strategy_check: dict[str, Any],
    proof_execution_evidence: dict[str, Any],
    local_overlay: dict[str, Any] | None = None,
    local_high_risk_overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lane_authority = {
        str(command.get("lane", "")): {
            "authority": str(command.get("route_authority", "")),
            "route_authority": str(command.get("route_authority", "")),
            "authority_surface": str(command.get("authority_surface", "")),
            "fallback_status": str(command.get("fallback_status", "")),
        }
        for command in selected_commands
        if isinstance(command, dict) and str(command.get("lane", "")).strip()
    }
    compact_lanes = []
    for lane in selected_lanes:
        if not isinstance(lane, dict):
            continue
        lane_id = str(lane.get("id", ""))
        authority = lane_authority.get(lane_id) or _proof_route_authority_for_lane(
            lane=lane,
            route_source="host-declared-domain-proof-lane"
            if lane.get("domain_lane")
            else "local-only-high-risk-overlay"
            if lane.get("local_overlay")
            else "verification-manual-protocol"
            if lane_id.startswith("verification:")
            else "live-confirmed-proof-rule",
        )
        compact_lanes.append(
            {
                "id": lane_id,
                "why": str(lane.get("when", "")),
                "commands": [str(command) for command in _list_payload(lane.get("enough_proof"))],
                "manual_evidence": [str(item) for item in _list_payload(lane.get("manual_evidence"))],
                "review_aids": [str(item) for item in _list_payload(lane.get("review_aids"))],
                "evidence_concepts": [str(item) for item in _list_payload(lane.get("evidence_concepts"))],
                **(
                    {"evidence_concept_usage": lane["evidence_concept_usage"]}
                    if isinstance(lane.get("evidence_concept_usage"), dict)
                    else {}
                ),
                "claim_boundary": str(lane.get("claim_boundary", "")),
                "route_authority": authority,
                **({"domain_lane": lane["domain_lane"]} if lane.get("domain_lane") else {}),
                **({"local_overlay": lane["local_overlay"]} if lane.get("local_overlay") else {}),
                **({"validation_profile": lane["validation_profile"]} if lane.get("validation_profile") else {}),
            }
        )
    manual_required = bool(manual_verification) or any(item.get("required") for item in manual_proof_obligations)
    architecture_count = int(architecture_principles.get("matched_count", 0) or 0) if isinstance(architecture_principles, dict) else 0
    assurance_active = (
        int(active_assurance_requirements.get("active_count", 0) or 0) if isinstance(active_assurance_requirements, dict) else 0
    )
    verification_active = int(verification.get("active_count", 0) or 0) if isinstance(verification, dict) else 0
    degraded_domain_concepts = _degraded_domain_lane_evidence_concepts(selected_lanes)
    closeout_posture_status = (
        str(high_assurance_closeout_posture.get("status", "not-configured"))
        if isinstance(high_assurance_closeout_posture, dict)
        else "not-configured"
    )
    closeout_posture_missing = (
        _list_payload(high_assurance_closeout_posture.get("missing_evidence")) if isinstance(high_assurance_closeout_posture, dict) else []
    )
    closeout_posture_waivers = (
        _list_payload(high_assurance_closeout_posture.get("human_waiver_refs")) if isinstance(high_assurance_closeout_posture, dict) else []
    )
    closeout_posture_uncertainty = (
        _list_payload(high_assurance_closeout_posture.get("uncertainty")) if isinstance(high_assurance_closeout_posture, dict) else []
    )
    blockers: list[str] = []
    if required_commands:
        blockers.append("required proof commands have not been recorded as passed")
    if manual_required:
        blockers.append("manual evidence or review is required")
    if unavailable_commands:
        blockers.append("one or more selected proof commands are unavailable")
    if host_policy_blocked_commands:
        blockers.append("host proof policy blocked one or more commands")
    if architecture_count:
        blockers.append("matched architecture principle preservation claim is unresolved")
    if assurance_active:
        blockers.append("active assurance requirements need closeout evidence or waiver")
    if verification_active and manual_required:
        blockers.append("Verification evidence remains missing or stale")
    if degraded_domain_concepts:
        blockers.append("domain proof lane contains undeclared or unclassified evidence concepts")
    if closeout_posture_missing:
        blockers.append("high-assurance closeout posture evidence is missing")
    if closeout_posture_waivers or closeout_posture_uncertainty:
        blockers.append("high-assurance closeout posture requires human waiver or uncertainty acknowledgement")
    overlay_claim_effects = _local_overlay_claim_effects(local_high_risk_overlay or {})
    overlay_blockers = _list_payload(overlay_claim_effects.get("blockers"))
    if overlay_blockers:
        blockers.append("local high-risk overlay constrains proof or closeout claims")
    if host_policy_blocked_commands:
        safe_claim_state = "human-waiver-required"
    elif closeout_posture_waivers or closeout_posture_uncertainty:
        safe_claim_state = "human-waiver-required"
    elif any(str(item).startswith("unresolved-question:human-review-required") for item in overlay_blockers):
        safe_claim_state = "human-waiver-required"
    elif overlay_blockers:
        safe_claim_state = "overlay-review-required"
    elif manual_required:
        safe_claim_state = "manual-review-required"
    elif required_commands or unavailable_commands or architecture_count or assurance_active or closeout_posture_missing:
        safe_claim_state = "proof-missing"
    else:
        safe_claim_state = "slice-only-completion"
    return {
        "kind": "agentic-workspace/proof-decision-packet/v1",
        "status": "attention" if blockers else "clear",
        "changed_paths": changed_paths,
        "selected_lane_count": len(compact_lanes),
        "selected_lanes": compact_lanes,
        "required_commands": required_commands,
        "manual_checks": manual_proof_obligations,
        "route_authority": {
            "command_count": len(selected_commands),
            "commands": selected_commands,
            "rule": "Authority explains why proof was selected; it does not certify legal, security, or compliance correctness.",
        },
        "active_pressure": {
            "assurance_requirement_count": assurance_active,
            "verification_protocol_count": verification_active,
            "architecture_principle_match_count": architecture_count,
            "high_assurance_closeout_posture_status": closeout_posture_status,
            "local_overlay_status": str((local_overlay or {}).get("status", "absent")),
            "local_overlay_active_count": int((local_overlay or {}).get("active_count", 0) or 0),
            "local_high_risk_overlay_status": str((local_high_risk_overlay or {}).get("status", "absent")),
            "local_high_risk_overlay_active_count": int((local_high_risk_overlay or {}).get("active_count", 0) or 0),
            "test_strategy_status": str(test_strategy_check.get("status", "")) if isinstance(test_strategy_check, dict) else "",
        },
        "high_assurance_closeout_posture": high_assurance_closeout_posture,
        "local_overlay": local_overlay or {"status": "absent", "active_count": 0},
        "local_high_risk_overlay": local_high_risk_overlay or {"status": "absent", "active_count": 0},
        "missing_or_unresolved": {
            "blockers": blockers,
            "unavailable_commands": unavailable_commands,
            "host_policy_blocked_commands": host_policy_blocked_commands,
            "degraded_evidence_concepts": degraded_domain_concepts,
            "closeout_posture_missing_evidence": closeout_posture_missing,
            "closeout_posture_human_waiver_refs": closeout_posture_waivers,
            "closeout_posture_uncertainty": closeout_posture_uncertainty,
            "local_overlay_blockers": overlay_blockers,
            "local_overlay_warnings": _list_payload(overlay_claim_effects.get("warnings")),
            "local_overlay_ci_validation": _list_payload(overlay_claim_effects.get("ci_validation")),
            "local_overlay_unresolved_questions": _list_payload(overlay_claim_effects.get("unresolved_questions")),
            "proof_execution_evidence_status": str(proof_execution_evidence.get("status", "")),
        },
        "safe_claim_now": {
            "state": safe_claim_state,
            "claim": "Only a local slice/proof-selection claim is safe until proof execution and closeout evidence are recorded."
            if blockers
            else "No proof-selection blocker is visible; acceptance and closeout reconciliation still remain agent-owned.",
            "does_not_certify": ["legal correctness", "security correctness", "compliance correctness"],
            "human_owned": ["waivers", "domain certification", "accepted re-scoping"],
        },
        "detail_selectors": [
            "proof_obligations",
            "verification",
            "assurance_requirements",
            "architecture_principles",
            "high_assurance_closeout_posture",
            "local_overlay",
            "high_risk_overlay",
            "test_strategy_check",
            "proof_route_explanation",
        ],
        "verbose_detail": "agentic-workspace proof --target ./repo --verbose --changed <paths> --format json",
        "rule": "Compact packet is the ordinary-agent decision surface; verbose proof remains the debugging surface.",
    }


def _learned_route_maturity(hint: dict[str, Any]) -> str:
    confirmation = str(hint.get("confirmation", "")).strip()
    state = str(hint.get("state", "candidate")).strip()
    if confirmation == "learned-confirmed":
        return "confirmed-learned"
    if confirmation == "live-confirmed":
        return "confirmed-live"
    if state in {"stale", "negative", "superseded", "invalid-authority"}:
        return state
    if state == "confirmed":
        return "confirmed"
    return "candidate"


def _default_proof_classes_for_hint(hint: dict[str, Any]) -> dict[str, list[str]]:
    command = str(hint.get("candidate_command", "")).strip()
    state = str(hint.get("state", "candidate")).strip()
    if not command:
        return {}
    if state == "negative":
        return {"not_applicable": [command]}
    if state in {"stale", "superseded", "invalid-authority"}:
        return {"unavailable_manual": [command]}
    return {"required": [command]}


def _learned_proof_route_model_payload(
    *,
    changed_paths: list[str],
    learned_route_hints: dict[str, Any],
    selected_lanes: list[dict[str, Any]],
    selected_commands: list[dict[str, Any]],
    manual_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    selected_lane_ids = {str(command.get("lane", "")) for command in selected_commands if isinstance(command, dict)}
    selected_commands_by_lane = {
        str(command.get("lane", "")): str(command.get("command", ""))
        for command in selected_commands
        if isinstance(command, dict) and str(command.get("lane", ""))
    }
    selected_learned_lanes = {
        str(lane.get("id", "")): _as_dict(lane.get("learned_route"))
        for lane in selected_lanes
        if isinstance(lane, dict) and isinstance(lane.get("learned_route"), dict)
    }
    route_records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for bucket in ("confirmed", "stale", "negative", "superseded", "invalid"):
        for raw_hint in _list_payload(learned_route_hints.get(bucket)):
            if not isinstance(raw_hint, dict):
                continue
            hint = raw_hint
            command = str(hint.get("candidate_command", "")).strip()
            route_id = str(hint.get("id") or command or bucket).strip()
            key = (route_id, command)
            if key in seen:
                continue
            seen.add(key)
            lane_id = next(
                (
                    candidate_lane_id
                    for candidate_lane_id, lane in selected_learned_lanes.items()
                    if str(lane.get("id", "")) == route_id or selected_commands_by_lane.get(candidate_lane_id) == command
                ),
                "",
            )
            selected = lane_id in selected_lane_ids
            proof_classes = _as_dict(hint.get("proof_classes")) or _default_proof_classes_for_hint(hint)
            route_records.append(
                {
                    "kind": "learned-proof-route/v1",
                    "id": route_id,
                    "route_class": str(hint.get("route_class") or hint.get("intent_type") or "behavior-test"),
                    "state": str(hint.get("state", "candidate")),
                    "maturity": _learned_route_maturity(hint),
                    "selected": selected,
                    "selected_lane": lane_id,
                    "scope": str(hint.get("scope", "repo")),
                    "matched_changed_paths": _list_payload(selected_learned_lanes.get(lane_id, {}).get("matched_paths")) if lane_id else [],
                    "risk_markers": _list_payload(hint.get("risk_markers")),
                    "evidence": _list_payload(hint.get("evidence")),
                    "proof_classes": proof_classes,
                    "override_semantics": _as_dict(hint.get("override_semantics")),
                    "source": {
                        "source": str(hint.get("source", "")),
                        "source_path": str(hint.get("source_path", "")),
                        "owner": str(hint.get("owner", "")),
                        "provenance": str(hint.get("provenance", "")),
                        "learned_at": str(hint.get("learned_at", "")),
                    },
                }
            )
    selected_routes = [route for route in route_records if route["selected"]]
    fallback_reason = ""
    if not selected_routes:
        fallback_reason = "no learned route matched changed paths and live target capabilities"
        if isinstance(manual_verification, dict):
            fallback_reason = str(manual_verification.get("summary") or manual_verification.get("reason") or fallback_reason)
    route_classes = sorted({str(route.get("route_class", "")) for route in route_records if route.get("route_class")})
    return {
        "kind": "learned-proof-route-model/v1",
        "status": "selected" if selected_routes else "available" if route_records else "absent",
        "changed_paths": changed_paths,
        "route_class_count": len(route_classes),
        "route_classes": route_classes,
        "selected_route_count": len(selected_routes),
        "selected_routes": selected_routes,
        "routes": route_records,
        "fallback": {
            "status": "not-needed" if selected_routes else "used",
            "reason": fallback_reason,
            "manual_verification_required": isinstance(manual_verification, dict),
        },
        "proof_class_vocabulary": ["required", "recommended", "optional_confidence", "unavailable_manual", "not_applicable"],
        "override_rule": (
            "Learned routes can narrow or explain proof only within their evidence scope; repo policy, user instruction, "
            "high-risk signals, stale evidence, unavailable commands, or explicit override semantics must escalate instead."
        ),
        "repo_neutrality_rule": "Route class names are host-owned evidence fields; AW does not treat them as global domains or universal requirements.",
        "closeout_semantics": {
            "selected_route_required": bool(selected_routes),
            "report_maturity": "name selected route class, maturity, evidence source, and fallback/override state",
            "issue_closure": "learned proof route selection alone never authorizes issue or parent closure",
        },
    }


def _proof_selection_for_changed_paths(
    *,
    changed_paths: list[str],
    target_root: Path | None = None,
    include_durable_intent: bool = True,
    task_text: str | None = None,
    acceptance: dict[str, Any] | None = None,
    include_assurance_requirements: bool = True,
    include_routine_work_context: bool = True,
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
        return next((lane for lane in validation_lanes if lane["id"] == lane_id))

    selected_ids: list[str] = []
    routing_reductions: list[dict[str, str]] = []

    def _select(lane_id: str) -> None:
        if lane_id not in selected_ids:
            selected_ids.append(lane_id)

    def generated_command_package_scope() -> str | None:
        has_python = any(
            (
                path.startswith("generated/python/")
                or path.startswith("generated/workspace/python/")
                or path.startswith("generated/planning/python/")
                or path.startswith("generated/memory/python/")
                or path.startswith("generated/verification/python/")
            )
            for path in changed_paths
        )
        has_typescript = any(
            (
                path.startswith("generated/workspace/typescript/")
                or path.startswith("generated/planning/typescript/")
                or path.startswith("generated/memory/typescript/")
                or path.startswith("generated/verification/typescript/")
            )
            for path in changed_paths
        )
        has_shared_source = any(
            (
                path in {"src/agentic_workspace/contracts/command_package_ir.json"}
                or path.startswith("scripts/generate/generate_command_packages.py")
                for path in changed_paths
            )
        )
        if has_python and (not has_typescript) and (not has_shared_source):
            return "python-only"
        if has_typescript and (not has_python):
            return "typescript-only"
        return None

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
        cli_authority_classification = _cli_authority_classification_for_path(changed_path)
        if cli_authority_lane and cli_authority_classification:
            _select(str(cli_authority_lane))
            if cli_authority_classification.get("id") in {"root-workspace-cli-runtime", "package-cli-runtime"}:
                _select("generated_command_packages")
    selected_lanes = [copy.deepcopy(_lane(lane_id)) for lane_id in selected_ids]
    generated_scope = generated_command_package_scope()
    if generated_scope == "python-only":
        for lane in selected_lanes:
            if lane["id"] == "generated_command_packages":
                lane["enough_proof"] = [
                    "uv run python scripts/check/check_generated_command_packages.py",
                    "uv run python scripts/check/run_operation_conformance_tests.py --target python",
                    "uv run python scripts/check/check_generated_command_packages.py --python-conformance",
                    "uv run python scripts/check/check_generated_command_packages.py --python-docker-conformance --require-docker",
                    "uv run pytest tests/test_workspace_proof_generated_packages_cli.py -q",
                ]
                lane["ci_relationship"] = (
                    "CI may repeat generated-package proof; local Python generated-package closeout should run static, local Python conformance, and Python Docker conformance serially."
                )
                break
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
    selected_lanes.extend(_supplemental_proof_lanes_for_changed_paths(changed_paths=changed_paths))
    runtime_mirror_proof_lane = _runtime_mirror_consistency_proof_lane(changed_paths=changed_paths)
    if runtime_mirror_proof_lane is not None:
        selected_lanes.append(runtime_mirror_proof_lane)
    release_proof_lane = _coordinated_release_proof_lane(target_root=target_root, changed_paths=changed_paths)
    if release_proof_lane is not None:
        selected_lanes.append(release_proof_lane)
    planning_assurance = _active_planning_assurance_for_proof(target_root=target_root)
    active_plan_lanes: list[dict[str, Any]] = []
    active_plan_commands = _dedupe(
        [str(command).strip() for command in _list_payload(planning_assurance.get("validation_commands")) if str(command).strip()]
    )
    if (not changed_paths) and planning_assurance.get("status") == "present" and active_plan_commands:
        active_plan_lanes.append(
            {
                "id": "planning:active_validation",
                "when": "proof --current selected active planning validation commands",
                "enough_proof": active_plan_commands,
                "recovery_signal": "missing or failing active plan validation should block closeout until resolved or explicitly routed",
                "proof_kind": "targeted-test",
                "proof_responsibility": "local-closeout",
                "execution_mode": "serial-recommended",
                "planning_source": str(_as_dict(planning_assurance.get("task")).get("surface") or ""),
            }
        )
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
                    "disallowed_commands": list(profile.disallowed_commands),
                }
            )
    active_assurance_requirements = (
        _assurance_requirements_report_payload(
            config=config,
            target_root=target_root,
            active_planning_record=planning_assurance if planning_assurance.get("status") == "present" else None,
            task_text=task_text,
            changed_paths=changed_paths,
        )
        if include_assurance_requirements
        else {}
    )
    requirement_lanes: list[dict[str, Any]] = []
    existing_concern_profiles = {str(lane.get("proof_profile", "")) for lane in concern_lanes}
    for requirement in active_assurance_requirements.get("active", []):
        if not isinstance(requirement, dict):
            continue
        profile_id = str(requirement.get("proof_profile") or "").strip()
        if not profile_id:
            continue
        profile = configured_profiles.get(profile_id)
        if profile is None:
            if profile_id not in missing_concern_profiles:
                missing_concern_profiles.append(profile_id)
            continue
        if profile_id in existing_concern_profiles:
            continue
        requirement_lanes.append(
            {
                "id": f"assurance-requirement:{requirement.get('id')}",
                "when": "matched repo-declared assurance requirement selects this proof profile",
                "enough_proof": list(profile.required_commands),
                "recovery_signal": "missing or failing requirement proof should block broad assurance closeout until resolved or explicitly waived",
                "proof_profile": profile.id,
                "optional_commands": list(profile.optional_commands),
                "review_aids": list(profile.review_aids),
                "disallowed_commands": list(profile.disallowed_commands),
                "requirement_id": str(requirement.get("id", "")),
                "applies_because": _list_payload(requirement.get("applies_because")),
            }
        )
        existing_concern_profiles.add(profile_id)
    verification = (
        _verification_report_payload(
            target_root=target_root,
            changed_paths=changed_paths,
            task_text=task_text,
            active_planning_record=planning_assurance if planning_assurance.get("status") == "present" else None,
            assurance_requirements=active_assurance_requirements,
        )
        if target_root is not None
        else {"status": "unavailable", "active_count": 0}
    )
    active_assurance_requirements = _assurance_requirements_with_verification(active_assurance_requirements, verification)
    verification_lanes: list[dict[str, Any]] = []
    active_verification_routes = [route for route in _list_payload(verification.get("active_proof_routes")) if isinstance(route, dict)]
    for protocol in _list_payload(verification.get("active_protocols")):
        if not isinstance(protocol, dict):
            continue
        protocol_id = str(protocol.get("id", "")).strip()
        if not protocol_id:
            continue
        protocol_routes = [
            route
            for route in active_verification_routes
            if protocol_id in {str(ref).strip() for ref in _list_payload(route.get("protocol_refs"))}
            or set(_list_payload(protocol.get("scenario_refs"))).intersection(
                {str(ref).strip() for ref in _list_payload(route.get("scenario_refs"))}
            )
        ]
        route_commands = _dedupe(
            [str(command).strip() for route in protocol_routes for command in _list_payload(route.get("commands")) if str(command).strip()]
        )
        verification_lanes.append(
            {
                "id": f"verification:{protocol_id}",
                "when": "matched repo verification protocol selects soft verification proof",
                "enough_proof": _dedupe(
                    [str(command) for command in _list_payload(protocol.get("commands")) if str(command).strip()] + route_commands
                ),
                "recovery_signal": "missing verification evidence should be recorded as residual risk or evidence before broad closeout",
                "proof_kind": "diff-review" if not protocol.get("commands") and not route_commands else "targeted-test",
                "proof_responsibility": "local-closeout",
                "execution_mode": "serial-recommended",
                "verification_protocol_id": protocol_id,
                "verification_scenario_refs": _list_payload(protocol.get("scenario_refs")),
                "verification_expected_evidence": _list_payload(protocol.get("expected_evidence")),
                "verification_proof_route_ids": [str(route.get("id")) for route in protocol_routes if route.get("id")],
                "review_aids": _dedupe(
                    [str(item) for item in _list_payload(protocol.get("review_aids"))]
                    + [str(item) for route in protocol_routes for item in _list_payload(route.get("review_aids"))]
                ),
                "applies_because": _list_payload(protocol.get("applies_because")),
            }
        )
    domain_lanes = _host_domain_proof_lanes_for_changed_paths(config=config, changed_paths=changed_paths, task_text=task_text)
    domain_lanes = _annotate_domain_lane_evidence_concepts(domain_lanes=domain_lanes, verification=verification)
    selected_lanes.extend(active_plan_lanes)
    selected_lanes.extend(concern_lanes)
    selected_lanes.extend(requirement_lanes)
    selected_lanes.extend(verification_lanes)
    selected_lanes.extend(domain_lanes)
    local_overlay = _local_overlay_for_work(
        config=config,
        changed_paths=changed_paths,
        task_text=task_text,
        cli_invoke=cli_invoke,
    )
    local_high_risk_overlay = _local_high_risk_overlay_for_work(
        config=config,
        changed_paths=changed_paths,
        task_text=task_text,
        cli_invoke=cli_invoke,
    )
    local_overlay_lanes = _local_overlay_lanes(local_high_risk_overlay)
    selected_lanes.extend(local_overlay_lanes)
    make_targets = _makefile_targets(target_root)
    package_scripts = _package_json_scripts(target_root)
    project_roots = _project_roots_for_changed_paths(target_root=target_root, changed_paths=changed_paths)
    target_capabilities = _target_proof_capabilities(target_root=target_root, make_targets=make_targets, project_roots=project_roots)
    learned_route_hints = _confirm_learned_route_hints(
        learned_hints=_load_proof_route_hints(target_root=target_root), target_capabilities=target_capabilities
    )
    target_capabilities = _apply_learned_route_hints_to_capabilities(
        target_capabilities=target_capabilities, learned_route_hints=learned_route_hints
    )
    selected_lanes.extend(_learned_proof_lanes_for_changed_paths(changed_paths=changed_paths, learned_route_hints=learned_route_hints))
    docs_process_route = _docs_process_route_refinement(
        changed_paths=changed_paths,
        selected_lanes=selected_lanes,
        task_text=task_text,
        learned_route_hints=learned_route_hints,
    )
    if docs_process_route["status"] == "active":
        selected_lanes = _apply_docs_process_route_to_lanes(
            selected_lanes=selected_lanes,
            docs_review_lane=copy.deepcopy(_lane("repo_docs_review")),
            docs_process_route=docs_process_route,
        )
        routing_reductions.extend(docs_process_route["routing_reductions"])
    learned_negative_commands = {
        str(hint.get("candidate_command", "")).strip()
        for hint in learned_route_hints.get("negative", [])
        if str(hint.get("candidate_command", "")).strip()
    }
    selection_make_targets = _make_targets_without_negative_routes(make_targets, learned_negative_commands)
    selection_package_scripts = _package_scripts_without_negative_routes(package_scripts, learned_negative_commands)
    selection_role_commands = target_capabilities.get("role_commands", {})
    proof_command_adjustments: list[dict[str, str]] = []
    unavailable_proof_commands: list[dict[str, str]] = []
    host_policy_disallowed_commands: dict[str, dict[str, str]] = {}
    for lane in [*concern_lanes, *requirement_lanes]:
        for raw_command in lane.get("disallowed_commands", []):
            raw_command_text = str(raw_command).strip()
            if not raw_command_text:
                continue
            candidate_commands = [raw_command_text]
            adapted_command, _adjustment = _adapt_make_proof_command_for_target(
                command=raw_command_text,
                target_root=target_root,
                make_targets=selection_make_targets,
                package_scripts=selection_package_scripts,
                role_commands=selection_role_commands,
                project_roots=project_roots,
                record_missing_makefile_as_unavailable=bool(lane.get("proof_profile") or lane.get("subsystem")),
            )
            if adapted_command is not None:
                candidate_commands.append(adapted_command)
            for candidate_command in candidate_commands:
                resolved_command = str(
                    _command_with_cli_invoke(
                        command=_proof_command_for_target(command=candidate_command, target_root=target_root), cli_invoke=cli_invoke
                    )
                )
                host_policy_disallowed_commands[resolved_command] = {
                    "lane": str(lane.get("id", "")),
                    "proof_profile": str(lane.get("proof_profile", "")),
                    "command": resolved_command,
                    "configured_command": raw_command_text,
                    "reason": "host-configured proof profile disallows this command",
                }
    host_policy_blocked_commands: list[dict[str, str]] = []
    for lane in selected_lanes:
        lane["proof_kind"] = _proof_kind_for_lane(lane)
        adapted_commands: list[str] = []
        for raw_command in lane.get("enough_proof", []):
            adapted_command, adjustment = _adapt_make_proof_command_for_target(
                command=str(raw_command),
                target_root=target_root,
                make_targets=selection_make_targets,
                package_scripts=selection_package_scripts,
                role_commands=selection_role_commands,
                project_roots=project_roots,
                record_missing_makefile_as_unavailable=bool(lane.get("proof_profile") or lane.get("subsystem")),
            )
            if adjustment is not None:
                adjustment = {"lane": str(lane.get("id", "")), **adjustment}
                if adapted_command is None:
                    unavailable_proof_commands.append(adjustment)
                else:
                    proof_command_adjustments.append(adjustment)
            if adapted_command is None:
                continue
            missing_path_refs = _missing_repo_path_references_in_command(command=adapted_command, target_root=target_root)
            if missing_path_refs:
                unavailable_proof_commands.append(
                    {
                        "lane": str(lane.get("id", "")),
                        "command": adapted_command,
                        "reason": "selected proof command references path-like arguments absent from the target repo",
                        "missing_paths": ", ".join(missing_path_refs),
                    }
                )
                continue
            resolved_command = str(
                _command_with_cli_invoke(
                    command=_proof_command_for_target(command=adapted_command, target_root=target_root), cli_invoke=cli_invoke
                )
            )
            disallowed = host_policy_disallowed_commands.get(resolved_command)
            if disallowed is not None:
                host_policy_blocked_commands.append({**disallowed, "selected_by_lane": str(lane.get("id", ""))})
                continue
            adapted_commands.append(resolved_command)
        lane["enough_proof"] = adapted_commands
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
    adjustments_by_replacement = {
        str(adjustment["replacement"]): adjustment for adjustment in proof_command_adjustments if adjustment.get("replacement")
    }
    learned_confirmed_commands = {
        str(hint.get("candidate_command", "")).strip()
        for hint in learned_route_hints.get("confirmed", [])
        if isinstance(hint, dict)
        and str(hint.get("candidate_command", "")).strip()
        and str(hint.get("confirmation", "")) == "learned-confirmed"
    }
    proof_intents = [_proof_intent_for_lane(lane) for lane in selected_lanes]
    intent_by_lane_id = {intent["id"]: intent for intent in proof_intents}
    selected_commands: list[dict[str, Any]] = []
    for lane in selected_lanes:
        intent = intent_by_lane_id.get(str(lane.get("id", "")), {})
        for command in lane.get("enough_proof", []):
            command_text = str(command)
            command_cwd, run_command = _split_validation_command(command_text)
            route_source = _proof_route_source_for_lane(
                lane=lane, command=command_text, adjustments_by_replacement=adjustments_by_replacement
            )
            route_authority = _proof_route_authority_for_lane(
                lane=lane,
                route_source=route_source,
                learned_confirmed=command_text in learned_confirmed_commands and route_source == "live-adapted-target-capability",
            )
            selected_commands.append(
                {
                    "kind": "proof-command/v1",
                    "command": command_text,
                    "cwd": command_cwd,
                    "run": run_command,
                    "selected_from": route_source,
                    "route_authority": route_authority["authority"],
                    "fallback_status": route_authority["fallback_status"],
                    "authority_surface": route_authority["authority_surface"],
                    "promotion_candidate": route_authority["promotion_candidate"],
                    "maintenance_target": route_authority["maintenance_target"],
                    "intent_type": str(intent.get("type", "behavior-test")),
                    "lane": str(lane.get("id", "")),
                    "required": True,
                    **_lane_execution_metadata(lane),
                }
            )
    unavailable_commands = [
        {
            "kind": "proof-command-unavailable/v1",
            "command": str(command.get("command", "")),
            "lane": str(command.get("lane", "")),
            "reason": str(command.get("reason", "")),
            **({"replacement": command["replacement"]} if command.get("replacement") else {}),
            **({"missing_paths": str(command["missing_paths"])} if command.get("missing_paths") else {}),
        }
        for command in unavailable_proof_commands
    ]
    manual_verification: dict[str, Any] | None = None
    if not required_commands or unavailable_proof_commands:
        manual_verification = {
            "kind": "manual-verification/v1",
            "status": "required" if not required_commands else "required-for-unavailable-proof",
            "reason": "no live-confirmed executable route was selected"
            if not required_commands
            else "some selected proof commands are unavailable in this target repo",
            "summary": "Review changed behavior manually and record evidence because no executable proof route was selected."
            if not required_commands
            else "Review unavailable proof expectations manually and record why repo-specific proof is sufficient.",
            "instructions": [
                "Inspect the changed paths against the requested task outcome.",
                "Use target_proof_capabilities.candidate_commands only if they are relevant to this change.",
                "Record what was manually checked and why unavailable commands were not required for closeout.",
            ],
            "templates": _manual_verification_templates_for_intents(proof_intents=proof_intents),
            "candidate_commands": target_capabilities.get("candidate_commands", []),
            "unavailable_commands": unavailable_commands,
        }
    proof_receipt_reconciliation = _proof_receipt_reconciliation_payload(
        target_root=target_root,
        required_commands=required_commands,
        changed_paths=changed_paths,
        selected_commands=selected_commands,
    )
    proof_execution_evidence = {
        "kind": "proof-execution-evidence/v1",
        "status": "recorded-and-accepted" if proof_receipt_reconciliation.get("status") == "accepted" else "not-run-or-not-recorded",
        "state_model": list(_PROOF_EXECUTION_STATUSES),
        "expected_commands": required_commands,
        "blocking_expected_commands": [
            str(item.get("command", ""))
            for item in _list_payload(proof_receipt_reconciliation.get("commands"))
            if isinstance(item, dict) and item.get("blocking")
        ],
        "non_blocking_selected_count": proof_receipt_reconciliation.get("non_blocking_selected_count", 0),
        "manual_verification_expected": manual_verification is not None,
        "receipt_reconciliation": proof_receipt_reconciliation,
        "missing_evidence_diagnostics": {
            "not-run-or-not-recorded": "no trusted receipt exists for this selected command",
            "run-but-not-recorded": "a receipt exists, but not for this selected command",
            "record-stale-untrusted": "a receipt exists, but command/path/result trust does not match the current proof selection",
            "recorded-failed": "the selected command was recorded as failed",
            "accepted": "the selected command has an exact matching passed receipt",
            "aggregate-selected-proof": "a passed receipt covers the selected proof set by identity or proof_commands",
        },
        "rule": (
            "Proof selection describes expected proof only; closeout must record what actually ran, failed, was skipped, "
            "or was manually verified. Latest receipts are reconciled but do not bypass intent or closeout review."
        ),
    }
    proof_receipt_bridge = _proof_receipt_bridge_payload(
        changed_paths=changed_paths,
        proof_receipt_reconciliation=proof_receipt_reconciliation,
        cli_invoke=cli_invoke,
    )
    configured_policy = [
        {
            "kind": "proof-profile/v1",
            "source": "host-config",
            "id": str(lane.get("proof_profile", "")),
            "required_commands": list(lane.get("enough_proof", [])),
            "optional_commands": list(lane.get("optional_commands", [])),
            "review_aids": list(lane.get("review_aids", [])),
            "disallowed_commands": [
                str(
                    _command_with_cli_invoke(
                        command=_proof_command_for_target(command=str(command), target_root=target_root), cli_invoke=cli_invoke
                    )
                )
                for command in lane.get("disallowed_commands", [])
            ],
        }
        for lane in [*concern_lanes, *requirement_lanes]
        if lane.get("proof_profile")
    ]
    domain_policy = [
        {
            "kind": "domain-proof-lane/v1",
            "source": "host-config",
            "id": str(_as_dict(lane.get("domain_lane")).get("id") or lane.get("id", "")),
            "purpose": str(_as_dict(lane.get("domain_lane")).get("purpose") or ""),
            "matched_paths": _list_payload(_as_dict(lane.get("domain_lane")).get("matched_paths")),
            "matched_task_markers": _list_payload(_as_dict(lane.get("domain_lane")).get("matched_task_markers")),
            "required_commands": list(lane.get("enough_proof", [])),
            "manual_evidence": _list_payload(lane.get("manual_evidence")),
            "review_aids": _list_payload(lane.get("review_aids")),
            "evidence_concepts": _list_payload(lane.get("evidence_concepts")),
            **({"evidence_concept_usage": lane["evidence_concept_usage"]} if isinstance(lane.get("evidence_concept_usage"), dict) else {}),
            "claim_boundary": str(lane.get("claim_boundary", "")),
            "authority_refs": _list_payload(lane.get("authority_refs")),
        }
        for lane in domain_lanes
    ]
    configured_policy.extend(domain_policy)
    learned_route_reliance = _learned_route_reliance_payload(
        selected_commands=selected_commands,
        learned_route_hints=learned_route_hints,
    )
    learned_proof_route_model = _learned_proof_route_model_payload(
        changed_paths=changed_paths,
        learned_route_hints=learned_route_hints,
        selected_lanes=selected_lanes,
        selected_commands=selected_commands,
        manual_verification=manual_verification,
    )
    proof_next_decision = _proof_next_decision_payload(
        required_commands=required_commands,
        selected_commands=selected_commands,
        unavailable_commands=unavailable_commands,
        host_policy_blocked_commands=host_policy_blocked_commands,
        manual_verification=manual_verification,
        learned_route_hints=learned_route_hints,
    )
    proof_route_decision = _proof_route_decision_payload(
        proof_next_decision=proof_next_decision,
        selected_commands=selected_commands,
        required_commands=required_commands,
        manual_verification=manual_verification,
        unavailable_commands=unavailable_commands,
        learned_route_reliance=learned_route_reliance,
    )
    proof_route_precedence = _proof_route_precedence_payload(selected_commands=selected_commands)
    host_repo_learning = _host_repo_learning_posture_payload(
        target_capabilities=target_capabilities,
        learned_route_hints=learned_route_hints,
        unavailable_commands=unavailable_commands,
        host_policy_blocked_commands=host_policy_blocked_commands,
        selected_commands=selected_commands,
    )
    manual_proof_obligations = [
        *_manual_proof_obligations_payload(verification=verification),
        *_domain_manual_proof_obligations(domain_lanes),
    ]
    proof_route_maintenance = _proof_route_maintenance_payload(
        selected_lanes=selected_lanes,
        selected_commands=selected_commands,
        learned_route_hints=learned_route_hints,
        manual_proof_obligations=manual_proof_obligations,
    )
    proof_route_explanation = _proof_route_explanation_payload(
        proof_intents=proof_intents,
        configured_policy=configured_policy,
        learned_route_hints=learned_route_hints,
        learned_route_reliance=learned_route_reliance,
        target_capabilities=target_capabilities,
        host_repo_learning=host_repo_learning,
        selected_commands=selected_commands,
        unavailable_commands=unavailable_commands,
        host_policy_blocked_commands=host_policy_blocked_commands,
        manual_verification=manual_verification,
        proof_execution_evidence=proof_execution_evidence,
    )
    generated_cli_freshness = _generated_cli_freshness_payload(
        changed_paths=changed_paths,
        selected_lanes=selected_lanes,
        required_commands=required_commands,
    )
    release_proof_profile = _release_proof_profile_payload(
        changed_paths=changed_paths,
        selected_lanes=selected_lanes,
        required_commands=required_commands,
    )
    architecture_principles = _architecture_principles_payload(
        target_root=target_root,
        changed_paths=changed_paths,
        cli_invoke=cli_invoke,
        compact=False,
    )
    high_assurance_closeout_posture = _host_closeout_posture_packet(
        config=config,
        changed_paths=changed_paths,
        task_text=task_text,
        selected_lanes=selected_lanes,
        active_assurance_requirements=active_assurance_requirements,
    )
    optional_commands = ["agentic-workspace proof --target ./repo --current --format json", "agentic-workspace summary --format json"]
    for concern_lane in [*concern_lanes, *requirement_lanes, *verification_lanes]:
        for command in concern_lane.get("optional_commands", []):
            if command not in optional_commands:
                optional_commands.append(str(command))
    optional_commands = [
        str(
            _command_with_cli_invoke(
                command=_proof_command_for_target(command=str(command), target_root=target_root), cli_invoke=cli_invoke
            )
        )
        for command in optional_commands
    ]
    proof_narrowness = _proof_narrowness_payload(
        selected_lanes=selected_lanes,
        selected_commands=selected_commands,
        required_commands=required_commands,
        optional_commands=optional_commands,
        broaden_when=broaden_when,
        escalate_when=escalate_when,
        manual_verification=manual_verification,
    )
    proof_obligations = _proof_obligations_payload(
        required_commands=required_commands,
        optional_commands=optional_commands,
        manual_verification=manual_verification,
        selected_commands=selected_commands,
        manual_proof_obligations=manual_proof_obligations,
    )
    proof_requirement_tiers = _proof_requirement_tiers_payload(
        selected_commands=selected_commands,
        required_commands=required_commands,
        optional_commands=optional_commands,
        manual_proof_obligations=manual_proof_obligations,
        unavailable_commands=unavailable_commands,
        host_policy_blocked_commands=host_policy_blocked_commands,
    )
    intent_proof = _intent_proof_prompt_payload(task_text=task_text, acceptance=acceptance, claim_boundary="slice")
    proof_confidence = _proof_confidence_payload(
        intent_proof=intent_proof,
        proof_execution_evidence=proof_execution_evidence,
    )
    proof_adequacy = _proof_adequacy_payload(
        required_commands=required_commands,
        optional_commands=optional_commands,
        selected_lanes=selected_lanes,
        verification=verification,
        proof_obligations=proof_obligations,
        proof_confidence=proof_confidence,
        manual_verification=manual_verification,
    )
    proof_command_explanations = _proof_command_explanations_payload(
        selected_commands=selected_commands,
        required_commands=required_commands,
        optional_commands=optional_commands,
        unavailable_commands=unavailable_commands,
        host_policy_blocked_commands=host_policy_blocked_commands,
        manual_verification=manual_verification,
    )
    proof_closeout_summary = _proof_closeout_summary_payload(
        changed_paths=changed_paths,
        selected_lanes=selected_lanes,
        proof_route_decision=proof_route_decision,
        proof_command_explanations=proof_command_explanations,
        proof_execution_evidence=proof_execution_evidence,
        proof_receipt_reconciliation=proof_receipt_reconciliation,
        proof_receipt_bridge=proof_receipt_bridge,
        learned_route_reliance=learned_route_reliance,
        manual_verification=manual_verification,
        unavailable_commands=unavailable_commands,
        host_policy_blocked_commands=host_policy_blocked_commands,
    )
    active_planning_record_for_requirement = (
        _active_planning_record_for_report_section(target_root=target_root) if target_root is not None else {}
    )
    issue_scope_evidence_for_requirement = (
        _issue_scope_evidence_payload(
            target_root=target_root,
            config=config,
            issue_refs=sorted(set(re.findall("#\\d+", task_text or ""))),
        )
        if target_root is not None and config is not None
        else {"kind": "agentic-workspace/issue-scope-evidence/v1", "status": "not-applicable", "issue_refs": []}
    )
    requirement_grounding = _requirement_grounding_payload(
        target_root=target_root or Path("."),
        task_text=task_text,
        changed_paths=changed_paths,
        active_planning_record=active_planning_record_for_requirement,
        issue_scope_evidence=issue_scope_evidence_for_requirement,
        assurance_requirements=active_assurance_requirements,
        verification=verification,
    )
    test_strategy_check = (
        _test_strategy_check_payload(
            target_root=target_root,
            changed_paths=changed_paths,
            task_text=task_text,
            verification=verification,
        )
        if target_root is not None
        else {"kind": "agentic-workspace/test-strategy-check/v1", "status": "unavailable", "changed_test_paths": []}
    )
    proof_decision = _proof_decision_packet(
        changed_paths=changed_paths,
        selected_lanes=selected_lanes,
        selected_commands=selected_commands,
        required_commands=required_commands,
        manual_proof_obligations=manual_proof_obligations,
        manual_verification=manual_verification,
        unavailable_commands=unavailable_commands,
        host_policy_blocked_commands=host_policy_blocked_commands,
        active_assurance_requirements=active_assurance_requirements,
        verification=verification,
        architecture_principles=architecture_principles,
        high_assurance_closeout_posture=high_assurance_closeout_posture,
        test_strategy_check=test_strategy_check,
        proof_execution_evidence=proof_execution_evidence,
        local_overlay=local_overlay,
        local_high_risk_overlay=local_high_risk_overlay,
    )
    forecast_carry = _load_decision_point_forecast(target_root=target_root, task_text=task_text)
    forecast_identity = _as_dict(forecast_carry.get("forecast_identity"))
    implementation_confirmation = _as_dict(_as_dict(forecast_carry.get("phase_confirmations")).get("implementation"))
    try:
        actual_intent = (
            _intent_decision_projection(target_root=target_root, config=config, changed_paths=changed_paths, compact=True)
            if target_root is not None and isinstance(config, WorkspaceConfig)
            else {}
        )
    except WorkspaceUsageError:
        actual_intent = {}
    actual_subsystems = _list_payload(_as_dict(actual_intent.get("subsystem_intent")).get("matches"))[:2]
    actual_basis = {
        "actual_paths": changed_paths,
        "system_principle_ids": [str(item.get("id", "")) for item in _list_payload(architecture_principles.get("matched_principles"))[:2]],
        "subsystem_intent_ids": [str(item.get("id", "")) for item in actual_subsystems],
    }
    actual_intent_digest = hashlib.sha256(json.dumps(actual_basis, sort_keys=True).encode()).hexdigest()[:16]
    corrected = bool(
        forecast_identity
        and (
            set(forecast_identity.get("planned_paths", [])) != set(changed_paths)
            or forecast_identity.get("system_principle_ids", []) != actual_basis["system_principle_ids"]
            or forecast_identity.get("subsystem_intent_ids", []) != actual_basis["subsystem_intent_ids"]
            or _decision_point_source_revision_status(target_root=target_root, carry=forecast_carry)["status"] == "changed"
        )
    )
    decision_point_confirmation = {
        "kind": "agentic-workspace/decision-point-intent-confirmation/v1",
        "phase": "proof",
        "status": "corrected" if corrected else "preserved" if forecast_identity else "unresolved",
        "forecast_identity": forecast_identity,
        "forecast_digest": forecast_identity.get("digest", ""),
        "actual_scope_digest": actual_intent_digest,
        "changed_paths": changed_paths,
        "system_principles": _list_payload(architecture_principles.get("matched_principles"))[:2],
        "subsystem_intents": actual_subsystems,
        "implementation_confirmation": implementation_confirmation,
        "source_revision_confirmation": _decision_point_source_revision_status(target_root=target_root, carry=forecast_carry),
        "implementation_record_digest": _as_dict(implementation_confirmation.get("carry_forward")).get("record_digest", ""),
        "claim_boundary": "Closeout must consume this exact confirmation record and account for preserved, corrected, or unresolved intent.",
        "closeout_required_claim": "preserved|corrected|unresolved",
    }
    decision_point_confirmation = _record_decision_point_confirmation(
        target_root=target_root, phase="proof", confirmation=decision_point_confirmation, task_text=task_text
    )
    proof_selection = {
        "kind": "proof-selection/v1",
        "changed_paths": changed_paths,
        "proof_strategy": {
            "kind": "proof-strategy/v1",
            "proof_types": [
                {"id": "executable", "meaning": "A discovered target command can directly exercise the changed behavior or surface."},
                {
                    "id": "surface-check",
                    "meaning": "A structured checker can inspect changed declarations, manifests, or generated surfaces.",
                },
                {"id": "diff-review", "meaning": "The trust question is human/agent review of the diff against the requested outcome."},
                {
                    "id": "manual-verification",
                    "meaning": "No trustworthy executable route was discovered; closeout needs explicit manual verification evidence.",
                },
            ],
            "selection_order": [
                "match changed paths to proof intent",
                "enrich with target repo capabilities and configured assurance profiles",
                "emit executable commands only when the target exposes the required capability",
                "emit manual verification instructions when executable proof is unavailable",
            ],
            "anti_rationalization_gates": [
                {
                    "red_flag": "Tests passed, so completion is claimable.",
                    "use_instead": "Record proof execution evidence, reconcile requested intent, and use completion/closeout options before claiming done.",
                },
                {
                    "red_flag": "The local slice works, so the parent lane or epic is closed.",
                    "use_instead": "Keep parent intent open unless closeout fields and continuation owner explicitly prove it is satisfied.",
                },
                {
                    "red_flag": "A skill wording change is only prose.",
                    "use_instead": "Name the behavior the skill steers and run the CLI or contract proof that shows routing, allowed actions, or completion claims still behave correctly.",
                },
            ],
        },
        "target_proof_capabilities": target_capabilities,
        "host_repo_learning": host_repo_learning,
        "learned_route_hints": learned_route_hints,
        "learned_route_reliance": learned_route_reliance,
        "learned_proof_route_model": learned_proof_route_model,
        "proof_route_maintenance": proof_route_maintenance,
        "proof_route_precedence": proof_route_precedence,
        "proof_intents": proof_intents,
        "configured_policy": configured_policy,
        "verification": verification,
        "selected_commands": selected_commands,
        "unavailable_commands": unavailable_commands,
        "host_policy_blocked_commands": host_policy_blocked_commands,
        "proof_execution_evidence": proof_execution_evidence,
        "proof_receipt_reconciliation": proof_receipt_reconciliation,
        "proof_receipt_bridge": proof_receipt_bridge,
        "proof_requirement_tiers": proof_requirement_tiers,
        "proof_decision": proof_decision,
        "high_assurance_closeout_posture": high_assurance_closeout_posture,
        "intent_proof": intent_proof,
        "proof_confidence": proof_confidence,
        "proof_adequacy": proof_adequacy,
        "proof_command_explanations": proof_command_explanations,
        "proof_closeout_summary": proof_closeout_summary,
        "docs_process_route": docs_process_route,
        "requirement_grounding": requirement_grounding,
        "test_strategy_check": test_strategy_check,
        "architecture_principles": architecture_principles,
        "decision_point_intent_confirmation": decision_point_confirmation,
        "proof_route_selection": proof_route_decision,
        "proof_route_decision": proof_route_decision,
        "proof_route_explanation": proof_route_explanation,
        "legacy_aliases": {"proof_route_decision": "proof_route_selection"},
        "proof_next_decision": proof_next_decision,
        "proof_command_tiers": _proof_command_tiers(selected_commands=selected_commands, required_commands=required_commands),
        "proof_narrowness": proof_narrowness,
        "proof_obligations": proof_obligations,
        "transient_validation_retry": _transient_validation_retry_guidance(required_commands=required_commands),
        "tiny_surface_compatibility_review": _tiny_surface_compatibility_review(changed_paths),
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
                "route_authority": _proof_route_authority_for_lane(
                    lane=lane,
                    route_source="verification-manual-protocol"
                    if str(lane.get("id", "")).startswith("verification:")
                    else "host-declared-domain-proof-lane"
                    if lane.get("domain_lane")
                    else "live-confirmed-proof-rule",
                ),
                **({"proof_profile": lane["proof_profile"]} if lane.get("proof_profile") else {}),
                **({"domain_lane": lane["domain_lane"]} if lane.get("domain_lane") else {}),
                **({"local_overlay": lane["local_overlay"]} if lane.get("local_overlay") else {}),
                **({"validation_profile": lane["validation_profile"]} if lane.get("validation_profile") else {}),
                **({"manual_evidence": lane["manual_evidence"]} if lane.get("manual_evidence") else {}),
                **({"evidence_concepts": lane["evidence_concepts"]} if lane.get("evidence_concepts") else {}),
                **({"evidence_concept_usage": lane["evidence_concept_usage"]} if lane.get("evidence_concept_usage") else {}),
                **({"claim_boundary": lane["claim_boundary"]} if lane.get("claim_boundary") else {}),
                **({"authority_refs": lane["authority_refs"]} if lane.get("authority_refs") else {}),
                **({"requirement_id": lane["requirement_id"]} if lane.get("requirement_id") else {}),
                **({"verification_protocol_id": lane["verification_protocol_id"]} if lane.get("verification_protocol_id") else {}),
                **({"verification_scenario_refs": lane["verification_scenario_refs"]} if lane.get("verification_scenario_refs") else {}),
                **(
                    {"verification_expected_evidence": lane["verification_expected_evidence"]}
                    if lane.get("verification_expected_evidence")
                    else {}
                ),
                **(
                    {"verification_proof_route_ids": lane["verification_proof_route_ids"]}
                    if lane.get("verification_proof_route_ids")
                    else {}
                ),
                **({"applies_because": lane["applies_because"]} if lane.get("applies_because") else {}),
                **({"review_aids": lane["review_aids"]} if lane.get("review_aids") else {}),
                **({"matched_paths": lane["matched_paths"]} if lane.get("matched_paths") else {}),
                **({"subsystem": lane["subsystem"]} if lane.get("subsystem") else {}),
                **({"weak_agent_safe_routing": lane["weak_agent_safe_routing"]} if lane.get("weak_agent_safe_routing") else {}),
                **({"non_local_references": lane["non_local_references"]} if lane.get("non_local_references") else {}),
            }
            for lane in selected_lanes
        ],
        "required_commands": required_commands,
        "manual_proof_obligations": manual_proof_obligations,
        "sufficiency": _workflow_sufficiency_payload(
            surface="proof",
            decision="required-proof-selected" if required_commands else "no-required-proof-selected",
            reason="Selected commands are the minimal proof for the matched changed paths; broaden only if task intent or failures demand it."
            if required_commands
            else "No changed-path proof rule selected a required command; use current proof or a task-specific proof before closeout.",
            required_next_action="run required_commands" if required_commands else "choose task-specific proof or current proof",
            evidence_required=["proof execution evidence"] if required_commands else [],
            drill_down={"full_detail": "agentic-workspace proof --verbose --changed <paths> --format json"},
        ),
        "optional_commands": optional_commands,
        "validation_plan": _validation_plan_for_proof(
            selected_lanes=selected_lanes, optional_commands=optional_commands, target_root=target_root, cli_invoke=cli_invoke
        ),
        "broaden_when": broaden_when,
        "escalate_when": escalate_when,
        "completion_options": _proof_completion_options(
            required_commands=required_commands,
            manual_verification=manual_verification,
            test_strategy_check=test_strategy_check,
        ),
    }
    if routing_reductions:
        proof_selection["routing_reductions"] = routing_reductions
    if generated_cli_freshness is not None:
        proof_selection["generated_cli_freshness"] = generated_cli_freshness
    if release_proof_profile is not None:
        proof_selection["release_proof_profile"] = release_proof_profile
    if proof_command_adjustments:
        proof_selection["proof_command_adjustments"] = proof_command_adjustments
    if unavailable_proof_commands:
        proof_selection["unavailable_proof_commands"] = unavailable_proof_commands
        proof_selection["escalate_when"].append(
            "Some selected proof commands are unavailable in this target repo; choose repo-specific proof before closeout."
        )
    if host_policy_blocked_commands:
        proof_selection["host_policy_blocked_commands"] = host_policy_blocked_commands
        proof_selection["escalate_when"].append(
            "Host-configured proof policy blocked one or more discovered or selected commands; choose allowed repo-specific proof before closeout."
        )
    if manual_verification is not None:
        proof_selection["manual_verification"] = manual_verification
    if local_high_risk_overlay.get("status") == "active":
        proof_selection["high_risk_overlay"] = local_high_risk_overlay
    if local_overlay.get("status") == "active":
        proof_selection["local_overlay"] = local_overlay
    if config is not None and target_root is not None and include_durable_intent:
        durable_intent = _intent_decision_projection(target_root=target_root, config=config, changed_paths=changed_paths, compact=True)
        proof_selection["durable_intent"] = durable_intent
        if durable_intent.get("status") == "present":
            intent_effect = (
                "Relevant durable intent may add proof, review, or escalation expectations; inspect durable_intent before closeout."
            )
            if intent_effect not in proof_selection["escalate_when"]:
                proof_selection["escalate_when"].append(intent_effect)
    if include_routine_work_context and config is not None and target_root is not None:
        proof_selection["current_work_context"] = resolve_current_work_context(
            root=target_root,
            task=str(task_text or ""),
        )
        workflow_obligations = _workflow_obligations_report_payload(
            config=config,
            active_planning_record=None,
            task_text=task_text,
            changed_paths=changed_paths,
        )
        proof_routine_context = _routine_work_context_payload(
            source_payload={"proof": proof_selection, "workflow_obligations": workflow_obligations, "verification": verification},
            surface="proof",
            cli_invoke=cli_invoke,
            target_root=target_root,
            changed_paths=changed_paths,
            task_text=task_text,
            compact=True,
        )
        if proof_routine_context.get("status") == "attention":
            proof_selection["routine_work_context"] = proof_routine_context
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
                evidence=planning_assurance.get("traceability_refs", {}).get(ref, [])
                if isinstance(planning_assurance.get("traceability_refs", {}), dict)
                else [],
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
            declared=planning_assurance.get("proof_execution_evidence", []), required_commands=required_commands
        )
        proof_selection["planning_assurance"] = {
            **planning_assurance,
            "missing_configured_proof_profiles": missing_concern_profiles,
            "trust_state": {
                "assurance_level": planning_assurance.get("adaptive_assurance", {}).get(
                    "level", config.assurance.default_level if config is not None else DEFAULT_ASSURANCE_LEVEL
                )
                if isinstance(planning_assurance.get("adaptive_assurance", {}), dict)
                else config.assurance.default_level
                if config is not None
                else DEFAULT_ASSURANCE_LEVEL,
                "assurance_level_source": "explicit-slice-field"
                if isinstance(planning_assurance.get("adaptive_assurance", {}), dict)
                and "level" in planning_assurance.get("adaptive_assurance", {})
                else config.assurance.default_level_source
                if config is not None
                else "product-default",
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
            "rule": "Path lanes stay package-defined; concern profiles are host-configured and activated from active planning assurance fields.",
        }
    if include_assurance_requirements:
        proof_selection["assurance_requirements"] = active_assurance_requirements
    markdown_path_reference_review = _markdown_path_reference_review_for_changed_paths(changed_paths=changed_paths, target_root=target_root)
    if markdown_path_reference_review["changed_paths"]:
        proof_selection["markdown_path_reference_review"] = markdown_path_reference_review
    local_tool_coupling_review = _local_tool_coupling_review_for_changed_paths(
        changed_paths=changed_paths, target_root=target_root, task_text=task_text
    )
    if local_tool_coupling_review["status"] != "not-active":
        proof_selection["local_tool_coupling_review"] = local_tool_coupling_review
    template_burden_review = _template_burden_review_for_changed_paths(
        changed_paths=changed_paths,
        target_root=target_root,
        task_text=task_text,
        learned_route_hints=learned_route_hints,
    )
    if template_burden_review["changed_paths"]:
        proof_selection["template_burden_review"] = template_burden_review
    surface_value_review = _surface_value_review_for_changed_paths(changed_paths=changed_paths, target_root=target_root)
    if surface_value_review["durable_surface_count"]:
        proof_selection["surface_value_review"] = surface_value_review
    runtime_symbol_working_set = runtime_symbol_working_set_for_changed_paths(changed_paths, target_root=target_root)
    if runtime_symbol_working_set.get("status") == "present":
        proof_selection["runtime_symbol_working_set"] = runtime_symbol_working_set
    runtime_source_review = runtime_source_edit_review_for_changed_paths(changed_paths, target_root=target_root, task_text=task_text)
    if runtime_source_review["changed_paths"]:
        proof_selection["runtime_source_edit_review"] = runtime_source_review
    direct_cli_review = _direct_cli_edit_review_for_changed_paths(changed_paths)
    if direct_cli_review["changed_paths"]:
        proof_selection["direct_cli_edit_review"] = direct_cli_review
    skill_behavior_review = _skill_behavior_impact_review_for_changed_paths(changed_paths)
    if skill_behavior_review["changed_paths"]:
        proof_selection["skill_behavior_impact_review"] = skill_behavior_review
    cli_authority_review = _cli_authority_review_for_changed_paths(changed_paths)
    if cli_authority_review["changed_paths"]:
        proof_selection["cli_authority_review"] = cli_authority_review
    return proof_selection


_MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*]\(([^)]+)\)")
_MARKDOWN_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_PATH_LIKE_SUFFIXES = (
    ".md",
    ".markdown",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".ts",
    ".txt",
)
_ROOT_PATH_NAMES = {"README.md", "AGENTS.md", "Makefile", "pyproject.toml", "uv.lock"}


def _markdown_path_reference_review_for_changed_paths(*, changed_paths: list[str], target_root: Path | None) -> dict[str, Any]:
    reviewed_paths: list[str] = []
    references: list[dict[str, Any]] = []
    for changed_path in changed_paths:
        if not changed_path.lower().endswith((".md", ".markdown")):
            continue
        path = Path(changed_path)
        source_path = path if path.is_absolute() else (target_root / path if target_root is not None else path)
        if not source_path.is_file():
            continue
        reviewed_paths.append(changed_path)
        for line_number, line in enumerate(source_path.read_text(encoding="utf-8").splitlines(), start=1):
            for raw_ref in _markdown_path_reference_candidates(line):
                reference = _classify_markdown_path_reference(
                    raw_ref=raw_ref,
                    source_path=changed_path,
                    line_number=line_number,
                    target_root=target_root,
                )
                if reference:
                    references.append(reference)
    missing = [item for item in references if item["status"] == "missing"]
    valid = [item for item in references if item["status"] == "valid"]
    ambiguous = [item for item in references if item["status"] == "ambiguous"]
    status = "not-applicable"
    if missing:
        status = "attention-needed"
    elif reviewed_paths:
        status = "clear"
    return {
        "kind": "agentic-workspace/markdown-path-reference-review/v1",
        "status": status,
        "changed_paths": reviewed_paths,
        "reference_count": len(references),
        "missing_count": len(missing),
        "valid_count": len(valid),
        "ambiguous_count": len(ambiguous),
        "missing_references": missing,
        "valid_references": valid,
        "ambiguous_references": ambiguous,
        "rule": "Changed Markdown guidance is scanned for likely concrete repo-local path references; examples, placeholders, globs, URLs, anchors, and command-like snippets are not hard failures.",
        "review_gate": "Missing likely concrete repo-local path references need correction or explicit closeout explanation before using docs/process proof as sufficient.",
        "route_learning_evidence": {
            "source": "changed Markdown static analysis",
            "candidate_route": "docs/process path-reference check",
            "parent_issue": "#1994",
            "owner_options": ["Memory", "config proof profile", "docs/checks", "Planning", "issue follow-up"],
            "recording_rule": (
                "Missed or useful path-reference findings can be captured as repo-local route-learning evidence, then "
                "promoted to a configured docs/process proof route or executable check when that owner is better."
            ),
            "capture_command": _markdown_path_reference_capture_command(changed_paths=reviewed_paths),
            "memory_note_entry": _markdown_path_reference_memory_note_entry(),
        },
    }


def _markdown_path_reference_candidates(line: str) -> list[str]:
    candidates = [match.group(1) for match in _MARKDOWN_LINK_RE.finditer(line)]
    candidates.extend(match.group(1) for match in _MARKDOWN_INLINE_CODE_RE.finditer(line))
    return candidates


def _classify_markdown_path_reference(
    *, raw_ref: str, source_path: str, line_number: int, target_root: Path | None
) -> dict[str, Any] | None:
    normalized = _normalize_markdown_path_reference(raw_ref)
    if normalized is None:
        return None
    if _markdown_reference_is_ambiguous(normalized):
        return {
            "source_path": source_path,
            "line": line_number,
            "raw_reference": raw_ref,
            "reference": normalized,
            "status": "ambiguous",
            "reason": "placeholder, glob, command, or non-concrete path-like reference",
        }
    if not _markdown_reference_is_path_like(normalized):
        return None
    exists = _changed_path_exists(target_root=target_root, changed_path=normalized)
    return {
        "source_path": source_path,
        "line": line_number,
        "raw_reference": raw_ref,
        "reference": normalized,
        "status": "valid" if exists else "missing",
        "reason": "repo-local path exists" if exists else "likely concrete repo-local path does not exist",
    }


def _normalize_markdown_path_reference(raw_ref: str) -> str | None:
    ref = raw_ref.strip().strip("<>").strip()
    if not ref or ref.startswith(("#", "http://", "https://", "mailto:")):
        return None
    if " " in ref or "\t" in ref:
        return ref
    ref = ref.split("#", 1)[0].split("?", 1)[0]
    ref = ref.strip().strip(".,;:)]}")
    while ref.startswith("./"):
        ref = ref[2:]
    return ref.replace("\\", "/") or None


def _markdown_reference_is_ambiguous(ref: str) -> bool:
    if any(token in ref for token in ("<", ">", "{", "}", "...", "*", "?")):
        return True
    if ref.startswith(("$", "python ", "uv ", "make ", "git ", "npm ", "pnpm ")):
        return True
    return " " in ref


def _markdown_reference_is_path_like(ref: str) -> bool:
    if "/" in ref:
        return True
    if ref in _ROOT_PATH_NAMES:
        return True
    return ref.endswith(_PATH_LIKE_SUFFIXES)


def _markdown_path_reference_capture_command(*, changed_paths: list[str]) -> str:
    files_arg = " ".join(changed_paths) if changed_paths else "<changed markdown paths>"
    return (
        "agentic-workspace memory capture-note --target . --slug markdown-path-reference-proof-route "
        '--summary "docs/process path-reference check found useful repo-local proof evidence" '
        f"--files {files_arg} --format json"
    )


def _markdown_path_reference_memory_note_entry() -> str:
    entry = {
        "state": "confirmed",
        "intent_type": "static-check",
        "candidate_command": "agentic-workspace proof --changed <markdown paths> --format json",
        "source": "proof-selection",
        "confidence": "medium",
        "requires_live_confirmation": False,
        "scope": "docs/process",
        "owner": "Memory",
        "provenance": "markdown_path_reference_review classified valid, missing, and ambiguous repo-local references",
        "learned_at": date.today().isoformat(),
    }
    return f"agentic-workspace-proof-route: {json.dumps(entry, sort_keys=True)}"


_LOCAL_TOOL_NEUTRALITY_TERMS = (
    "tool-neutral",
    "tool neutral",
    "tool neutrality",
    "no agentic workspace",
    "no local tool",
    "local-tool coupling",
    "avoid local tool",
)
_LOCAL_TOOL_TERMS = ("agentic workspace", "agentic-workspace", ".agentic-workspace", "run_agentic_workspace.py")
_MANDATORY_PROCESS_TERMS = ("must", "required", "shall", "always", "need to", "needs to", "have to")
_OPTIONAL_EVIDENCE_TERMS = ("optional", "may", "can", "if using", "when using", "local evidence", "implementation evidence")


def _local_tool_coupling_review_for_changed_paths(
    *, changed_paths: list[str], target_root: Path | None, task_text: str | None
) -> dict[str, Any]:
    task_activation = _local_tool_coupling_activation(task_text=task_text)
    scanned_files: list[tuple[str, list[str]]] = []
    file_activation: list[str] = []
    for changed_path in changed_paths:
        if not changed_path.lower().endswith((".md", ".markdown")):
            continue
        path = Path(changed_path)
        source_path = path if path.is_absolute() else (target_root / path if target_root is not None else path)
        if not source_path.is_file():
            continue
        lines = source_path.read_text(encoding="utf-8").splitlines()
        scanned_files.append((changed_path, lines))
        for line in lines:
            file_activation.extend(term for term in _LOCAL_TOOL_NEUTRALITY_TERMS if term in line.lower())
    activation = _dedupe([*task_activation, *file_activation])
    if not activation:
        return {
            "kind": "agentic-workspace/local-tool-coupling-review/v1",
            "status": "not-active",
            "activation": {"status": "absent", "source": "task-intent"},
        }
    reviewed_paths: list[str] = []
    flagged: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    for changed_path, lines in scanned_files:
        reviewed_paths.append(changed_path)
        for line_number, line in enumerate(lines, start=1):
            classification = _classify_local_tool_coupling_line(line)
            if classification is None:
                continue
            item = {
                "source_path": changed_path,
                "line": line_number,
                "text": line.strip(),
                "matched_terms": classification["matched_terms"],
                "reason": classification["reason"],
            }
            if classification["status"] == "flagged":
                flagged.append(item)
            elif classification["status"] == "accepted":
                accepted.append(item)
            else:
                ambiguous.append(item)
    return {
        "kind": "agentic-workspace/local-tool-coupling-review/v1",
        "status": "attention-needed" if flagged else "clear",
        "activation": {"status": "active", "source": "task-intent", "matched_terms": activation},
        "changed_paths": reviewed_paths,
        "flagged_count": len(flagged),
        "accepted_optional_count": len(accepted),
        "ambiguous_count": len(ambiguous),
        "flagged_references": flagged,
        "accepted_optional_references": accepted,
        "ambiguous_references": ambiguous,
        "rule": (
            "When tool neutrality is in scope, changed guidance is scanned for local-tool references. Mandatory repository-process "
            "wording is flagged; optional local evidence wording is allowed."
        ),
        "review_gate": "Flagged mandatory local-tool process wording needs rewrite or explicit closeout explanation.",
    }


def _local_tool_coupling_activation(*, task_text: str | None) -> list[str]:
    text = (task_text or "").lower()
    return [term for term in _LOCAL_TOOL_NEUTRALITY_TERMS if term in text]


def _classify_local_tool_coupling_line(line: str) -> dict[str, Any] | None:
    text = line.lower()
    matched_terms = [term for term in _LOCAL_TOOL_TERMS if term in text]
    if not matched_terms:
        return None
    if any(term in text for term in _OPTIONAL_EVIDENCE_TERMS):
        return {
            "status": "accepted",
            "matched_terms": matched_terms,
            "reason": "optional or evidence-scoped local-tool wording",
        }
    if any(term in text for term in _MANDATORY_PROCESS_TERMS):
        return {
            "status": "flagged",
            "matched_terms": matched_terms,
            "reason": "mandatory repository-process wording references a local tool while tool neutrality is in scope",
        }
    return {
        "status": "ambiguous",
        "matched_terms": matched_terms,
        "reason": "local-tool reference needs human interpretation under tool-neutral task intent",
    }


_TEMPLATE_BURDEN_ACTIVATION_TERMS = (
    "template-burden",
    "template burden",
    "low-risk answer",
    "low risk answer",
    "contributor-burden",
    "contributor burden",
)
_TEMPLATE_BURDEN_PATH_TERMS = ("pull_request_template", "issue_template", ".github/issue_template")
_TEMPLATE_BURDEN_SECTION_TERMS = ("risk", "evidence", "proof", "validation", "assurance", "gap")
_TEMPLATE_LOW_RISK_TERMS = ("not applicable", "n/a", "no high-risk", "no evidence gaps", "optional", "if applicable")


def _template_burden_review_for_changed_paths(
    *, changed_paths: list[str], target_root: Path | None, task_text: str | None, learned_route_hints: dict[str, Any] | None
) -> dict[str, Any]:
    template_paths = [changed_path for changed_path in changed_paths if _is_template_path(changed_path)]
    activation = _template_burden_activation(task_text=task_text, learned_route_hints=learned_route_hints)
    if not template_paths:
        return {
            "kind": "agentic-workspace/template-burden-review/v1",
            "status": "not-applicable",
            "changed_paths": [],
            "activation": {"status": "not-applicable"},
        }
    if not activation:
        return {
            "kind": "agentic-workspace/template-burden-review/v1",
            "status": "not-active",
            "changed_paths": template_paths,
            "flagged_count": 0,
            "accepted_count": 0,
            "flagged_sections": [],
            "accepted_sections": [],
            "activation": {
                "status": "absent",
                "rule": "Template-burden review needs explicit task intent or repo-local learned route evidence.",
            },
            "process_surface": "pr-or-issue-template",
        }
    reviewed_paths: list[str] = []
    flagged: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for changed_path in template_paths:
        path = Path(changed_path)
        source_path = path if path.is_absolute() else (target_root / path if target_root is not None else path)
        if not source_path.is_file():
            continue
        reviewed_paths.append(changed_path)
        lines = source_path.read_text(encoding="utf-8").splitlines()
        text = "\n".join(lines).lower()
        has_low_risk_path = any(term in text for term in _TEMPLATE_LOW_RISK_TERMS)
        for line_number, line in enumerate(lines, start=1):
            line_lower = line.lower()
            if not line.lstrip().startswith("#"):
                continue
            if not any(term in line_lower for term in _TEMPLATE_BURDEN_SECTION_TERMS):
                continue
            item = {"source_path": changed_path, "line": line_number, "text": line.strip()}
            if "optional" in line_lower or has_low_risk_path:
                accepted.append({**item, "reason": "template section is optional or gives a low-risk/not-applicable answer path"})
            else:
                flagged.append(
                    {
                        **item,
                        "reason": "mandatory-looking template section may burden every future contributor without a low-risk answer path",
                    }
                )
    return {
        "kind": "agentic-workspace/template-burden-review/v1",
        "status": "attention-needed" if flagged else "clear" if reviewed_paths else "not-applicable",
        "activation": {"status": "active", "signals": activation},
        "changed_paths": reviewed_paths,
        "flagged_count": len(flagged),
        "accepted_count": len(accepted),
        "flagged_sections": flagged,
        "accepted_sections": accepted,
        "rule": (
            "PR and issue template changes are process-surface changes. Mandatory risk/evidence/proof sections should give "
            "ordinary low-risk contributors an explicit lightweight answer path."
        ),
        "review_gate": "Flagged template sections need optional wording, a not-applicable example, or explicit closeout rationale.",
        "route_learning_evidence": {
            "source": "repo-local template-burden review signal",
            "candidate_route": "docs/process template-burden review",
            "parent_issue": "#1997",
            "owner_options": ["Memory", "config proof profile", "docs/checks", "Planning", "issue follow-up"],
            "recording_rule": (
                "Useful or missed template-burden findings should be captured as repo-local route-learning evidence before "
                "they become routine proof/review signals for future template changes."
            ),
            "capture_command": _template_burden_capture_command(changed_paths=reviewed_paths),
            "memory_note_entry": _template_burden_memory_note_entry(),
        },
    }


def _is_template_path(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    return any(term in normalized for term in _TEMPLATE_BURDEN_PATH_TERMS)


def _template_burden_activation(*, task_text: str | None, learned_route_hints: dict[str, Any] | None) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    task_lower = (task_text or "").lower()
    for term in _TEMPLATE_BURDEN_ACTIVATION_TERMS:
        if term in task_lower:
            signals.append({"source": "task-intent", "term": term})
    for hint in (learned_route_hints or {}).get("confirmed", []):
        searchable = " ".join(
            str(hint.get(field, ""))
            for field in ("id", "candidate_command", "scope", "provenance", "source_path")
            if str(hint.get(field, "")).strip()
        ).lower()
        matched_terms = [term for term in _TEMPLATE_BURDEN_ACTIVATION_TERMS if term in searchable]
        if not matched_terms:
            continue
        signals.append(
            {
                "source": "repo-learned-proof-route",
                "route_id": str(hint.get("id", "")),
                "owner": str(hint.get("owner", "")),
                "term": matched_terms[0],
            }
        )
    return signals


def _template_burden_capture_command(*, changed_paths: list[str]) -> str:
    files_arg = " ".join(changed_paths) if changed_paths else "<changed template paths>"
    return (
        "agentic-workspace memory capture-note --target . --slug template-burden-review-route "
        '--summary "docs/process template-burden review found useful repo-local evidence" '
        f"--files {files_arg} --format json"
    )


def _template_burden_memory_note_entry() -> str:
    entry = {
        "state": "confirmed",
        "intent_type": "static-check",
        "candidate_command": "agentic-workspace proof --changed <template paths> --format json",
        "source": "memory",
        "confidence": "medium",
        "requires_live_confirmation": False,
        "scope": "docs/process template-burden",
        "owner": "Memory",
        "provenance": "template_burden_review classified mandatory and optional PR/issue template guidance",
        "learned_at": date.today().isoformat(),
    }
    return f"agentic-workspace-proof-route: {json.dumps(entry, sort_keys=True)}"


_DOCS_PROCESS_ACTIVATION_TERMS = (
    "docs/process",
    "docs-only",
    "documentation-only",
    "markdown path reference",
    "path-reference",
    "template-burden",
    "template burden",
    "tool-neutral",
    "local-tool coupling",
    "learned docs",
)


def _docs_process_route_refinement(
    *, changed_paths: list[str], selected_lanes: list[dict[str, Any]], task_text: str | None, learned_route_hints: dict[str, Any]
) -> dict[str, Any]:
    docs_paths = [path for path in changed_paths if _is_docs_process_route_path(path)]
    activation = _docs_process_route_activation(task_text=task_text, learned_route_hints=learned_route_hints)
    selected_lane_ids = [str(lane.get("id", "")) for lane in selected_lanes]
    if not changed_paths or len(docs_paths) != len(changed_paths):
        return {
            "kind": "agentic-workspace/docs-process-route/v1",
            "status": "not-applicable",
            "changed_paths": docs_paths,
            "activation": activation,
        }
    if not activation:
        return {
            "kind": "agentic-workspace/docs-process-route/v1",
            "status": "not-active",
            "changed_paths": docs_paths,
            "activation": activation,
            "rule": "Docs/process route narrowing needs explicit task intent or repo-local learned route evidence.",
        }
    reductions = []
    if "workspace_cli" in selected_lane_ids:
        reductions.append(
            {
                "path": ", ".join(docs_paths),
                "from_lane": "workspace_cli",
                "to_lane": "repo_docs_review",
                "reason": "repo-learned docs/process route covers documentation, template, path-reference, and guidance checks",
            }
        )
    return {
        "kind": "agentic-workspace/docs-process-route/v1",
        "status": "active",
        "changed_paths": docs_paths,
        "activation": activation,
        "routing_reductions": reductions,
        "required_review_packets": [
            "markdown_path_reference_review",
            "template_burden_review",
            "local_tool_coupling_review",
            "proof_closeout_summary",
        ],
        "route_maturity": "repo-learned"
        if any(signal.get("source") == "repo-learned-proof-route" for signal in activation)
        else "task-scoped",
        "rule": (
            "When repo evidence supports a docs/process route, docs-only guidance and template changes use docs/process proof "
            "before broad backend proof. Broader proof remains an escalation, policy, or confidence route."
        ),
    }


def _apply_docs_process_route_to_lanes(
    *, selected_lanes: list[dict[str, Any]], docs_review_lane: dict[str, Any], docs_process_route: dict[str, Any]
) -> list[dict[str, Any]]:
    lanes = [lane for lane in selected_lanes if str(lane.get("id", "")) != "workspace_cli"]
    docs_lane = next((lane for lane in lanes if str(lane.get("id", "")) == "repo_docs_review"), None)
    if docs_lane is None:
        docs_lane = docs_review_lane
        lanes.insert(0, docs_lane)
    docs_lane["learned_route"] = {
        "id": "docs-process",
        "source": "repo-local evidence",
        "maturity": docs_process_route.get("route_maturity", "repo-learned"),
    }
    docs_lane["enough_proof"] = [_docs_process_review_command(changed_paths=docs_process_route.get("changed_paths", []))]
    docs_lane["recovery_signal"] = (
        "Docs/process proof should resolve Markdown paths, template burden, tool-neutral wording, and diff review before "
        "broad backend proof is treated as necessary."
    )
    return lanes


def _docs_process_route_activation(*, task_text: str | None, learned_route_hints: dict[str, Any]) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    task_lower = (task_text or "").lower()
    for term in _DOCS_PROCESS_ACTIVATION_TERMS:
        if term in task_lower:
            signals.append({"source": "task-intent", "term": term})
    for hint in learned_route_hints.get("confirmed", []):
        if not isinstance(hint, dict):
            continue
        searchable = " ".join(
            str(hint.get(field, ""))
            for field in ("id", "candidate_command", "scope", "provenance", "source_path")
            if str(hint.get(field, "")).strip()
        ).lower()
        matched_terms = [term for term in _DOCS_PROCESS_ACTIVATION_TERMS if term in searchable]
        if not matched_terms:
            continue
        signals.append(
            {
                "source": "repo-learned-proof-route",
                "route_id": str(hint.get("id", "")),
                "owner": str(hint.get("owner", "")),
                "term": matched_terms[0],
            }
        )
    return signals


def _is_docs_process_route_path(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    if normalized in {"readme.md", "packages/planning/readme.md", "packages/memory/readme.md"}:
        return True
    if normalized.startswith((".agentic-workspace/docs/", "docs/")) and normalized.endswith((".md", ".markdown")):
        return True
    if normalized == ".github/pull_request_template.md":
        return True
    if normalized.startswith(".github/issue_template/") or normalized.startswith(".github/issue_template"):
        return True
    return False


def _docs_process_review_command(*, changed_paths: list[str]) -> str:
    base_paths = ["README.md", "docs", ".agentic-workspace/docs", "packages/planning/README.md", "packages/memory/README.md"]
    template_paths = [
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE",
    ]
    include_templates = any(str(path).lower().replace("\\", "/").startswith(".github/") for path in changed_paths)
    paths = [*base_paths, *(template_paths if include_templates else [])]
    return f"git diff -- {' '.join(paths)}"


def _proof_closeout_summary_payload(
    *,
    changed_paths: list[str],
    selected_lanes: list[dict[str, Any]],
    proof_route_decision: dict[str, Any],
    proof_command_explanations: dict[str, Any],
    proof_execution_evidence: dict[str, Any],
    proof_receipt_reconciliation: dict[str, Any],
    proof_receipt_bridge: dict[str, Any],
    learned_route_reliance: dict[str, Any],
    manual_verification: dict[str, Any] | None,
    unavailable_commands: list[dict[str, Any]],
    host_policy_blocked_commands: list[dict[str, str]],
) -> dict[str, Any]:
    route = _proof_closeout_route_payload(
        proof_route_decision=proof_route_decision,
        proof_command_explanations=proof_command_explanations,
        learned_route_reliance=learned_route_reliance,
    )
    proof_results = _proof_closeout_proof_results(
        proof_execution_evidence=proof_execution_evidence,
        proof_receipt_reconciliation=proof_receipt_reconciliation,
    )
    maturity_gaps = _proof_closeout_maturity_gaps(proof_command_explanations=proof_command_explanations)
    maturity_disposition = _proof_closeout_maturity_disposition(
        proof_route_decision=proof_route_decision,
        proof_results=proof_results,
        maturity_gaps=maturity_gaps,
    )
    remaining_gaps = _proof_closeout_remaining_gaps(
        proof_results=proof_results,
        manual_verification=manual_verification,
        unavailable_commands=unavailable_commands,
        host_policy_blocked_commands=host_policy_blocked_commands,
        maturity_blockers=maturity_disposition["blockers"],
    )
    risk_lanes = _dedupe([str(lane.get("id", "")).strip() for lane in selected_lanes if str(lane.get("id", "")).strip()])
    status = (
        "sufficient-recorded"
        if not remaining_gaps and proof_results
        else "not-yet-sufficient"
        if remaining_gaps
        else "needs-agent-judgment"
    )
    sufficiency = _proof_closeout_sufficiency_text(status=status, proof_results=proof_results, remaining_gaps=remaining_gaps)
    lines = [
        f"Changed paths: {_join_or_none(changed_paths)}.",
        f"Route: {route['name']} ({route['source']}; maturity={route['maturity']}).",
        f"Risk lanes: {_join_or_none(risk_lanes)}.",
        f"Required proof: {_join_or_none([item['command'] for item in proof_results])}.",
        f"Proof result: {_proof_closeout_result_line(proof_results)}.",
        f"Remaining gaps: {_join_or_none(remaining_gaps)}.",
        f"Sufficiency: {sufficiency}",
    ]
    return {
        "kind": "agentic-workspace/proof-closeout-summary/v1",
        "status": status,
        "changed_paths": changed_paths,
        "changed_surface_groups": _proof_closeout_surface_groups(changed_paths=changed_paths),
        "route": route,
        "applicable_risk_lanes": risk_lanes,
        "risk_lane_statement": _join_or_none(risk_lanes),
        "required_proof": [item["command"] for item in proof_results],
        "proof_results": proof_results,
        "proof_result_statement": _proof_closeout_result_line(proof_results),
        "receipt_bridge": {
            "status": str(proof_receipt_bridge.get("status", "")),
            "missing_receipt_count": int(proof_receipt_bridge.get("missing_receipt_count", 0) or 0),
            "detail_selector": "proof_receipt_bridge",
        },
        "remaining_gaps": remaining_gaps,
        "remaining_gap_statement": _join_or_none(remaining_gaps),
        "route_maturity": maturity_disposition,
        "route_maturity_advisories": maturity_disposition["advisories"],
        "route_maturity_gaps": maturity_disposition["blockers"],
        "sufficiency": {"status": status, "why": sufficiency},
        "pr_validation_lines": lines,
        "rule": "This is a human-facing projection of proof-selection and receipt evidence; it does not replace the underlying proof records.",
    }


def _proof_closeout_route_payload(
    *, proof_route_decision: dict[str, Any], proof_command_explanations: dict[str, Any], learned_route_reliance: dict[str, Any]
) -> dict[str, str]:
    selected = proof_route_decision.get("selected_command") if isinstance(proof_route_decision, dict) else None
    if isinstance(selected, dict):
        route_source = str(selected.get("route_source", ""))
        fallback_status = str(selected.get("fallback_status", ""))
        command = str(selected.get("command", ""))
        reason_classes = _reason_classes_for_command(command=command, proof_command_explanations=proof_command_explanations)
        reliance_items = learned_route_reliance.get("items", []) if isinstance(learned_route_reliance, dict) else []
        learned_item = next((item for item in reliance_items if isinstance(item, dict) and item.get("command") == command), {})
        source = str(learned_item.get("source") or selected.get("authority_surface") or route_source)
        evidence = str(learned_item.get("provenance") or selected.get("route_authority") or route_source)
        maturity = (
            "learned-confirmed"
            if learned_item
            else "conservative-fallback"
            if "conservative-fallback" in reason_classes
            else fallback_status
        )
        return {
            "name": route_source or "selected-proof-route",
            "command": command,
            "source": source or "unknown",
            "evidence": evidence or "not recorded",
            "maturity": maturity or "unknown",
            "fallback_status": fallback_status,
            "reason_classes": ", ".join(reason_classes),
        }
    manual = proof_route_decision.get("manual_fallback") if isinstance(proof_route_decision, dict) else None
    return {
        "name": "manual-fallback" if manual else str(proof_route_decision.get("route_source", "none")),
        "command": "",
        "source": "manual-verification" if manual else "none",
        "evidence": str(manual.get("summary", "")) if isinstance(manual, dict) else "no route selected",
        "maturity": "manual-required" if manual else "none",
        "fallback_status": "manual-required" if manual else "none",
        "reason_classes": "unavailable-manual" if manual else "",
    }


def _reason_classes_for_command(*, command: str, proof_command_explanations: dict[str, Any]) -> list[str]:
    for item in _list_payload(proof_command_explanations.get("required")):
        if isinstance(item, dict) and item.get("command") == command:
            return [str(value) for value in _list_payload(item.get("reason_classes"))]
    return []


def _proof_closeout_proof_results(
    *, proof_execution_evidence: dict[str, Any], proof_receipt_reconciliation: dict[str, Any]
) -> list[dict[str, str]]:
    execution_by_command = {
        str(item.get("command", "")): item for item in _list_payload(proof_execution_evidence.get("commands")) if isinstance(item, dict)
    }
    results: list[dict[str, str]] = []
    for item in _list_payload(proof_receipt_reconciliation.get("commands")):
        if not isinstance(item, dict):
            continue
        command = str(item.get("command", ""))
        execution = execution_by_command.get(command, {})
        evidence_state = str(item.get("evidence_state", ""))
        result = (
            "passed"
            if evidence_state == "accepted"
            else "failed"
            if evidence_state == "recorded-failed"
            else str(execution.get("status", "missing"))
        )
        results.append(
            {
                "command": command,
                "result": result,
                "receipt_state": evidence_state or "not-recorded",
                "execution_state": str(execution.get("status", "missing")),
                "evidence_source": "proof-receipt" if evidence_state == "accepted" else "execution-evidence" if execution else "missing",
            }
        )
    if results:
        return results
    for item in _list_payload(proof_execution_evidence.get("commands")):
        if isinstance(item, dict):
            results.append(
                {
                    "command": str(item.get("command", "")),
                    "result": str(item.get("status", "missing")),
                    "receipt_state": "not-recorded",
                    "execution_state": str(item.get("status", "missing")),
                    "evidence_source": "execution-evidence",
                }
            )
    return results


def _proof_closeout_maturity_gaps(*, proof_command_explanations: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for item in _list_payload(proof_command_explanations.get("required")):
        if not isinstance(item, dict):
            continue
        if "conservative-fallback" in _list_payload(item.get("reason_classes")):
            gaps.append(f"{item.get('command')}: conservative fallback; narrower learned route evidence is missing or immature")
    return gaps


def _proof_closeout_maturity_disposition(
    *, proof_route_decision: dict[str, Any], proof_results: list[dict[str, str]], maturity_gaps: list[str]
) -> dict[str, Any]:
    selected = _as_dict(proof_route_decision.get("selected_command"))
    authority = str(selected.get("route_authority") or "").strip()
    authority_surface = str(selected.get("authority_surface") or "").strip()
    result_by_command = {str(item.get("command") or ""): str(item.get("result") or "") for item in proof_results}
    maturity_commands = [gap.split(": conservative fallback", 1)[0] for gap in maturity_gaps]
    uncovered_commands = [command for command in maturity_commands if result_by_command.get(command) not in {"passed", "waived"}]
    authority_established = bool(authority and authority_surface)
    coverage_established = bool(maturity_commands) and not uncovered_commands
    advisory_allowed = authority_established and coverage_established
    return {
        "status": "advisory" if advisory_allowed else "blocked" if maturity_gaps else "not-applicable",
        "authority": authority,
        "authority_surface": authority_surface,
        "authority_established": authority_established,
        "coverage_established": coverage_established,
        "uncovered_commands": uncovered_commands,
        "advisories": maturity_gaps if advisory_allowed else [],
        "blockers": [] if advisory_allowed else maturity_gaps,
        "rule": "Conservative route maturity is advisory only when selected route authority is explicit and every affected command has accepted covering proof.",
    }


def _proof_closeout_remaining_gaps(
    *,
    proof_results: list[dict[str, str]],
    manual_verification: dict[str, Any] | None,
    unavailable_commands: list[dict[str, Any]],
    host_policy_blocked_commands: list[dict[str, str]],
    maturity_blockers: list[str],
) -> list[str]:
    gaps: list[str] = []
    for item in proof_results:
        if item.get("result") not in {"passed", "waived"}:
            gaps.append(f"{item.get('command')}: proof result is {item.get('result')}")
    if isinstance(manual_verification, dict):
        gaps.append(str(manual_verification.get("summary") or manual_verification.get("reason") or "manual verification required"))
    gaps.extend(f"{item.get('command')}: {item.get('reason')}" for item in unavailable_commands if isinstance(item, dict))
    gaps.extend(f"{item.get('command')}: host policy blocked selected proof" for item in host_policy_blocked_commands)
    gaps.extend(maturity_blockers)
    return _dedupe([gap for gap in gaps if gap.strip()])


def _proof_closeout_surface_groups(*, changed_paths: list[str]) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = {}
    for path in changed_paths:
        group = "docs/process" if path.lower().endswith((".md", ".markdown")) or path.startswith(".github/") else "runtime/source"
        groups.setdefault(group, []).append(path)
    return [{"group": group, "paths": paths} for group, paths in groups.items()]


def _proof_closeout_sufficiency_text(*, status: str, proof_results: list[dict[str, str]], remaining_gaps: list[str]) -> str:
    if status == "sufficient-recorded":
        return "All selected required proof has accepted execution evidence for the changed-path boundary."
    if remaining_gaps:
        return "Required proof or route maturity gaps remain; do not use this summary as completion proof yet."
    if not proof_results:
        return "No required proof result is recorded; agent judgment must supply task-specific closeout evidence."
    return "Proof status needs agent interpretation before a completion claim."


def _proof_closeout_result_line(proof_results: list[dict[str, str]]) -> str:
    if not proof_results:
        return "none recorded"
    return "; ".join(f"{item['command']} -> {item['result']}" for item in proof_results)


def _join_or_none(values: list[str]) -> str:
    visible = [str(value).strip() for value in values if str(value).strip()]
    return ", ".join(visible) if visible else "none known"


def _proof_command_explanations_payload(
    *,
    selected_commands: list[dict[str, Any]],
    required_commands: list[str],
    optional_commands: list[str],
    unavailable_commands: list[dict[str, Any]],
    host_policy_blocked_commands: list[dict[str, str]],
    manual_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    selected_by_text = {str(command.get("command", "")): command for command in selected_commands}
    required_items = [
        _proof_command_explanation_item(command=str(command), selected=selected_by_text.get(str(command), {}), blocking=True)
        for command in required_commands
    ]
    optional_items = [
        {
            "command": str(command),
            "reason_classes": ["optional-confidence"],
            "blocking": False,
            "why": "Recommended confidence check; it may raise trust but does not replace required proof.",
        }
        for command in optional_commands
        if str(command) not in set(required_commands)
    ]
    manual_items = (
        [
            {
                "kind": "manual-verification/v1",
                "status": str(manual_verification.get("status", "")),
                "reason_classes": ["unavailable-manual"],
                "blocking": True,
                "why": str(manual_verification.get("reason", "")) or "Manual verification is required.",
            }
        ]
        if manual_verification is not None
        else []
    )
    unavailable_items = [
        {
            "command": str(command.get("command", "")),
            "lane": str(command.get("lane", "")),
            "reason": str(command.get("reason", "")),
            "reason_classes": ["unavailable-manual"],
            "blocking": True,
            **({"missing_paths": command["missing_paths"]} if command.get("missing_paths") else {}),
            **({"replacement": command["replacement"]} if command.get("replacement") else {}),
        }
        for command in unavailable_commands
    ]
    policy_blocked_items = [
        {
            "command": str(command.get("command", "")),
            "lane": str(command.get("lane", "")),
            "reason": str(command.get("reason", "")),
            "reason_classes": ["explicit-config-policy"],
            "blocking": True,
            "configured_command": str(command.get("configured_command", "")),
        }
        for command in host_policy_blocked_commands
    ]
    return {
        "kind": "agentic-workspace/proof-command-explanations/v1",
        "status": "present" if required_items or optional_items or manual_items or unavailable_items or policy_blocked_items else "empty",
        "reason_class_model": {
            "learned-repo-evidence": "selected from confirmed repo-local route evidence or Memory-backed learning",
            "explicit-config-policy": "selected or blocked by host configuration, subsystem ownership, local overlay, or proof profile",
            "changed-surface-risk": "selected because changed paths matched a proof rule or risk lane",
            "conservative-fallback": "selected through package seed, broad fallback, or live-adapted target capability before route learning is mature",
            "optional-confidence": "recommended confidence check that is not a hard closeout blocker",
            "unavailable-manual": "manual verification or explanation is required because executable proof is missing, blocked, or unavailable",
        },
        "required": required_items,
        "optional_confidence": optional_items,
        "manual_or_unavailable": [*manual_items, *unavailable_items, *policy_blocked_items],
        "blocking_rule": (
            "Only required commands, host-policy blockers, unavailable required proof, and required manual verification block closeout; "
            "optional confidence checks remain visible but non-blocking."
        ),
        "route_maturity_rule": "Commands with conservative-fallback should be refined by learned route evidence before treating them as route-specific.",
    }


def _proof_command_explanation_item(*, command: str, selected: dict[str, Any], blocking: bool) -> dict[str, Any]:
    route_source = str(selected.get("selected_from", ""))
    fallback_status = str(selected.get("fallback_status", ""))
    reason_classes = _proof_command_reason_classes(route_source=route_source, fallback_status=fallback_status)
    return {
        "command": command,
        "lane": str(selected.get("lane", "")),
        "intent_type": str(selected.get("intent_type", "")),
        "route_source": route_source,
        "fallback_status": fallback_status,
        "route_authority": str(selected.get("route_authority", "")),
        "reason_classes": reason_classes,
        "blocking": blocking,
        "why": _proof_command_explanation_text(reason_classes=reason_classes, selected=selected),
    }


def _proof_command_reason_classes(*, route_source: str, fallback_status: str) -> list[str]:
    classes: list[str] = []
    if route_source == "repo-learned-proof-route":
        classes.append("learned-repo-evidence")
    if route_source in {
        "host-configured-proof-profile",
        "host-declared-domain-proof-lane",
        "host-configured-subsystem",
        "local-only-high-risk-overlay",
        "verification-manual-protocol",
    }:
        classes.append("explicit-config-policy")
    if route_source in {"live-confirmed-proof-rule", "live-adapted-target-capability"}:
        classes.append("changed-surface-risk")
    if fallback_status in {"seed-fallback", "fallback", "candidate-live-confirmed"}:
        classes.append("conservative-fallback")
    return classes or ["changed-surface-risk"]


def _proof_command_explanation_text(*, reason_classes: list[str], selected: dict[str, Any]) -> str:
    lane = str(selected.get("lane", ""))
    if "learned-repo-evidence" in reason_classes:
        return f"Required because learned repo evidence selected lane {lane}."
    if "explicit-config-policy" in reason_classes:
        return f"Required because host-owned policy or configuration selected lane {lane}."
    if "conservative-fallback" in reason_classes:
        return f"Required as conservative fallback for lane {lane}; refine with learned route evidence when possible."
    return f"Required because changed-surface risk selected lane {lane}."
