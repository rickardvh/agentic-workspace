from __future__ import annotations

import copy
import json
import os
from collections.abc import Callable
from difflib import get_close_matches
from pathlib import Path
from typing import Any

from agentic_workspace.config import DEFAULT_CLI_INVOKE, WorkspaceUsageError
from agentic_workspace.repository_scanning import repository_scan_files
from agentic_workspace.workspace_output import bounded_selector_inventory

REPO_FRICTION_LARGE_FILE_THRESHOLD = 400
REPO_FRICTION_CONCEPT_SURFACE_THRESHOLD = 200
REPO_FRICTION_MAX_HOTSPOTS = 5
REPO_FRICTION_MAX_SCAN_FILES = 1200
REPO_FRICTION_SCAN_SUFFIXES = {
    ".md",
    ".py",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
}
REPO_FRICTION_REGENERABLE_CACHE_PREFIXES = (".agentic-workspace/local/cache/", "scratch/")

STANDING_INTENT_CANONICAL_DOC = ".agentic-workspace/docs/standing-intent-contract.md"
REASONING_ECONOMY_EVIDENCE_LEDGER_PATH = ".agentic-workspace/verification/reasoning-economy-evidence.json"

REPORT_SECTION_ALIASES = {
    "active_work": "current_work",
    "current_work": "current_work",
    "current_external_work": "external_work_reconciliation",
    "external_work": "external_work_reconciliation",
}


def communication_contract_payload(*, surface: str) -> dict[str, Any]:
    phase_expectations = {
        "startup": {
            "primary_question": "What is the next safe action?",
            "include": ["decision", "blocking_or_allowed_action", "required_skill_or_command", "state_boundary"],
            "default_detail": "action-first routing plus selector-backed detail routes",
        },
        "shaping": {
            "primary_question": "What is the smallest safe workflow shape?",
            "include": ["scope_decision", "why_it_matters", "promotion_or_planning_boundary", "next_safe_action"],
            "default_detail": "state the bounded slice and non-goals when needed",
        },
        "implementation": {
            "primary_question": "What narrow working set is safe to touch now?",
            "include": ["changed_paths", "proof_route", "acceptance_boundary", "residue_owner"],
            "default_detail": "name only action-changing warnings and selected proof",
        },
        "proof": {
            "primary_question": "What evidence is required before the claim?",
            "include": ["required_commands", "proof_gap_or_pass", "claim_boundary", "rerun_or_record_route"],
            "default_detail": "summarize proof state without raw logs unless failure lines are needed",
        },
        "closeout": {
            "primary_question": "Can this completion claim be trusted?",
            "include": ["intent_satisfaction", "proof_receipts", "residue", "safe_claim_level"],
            "default_detail": "compact claim, evidence, residue, and closure boundary",
        },
        "handoff_review": {
            "primary_question": "What must the next agent or reviewer know without replaying chat?",
            "include": ["finding_or_change", "evidence_ref", "risk_or_residue", "next_owner"],
            "default_detail": "findings first for reviews; handoff facts only when continuation matters",
        },
    }
    return {
        "kind": "agentic-workspace/communication-contract/v1",
        "surface": surface,
        "status": "active",
        "default_posture": "decision_first_state_backed",
        "narration_budget": "minimal",
        "required_order": ["decision_or_finding", "why_it_matters", "evidence_or_proof_route", "residue_or_boundary", "next_safe_action"],
        "include": [
            "decision_or_finding",
            "current_intent_relevance",
            "evidence_or_proof_route",
            "unresolved_residue_or_safety_boundary",
            "next_safe_action",
        ],
        "suppress_by_default": [
            "chronological_tool_call_narration",
            "repeated_context_reconstruction",
            "generic_caveats_that_do_not_change_action_safety",
            "broad_rationale_when_decisive_state_and_boundary_are_enough",
        ],
        "expand_when": [
            "ambiguous_action_safety",
            "irreversible_or_destructive_change",
            "stale_missing_or_failed_proof",
            "user_requests_detail",
            "rejected_alternative_prevents_rediscovery",
            "handoff_or_review_needs_continuation_context",
        ],
        "phase_expectations": phase_expectations,
        "state_usage_rule": (
            "Use compact AW fields as the evidence source first; cite or expand raw docs only when selectors, proof gaps, "
            "or safety boundaries require it."
        ),
        "cost_evaluation": {
            "question": "Did structured state reduce rereads, narration, or reconstruction without weakening proof, residue, or action clarity?",
            "preserve": ["evidence", "proof_boundary", "unresolved_residue", "next_safe_action"],
            "reduce": ["low_value_narration", "repeated_rereads", "context_reconstruction"],
        },
        "detail_command": "agentic-workspace defaults --section communication_contract --format json",
    }


def compact_communication_contract_payload(*, surface: str) -> dict[str, Any]:
    full = communication_contract_payload(surface=surface)
    return {
        "kind": full["kind"],
        "surface": full["surface"],
        "status": full["status"],
        "default_posture": full["default_posture"],
        "narration_budget": full["narration_budget"],
        "phase_ids": list(full["phase_expectations"].keys()),
        "expand_when": full["expand_when"],
        "cost_evaluation": {
            "preserve": full["cost_evaluation"]["preserve"],
            "reduce": full["cost_evaluation"]["reduce"],
        },
    }


def _state_delta_claim_boundary(decision_packet: dict[str, Any]) -> str:
    claim_boundary = decision_packet.get("claim_boundary", "not-evaluated")
    if isinstance(claim_boundary, dict):
        claim_boundary = str(
            claim_boundary.get("status")
            or claim_boundary.get("gate_result")
            or claim_boundary.get("claim_level_allowed")
            or "structured-boundary"
        )
    return str(claim_boundary)


def state_delta_core_payload(
    *,
    surface: str,
    decision_packet: dict[str, Any],
    communication_contract: dict[str, Any] | None = None,
    evidence_basis: list[str] | None = None,
    missing_evidence: list[str] | None = None,
    safe_probe: str | None = None,
    response_shape: list[str] | None = None,
    avoid_repeat: list[str] | None = None,
) -> dict[str, Any]:
    contract = (
        communication_contract if isinstance(communication_contract, dict) else compact_communication_contract_payload(surface=surface)
    )
    blocked_actions = [str(item) for item in decision_packet.get("blocked_actions", []) if str(item).strip()]
    required_commands = [str(item) for item in decision_packet.get("required_commands", []) if str(item).strip()]
    detail_routes = decision_packet.get("detail_routes", {})
    route_keys = list(detail_routes.keys()) if isinstance(detail_routes, dict) else []
    known_evidence = [
        str(item)
        for item in (
            evidence_basis
            or [
                f"phase_question={decision_packet.get('phase_question', '')}",
                f"next_action={decision_packet.get('next_action', '')}",
                f"claim_boundary={decision_packet.get('claim_boundary', '')}",
            ]
        )
        if str(item).strip()
    ]
    missing = [
        str(item)
        for item in (
            missing_evidence
            or (
                required_commands
                if required_commands
                else ["proof execution evidence before hard completion claim"]
                if "claim" in str(decision_packet.get("claim_boundary", "")).lower()
                else []
            )
        )
        if str(item).strip()
    ]
    default_safe_probe = ""
    if required_commands:
        default_safe_probe = required_commands[0]
    elif route_keys:
        default_safe_probe = f"inspect selector {route_keys[0]}"
    claim_boundary = _state_delta_claim_boundary(decision_packet)
    default_response_shape = response_shape or [
        "decision_or_finding",
        "evidence_or_proof_boundary",
        "residue_or_claim_boundary",
        "next_safe_action",
    ]
    default_avoid_repeat = avoid_repeat or [
        "chronological_tool_call_narration",
        "repeated_context_reconstruction",
    ]
    expand_when = list(contract.get("expand_when", [])) or [
        "stale_missing_or_failed_proof",
        "user_requests_detail",
    ]
    return {
        "kind": "agentic-workspace/state-delta-core/v1",
        "surface": surface,
        "status": "blocked" if blocked_actions else "evidence-seeking" if missing else "ready",
        "decision": {
            "question": str(decision_packet.get("phase_question", "") or "What decision is being made now?"),
            "next_action": decision_packet.get("next_action", ""),
            "safe_probe": safe_probe or default_safe_probe or "answer from the current decision packet",
            "response_shape": default_response_shape,
        },
        "evidence": {
            "known": known_evidence[:2],
            **({"missing": missing[:2]} if missing else {}),
            "route_ids": route_keys[:3],
        },
        "boundary": {
            "proof": claim_boundary,
            "claim": claim_boundary,
            "residue_owner": decision_packet.get("residue_owner", "none"),
        },
        "output_policy": {
            "speak_when": ["decision_changed", "proof_boundary_changed", "next_safe_action_changed"],
            "stay_compact_when": ["state_unchanged", "detail_route_available", "chronology_not_trust_relevant"],
            "expand_when": expand_when,
            "avoid": default_avoid_repeat,
            "preserve": ["proof_boundary", "residue_or_claim_boundary", "next_safe_action"],
        },
        "state_backed": True,
    }


def current_decision_payload(
    *,
    surface: str,
    decision_packet: dict[str, Any],
    evidence_basis: list[str] | None = None,
    missing_evidence: list[str] | None = None,
    safe_probe: str | None = None,
    response_shape: list[str] | None = None,
    avoid_repeat: list[str] | None = None,
    state_delta_core: dict[str, Any] | None = None,
) -> dict[str, Any]:
    core = (
        state_delta_core
        if isinstance(state_delta_core, dict)
        else state_delta_core_payload(
            surface=surface,
            decision_packet=decision_packet,
            evidence_basis=evidence_basis,
            missing_evidence=missing_evidence,
            safe_probe=safe_probe,
            response_shape=response_shape,
            avoid_repeat=avoid_repeat,
        )
    )
    decision = core.get("decision", {}) if isinstance(core.get("decision"), dict) else {}
    evidence = core.get("evidence", {}) if isinstance(core.get("evidence"), dict) else {}
    boundary = core.get("boundary", {}) if isinstance(core.get("boundary"), dict) else {}
    policy = core.get("output_policy", {}) if isinstance(core.get("output_policy"), dict) else {}
    missing = [str(item) for item in evidence.get("missing", []) if str(item).strip()]
    return {
        "kind": "agentic-workspace/current-decision/v1",
        "surface": surface,
        "status": core.get("status", "ready"),
        "decision_question": decision.get("question", "What decision is being made now?"),
        "known_evidence": list(evidence.get("known", []))[:1],
        **({"missing_evidence": missing[:2]} if missing else {}),
        "safe_probe": decision.get("safe_probe", "answer from the current decision packet"),
        "response_shape": list(decision.get("response_shape", [])),
        "avoid_repeat": list(policy.get("avoid", [])),
        "proof_boundary": boundary.get("proof", "not-evaluated"),
        "residue_owner": boundary.get("residue_owner", "none"),
        "next_action": decision.get("next_action", ""),
        "detail_route_ids": list(evidence.get("route_ids", []))[:3],
        "state_backed": True,
    }


def message_economy_payload(
    *,
    surface: str,
    communication_contract: dict[str, Any] | None = None,
    state_delta_core: dict[str, Any] | None = None,
) -> dict[str, Any]:
    core_policy = (
        state_delta_core.get("output_policy", {})
        if isinstance(state_delta_core, dict) and isinstance(state_delta_core.get("output_policy"), dict)
        else {}
    )
    if core_policy:
        speak_when = list(core_policy.get("speak_when", []))
        stay_compact_when = list(core_policy.get("stay_compact_when", []))
        expand_when = list(core_policy.get("expand_when", []))
        preserve = list(core_policy.get("preserve", []))
    else:
        contract = (
            communication_contract if isinstance(communication_contract, dict) else compact_communication_contract_payload(surface=surface)
        )
        speak_when = ["decision_changed", "proof_boundary_changed", "next_safe_action_changed"]
        stay_compact_when = ["state_unchanged", "detail_route_available", "chronology_not_trust_relevant"]
        expand_when = list(contract.get("expand_when", [])) or ["stale_missing_or_failed_proof", "user_requests_detail"]
        preserve = ["proof_boundary", "residue_or_claim_boundary", "next_safe_action"]
    return {
        "kind": "agentic-workspace/message-economy/v1",
        "surface": surface,
        "status": "active",
        "speak_when": speak_when,
        "stay_compact_when": stay_compact_when,
        "expand_when": expand_when,
        "discourage": ["low_value_tool_chronology", "repeated_state_recaps"],
        "preserve": preserve,
        "state_backed": True,
    }


def continuation_capsule_payload(
    *,
    surface: str,
    current_decision: dict[str, Any],
    message_economy: dict[str, Any] | None = None,
    preserved_intent: str | None = None,
    stale_context: list[str] | None = None,
    state_delta_core: dict[str, Any] | None = None,
) -> dict[str, Any]:
    core = state_delta_core if isinstance(state_delta_core, dict) else {}
    decision = core.get("decision", {}) if isinstance(core.get("decision"), dict) else {}
    evidence = core.get("evidence", {}) if isinstance(core.get("evidence"), dict) else {}
    boundary = core.get("boundary", {}) if isinstance(core.get("boundary"), dict) else {}
    policy = core.get("output_policy", {}) if isinstance(core.get("output_policy"), dict) else {}
    economy = message_economy if isinstance(message_economy, dict) else message_economy_payload(surface=surface, state_delta_core=core)
    proof_boundary = boundary.get("proof", current_decision.get("proof_boundary", "not-evaluated"))
    residue_owner = boundary.get("residue_owner", current_decision.get("residue_owner", "none"))
    known_evidence = list(evidence.get("known", current_decision.get("known_evidence", [])))[:2]
    next_action = decision.get("next_action", current_decision.get("next_action", ""))
    return {
        "kind": "agentic-workspace/continuation-capsule/v1",
        "surface": surface,
        "status": "available",
        "preserved_intent": preserved_intent or str(decision.get("question", current_decision.get("decision_question", ""))),
        "current_decision": {
            "question": decision.get("question", current_decision.get("decision_question", "")),
            "status": current_decision.get("status", "unknown"),
            "next_action": next_action,
        },
        "proof_boundary": proof_boundary,
        "known_evidence": known_evidence,
        "unresolved_residue": residue_owner,
        "next_safe_action": next_action,
        "do_not_repeat": stale_context or list(policy.get("avoid", [])),
        "expansion_triggers": list(policy.get("expand_when", economy.get("expand_when", [])))[:3],
        "state_backed": True,
    }


def evidence_bundle_payload(
    *, surface: str, current_decision: dict[str, Any], state_delta_core: dict[str, Any] | None = None
) -> dict[str, Any]:
    core = state_delta_core if isinstance(state_delta_core, dict) else {}
    decision = core.get("decision", {}) if isinstance(core.get("decision"), dict) else {}
    evidence = core.get("evidence", {}) if isinstance(core.get("evidence"), dict) else {}
    route_ids = evidence.get("route_ids", current_decision.get("detail_route_ids", []))
    minimal_surfaces = [{"id": str(item)} for item in route_ids if str(item).strip()][:6]
    missing_evidence = [str(item) for item in evidence.get("missing", current_decision.get("missing_evidence", [])) if str(item).strip()]
    return {
        "kind": "agentic-workspace/evidence-bundle/v1",
        "surface": surface,
        "status": "available" if minimal_surfaces or missing_evidence else "not-needed",
        "supports_decision": decision.get("question", current_decision.get("decision_question", "")),
        "minimal_evidence_surfaces": minimal_surfaces,
        **({"missing_evidence": missing_evidence[:2]} if missing_evidence else {}),
        "decision_changes_when": [
            {
                "outcome": "proof or safe probe passes",
                "decision_effect": "answer from the compact state delta",
            },
        ],
        "escalate_when": [
            "proof boundary is stale or missing for a hard claim",
            "residue owner is unresolved",
        ],
        "state_backed": True,
    }


def _load_reasoning_economy_evidence_ledger(*, target_root: Path | None) -> dict[str, Any]:
    if target_root is None:
        return {
            "status": "absent",
            "path": REASONING_ECONOMY_EVIDENCE_LEDGER_PATH,
            "entries": [],
            "rule": "Repo-specific evidence is optional and must be supplied by the target repository.",
        }
    ledger_path = target_root / REASONING_ECONOMY_EVIDENCE_LEDGER_PATH
    if not ledger_path.is_file():
        return {
            "status": "absent",
            "path": REASONING_ECONOMY_EVIDENCE_LEDGER_PATH,
            "entries": [],
            "rule": "Repo-specific evidence is optional and must be supplied by the target repository.",
        }
    try:
        payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "invalid",
            "path": REASONING_ECONOMY_EVIDENCE_LEDGER_PATH,
            "entries": [],
            "error": str(exc),
        }
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return {
            "status": "invalid",
            "path": REASONING_ECONOMY_EVIDENCE_LEDGER_PATH,
            "entries": [],
            "error": "entries must be a list",
        }
    normalized_entries = [
        {
            key: item[key]
            for key in (
                "ref",
                "evidence_class",
                "adjacent_support",
                "visible_artifact_signal",
                "source",
            )
            if isinstance(item, dict) and key in item
        }
        for item in entries
        if isinstance(item, dict)
    ]
    return {
        "status": "loaded",
        "path": REASONING_ECONOMY_EVIDENCE_LEDGER_PATH,
        "kind": payload.get("kind", "agentic-workspace/reasoning-economy-evidence-ledger/v1"),
        "entry_count": len(normalized_entries),
        "entries": normalized_entries,
        "owner": payload.get("owner", "target-repository"),
        "rule": "Repo-specific evidence is target-owned; package runtime only defines generic evidence classes and checks.",
    }


def reasoning_economy_evidence_payload(*, target_root: Path | None = None, cli_invoke: str = DEFAULT_CLI_INVOKE) -> dict[str, Any]:
    required_visible_fields = [
        "decision_or_finding",
        "proof_boundary",
        "residue_or_boundary",
        "next_action_or_closure_status",
    ]
    fixtures = [
        {
            "id": "visible-closeout-artifact",
            "artifact_surface": "closeout_report or PR closeout",
            "present_fields": required_visible_fields,
            "signals": ["omits_low_value_tool_chronology"],
            "expected_result": "pass",
        },
        {
            "id": "tool-chronology-without-claim-boundary",
            "artifact_surface": "PR body or final response",
            "present_fields": ["proof_boundary"],
            "signals": ["low_value_tool_chronology"],
            "expected_result": "flag",
        },
    ]
    checked_fixtures: list[dict[str, Any]] = []
    for fixture in fixtures:
        present = set(str(field) for field in fixture.get("present_fields", []))
        missing = [field for field in required_visible_fields if field not in present]
        low_value_chronology = "low_value_tool_chronology" in set(str(signal) for signal in fixture.get("signals", []))
        result = "pass" if not missing and not low_value_chronology else "flag"
        checked_fixtures.append(
            {
                **fixture,
                "result": result,
                "missing_required_visible_fields": missing,
                "negative_signal_detected": "low_value_tool_chronology" if low_value_chronology else "",
            }
        )
    evidence_ledger_source = _load_reasoning_economy_evidence_ledger(target_root=target_root)
    return {
        "kind": "agentic-workspace/reasoning-economy-evidence/v1",
        "status": "available",
        "scope": "visible_external_artifacts_only",
        "evidence_ledger_source": evidence_ledger_source,
        "non_goals": [
            "hidden chain-of-thought grading",
            "semantic scoring of private reasoning",
            "credit for shorter output without preserved proof and residue",
        ],
        "evidence_classes": {
            "direct": {
                "definition": (
                    "A visible PR, closeout, report, or review artifact changed behavior by leading with the decision or finding, "
                    "showing proof boundary, preserving residue, and naming next action or closure status."
                ),
                "positive_signals": [
                    "decision_or_finding_first",
                    "proof_boundary_visible",
                    "residue_or_boundary_visible",
                    "next_action_or_closure_status_visible",
                    "low_value_tool_chronology_omitted",
                ],
            },
            "adjacent": {
                "definition": (
                    "A routing, proof, fixture, or compact-state change supports reasoning economy but does not by itself prove "
                    "visible artifact behavior improved."
                ),
                "positive_signals": ["selector_or_fixture_added", "proof_route_preserved", "report_section_discoverable"],
            },
            "none": {
                "definition": (
                    "Passing tests, internal routing, raw command chronology, or hidden reasoning claims alone are not reasoning-economy evidence."
                ),
                "negative_signals": ["tests_only", "tool_chronology_only", "private_reasoning_claim", "brevity_without_boundary"],
            },
        },
        "evidence_ledger": evidence_ledger_source.get("entries", []),
        "behavior_check": {
            "kind": "agentic-workspace/visible-artifact-behavior-check/v1",
            "applies_to": ["PR body", "review closeout", "report section", "closeout_report", "handoff summary"],
            "required_visible_fields": required_visible_fields,
            "flag_when": [
                "low_value_tool_chronology appears without a decision-changing purpose",
                "proof is collapsed into generic success language",
                "residue or closure status is missing",
                "the artifact claims reasoning quality from hidden reasoning or brevity alone",
            ],
            "expand_when": [
                "stale_missing_or_failed_proof",
                "ambiguous_action_safety",
                "unresolved_residue_changes_next_owner",
                "user_requests_detail",
            ],
        },
        "fixture_results": checked_fixtures,
        "query": _command_with_cli_invoke(
            "agentic-workspace report --target ./repo --section reasoning_economy --format json",
            cli_invoke=cli_invoke,
        ),
    }


def output_contract_payload(
    *,
    optimization_bias: str,
    optimization_bias_source: str,
    bias_payload: dict[str, Any],
    surface: str,
) -> dict[str, Any]:
    budget_by_density = {
        "compact": {
            "default_detail": "router-only",
            "section_hint_limit": 8,
            "deep_detail": "selectors-required",
        },
        "balanced": {
            "default_detail": "router-with-brief-context",
            "section_hint_limit": 12,
            "deep_detail": "selectors-preferred",
        },
        "explanatory": {
            "default_detail": "router-with-extra-labels",
            "section_hint_limit": 16,
            "deep_detail": "selectors-still-required-for-high-volume-sections",
        },
    }
    verbosity_budget = budget_by_density.get(str(bias_payload["report_density"]), budget_by_density["balanced"])
    return {
        "owner_surface": "workspace",
        "surface": surface,
        "optimization_bias": optimization_bias,
        "optimization_bias_source": optimization_bias_source,
        "rule": (
            "Optimization bias may change rendering density and residue style only; "
            "it must not change execution method or canonical state semantics."
        ),
        "applies_to": [
            "derived reporting density",
            "rendered human-facing view density",
            "durable residue style when truth stays unchanged",
        ],
        "surface_boundary": bias_payload["surface_boundary"],
        "report_density": bias_payload["report_density"],
        "verbosity_budget": verbosity_budget,
        "communication_contract": communication_contract_payload(surface=surface),
        "residue_density": bias_payload["residue_density"],
        "rendered_view_style": bias_payload["rendered_view_style"],
        "must_not_change": list(bias_payload["does_not_affect"]),
    }


def _target_arg_from_payload(payload: dict[str, Any]) -> str:
    target = str(payload.get("target") or ".")
    if target == ".":
        return "."
    try:
        relative = os.path.relpath(Path(target).resolve(), Path.cwd().resolve())
    except OSError:
        relative = target
    if relative == ".":
        return "."
    return Path(relative).as_posix()


def _command_with_cli_invoke(command: str, *, cli_invoke: str, target_arg: str = "./repo") -> str:
    command = command.replace("--target ./repo", f"--target {target_arg}")
    if cli_invoke == DEFAULT_CLI_INVOKE or not command.startswith(DEFAULT_CLI_INVOKE):
        return command
    return f"{cli_invoke}{command.removeprefix(DEFAULT_CLI_INVOKE)}"


def _is_command_field(key: str) -> bool:
    return (
        key
        in {
            "after_write",
            "detail",
            "first_command",
            "inspect",
            "next_command",
            "one_compact_check",
            "ordinary_entry",
            "preferred_mutation_command_template",
            "query",
            "recover_by",
            "recover_by_default",
            "reference_command",
            "required_next_inspection",
            "run",
            "selection_path",
            "selector",
        }
        or key == "command"
        or key.endswith("_command")
    )


def _localize_command_fields(value: Any, *, cli_invoke: str, target_arg: str = "./repo") -> Any:
    if isinstance(value, dict):
        localized: dict[str, Any] = {}
        for key, nested in value.items():
            if isinstance(nested, str) and _is_command_field(key):
                localized[key] = _command_with_cli_invoke(nested, cli_invoke=cli_invoke, target_arg=target_arg)
            elif key in {"commands", "consult"} and isinstance(nested, list):
                localized[key] = [
                    _command_with_cli_invoke(item, cli_invoke=cli_invoke, target_arg=target_arg)
                    if isinstance(item, str)
                    else _localize_command_fields(item, cli_invoke=cli_invoke, target_arg=target_arg)
                    for item in nested
                ]
            else:
                localized[key] = _localize_command_fields(nested, cli_invoke=cli_invoke, target_arg=target_arg)
        return localized
    if isinstance(value, list):
        return [_localize_command_fields(item, cli_invoke=cli_invoke, target_arg=target_arg) for item in value]
    return value


def report_profile_payload(*, context_router: dict[str, Any], cli_invoke: str = DEFAULT_CLI_INVOKE) -> dict[str, Any]:
    return {
        "default_profile": "router",
        "full_profile": "full",
        "context_router": context_router,
        "section_selector": "--section <top-level-field>",
        "default_command": _command_with_cli_invoke("agentic-workspace report --target ./repo --format json", cli_invoke=cli_invoke),
        "full_profile_command": _command_with_cli_invoke(
            "agentic-workspace report --target ./repo --verbose --format json", cli_invoke=cli_invoke
        ),
        "full_profile_cost": {
            "classification": "deep-audit",
            "expected_cost": "high",
            "use_when": "only when router fields or a selected section are insufficient for audit, retention, or cross-module diagnosis",
            "avoid_for": "ordinary startup, first-contact orientation, and narrow implementation routing",
        },
        "section_command": _command_with_cli_invoke(
            "agentic-workspace report --target ./repo --section <section> --format json", cli_invoke=cli_invoke
        ),
        "rule": (
            "Default report output should route to decision-grade current state before exposing high-volume "
            "module detail. Use --verbose or --section when deeper data is needed."
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
            "routine_work_context",
            "durable_intent",
            "memory_consult",
            "improvement_intake",
            "external_work_reconciliation",
            "successful_completion_cost",
            "maintenance_pressure",
            "reuse_pressure",
            "closeout_report",
        ],
        "router_shape_guard": {
            "status": "active",
            "max_top_level_fields": 22,
            "high_volume_sections_excluded": ["module_reports", "reports", "registry", "config"],
            "warning_sample_limit": 5,
            "rule": "Default router output should summarize health, current work, next action, warnings, and selectors before raw high-volume detail.",
        },
    }


def select_report_payload(
    payload: dict[str, Any],
    *,
    profile: str,
    section: str | None,
    compact_answer: Callable[..., dict[str, Any]],
    context_router: dict[str, Any],
    cli_invoke: str = DEFAULT_CLI_INVOKE,
) -> dict[str, Any]:
    target_arg = _target_arg_from_payload(payload)
    if section:
        if profile != "router":
            raise WorkspaceUsageError("report detail selectors are mutually exclusive; use either --verbose or --section.")
        resolved_section, answer = _resolve_report_section(payload, section)
        if answer is None:
            raise WorkspaceUsageError(_unknown_report_section_message(section, payload))
        selector = {"section": section}
        if resolved_section != section:
            selector["resolved_section"] = resolved_section
        answer = _compact_report_section_answer(resolved_section, answer, cli_invoke=cli_invoke, target_arg=target_arg)
        return compact_answer(
            surface="report",
            selector=selector,
            answer=answer,
            refs=[
                ".agentic-workspace/docs/reporting-contract.md",
                _command_with_cli_invoke(
                    "agentic-workspace report --target ./repo --verbose --format json",
                    cli_invoke=cli_invoke,
                    target_arg=target_arg,
                ),
            ],
        )
    if profile == "full":
        return payload
    if profile == "router":
        return report_router_payload(payload, context_router=context_router, cli_invoke=cli_invoke)
    raise WorkspaceUsageError("report detail mode must be either router or full")


def _resolve_report_section(payload: dict[str, Any], section: str) -> tuple[str, Any | None]:
    if section in payload:
        return section, payload[section]
    alias = REPORT_SECTION_ALIASES.get(section)
    if alias == "current_work":
        effective_authority = payload.get("effective_authority", {})
        if isinstance(effective_authority, dict):
            current_work = effective_authority.get("current_work")
            if current_work is not None:
                return "effective_authority.current_work", current_work
        return "effective_authority.current_work", {}
    if alias and alias in payload:
        return alias, payload[alias]
    return section, None


def closeout_claim_boundary_payload(
    closeout_trust: dict[str, Any], *, cli_invoke: str = DEFAULT_CLI_INVOKE, target_arg: str = "./repo"
) -> dict[str, Any]:
    if not isinstance(closeout_trust, dict):
        closeout_trust = {}

    def compact(value: Any, keys: tuple[str, ...]) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {key: value.get(key) for key in keys if key in value}

    completion_gate = closeout_trust.get("completion_gate", {})
    completion_gate = completion_gate if isinstance(completion_gate, dict) else {}
    claim_authorization = completion_gate.get("claim_authorization", {})
    claim_authorization = claim_authorization if isinstance(claim_authorization, dict) else {}
    strict_gate = closeout_trust.get("strict_closeout_gate", {})
    strict_gate = strict_gate if isinstance(strict_gate, dict) else {}
    terminal_action = closeout_trust.get("terminal_action", {})
    terminal_action = terminal_action if isinstance(terminal_action, dict) else {}
    closeout_protocol = closeout_trust.get("closeout_protocol", {})
    closeout_protocol = closeout_protocol if isinstance(closeout_protocol, dict) else {}
    readiness = closeout_protocol.get("readiness", {})
    readiness = readiness if isinstance(readiness, dict) else {}
    residue_routing = closeout_protocol.get("residue_routing", {})
    residue_routing = residue_routing if isinstance(residue_routing, dict) else {}
    closure_permission = closeout_protocol.get("closure_permission", {})
    closure_permission = closure_permission if isinstance(closure_permission, dict) else {}
    proof_dependency = closeout_protocol.get("proof_dependency", {})
    proof_dependency = proof_dependency if isinstance(proof_dependency, dict) else {}
    proof_dependency_status = "unknown"
    if proof_dependency.get("run_proof_allowed") is True:
        proof_dependency_status = "proof-required"
    elif proof_dependency.get("run_proof_allowed") is False:
        proof_dependency_status = "satisfied"

    blocking_fields: list[str] = []
    for option in _support_list_payload(closeout_trust.get("completion_options")):
        if not isinstance(option, dict) or option.get("allowed") is True:
            continue
        for field in _support_list_payload(option.get("blocking_fields")):
            field_text = str(field)
            if field_text and field_text not in blocking_fields:
                blocking_fields.append(field_text)

    next_action = (
        terminal_action.get("recommended_next_action")
        or completion_gate.get("required_next_action")
        or strict_gate.get("recommended_next_action")
        or closeout_protocol.get("status")
        or ""
    )
    detail_command = _command_with_cli_invoke(
        "agentic-workspace report --target ./repo --section closeout_trust --format json",
        cli_invoke=cli_invoke,
        target_arg=target_arg,
    )

    return _localize_command_fields(
        {
            "kind": "agentic-workspace/closeout-claim-boundary/v1",
            "status": completion_gate.get("status", closeout_trust.get("status", "unavailable")),
            "trust": closeout_trust.get("trust", ""),
            "active_intent_satisfied": completion_gate.get("active_intent_satisfied", False),
            "claim_level_allowed": completion_gate.get("claim_level_allowed", "none"),
            "claim_authorization": {
                key: claim_authorization.get(key)
                for key in (
                    "allowed_claim_classes",
                    "blocked_claim_classes",
                    "closure_actions",
                    "rule",
                )
                if key in claim_authorization
            },
            "blocking_fields": blocking_fields,
            "strict_closeout": compact(strict_gate, ("status", "blocking", "required_for_broad_work", "recommended_next_action")),
            "readiness": compact(readiness, ("status", "can_close", "blocking_fields", "warning_fields", "rule")),
            "residue_routing": compact(
                residue_routing,
                (
                    "required",
                    "durable_residue_required",
                    "safe_destination",
                    "destination",
                    "owner",
                    "next_action",
                    "rule",
                ),
            ),
            "proof_dependency": {
                "status": proof_dependency_status,
                **compact(
                    proof_dependency,
                    (
                        "run_proof_allowed",
                        "proof_confidence",
                        "verification_status",
                        "verification_active_count",
                        "required",
                        "proof_status",
                        "command",
                        "rule",
                    ),
                ),
            },
            "closure_permission": compact(
                closure_permission,
                (
                    "status",
                    "allowed",
                    "claim_work_complete_allowed",
                    "keep_parent_open_allowed",
                    "blocked_reason",
                    "rule",
                ),
            ),
            "next_action": next_action,
            "source_detail_command": detail_command,
            "detail_selector": "closeout_trust",
            "rule": "Derived from closeout_trust; use this selector for the compact claim boundary and closeout_trust for full proof and residue detail.",
        },
        cli_invoke=cli_invoke,
        target_arg=target_arg,
    )


def issue_1969_acceptance_evidence_matrix_payload(
    *,
    target_root: Path | None,
    closeout_claim_boundary: dict[str, Any] | None = None,
    cli_invoke: str = DEFAULT_CLI_INVOKE,
) -> dict[str, Any]:
    root = target_root or Path(".")
    lane_path = root / ".agentic-workspace" / "planning" / "lanes" / "issue-1969-state-delta-loop.lane.json"
    execplan_path = root / ".agentic-workspace" / "planning" / "execplans" / "issue-1969-lane-stack.plan.json"

    def read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return value if isinstance(value, dict) else {}

    lane_record = read_json(lane_path)
    execplan_record = read_json(execplan_path)
    closeout_claim_boundary = closeout_claim_boundary if isinstance(closeout_claim_boundary, dict) else {}
    source_refs = [
        ref
        for ref, present in (
            (".agentic-workspace/planning/lanes/issue-1969-state-delta-loop.lane.json", bool(lane_record)),
            (".agentic-workspace/planning/execplans/issue-1969-lane-stack.plan.json", bool(execplan_record)),
            ("https://github.com/rickardvh/agentic-workspace/issues/1969", True),
        )
        if present
    ]

    def row(
        row_id: str,
        criterion: str,
        state: str,
        evidence_refs: list[str],
        *,
        missing_evidence: list[str] | None = None,
        follow_up_owner: str = "none-known",
        current_proof_boundary: str = "historical evidence only; current HEAD still requires selected proof and closeout gates",
    ) -> dict[str, Any]:
        return {
            "id": row_id,
            "criterion": criterion,
            "state": state,
            "evidence_refs": evidence_refs,
            "missing_evidence": missing_evidence or [],
            "follow_up_owner": follow_up_owner,
            "current_proof_boundary": current_proof_boundary,
        }

    rows = [
        row(
            "state_delta_model",
            "Define a compact state-delta-first message model for the AW operating loop.",
            "satisfied",
            [
                ".agentic-workspace/planning/lanes/issue-1969-state-delta-loop.lane.json",
                ".agentic-workspace/planning/execplans/issue-1969-lane-stack.plan.json",
                "#1976",
                "#1977",
                "#1978",
                "#1979",
                "#1980",
            ],
        ),
        row(
            "ordinary_workflow_decision_packet",
            "Expose current decision, known evidence, missing evidence, safe probe, and response shape before visible output.",
            "satisfied",
            ["#1976", "#1979", ".agentic-workspace/planning/execplans/issue-1969-lane-stack.plan.json"],
        ),
        row(
            "continuation_recheck_without_recap",
            "Resume or re-review from compact state without a prose recap of the whole history.",
            "satisfied",
            ["#1978", "#1987", "#2004", "#2005", "#2006", "#2007", "#2008", "#2009", "#2010"],
        ),
        row(
            "proof_residue_next_action_closure",
            "Preserve proof boundary, residue, next action, and honest closure in state-delta closeout.",
            "stale",
            ["#1981", "#1982", "#2021", "#2023", "#2024", "#2025"],
            missing_evidence=[
                "current closeout authorization must be checked separately through closeout_claim_boundary or closeout_trust"
            ],
            follow_up_owner="#2030",
            current_proof_boundary="matrix evidence is not closeout authorization; use closeout gates for current closure claims",
        ),
        row(
            "narration_reduction",
            "Show reduced process narration or repeated context while preserving proof, residue, and next action.",
            "needs-human-judgment",
            [
                "https://github.com/rickardvh/agentic-workspace/issues/1969#issuecomment-4896594752",
                "https://github.com/rickardvh/agentic-workspace/issues/1969#issuecomment-4899165831",
            ],
            missing_evidence=["fixture-backed or dogfooded before/after narration comparison"],
            follow_up_owner="#2028",
        ),
        row(
            "expansion_triggers",
            "Make expansion triggers explicit and preserve proof, safety, uncertainty, and residue detail when needed.",
            "satisfied",
            ["#1977", "#1979", "#1980", "src/agentic_workspace/reporting_support.py"],
        ),
        row(
            "structured_state_not_prompt_keywords",
            "Use structured state rather than prompt-prose classifiers or broad always-on dumps.",
            "satisfied",
            [
                "#1976",
                "#1977",
                "#1978",
                "#1979",
                "#1980",
                "#1983",
                "#2004",
                "#2024",
                "#2025",
            ],
        ),
        row(
            "omission_proof",
            "Show why compact operating-loop outputs can omit hidden detail without losing needed state.",
            "missing",
            [],
            missing_evidence=["omission proof packet or fixture evidence for selector-hidden context"],
            follow_up_owner="#2029",
        ),
    ]
    counts = {
        state: sum(1 for item in rows if item["state"] == state) for state in ("satisfied", "missing", "stale", "needs-human-judgment")
    }
    closeout_status = {
        "status": closeout_claim_boundary.get("status", "unavailable"),
        "trust": closeout_claim_boundary.get("trust", ""),
        "claim_level_allowed": closeout_claim_boundary.get("claim_level_allowed", ""),
        "closure_permission": closeout_claim_boundary.get("closure_permission", {}),
        "detail_selector": closeout_claim_boundary.get("detail_selector", "closeout_trust"),
    }
    matrix_authorizes_closure = False
    return _localize_command_fields(
        {
            "kind": "agentic-workspace/issue-1969-acceptance-evidence-matrix/v1",
            "status": "available",
            "parent_issue": "#1969",
            "criterion_count": len(rows),
            "state_counts": counts,
            "source_refs": source_refs,
            "rows": rows,
            "closeout_gate_boundary": {
                "matrix_authorizes_closure": matrix_authorizes_closure,
                "rule": "This matrix maps evidence; it does not authorize #1969 closure without current proof and closeout gates.",
                "current_closeout_claim_boundary": closeout_status,
                "claim_boundary_selector": _command_with_cli_invoke(
                    "agentic-workspace report --target ./repo --section closeout_claim_boundary --format json",
                    cli_invoke=cli_invoke,
                ),
            },
            "update_model": {
                "historical_refs_are_inputs": True,
                "current_proof_required": True,
                "smallest_follow_up_owner_field": "rows[].follow_up_owner",
                "rule": "Update row states from durable issue, PR, packet, test, doc, or comment refs; do not infer closure from raw merged count.",
            },
            "dogfooding_boundary": {
                "without_manual_reread": bool(lane_record or execplan_record),
                "evidence_source": "checked-in #1969 lane/execplan plus stable issue and PR refs",
            },
        },
        cli_invoke=cli_invoke,
    )


def _compact_report_section_answer(section: str, answer: Any, *, cli_invoke: str, target_arg: str = "./repo") -> Any:
    if section == "reasoning_economy" and isinstance(answer, dict):
        behavior = answer.get("behavior_check", {})
        behavior = behavior if isinstance(behavior, dict) else {}
        return _localize_command_fields(
            {
                "kind": answer.get("kind", "agentic-workspace/reasoning-economy-evidence/v1"),
                "status": answer.get("status", "available"),
                "scope": answer.get("scope", "visible_external_artifacts_only"),
                "evidence_class_ids": list((answer.get("evidence_classes", {}) or {}).keys())
                if isinstance(answer.get("evidence_classes"), dict)
                else [],
                "required_visible_fields": behavior.get("required_visible_fields", []),
                "ledger_refs": [
                    item.get("ref", "") for item in _support_list_payload(answer.get("evidence_ledger")) if isinstance(item, dict)
                ],
                "fixture_results": [
                    {
                        key: item.get(key)
                        for key in (
                            "id",
                            "result",
                            "expected_result",
                            "missing_required_visible_fields",
                            "negative_signal_detected",
                        )
                        if isinstance(item, dict) and key in item
                    }
                    for item in _support_list_payload(answer.get("fixture_results"))
                ],
                "non_goals": answer.get("non_goals", []),
                "detail_command": _command_with_cli_invoke(
                    "agentic-workspace report --target ./repo --verbose --format json",
                    cli_invoke=cli_invoke,
                    target_arg=target_arg,
                ),
                "detail_selector": "reasoning_economy",
            },
            cli_invoke=cli_invoke,
            target_arg=target_arg,
        )
    if section == "improvement_intake" and isinstance(answer, dict):
        candidates = [
            {
                key: item[key]
                for key in (
                    "kind",
                    "candidate_kind",
                    "source",
                    "summary",
                    "recommended_destination",
                    "recommended_action",
                    "routing_decision",
                )
                if isinstance(item, dict) and key in item
            }
            for item in _support_list_payload(answer.get("improvement_signal_candidates"))[:5]
        ]
        repo_existing = answer.get("repo_wide_existing_candidates", {})
        repo_existing = repo_existing if isinstance(repo_existing, dict) else {}
        setup_findings = answer.get("setup_findings", {})
        setup_findings = setup_findings if isinstance(setup_findings, dict) else {}
        intake_scope = answer.get("intake_scope", {})
        intake_scope = intake_scope if isinstance(intake_scope, dict) else {}
        return _localize_command_fields(
            {
                "kind": answer.get("kind", "workspace-improvement-intake/v1"),
                "status": answer.get("status", "available"),
                "role": answer.get("role", "router-not-backlog"),
                "intake_scope": {
                    key: intake_scope.get(key) for key in ("status", "session_section", "repo_wide_section", "rule") if key in intake_scope
                },
                "audience_boundary": answer.get("audience_boundary", {}),
                "candidate_count": answer.get("candidate_count", len(candidates)),
                "candidate_sample": candidates,
                "repo_wide_existing_candidates": {
                    key: repo_existing.get(key)
                    for key in ("status", "included_by_default", "candidate_count", "command", "full_scan_command")
                    if key in repo_existing
                },
                "setup_findings": {
                    key: setup_findings.get(key)
                    for key in ("status", "candidate_count", "promotable_count", "dismissed_count", "command")
                    if key in setup_findings
                },
                "detail_command": _command_with_cli_invoke(
                    "agentic-workspace report --target ./repo --verbose --format json",
                    cli_invoke=cli_invoke,
                    target_arg=target_arg,
                ),
                "detail_selector": "improvement_intake",
                "rule": "Selected dogfooding report sections return compact routing evidence by default; use --verbose for full payload detail.",
            },
            cli_invoke=cli_invoke,
            target_arg=target_arg,
        )
    if section == "repo_friction" and isinstance(answer, dict):

        def compact_collection(value: Any) -> dict[str, Any]:
            if not isinstance(value, dict):
                return {"status": "unavailable", "count": 0, "sample": []}
            items = [
                {
                    key: item[key]
                    for key in (
                        "kind",
                        "path",
                        "relative_path",
                        "line_count",
                        "summary",
                        "surface_role",
                        "recommended_action",
                        "route",
                    )
                    if isinstance(item, dict) and key in item
                }
                for item in _support_list_payload(value.get("items"))[:3]
            ]
            return {
                "status": value.get("status", "available"),
                "count": value.get("count", value.get("item_count", len(items))),
                "sample": items,
            }

        policy = answer.get("policy", {})
        policy = policy if isinstance(policy, dict) else {}
        return _localize_command_fields(
            {
                "kind": answer.get("kind", "workspace-repo-friction/v1"),
                "status": answer.get("status", "available"),
                "summary": answer.get("summary", ""),
                "policy": {
                    key: policy.get(key) for key in ("status", "mode", "max_candidate_count", "candidate_limit", "rule") if key in policy
                },
                "large_file_hotspots": compact_collection(answer.get("large_file_hotspots")),
                "concept_surface_hotspots": compact_collection(answer.get("concept_surface_hotspots")),
                "regenerable_cache_hotspots": compact_collection(answer.get("regenerable_cache_hotspots")),
                "external_evidence_count": len(_support_list_payload(answer.get("external_evidence"))),
                "capture_shortcut": answer.get("capture_shortcut", {}),
                "detail_command": _command_with_cli_invoke(
                    "agentic-workspace report --target ./repo --verbose --format json",
                    cli_invoke=cli_invoke,
                    target_arg=target_arg,
                ),
                "detail_selector": "repo_friction",
                "rule": "Selected dogfooding report sections return compact routing evidence by default; use --verbose for full payload detail.",
            },
            cli_invoke=cli_invoke,
            target_arg=target_arg,
        )
    if section == "local_footprint" and isinstance(answer, dict):
        scratch = answer.get("scratch_retention", {})
        scratch = scratch if isinstance(scratch, dict) else {}
        policy = answer.get("policy", {})
        policy = policy if isinstance(policy, dict) else {}

        def compact_scratch_entry(value: Any) -> dict[str, Any]:
            if not isinstance(value, dict):
                return {}
            return {
                key: value.get(key)
                for key in (
                    "path",
                    "classification",
                    "retention",
                    "bytes",
                    "display_size",
                    "file_count",
                    "age_hours",
                    "eligible_for_auto_prune",
                    "reason",
                    "protect_until",
                )
                if key in value
            }

        return _localize_command_fields(
            {
                "kind": answer.get("kind", "agentic-workspace/local-footprint/v1"),
                "status": answer.get("status", "available"),
                "root": answer.get("root", ".agentic-workspace"),
                "tracked": answer.get("tracked", {}),
                "ignored": answer.get("ignored", {}),
                "budget_status": _support_list_payload(answer.get("budget_status"))[:5],
                "scratch_retention": {
                    "root": scratch.get("root", ".agentic-workspace/local/scratch"),
                    "runs_root": scratch.get("runs_root", ".agentic-workspace/local/scratch/runs"),
                    "managed_run_count": scratch.get("managed_run_count", 0),
                    "legacy_entry_count": scratch.get("legacy_entry_count", 0),
                    "legacy_entry_omitted_count": scratch.get("legacy_entry_omitted_count", 0),
                    "eligible_prune_count": scratch.get("eligible_prune_count", 0),
                    "eligible_prune_paths": _support_list_payload(scratch.get("eligible_prune_paths"))[:5],
                    "legacy_entries": [compact_scratch_entry(item) for item in _support_list_payload(scratch.get("legacy_entries"))[:3]],
                    "managed_runs": [compact_scratch_entry(item) for item in _support_list_payload(scratch.get("managed_runs"))[:3]],
                },
                "largest_local_offenders": _support_list_payload(answer.get("largest_local_offenders"))[:5],
                "policy": {
                    key: policy.get(key)
                    for key in (
                        "source",
                        "max_age_hours",
                        "protected_max_age_hours",
                        "max_total_bytes",
                        "warn_total_bytes",
                        "large_file_bytes",
                        "local_aw_warn_bytes",
                        "tracked_aw_warn_bytes",
                    )
                    if key in policy
                },
                "next_action": answer.get("next_action", {}),
                "scope_boundary": answer.get("scope_boundary", ""),
                "detail_command": _command_with_cli_invoke(
                    "agentic-workspace report --target ./repo --section local_footprint --verbose --format json",
                    cli_invoke=cli_invoke,
                    target_arg=target_arg,
                ),
                "rule": "Selected local footprint reports stay compact; use --verbose for subtree and full offender detail.",
            },
            cli_invoke=cli_invoke,
            target_arg=target_arg,
        )
    if section == "closeout_trust" and isinstance(answer, dict):

        def compact_closeout_check(value: dict[str, Any]) -> dict[str, Any]:
            status = str(value.get("status", ""))
            reason = str(value.get("reason", ""))
            if status == "unavailable" and "no active planning record" in reason:
                return {"status": "not-applicable", "reason": "no active planning record"}
            compact = {
                key: value.get(key) for key in ("status", "trust", "required_for_broad_work", "recommended_next_action") if key in value
            }
            if "continuation_surface" in value:
                compact["continuation_surface"] = value.get("continuation_surface")
            completion_boundary = value.get("completion_boundary", {})
            if isinstance(completion_boundary, dict):
                compact["completion_boundary"] = {
                    key: completion_boundary.get(key)
                    for key in (
                        "status",
                        "final_satisfaction",
                        "bounded_slice_success",
                        "partial_pr_may_close",
                        "required_follow_up_owner",
                        "required_residual_intent",
                        "evidence_required_for_final_completion",
                        "closure_rule",
                        "default_rule",
                    )
                    if key in completion_boundary
                }
            package_continuation = value.get("package_owned_continuation", {})
            if isinstance(package_continuation, dict):
                compact["package_owned_continuation"] = {
                    key: package_continuation.get(key)
                    for key in (
                        "status",
                        "surface_count",
                        "owner_surfaces",
                        "pending_pr_merge_count",
                        "pending_pr_merge_surfaces",
                        "rule",
                    )
                    if key in package_continuation
                }
            return compact

        def compact_current_task_closeout(value: dict[str, Any]) -> dict[str, Any]:
            if value.get("status") != "active":
                return {"status": value.get("status", "not-applicable")}
            scope = value.get("scope", {})
            scope = scope if isinstance(scope, dict) else {}
            planning_gate = scope.get("planning_safety_gate", {})
            planning_gate = planning_gate if isinstance(planning_gate, dict) else {}
            task_switch = scope.get("task_switch_reconciliation", {})
            task_switch = task_switch if isinstance(task_switch, dict) else {}
            proof = value.get("proof", {})
            proof = proof if isinstance(proof, dict) else {}
            proof_commands = _support_list_payload(proof.get("required_commands"))
            changed_paths = _support_list_payload(scope.get("changed_paths"))
            repo_wide = value.get("repo_wide_residue", {})
            repo_wide = repo_wide if isinstance(repo_wide, dict) else {}
            repo_wide_gate = repo_wide.get("strict_closeout_gate", {})
            repo_wide_gate = repo_wide_gate if isinstance(repo_wide_gate, dict) else {}
            repo_wide_completion_gate = repo_wide.get("completion_gate", {})
            repo_wide_completion_gate = repo_wide_completion_gate if isinstance(repo_wide_completion_gate, dict) else {}
            return {
                "kind": value.get("kind", "agentic-workspace/current-task-closeout/v1"),
                "status": "active",
                "scope": {
                    "status": scope.get("status", ""),
                    "relationship": scope.get("relationship", ""),
                    "changed_path_count": len(changed_paths),
                    "changed_paths": changed_paths[:12],
                    "changed_paths_omitted_count": max(0, len(changed_paths) - 12),
                    "planning_safety_gate": {
                        key: planning_gate.get(key)
                        for key in (
                            "kind",
                            "label",
                            "provenance",
                            "status",
                            "gate_result",
                            "workflow_sufficient",
                            "reason",
                            "required_next_action",
                            "active_planning_present",
                            "issue_refs",
                            "implementation_allowed",
                            "task_switch_reconciliation",
                        )
                        if key in planning_gate
                    },
                    "task_switch_reconciliation": {
                        key: task_switch.get(key)
                        for key in (
                            "kind",
                            "status",
                            "summary",
                            "current_task_class",
                            "recommended_next_action",
                            "safe_route_ids",
                            "blocked_claims",
                            "detail_selector",
                            "rule",
                        )
                        if key in task_switch
                    },
                    "rule": scope.get("rule", ""),
                },
                "strict_closeout_gate": value.get("strict_closeout_gate", {}),
                "completion_options": value.get("completion_options", []),
                "operating_loop": value.get("operating_loop", {}),
                "proof": {
                    "status": proof.get("status", ""),
                    "changed_path_count": len(_support_list_payload(proof.get("changed_paths"))),
                    "required_commands": proof_commands,
                    "required_command_count": len(proof_commands),
                    "proof_strategy": proof.get("proof_strategy", {}),
                    "detail_omitted": "full proof packet is available with report --section closeout_trust --verbose",
                },
                "repo_wide_residue": {
                    "strict_closeout_gate": repo_wide_gate,
                    "completion_gate": {
                        key: repo_wide_completion_gate.get(key)
                        for key in (
                            "kind",
                            "status",
                            "active_intent_satisfied",
                            "claim_level_allowed",
                            "required_next_action",
                            "claim_authorization",
                        )
                        if key in repo_wide_completion_gate
                    },
                    "trust": repo_wide.get("trust", ""),
                    "lower_trust_closeout_count": repo_wide.get("lower_trust_closeout_count", 0),
                },
                "rule": value.get("rule", ""),
            }

        historical_reviews = answer.get("historical_review_artifacts", {})
        historical_reviews = historical_reviews if isinstance(historical_reviews, dict) else {}
        retention_policy = historical_reviews.get("retention_policy", {})
        retention_policy = retention_policy if isinstance(retention_policy, dict) else {}
        package_evidence = answer.get("package_workflow_evidence", {})
        package_evidence = package_evidence if isinstance(package_evidence, dict) else {}
        intent_check = answer.get("intent_satisfaction_check", {})
        intent_check = intent_check if isinstance(intent_check, dict) else {}
        intent_proof_check = answer.get("intent_proof_check", {})
        intent_proof_check = intent_proof_check if isinstance(intent_proof_check, dict) else {}
        proof_confidence = answer.get("proof_confidence", {})
        proof_confidence = proof_confidence if isinstance(proof_confidence, dict) else {}
        assurance_requirements = answer.get("assurance_requirements", {})
        assurance_requirements = assurance_requirements if isinstance(assurance_requirements, dict) else {}
        verification = answer.get("verification", {})
        verification = verification if isinstance(verification, dict) else {}
        knowledge_authority_review = answer.get("knowledge_authority_review", {})
        knowledge_authority_review = knowledge_authority_review if isinstance(knowledge_authority_review, dict) else {}
        architecture_decision = answer.get("architecture_decision_closeout", {})
        architecture_decision = architecture_decision if isinstance(architecture_decision, dict) else {}
        architecture_candidate = architecture_decision.get("architecture_decision_candidate", {})
        architecture_candidate = architecture_candidate if isinstance(architecture_candidate, dict) else {}
        terminal_action = answer.get("terminal_action", {})
        terminal_action = terminal_action if isinstance(terminal_action, dict) else {}
        archived_slice = answer.get("archived_slice_closeout_evidence", {})
        archived_slice = archived_slice if isinstance(archived_slice, dict) else {}
        durable_action = answer.get("durable_residue_action", {})
        durable_action = durable_action if isinstance(durable_action, dict) else {}
        completion_options = answer.get("completion_options", [])
        completion_options = completion_options if isinstance(completion_options, list) else []
        closeout_protocol = answer.get("closeout_protocol", {})
        closeout_protocol = closeout_protocol if isinstance(closeout_protocol, dict) else {}
        strict_gate = answer.get("strict_closeout_gate", {})
        strict_gate = strict_gate if isinstance(strict_gate, dict) else {}
        completion_gate = answer.get("completion_gate", {})
        completion_gate = completion_gate if isinstance(completion_gate, dict) else {}
        memory_decision_packet = answer.get("memory_decision_packet", {})
        memory_decision_packet = memory_decision_packet if isinstance(memory_decision_packet, dict) else {}
        operating_loop = answer.get("operating_loop", {})
        operating_loop = operating_loop if isinstance(operating_loop, dict) else {}
        current_task_closeout = answer.get("current_task_closeout", {})
        current_task_closeout = current_task_closeout if isinstance(current_task_closeout, dict) else {}
        detail_command = _command_with_cli_invoke(
            "agentic-workspace report --target ./repo --verbose --format json",
            cli_invoke=cli_invoke,
            target_arg=target_arg,
        )
        compact_answer = {
            "status": answer.get("status", ""),
            "trust": answer.get("trust", ""),
            "archived_slice_closeout_evidence": {
                key: archived_slice.get(key)
                for key in (
                    "status",
                    "trust",
                    "scope",
                    "canonical_evidence",
                    "owner_surface",
                    "owner_kind",
                    "evidence_relationship",
                    "relevance",
                    "evidence_selection",
                    "source_plan",
                    "intended_archive",
                    "retention_state",
                    "freshness",
                    "proof_recorded",
                    "slice_completed",
                    "slice_status",
                    "closure_decision",
                    "parent_intent_status",
                    "parent_closure_blocked",
                    "rule",
                )
                if key in archived_slice
            },
            "strict_closeout_gate": strict_gate,
            "completion_gate": {
                key: completion_gate.get(key)
                for key in (
                    "kind",
                    "status",
                    "active_intent_satisfied",
                    "human_accepted_partial",
                    "claim_level_requested",
                    "claim_level_allowed",
                    "required_next_action",
                    "claim_authorization",
                    "residual_intent",
                    "self_review",
                    "continuation",
                    "task_posture_followthrough",
                    "authority_boundary",
                )
                if key in completion_gate
            },
            "lower_trust_closeout_count": answer.get("lower_trust_closeout_count", 0),
            "summary": answer.get("summary", ""),
            "terminal_action": terminal_action,
            "completion_options": completion_options,
            "memory_decision_packet": memory_decision_packet,
            "operating_loop": operating_loop,
            "current_task_closeout": compact_current_task_closeout(current_task_closeout),
            "closeout_protocol": {
                key: closeout_protocol.get(key)
                for key in (
                    "kind",
                    "protocol",
                    "status",
                    "source_surface",
                    "readiness",
                    "claim_boundary",
                    "residue_routing",
                    "knowledge_route_states",
                    "closure_permission",
                    "proof_dependency",
                    "detail_command",
                )
                if key in closeout_protocol
            },
            "assurance_requirements": {
                "status": assurance_requirements.get("status", "absent"),
                "configured_count": assurance_requirements.get("configured_count", 0),
                "active_count": assurance_requirements.get("active_count", 0),
                "missing_required_evidence_count": assurance_requirements.get("missing_required_evidence_count", 0),
                "evidence_status": assurance_requirements.get("evidence_status", []),
            },
            "verification": {
                "status": verification.get("status", "absent"),
                "configured": verification.get("configured", False),
                "protocol_count": verification.get("protocol_count", 0),
                "active_count": verification.get("active_count", 0),
                "active_protocols": verification.get("active_protocols", []),
                "evidence_status": verification.get("evidence_status", []),
            },
            "knowledge_authority_review": {
                key: knowledge_authority_review.get(key)
                for key in (
                    "kind",
                    "status",
                    "matched_source_count",
                    "workflow_obligation_match_count",
                    "stale_source_count",
                    "promotion_candidate_count",
                    "supersession_attention_count",
                    "next_actions",
                )
                if key in knowledge_authority_review
            },
            "proof_confidence": {
                key: proof_confidence.get(key)
                for key in ("status", "confidence", "claim_boundary", "proven_dimensions", "unproven_dimensions", "residual_risk")
                if key in proof_confidence
            },
            "checks": {
                "package_workflow_evidence": compact_closeout_check(package_evidence),
                "intent_satisfaction": compact_closeout_check(intent_check),
                "intent_proof": {
                    key: intent_proof_check.get(key)
                    for key in ("status", "trust", "claim_boundary", "warning")
                    if key in intent_proof_check
                },
                "architecture_decision": {
                    key: architecture_decision.get(key) for key in ("status", "configured", "decision_refs") if key in architecture_decision
                },
            },
            "durable_residue_action": {
                key: durable_action.get(key) for key in ("action", "summary", "command", "risk", "next_proof") if key in durable_action
            },
            "evidence_summary": {
                "historical_review_artifacts": {
                    "status": historical_reviews.get("status", "unavailable"),
                    "role": historical_reviews.get("role", ""),
                    "source_count": historical_reviews.get("source_count", 0),
                    "item_count": historical_reviews.get("item_count", 0),
                    "retention_policy_status": retention_policy.get("status", "unavailable"),
                    "retention_candidate_count": retention_policy.get("candidate_count", 0),
                    "detail": detail_command,
                }
            },
            "detail": detail_command,
        }
        if architecture_candidate.get("status") == "candidate":
            compact_answer["architecture_decision_candidate"] = {
                key: architecture_candidate.get(key)
                for key in ("status", "primary_route", "matched_markers", "decision_path_matches", "decision_target", "route")
                if key in architecture_candidate
            }
        return _localize_command_fields(compact_answer, cli_invoke=cli_invoke, target_arg=target_arg)
    if section == "agent_aids" and isinstance(answer, dict):
        storage = answer.get("storage", {})
        storage = storage if isinstance(storage, dict) else {}
        creation_affordance = answer.get("creation_affordance", {})
        creation_affordance = creation_affordance if isinstance(creation_affordance, dict) else {}
        storage_summary = {
            "candidate_root": storage.get("candidate_root", ".agentic-workspace/agent-aids"),
            "local_only_root": ".agentic-workspace/local/integrations",
            "manifest_name": storage.get("manifest_name", "manifest.json"),
            "manifest_check": storage.get("manifest_check", "python scripts/check/check_agent_aids.py"),
            "canonical_doc": storage.get("canonical_doc", ".agentic-workspace/docs/agent-aids-storage.md"),
        }
        return {
            "kind": answer.get("kind", "workspace-agent-aids-discovery/v1"),
            "status": answer.get("status", ""),
            "summary": answer.get("summary", {}),
            "primary_next_action": answer.get("primary_next_action", {}),
            "creation_affordance": creation_affordance,
            "storage_summary": storage_summary,
            "checked_in_aids": answer.get("checked_in_aids", []),
            "local_only": answer.get("local_only", {}),
            "recommended_actions": answer.get("recommended_actions", []),
            "recommended_action_omitted_count": answer.get("recommended_action_omitted_count", 0),
            "warnings": answer.get("warnings", []),
            "rules": answer.get("rules", []),
            "detail": _command_with_cli_invoke(
                "agentic-workspace defaults --section agent_aid_storage --format json",
                cli_invoke=cli_invoke,
            ),
        }
    return answer


def _unknown_report_section_message(section: str, payload: dict[str, Any]) -> str:
    available_sections = sorted(str(key) for key in payload.keys())
    available = ", ".join(available_sections)
    alias_sections = sorted(REPORT_SECTION_ALIASES)
    close_matches = get_close_matches(section, available_sections + alias_sections, n=3)
    suggestions = f" Did you mean: {', '.join(close_matches)}." if close_matches else ""
    recovery = (
        " Compact active-work routes: agentic-workspace summary --format json; "
        "agentic-workspace report --target ./repo --section next_action --format json; "
        "agentic-workspace report --target ./repo --section external_work_reconciliation --format json."
    )
    return f"Unknown report section {section!r}.{suggestions} Available sections: {available}.{recovery}"


def report_router_payload(
    payload: dict[str, Any], *, context_router: dict[str, Any], cli_invoke: str = DEFAULT_CLI_INVOKE
) -> dict[str, Any]:
    target_arg = _target_arg_from_payload(payload)
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
        planning_context = execution_shape.get("planning_context", execution_shape.get("task_shape", {}))
        if isinstance(planning_context, dict):
            current_work = {
                "status": str(planning_context.get("id", "unknown")),
                "summary": str(planning_context.get("summary", "")),
                "source": "execution_shape.planning_context",
            }
    section_hints = report_section_hints(payload, cli_invoke=cli_invoke, target_arg=target_arg)
    compact_section_hints = _compact_report_section_hints(section_hints)
    profile_payload = dict(payload.get("report_profile", report_profile_payload(context_router=context_router, cli_invoke=cli_invoke)))
    profile_payload = _localize_command_fields(profile_payload, cli_invoke=cli_invoke, target_arg=target_arg)
    profile_payload = _compact_report_profile(profile_payload)
    profile_payload["ordinary_agent_path"] = _ordinary_agent_path_payload(payload=payload, findings=findings, cli_invoke=cli_invoke)
    profile_payload["detail_sections"] = {
        "config_enforcement": _command_with_cli_invoke(
            "agentic-workspace report --target ./repo --section config_enforcement --format json",
            cli_invoke=cli_invoke,
            target_arg=target_arg,
        ),
        "config_effect_audit": _command_with_cli_invoke(
            "agentic-workspace report --target ./repo --section config_effect_audit --format json",
            cli_invoke=cli_invoke,
            target_arg=target_arg,
        ),
        "configuration_projection": _command_with_cli_invoke(
            "agentic-workspace report --target ./repo --section configuration_projection --format json",
            cli_invoke=cli_invoke,
            target_arg=target_arg,
        ),
        "selective_surfacing_evaluation": _command_with_cli_invoke(
            "agentic-workspace report --target ./repo --section selective_surfacing_evaluation --format json",
            cli_invoke=cli_invoke,
            target_arg=target_arg,
        ),
        "feature_tier": _command_with_cli_invoke(
            "agentic-workspace modules --target ./repo --format json", cli_invoke=cli_invoke, target_arg=target_arg
        ),
    }
    decision_grade_fields = list(profile_payload.get("decision_grade_fields", []))
    if "report_profile.ordinary_agent_path" not in decision_grade_fields:
        decision_grade_fields.append("report_profile.ordinary_agent_path")
    if "closeout_report" in payload and "closeout_report" not in decision_grade_fields:
        decision_grade_fields.append("closeout_report")
    maintainer_mode_value = payload.get("maintainer_mode", {})
    if isinstance(maintainer_mode_value, dict) and maintainer_mode_value.get("status") == "enabled":
        if "maintainer_mode" not in decision_grade_fields:
            decision_grade_fields.append("maintainer_mode")
    full_feature_tier = payload.get("feature_tier", {})
    advanced_policy = full_feature_tier.get("advanced_policy", {}) if isinstance(full_feature_tier, dict) else {}
    enabled_advanced_features = set(advanced_policy.get("enabled_features", []) if isinstance(advanced_policy, dict) else [])
    maintenance_pressure_value = payload.get("maintenance_pressure", {})
    maintenance_pressure_status = str(maintenance_pressure_value.get("status", "")) if isinstance(maintenance_pressure_value, dict) else ""
    maintenance_pressure_relevant = maintenance_pressure_status == "attention"
    if (
        "maintenance_pressure" in decision_grade_fields
        and "maintenance_pressure" not in enabled_advanced_features
        and not maintenance_pressure_relevant
    ):
        decision_grade_fields.remove("maintenance_pressure")
    profile_payload["decision_grade_fields"] = decision_grade_fields
    router_payload = {
        "kind": "workspace-report-router/v1",
        "schema": {
            "schema_version": "workspace-report-router-schema/v1",
            "full_profile_command": _command_with_cli_invoke(
                "agentic-workspace report --target ./repo --verbose --format json", cli_invoke=cli_invoke, target_arg=target_arg
            ),
            "section_command": _command_with_cli_invoke(
                "agentic-workspace report --target ./repo --section <section> --format json",
                cli_invoke=cli_invoke,
                target_arg=target_arg,
            ),
            "principle": "route first, inspect deep sections only when needed",
        },
        "command": "report",
        "target": payload.get("target", ""),
        "selected_modules": payload.get("selected_modules", []),
        "installed_modules": payload.get("installed_modules", []),
        "health": payload.get("health", "unknown"),
        "output_contract": _report_router_output_contract(payload.get("output_contract", {})),
        "communication_contract": payload.get(
            "communication_contract",
            _report_router_output_contract(payload.get("output_contract", {})).get("communication_contract", {}),
        ),
        "operating_posture": _report_router_operating_posture(payload.get("operating_posture", {})),
        "maintainer_mode": payload.get("maintainer_mode", {}),
        "report_profile": profile_payload,
        "current_work": current_work,
        "memory_consult": payload.get("memory_consult", {}),
        "routine_work_context": payload.get("routine_work_context", {}),
        "next_action": payload.get("next_action", {}),
        "warning_summary": {
            "total_count": len(findings),
            "by_severity": findings_by_severity,
            "by_module": findings_by_module,
            "sample": findings[:5],
            "raw_section": "findings",
        },
        "section_hints": compact_section_hints,
        "effective_authority": _report_router_effective_authority(payload.get("effective_authority", {})),
        "execution_shape": _report_router_execution_shape(payload.get("execution_shape", {})),
        "configuration_projection": payload.get("configuration_projection", {}),
        "selective_surfacing_evaluation": _report_router_selective_surfacing_evaluation(payload.get("selective_surfacing_evaluation", {})),
        "durable_intent": payload.get("durable_intent", {}),
        "improvement_intake": _report_router_improvement_intake(payload.get("improvement_intake", {})),
        "external_work_reconciliation": _report_router_external_work_reconciliation(payload.get("external_work_reconciliation", {})),
        "closeout_report": _report_router_closeout_report(payload.get("closeout_report", {}), cli_invoke=cli_invoke, target_arg=target_arg),
        "surface_value_guardrail": {
            "command": _command_with_cli_invoke(
                "agentic-workspace defaults --section surface_value_guardrail --format json", cli_invoke=cli_invoke
            ),
            "prefer": payload.get("surface_value_guardrail", {}).get("preference_order", []),
            "first_contact_budget": payload.get("surface_value_guardrail", {}).get("first_contact_budget", {}),
        },
        "deeper_detail": {
            "full_profile_command": _command_with_cli_invoke(
                "agentic-workspace report --target ./repo --verbose --format json", cli_invoke=cli_invoke, target_arg=target_arg
            ),
            "section_command": _command_with_cli_invoke(
                "agentic-workspace report --target ./repo --section <section> --format json",
                cli_invoke=cli_invoke,
                target_arg=target_arg,
            ),
            "lazy_section_catalog": "section_catalog",
            "high_volume_sections": profile_payload.get("high_volume_sections", []),
            "omitted_section_hint_count": max(0, len(section_hints) - len(compact_section_hints)),
        },
    }
    applicable_intent = _report_router_applicable_intent(payload.get("applicable_intent", {}))
    if applicable_intent.get("attention_required"):
        router_payload["applicable_intent"] = applicable_intent
    maintainer_mode = router_payload.get("maintainer_mode", {})
    if not (isinstance(maintainer_mode, dict) and maintainer_mode.get("status") == "enabled"):
        router_payload.pop("maintainer_mode", None)
    router_payload["surface_value_guardrail"]["prefer"] = router_payload["surface_value_guardrail"]["prefer"][:3]
    if "maintenance_pressure" in enabled_advanced_features or maintenance_pressure_relevant:
        router_payload["maintenance_pressure"] = _report_router_maintenance_pressure(payload.get("maintenance_pressure", {}))
    next_action_payload = router_payload.get("next_action", {})
    next_action_summary = (str(next_action_payload.get("summary", "")) if isinstance(next_action_payload, dict) else "") or str(
        router_payload.get("health", "unknown")
    )
    warning_summary_payload = router_payload.get("warning_summary", {})
    warning_summary_payload = warning_summary_payload if isinstance(warning_summary_payload, dict) else {}
    warning_sample = warning_summary_payload.get("sample", [])
    warning_sample_count = len(warning_sample) if isinstance(warning_sample, list) else 0
    compact_payload = {
        "kind": router_payload["kind"],
        "schema": router_payload["schema"],
        "command": router_payload["command"],
        "target": router_payload["target"],
        "health": router_payload["health"],
        "next_action": router_payload["next_action"],
        "communication_contract": _compact_communication_contract(router_payload.get("communication_contract")),
        "decision_packet": {
            "kind": "agentic-workspace/ordinary-decision-packet/v1",
            "surface": "report",
            "phase_question": "Which report fact changes the next action?",
            "next_action": next_action_summary,
            "blocked_actions": [],
            "required_commands": [],
            "claim_boundary": "reporting-only",
            "residue_owner": "current work" if current_work else "none",
            "reasons": [f"health={router_payload['health']}", f"warning_count={len(findings)}"],
            "detail_routes": {
                "current_work": _command_with_cli_invoke(
                    "agentic-workspace report --target ./repo --section current_work --format json",
                    cli_invoke=cli_invoke,
                    target_arg=target_arg,
                ),
                "warnings": _command_with_cli_invoke(
                    "agentic-workspace report --target ./repo --section findings --format json",
                    cli_invoke=cli_invoke,
                    target_arg=target_arg,
                ),
                "full_diagnostics": router_payload["deeper_detail"]["full_profile_command"],
            },
            "shown_because": ["command_phase=report", "report_section=default"],
            "absence_states": {
                "full_selector_inventory": "hidden_behind_detail_route",
                "high_volume_sections": "detail_omitted",
            },
        },
        "context": {
            "report_profile": router_payload["report_profile"],
            "current_work": router_payload["current_work"],
            "memory_consult": router_payload["memory_consult"],
            "routine_work_context": router_payload["routine_work_context"],
            "warning_summary": {
                "total_count": warning_summary_payload.get("total_count", 0),
                "by_severity": warning_summary_payload.get("by_severity", {}),
                "by_module": warning_summary_payload.get("by_module", {}),
                "sample_count": warning_sample_count,
                "detail_section": "findings",
            },
            "closeout_report": router_payload["closeout_report"],
            "absence_states": {
                "configuration_projection": "detail_omitted",
                "durable_intent": "detail_omitted",
                "external_work_reconciliation": "hidden_behind_detail_route",
                "execution_shape": "detail_omitted",
                "surface_value_guardrail": "detail_omitted",
            },
        },
        "drill_down": {
            "ordinary_profile": "primary=decision_packet;health=status;detail=exact_routes",
            "section_hints": {
                "status": "omitted-from-compact-default",
                "available_count": len(router_payload["section_hints"]) if isinstance(router_payload["section_hints"], list) else 0,
                "sample": [],
                "omitted_count": len(router_payload["section_hints"]) if isinstance(router_payload["section_hints"], list) else 0,
                "detail_route": router_payload["deeper_detail"]["section_command"],
            },
            "deeper_detail": {
                "full_profile_command": router_payload["deeper_detail"]["full_profile_command"],
                "section_command": router_payload["deeper_detail"]["section_command"],
                "omitted_section_hint_count": router_payload["deeper_detail"]["omitted_section_hint_count"],
            },
            "selector_inventory": bounded_selector_inventory(
                selectors=[
                    "next_action",
                    "health",
                    "context.report_profile",
                    "context.current_work",
                    "context.memory_consult",
                    "context.routine_work_context",
                    "communication_contract",
                    "context.warning_summary",
                    "context.execution_shape",
                    "context.configuration_projection",
                    "context.selective_surfacing_evaluation",
                    "context.improvement_intake",
                    "context.external_work_reconciliation",
                    "context.closeout_report",
                    "context.surface_value_guardrail",
                    "drill_down.section_hints",
                    "drill_down.deeper_detail.lazy_section_catalog",
                    "drill_down.deeper_detail",
                ],
                source_command="report",
                select_command=_command_with_cli_invoke(
                    "agentic-workspace report --target ./repo --section <section> --format json",
                    cli_invoke=cli_invoke,
                    target_arg=target_arg,
                ),
                inventory_command=router_payload["deeper_detail"]["full_profile_command"],
            ),
        },
    }
    return _localize_command_fields(compact_payload, cli_invoke=cli_invoke, target_arg=target_arg)


def _compact_report_profile(value: dict[str, Any]) -> dict[str, Any]:
    context_router = value.get("context_router", {})
    compact_context_router = {}
    if isinstance(context_router, dict):
        compact_context_router = {
            key: context_router[key] for key in ("first_view", "current_state_view", "proof_view", "fallback_view") if key in context_router
        }
    high_volume = value.get("high_volume_sections", [])
    if isinstance(high_volume, list):
        compact_high_volume = [
            {"section": item.get("section", ""), "reason": item.get("reason", "")} for item in high_volume if isinstance(item, dict)
        ]
    else:
        compact_high_volume = []
    return {
        key: value[key]
        for key in (
            "default_profile",
            "full_profile",
            "section_selector",
            "default_command",
            "full_profile_command",
            "full_profile_cost",
            "section_command",
            "rule",
            "decision_grade_fields",
            "router_shape_guard",
        )
        if key in value
    } | {
        "context_router": compact_context_router,
        "high_volume_sections": compact_high_volume,
    }


def _compact_report_section_hints(hints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {
        "effective_authority": 0,
        "execution_shape": 1,
        "routine_work_context": 2,
        "improvement_intake": 3,
        "applicable_intent": 4,
        "operating_posture": 5,
        "external_work_reconciliation": 6,
        "configuration_projection": 7,
        "selective_surfacing_evaluation": 8,
        "module_reports": 9,
        "successful_completion_cost": 10,
        "findings": 11,
    }
    ordered = sorted(
        hints,
        key=lambda item: (priority.get(str(item.get("section", "")), 99), str(item.get("section", ""))),
    )
    compact: list[dict[str, Any]] = []
    for item in ordered[:8]:
        compact.append(
            {key: item[key] for key in ("section", "why_now", "command", "volume", "advanced_feature") if key in item}
            | ({"purpose_summary": str(item.get("purpose", ""))[:80]} if item.get("purpose") else {})
        )
    return compact


def _support_list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _report_router_output_contract(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    budget = value.get("verbosity_budget", {})
    communication_contract = value.get("communication_contract", {})
    return {
        "optimization_bias": value.get("optimization_bias", ""),
        "optimization_bias_source": value.get("optimization_bias_source", ""),
        "report_density": value.get("report_density", ""),
        "rendered_view_style": value.get("rendered_view_style", ""),
        "default_detail": budget.get("default_detail", "") if isinstance(budget, dict) else "",
        "deep_detail": budget.get("deep_detail", "") if isinstance(budget, dict) else "",
        "communication_contract": _compact_communication_contract(communication_contract),
        "detail_section": "output_contract",
    }


def _compact_communication_contract(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    phase_expectations = value.get("phase_expectations", {})
    phase_ids = list(phase_expectations.keys()) if isinstance(phase_expectations, dict) else []
    return {
        key: value.get(key)
        for key in (
            "kind",
            "surface",
            "default_posture",
        )
        if key in value
    } | {
        "phase_ids": phase_ids,
    }


def _report_router_operating_posture(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    improvement = value.get("improvement_latitude", {})
    bias = value.get("optimization_bias", {})
    closeout_nudge = value.get("closeout_nudge", {})
    return {
        "kind": value.get("kind", ""),
        "status": value.get("status", ""),
        "surface": value.get("surface", ""),
        "improvement_latitude": improvement if isinstance(improvement, dict) else {},
        "optimization_bias": bias if isinstance(bias, dict) else {},
        "closeout_nudge": closeout_nudge if isinstance(closeout_nudge, dict) else {},
        "required_behavior_summary": "bounded evidence-backed action; compactly report useful incidental findings",
        "detail_section": "operating_posture",
    }


def _report_router_improvement_intake(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    candidates = [
        {key: item[key] for key in ("kind", "source", "summary", "recommended_destination") if isinstance(item, dict) and key in item}
        for item in _support_list_payload(value.get("improvement_signal_candidates"))[:3]
    ]
    return {
        "kind": value.get("kind", "workspace-improvement-intake/v1"),
        "role": value.get("role", "router-not-backlog"),
        "command": value.get("command", "agentic-workspace report --target ./repo --section improvement_intake --format json"),
        "audience_boundary": {
            "status": value.get("audience_boundary", {}).get("status", "target-repo")
            if isinstance(value.get("audience_boundary"), dict)
            else "target-repo"
        },
        "subtypes": [item.get("id", "") for item in _support_list_payload(value.get("subtypes")) if isinstance(item, dict)],
        "candidate_count": value.get("candidate_count", 0),
        "candidate_sample": candidates,
        "setup_findings": value.get("setup_findings", {}),
        "detail_section": "improvement_intake",
    }


def _report_router_config_enforcement(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    weak_routes = value.get("weak_field_routes", [])
    if not isinstance(weak_routes, list):
        weak_routes = []
    return {
        "kind": value.get("kind", "workspace-config-enforcement/v1"),
        "status": value.get("status", "unknown"),
        "field_count_by_class": value.get("field_count_by_class", {}),
        "class_ids": sorted(str(key) for key in (value.get("classes", {}) or {}).keys())
        if isinstance(value.get("classes", {}), dict)
        else [],
        "weak_field_route_count": len(weak_routes),
        "weak_field_route_sample": weak_routes[:2],
        "detail_section": "config_enforcement",
        "section_command": "agentic-workspace report --target ./repo --section config_enforcement --format json",
    }


def _report_router_config_effect_audit(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    warnings = value.get("claimed_vs_actual_warnings", [])
    if not isinstance(warnings, list):
        warnings = []
    agent_dependent = value.get("agent_dependent_fields", [])
    if not isinstance(agent_dependent, list):
        agent_dependent = []
    return {
        "kind": value.get("kind", "workspace-config-effect-audit/v1"),
        "status": value.get("status", "unknown"),
        "field_count_by_effect": value.get("field_count_by_effect", {}),
        "agent_dependent_field_count": len(agent_dependent),
        "warning_count": len(warnings),
        "detail_section": "config_effect_audit",
    }


def _report_router_selective_surfacing_evaluation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    checks = value.get("checks", [])
    if not isinstance(checks, list):
        checks = []
    failing = value.get("failing_checks", [])
    if not isinstance(failing, list):
        failing = []
    metrics = value.get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}
    return {
        "kind": value.get("kind", "agentic-workspace/selective-surfacing-evaluation/v1"),
        "status": value.get("status", "unknown"),
        "check_count": len(checks),
        "failing_check_count": len(failing),
        "scenario_count": value.get("scenario_count", 0),
        "metrics": {key: metrics[key] for key in ("projection_row_count", "compact_json_size", "compact_selector_count") if key in metrics},
        "detail_section": "selective_surfacing_evaluation",
    }


def _report_router_external_work_reconciliation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    freshness = value.get("freshness", {})
    if isinstance(freshness, dict):
        freshness = {
            key: freshness[key]
            for key in (
                "status",
                "refreshed_at",
                "trust_scope",
                "refresh_after_mutation",
                "refresh_command",
                "fresh_enough_to_trust",
            )
            if key in freshness
        }
    else:
        freshness = {}
    return {
        "kind": value.get("kind", "planning-external-work-reconciliation/v1"),
        "status": value.get("status", "unknown"),
        "primary_owner": value.get("primary_owner", ".agentic-workspace/planning/state.toml"),
        "freshness": freshness,
        "external_work_state": value.get("external_work_state", {}),
        "closeout_state": value.get("closeout_state", {}),
        "landed_open_state": value.get("landed_open_state", {}),
        "routine_reconciliation": value.get("routine_reconciliation", {}),
        "recommended_next_action": value.get("recommended_next_action", ""),
        "section_command": "agentic-workspace report --target ./repo --section external_work_reconciliation --format json",
    }


def _report_router_applicable_intent(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable", "source_count": 0}
    manual = value.get("manual_verification", [])
    manual = manual if isinstance(manual, list) else []
    conflicts = _support_list_payload(value.get("conflicts"))
    missing_authority = _support_list_payload(value.get("missing_authority"))
    authority_boundary = value.get("authority_boundary", {})
    if isinstance(authority_boundary, dict):
        authority_boundary = {
            "surface": authority_boundary.get("surface", "applicable_intent"),
            "authority_class": authority_boundary.get("authority_class", "advisory-support"),
            "rule": authority_boundary.get("reporting_rule") or authority_boundary.get("rule", ""),
        }
    else:
        authority_boundary = {}
    compact = {
        "status": value.get("status", "unavailable"),
        "source_count": value.get("source_count", 0),
        "conflict_status": value.get("conflict_status", "unknown"),
    }
    attention_required = bool(value.get("closeout_blocked", False) or conflicts or missing_authority or manual)
    if attention_required:
        compact["attention_required"] = True
        compact["conflict_count"] = len(conflicts)
        compact["missing_authority_count"] = len(missing_authority)
        compact["manual_verification_count"] = len(manual)
        compact["closeout_blocked"] = bool(value.get("closeout_blocked", False))
        compact["kind"] = value.get("kind", "agentic-workspace/applicable-intent-sources/v1")
        compact["detail_command"] = "agentic-workspace report --target ./repo --section applicable_intent --format json"
        compact["blocked_claims"] = value.get("blocked_claims", [])
        compact["authority_boundary"] = authority_boundary
    return compact


def _report_router_closeout_report(value: Any, *, cli_invoke: str = DEFAULT_CLI_INVOKE, target_arg: str = "./repo") -> dict[str, Any]:
    command = _command_with_cli_invoke(
        "agentic-workspace report --target ./repo --section closeout_report --format json",
        cli_invoke=cli_invoke,
        target_arg=target_arg,
    )
    if not isinstance(value, dict):
        return {
            "profile": "compact",
            "reason": "default",
            "escalation_source": "profile-policy-default",
            "next_command": command,
            "selector": "closeout_report",
        }
    routing = value.get("routing", {})
    routing = routing if isinstance(routing, dict) else {}
    profile_policy = value.get("profile_policy", {})
    profile_policy = profile_policy if isinstance(profile_policy, dict) else {}
    return {
        "profile": value.get("profile") or routing.get("profile", "compact"),
        "reason": routing.get("reason") or profile_policy.get("reason", "default"),
        "escalation_source": routing.get("escalation_source") or profile_policy.get("escalation_source", ""),
        "next_command": command,
        "selector": "closeout_report",
    }


def _report_router_maintenance_pressure(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"status": "unavailable"}
    subcategories = [
        {
            "id": item.get("id", ""),
            "status": item.get("status", "unknown"),
            "count": item.get("count", 0),
            "detail_section": item.get("detail_section", ""),
            "section_command": item.get("section_command", ""),
        }
        for item in _support_list_payload(value.get("subcategories"))
        if isinstance(item, dict)
    ]
    return {
        "kind": value.get("kind", "workspace-maintenance-pressure/v1"),
        "status": value.get("status", "unknown"),
        "current_execution_separate": value.get("current_execution_separate", True),
        "attention_category_count": value.get("attention_category_count", 0),
        "active_category_count": value.get("active_category_count", 0),
        "subcategories": [
            {key: item[key] for key in ("id", "status", "count", "detail_section", "section_command") if key in item}
            for item in subcategories
        ],
        "detail_sections": value.get("detail_sections", []),
        "recommended_next_action": value.get("recommended_next_action", ""),
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
    planning_context = value.get("planning_context", value.get("task_shape", {}))
    recommender = value.get("workflow_shape_guidance", value.get("task_shape_recommender", {}))
    if isinstance(recommender, dict):
        shapes = recommender.get("shapes", [])
        recommender = {
            "status": recommender.get("status", "unknown"),
            "rule": recommender.get("rule", ""),
            "shape_ids": [str(item.get("id", "")) for item in shapes if isinstance(item, dict)],
            "detail_section": "execution_shape",
        }
    else:
        recommender = {}
    fast_path = value.get("narrow_work_fast_path", {})
    if isinstance(fast_path, dict):
        fast_path = {
            "status": fast_path.get("status", "unknown"),
            "one_compact_check": fast_path.get("one_compact_check", ""),
            "rule": fast_path.get("rule", ""),
            "promote_when_count": len(fast_path.get("promote_when", []) if isinstance(fast_path.get("promote_when"), list) else []),
        }
    else:
        fast_path = {}
    return {
        "status": value.get("status", "unknown"),
        "planning_context": planning_context if isinstance(planning_context, dict) else {},
        "workflow_shape_guidance": recommender,
        "narrow_work_fast_path": fast_path,
        "recommendation": recommendation if isinstance(recommendation, dict) else {},
        "deviation_rule": value.get("deviation_rule", ""),
    }


def _ordinary_agent_path_payload(
    *, payload: dict[str, Any], findings: list[dict[str, Any]], cli_invoke: str = DEFAULT_CLI_INVOKE
) -> dict[str, Any]:
    effective_authority = payload.get("effective_authority", {})
    current_work = effective_authority.get("current_work", {}) if isinstance(effective_authority, dict) else {}
    if not isinstance(current_work, dict):
        current_work = {}
    current_status = str(current_work.get("status", "unknown") or "unknown")
    warning_count = len(findings)
    phase_questions = [
        {
            "phase": "startup",
            "question": "What is the smallest safe context before acting?",
            "primary_affordance": _command_with_cli_invoke(
                'agentic-workspace start --target ./repo --task "<task>" --format json', cli_invoke=cli_invoke
            ),
            "boundary": "Do not browse command inventories or raw workspace files before compact routing.",
        },
        {
            "phase": "work_shaping",
            "question": "Is this direct, bounded, lane, epic, takeover, or continuation work?",
            "primary_affordance": "start, summary, or routed Planning mutation",
            "boundary": "Decide work shape before implementation; do not treat passing checks as intent closure.",
        },
        {
            "phase": "governing_knowledge",
            "question": "Which source can change interpretation, edits, proof, or closeout?",
            "primary_affordance": "knowledge routes and gates in compact output",
            "boundary": "Surface action-changing authority and freshness only.",
        },
        {
            "phase": "implementation_context",
            "question": "What narrow working set is safe to touch now?",
            "primary_affordance": _command_with_cli_invoke(
                'agentic-workspace implement --changed <paths> --task "<task>" --format json', cli_invoke=cli_invoke
            ),
            "boundary": "Known-path context does not select broad roadmap work or close parent intent.",
        },
        {
            "phase": "proof",
            "question": "What evidence is required for the claim I want to make?",
            "primary_affordance": _command_with_cli_invoke(
                "agentic-workspace proof --target ./repo --changed <paths> --format json", cli_invoke=cli_invoke
            ),
            "boundary": "Proof execution is separate from intent-satisfaction judgment.",
        },
        {
            "phase": "closeout",
            "question": "What must survive after this agent stops?",
            "primary_affordance": "Planning closeout/archive, proof report fields, Memory capture, or follow-up issue",
            "boundary": "Route durable residue to one owner instead of leaving it in chat.",
        },
        {
            "phase": "continuation",
            "question": "How can a future agent resume without replaying chat?",
            "primary_affordance": _command_with_cli_invoke("agentic-workspace summary --format json", cli_invoke=cli_invoke),
            "boundary": "Expose freshness, claim boundary, proof state, and next action before raw rereads.",
        },
    ]
    ordinary_path: dict[str, Any] = {
        "status": "ready",
        "primary_design_unit": "phase_question",
        "rule": "Answer the current phase question first; commands are routed affordances, not the workflow.",
        "phase_questions": [{"phase": item["phase"], "question": item["question"]} for item in phase_questions],
        "lane_completion_model": _compact_ordinary_lane_completion_model(cli_invoke=cli_invoke),
        "entry_command": _command_with_cli_invoke("agentic-workspace start --target ./repo --format json", cli_invoke=cli_invoke),
        "deep_detail_rule": "Open section, memory, planning, or review artifacts only when compact output points there.",
        "current_signal": {
            "current_work_status": current_status,
            "warning_count": warning_count,
        },
        "stop_or_escalate_when_count": 4,
        "stop_or_escalate_rule": "Stop when health, active-plan continuity, proof ambiguity, or product/authority intent is unclear.",
    }
    recovery = _off_happy_path_recovery_payload(cli_invoke=cli_invoke)
    scenarios = recovery.get("scenarios", [])
    ordinary_path["off_happy_path_recovery"] = {
        "kind": recovery.get("kind", "workspace-off-happy-path-recovery/v1"),
        "status": recovery.get("status", "available"),
        "scenario_ids": [str(item.get("id", "")) for item in scenarios if isinstance(item, dict)],
        "detail_section": "report_profile",
        "recover_by_default": _command_with_cli_invoke("agentic-workspace start --target ./repo --format json", cli_invoke=cli_invoke),
    }
    return ordinary_path


def _compact_ordinary_lane_completion_model(*, cli_invoke: str = DEFAULT_CLI_INVOKE) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/ordinary-lane-completion-model/v1",
        "status": "available",
        "visibility_question": "Does this surface change the next safe action, working set, proof, owner, or continuation?",
        "minimal_survivor_shape": ["claim_boundary", "proof_summary", "residue_owner", "remaining_gap", "reopen_trigger"],
        "restart_scenario_ids": [
            "direct-work",
            "known-changed-paths",
            "active-lane-continuation",
            "takeover-or-recovery",
            "parent-lane-closeout",
        ],
        "affordance_first_rule_count": 7,
        "detail_section": "report_profile",
        "detail_command": _command_with_cli_invoke(
            "agentic-workspace report --target ./repo --section report_profile --format json", cli_invoke=cli_invoke
        ),
        "absence_state": "full_model_hidden_behind_detail_route",
    }


def _ordinary_lane_completion_model_payload(*, cli_invoke: str = DEFAULT_CLI_INVOKE) -> dict[str, Any]:
    return {
        "kind": "agentic-workspace/ordinary-lane-completion-model/v1",
        "status": "available",
        "rule": "A lane is done only when visible surfaces, artifact lifecycle, restart economics, and prose-to-affordance pressure are resolved or explicitly owned.",
        "visibility_disposition": {
            "question": "Does this surface change the next safe action, working set, proof, owner, or continuation?",
            "retained_first_contact": ["AGENTS.md", "start", "summary", "implement --changed", "proof --changed"],
            "routed_detail": ["planning", "memory", "report --section <section>", "config", "defaults", "ownership", "modules"],
            "diagnostic_or_recovery": ["preflight", "doctor", "status", "setup"],
            "lifecycle": ["init", "install", "upgrade", "uninstall", "prompt"],
            "generated_or_reference": ["docs/reference/", "generated command metadata"],
            "demotion_applied": "ordinary_agent_path now exposes phase questions and this lane model before legacy command fields; report detail remains behind section selectors.",
        },
        "artifact_lifecycle": {
            "active": "Owns current execution only while work is live; closeout must not preserve raw execution narrative.",
            "durable": "Promote only reusable intent, invariants, proof boundaries, or anti-rediscovery facts to docs, Memory, or issues.",
            "local_only": "Keep transient checkpoints and tool-local state outside canonical proof and package-owned residue.",
            "generated": "Treat generated/reference artifacts as derived detail; route through selectors or maintainer checks.",
            "promoted": "Once product output lands, it becomes normal repo output rather than AW residue.",
            "archived_or_removable": "Archive, demote, or remove residue that no longer changes continuation, proof, owner, or review.",
            "minimal_survivor_shape": ["claim_boundary", "proof_summary", "residue_owner", "remaining_gap", "reopen_trigger"],
        },
        "restart_scenarios": [
            {
                "id": "direct-work",
                "compact_entry": _command_with_cli_invoke(
                    'agentic-workspace start --target ./repo --task "<task>" --format json', cli_invoke=cli_invoke
                ),
                "must_recover": ["next_safe_action", "governing knowledge gate", "proof expectation"],
            },
            {
                "id": "known-changed-paths",
                "compact_entry": _command_with_cli_invoke(
                    'agentic-workspace implement --changed <paths> --task "<task>" --format json', cli_invoke=cli_invoke
                ),
                "must_recover": ["working set", "owner boundary", "proof route"],
            },
            {
                "id": "active-lane-continuation",
                "compact_entry": _command_with_cli_invoke("agentic-workspace summary --format json", cli_invoke=cli_invoke),
                "must_recover": ["active owner", "next slice or PR review action", "claim boundary", "remaining lane gaps"],
            },
            {
                "id": "takeover-or-recovery",
                "compact_entry": _command_with_cli_invoke("agentic-workspace preflight --format json", cli_invoke=cli_invoke),
                "must_recover": ["health", "repair action", "safe drill-down"],
            },
            {
                "id": "parent-lane-closeout",
                "compact_entry": _command_with_cli_invoke(
                    "agentic-workspace summary --select continuation_view,lanes --format json", cli_invoke=cli_invoke
                ),
                "must_recover": ["proof aggregation", "residue owner", "unresolved child slices", "closure permission"],
            },
        ],
        "affordance_first_rules": [
            "compact packet before explanation",
            "selector before copied source text",
            "next_safe_action before general guidance",
            "owner surface before broad reading",
            "proof route before proof advice",
            "claim boundary before closeout prose",
            "warning force before caution narrative",
        ],
        "reasoning_skill_boundary": "Use reasoning skills when semantic judgment is required; use CLI packets for facts, routes, selectors, proof commands, and claim boundaries.",
        "closeout_checks": [
            "surface disposition recorded",
            "artifact lifecycle survivor shape recorded",
            "restart scenarios reviewed or routed",
            "selected prose-first paths converted or owned",
        ],
    }


def _off_happy_path_recovery_payload(*, cli_invoke: str = DEFAULT_CLI_INVOKE) -> dict[str, Any]:
    return {
        "kind": "workspace-off-happy-path-recovery/v1",
        "status": "available",
        "rule": "When an agent starts from the wrong package surface, recover through compact commands before reading deep artifacts or hand-authoring durable state.",
        "scenarios": [
            {
                "id": "opened-report-before-start",
                "misuse": "agent starts from report detail before compact startup",
                "recovery_signal": "report_profile.ordinary_agent_path.entry_command",
                "recover_by": _command_with_cli_invoke("agentic-workspace start --target ./repo --format json", cli_invoke=cli_invoke),
            },
            {
                "id": "opened-deep-review-artifact",
                "misuse": "agent opens review or module detail before compact routing points there",
                "recovery_signal": "report_profile.ordinary_agent_path.deep_detail_rule",
                "recover_by": (
                    _command_with_cli_invoke("agentic-workspace report --target ./repo --format json", cli_invoke=cli_invoke)
                    + ", then only the named --section when needed"
                ),
            },
            {
                "id": "invalid-near-miss-command",
                "misuse": "agent runs an invalid or near-miss workspace command",
                "recovery_signal": "parser suggestion plus startup/preflight fallback hint",
                "recover_by": _command_with_cli_invoke("agentic-workspace preflight --format json", cli_invoke=cli_invoke),
            },
            {
                "id": "direct-generated-adapter-edit",
                "misuse": "agent changes a generated adapter or executable CLI surface directly",
                "recovery_signal": "proof selector generated-command or direct-cli-edit review",
                "recover_by": _command_with_cli_invoke(
                    "agentic-workspace proof --target ./repo --changed <paths> --format json", cli_invoke=cli_invoke
                ),
            },
            {
                "id": "hand-authored-durable-artifact",
                "misuse": "agent hand-authors a durable docs/planning/memory artifact without a compact proof route",
                "recovery_signal": "proof selector surface_value_review",
                "recover_by": _command_with_cli_invoke(
                    "agentic-workspace proof --target ./repo --changed <paths> --format json", cli_invoke=cli_invoke
                ),
            },
        ],
    }


def report_section_hints(
    payload: dict[str, Any], *, cli_invoke: str = DEFAULT_CLI_INVOKE, target_arg: str | None = None
) -> list[dict[str, Any]]:
    target_arg = target_arg or _target_arg_from_payload(payload)
    section_purposes = {
        "effective_authority": "authority, current work, system-intent pressure, idle context, and unresolved gaps",
        "execution_shape": "default execution posture and planning-backed work guidance",
        "durable_intent": "task, subsystem, and system intent pressure relevant to decisions before implementation or closeout",
        "applicable_intent": "compact applicable-intent source, authority, conflict, durable-outcome, and manual-verification evidence",
        "maintenance_pressure": "one compact router for audit, retention, footprint, external-evidence, and closeout residue",
        "reuse_pressure": "changed-path reuse and abstraction-pressure facts before adding local code",
        "operational_compression": "falsifiable advisory measures for whether surfaces reduce total operational cost",
        "successful_completion_cost": "recent model CLI evaluation cost, package-read overhead, and first-pass versus rework evidence",
        "reasoning_economy": "visible-artifact evidence classes, ledger examples, and fixture checks for compact closeout/report behavior",
        "findings": "raw warnings and attention signals grouped in router warning_summary",
        "module_reports": "deep planning and memory module reports",
        "reports": "workspace lifecycle report detail",
        "surface_value_guardrail": "surface growth review pressure",
        "assurance_requirements": "repo-declared assurance authority, evidence, proof profile, and claim-boundary facts",
        "closeout_trust": "closeout trust and lower-trust residue signals",
        "closeout_claim_boundary": "compact closeout claim permission, blockers, residue route, and proof dependency",
        "external_work_reconciliation": "one provider-agnostic external-work route for evidence freshness, closeout reconciliation, and landed-open checks",
        "external_evidence_safety": "compact external freshness, divergence, and closeout-safety decision support",
        "completion_contract": "Planning completion-contract lens for what must become true, proof, constraints, and blocked stop",
        "repair_loop_residue": "validation-driven repair loop residue across Planning and Verification",
        "structured_findings": "shared structured finding shape for review and promotion routing",
        "workflow_compliance_summary": "derived review/recovery summary of workflow entrypoint, gates, trust impact, and recovery action",
        "continuation_next_actions": "evidence-ranked next actions, validation, risks, and stop conditions for continuation",
        "migration_pilot_template": "optional migration-pilot decomposition shape with parity and rollout boundaries",
        "compact_output_criteria": "criteria for compact outputs to remain sufficient for cheap continuation",
        "automation_readiness": "provider-agnostic automation-readiness checklist that keeps execution outside AW",
        "external_work_delta": "provider-agnostic external-work snapshot or delta from prior evidence when available",
        "discovery": "setup discovery and candidate surfaces",
        "standing_intent": "effective standing intent and stronger-home guidance",
        "improvement_intake": "unified routing for setup findings, review findings, validation friction, and memory improvement signals",
        "repo_friction": "repo-friction and improvement pressure evidence",
        "operating_posture": "effective improvement and output posture for bounded action, incidental findings, and compact residue",
        "local_aw_state": "compact ownership-aware status for tracked, ignored, local-only, cache, payload, policy, and proof AW surfaces",
        "local_footprint": "tracked-vs-ignored AW footprint, local scratch retention budgets, largest offenders, and cleanup routing",
        "config": "resolved workspace config and local posture",
        "config_enforcement": "config fields classified by actual enforcement strength and operational routes",
        "config_effect_audit": "audit of actual config force, affected outputs, and agent-dependent settings",
        "configuration_projection": "config-to-runtime projection coverage, suppression rules, owner exceptions, and verification probes",
        "selective_surfacing_evaluation": "cheap contract checks for positive config surfacing, non-applicable suppression, and compact-output bounds",
        "registry": "module registry and lifecycle metadata",
    }
    findings = [finding for finding in payload.get("findings", []) if isinstance(finding, dict)]
    current_work = (
        payload.get("effective_authority", {}).get("current_work", {}) if isinstance(payload.get("effective_authority"), dict) else {}
    )
    current_status = str(current_work.get("status", "unknown") if isinstance(current_work, dict) else "unknown")
    why_now = {
        "effective_authority": ("inspect now if authority, idle state, or unresolved intent pressure affects whether work can proceed"),
        "execution_shape": "inspect now to choose direct work, light planning, or checked-in execplan promotion",
        "durable_intent": "inspect now when task intent may generalize into durable system or subsystem direction",
        "applicable_intent": "inspect before broad, subsystem-affecting, compliance-relevant, or soft-intent closeout decisions",
        "maintenance_pressure": "inspect now only when residue, retention, or closeout pressure affects the active lane",
        "reuse_pressure": "inspect before implementation when deciding whether to reuse, accept duplication, or route extraction follow-up",
        "operational_compression": "inspect now when assessing whether package surfaces are reducing total work",
        "successful_completion_cost": "inspect now when deciding whether workflow surfaces should stay default, shrink, or move behind selectors",
        "reasoning_economy": "inspect when proving closeout or report behavior got cheaper without losing proof, residue, or closure status",
        "findings": "inspect now because warnings are present" if findings else "skip unless diagnosing an absent-warning state",
        "module_reports": "deep detail; inspect only when a compact router field points to planning or memory internals",
        "reports": "deep lifecycle detail; inspect only for report/debug work",
        "surface_value_guardrail": "inspect before adding or expanding a visible surface",
        "assurance_requirements": "inspect when repo-declared assurance requirements may affect authority lookup, proof, review, or closeout claims",
        "closeout_trust": "inspect before closing broad work or auditing package-use evidence",
        "closeout_claim_boundary": "inspect immediately before final messages, PR readiness, issue closure, or closeout handoff",
        "external_work_reconciliation": "inspect when deciding whether checked-in planning, external work state, and landed evidence agree",
        "external_evidence_safety": "inspect before closeout when external issue, CI, scanner, or ticket evidence may be stale or divergent",
        "completion_contract": "inspect when deciding whether work is done, partial, blocked, or continuation-required",
        "repair_loop_residue": "inspect after failed validation, iterative repair, or partial proof to recover the next grounded action",
        "structured_findings": "inspect when review, friction, verification, or promotion residue needs one owner and disposition",
        "workflow_compliance_summary": "inspect during takeover, recovery, review, or closeout when workflow use affects trust",
        "continuation_next_actions": "inspect when a future session needs ranked next actions with evidence and stop conditions",
        "migration_pilot_template": "inspect before turning broad migration or modernization into a bounded pilot",
        "compact_output_criteria": "inspect when changing compact CLI output contracts or reviewing restart sufficiency",
        "automation_readiness": "inspect before adding external automation, bot, CI, ticket, or agent workflow integration",
        "external_work_delta": "inspect when external-work intake or closure state is part of the task",
        "discovery": "inspect during setup, bootstrap, or missing-surface diagnosis",
        "standing_intent": "inspect when product direction or stronger-home placement is the question",
        "improvement_intake": "inspect when a product or workflow improvement signal needs routing, dismissal, or durable ownership",
        "repo_friction": "inspect when choosing or routing improvement targets",
        "operating_posture": "inspect at startup, recovery, or closeout when improvement posture should affect behavior without adding obligations",
        "local_aw_state": "inspect after AW upgrades or local policy edits when tracked git status is not enough",
        "local_footprint": "inspect when .agentic-workspace/local or AW scratch size is surprising or over budget",
        "config": "deep detail; inspect only when resolved config, posture, or obligations matter",
        "config_enforcement": "inspect when deciding whether a config field is hard, operational, advisory, or local-only",
        "config_effect_audit": "inspect when verifying whether settings have concrete behavior or only advise agents",
        "configuration_projection": "inspect when verifying configured behavior has ordinary-path projection or stays suppressed",
        "selective_surfacing_evaluation": "inspect when proving config surfacing is executable, bounded, and not only documented",
        "registry": "deep detail; inspect only when module metadata or lifecycle registration matters",
    }
    if current_status in {"absent", "direct-or-no-active-plan"}:
        why_now["effective_authority"] = "inspect now only if idle state, authority, or system-intent pressure is unclear"
    feature_tier = payload.get("feature_tier", {})
    advanced_policy = feature_tier.get("advanced_policy", {}) if isinstance(feature_tier, dict) else {}
    enabled_advanced_features = set(advanced_policy.get("enabled_features", []) if isinstance(advanced_policy, dict) else [])
    advanced_sections = {
        "maintenance_pressure": "maintenance_pressure",
        "operational_compression": "maintenance_pressure",
        "closeout_trust": "review_artifacts",
        "external_work_delta": "external_adapters",
    }
    maintenance_pressure_value = payload.get("maintenance_pressure", {})
    maintenance_pressure_status = str(maintenance_pressure_value.get("status", "")) if isinstance(maintenance_pressure_value, dict) else ""
    hints: list[dict[str, Any]] = []
    for section, purpose in section_purposes.items():
        if section in payload:
            if section == "applicable_intent":
                applicable_compact = _report_router_applicable_intent(payload.get("applicable_intent", {}))
                if not applicable_compact.get("attention_required"):
                    continue
            advanced_feature = advanced_sections.get(section)
            relevant_advanced_section = section == "maintenance_pressure" and maintenance_pressure_status == "attention"
            if advanced_feature and advanced_feature not in enabled_advanced_features and not relevant_advanced_section:
                continue
            hints.append(
                {
                    "section": section,
                    "purpose": purpose,
                    "why_now": why_now.get(section, "inspect when this section is named by compact routing output"),
                    "command": _command_with_cli_invoke(
                        f"agentic-workspace report --target ./repo --section {section} --format json",
                        cli_invoke=cli_invoke,
                        target_arg=target_arg,
                    ),
                    "volume": "high" if section in {"module_reports", "reports", "registry", "config"} else "normal",
                    **({"advanced_feature": advanced_feature} if advanced_feature else {}),
                }
            )
    return hints


def standing_intent_payload(
    *,
    target_root: Path,
    config_policy: dict[str, Any],
    active_planning: dict[str, Any] | None,
    memory_installed: bool,
) -> dict[str, Any]:
    classes = [
        _standing_intent_class_payload(
            intent_class="config_policy",
            summary="Stable repo policy that should be queryable and preferably machine-readable.",
            default_owner=".agentic-workspace/config.toml",
            authoritative_kind="policy",
            durable_when=[
                "the guidance should survive startup without rereading prose",
                "the repo benefits from a compact machine-readable policy surface",
            ],
            transient_when=[
                "the guidance is only local execution choreography",
                "the rule is still too vague to encode as repo policy safely",
            ],
            stronger_home="config plus checks when verification is needed",
        ),
        _standing_intent_class_payload(
            intent_class="repo_doctrine",
            summary="Broad repo doctrine or design constraints that explain how the repo should be run.",
            default_owner="AGENTS.md or docs/design-principles.md",
            authoritative_kind="doctrine",
            durable_when=[
                "the guidance is repo-wide rather than task-local",
                "the guidance should remain legible as shared doctrine rather than a toggle",
            ],
            transient_when=[
                "the guidance only matters for the current active slice",
                "the better owner is actually config, Memory, or checks",
            ],
            stronger_home="config policy or enforceable workflow when prose becomes too weak",
        ),
        _standing_intent_class_payload(
            intent_class="durable_understanding",
            summary="Repo-specific interpretive understanding that lowers rediscovery cost without becoming hard policy.",
            default_owner="Memory",
            authoritative_kind="interpretive-understanding",
            durable_when=[
                "future work would pay rediscovery cost without the note",
                "the content explains repo-specific understanding rather than a hard rule",
            ],
            transient_when=[
                "a canonical doc or stronger owner now explains it better",
                "the note is only a local convenience or stale residue",
            ],
            stronger_home="canonical docs, config, or checks when the understanding becomes shared rule rather than interpretation",
        ),
        _standing_intent_class_payload(
            intent_class="active_directional_intent",
            summary="Bounded current direction that should steer work now without being mistaken for timeless doctrine.",
            default_owner=".agentic-workspace/planning/state.toml or .agentic-workspace/planning/execplans/",
            authoritative_kind="active-direction",
            durable_when=[
                "the direction still matters after the immediate chat turn",
                "the repo needs a bounded active owner surface for continuation",
            ],
            transient_when=[
                "the direction ends with the current local step",
                "the work has already been completed or archived",
            ],
            stronger_home="doctrine, policy, or checks only after the direction stops being lane-local",
        ),
        _standing_intent_class_payload(
            intent_class="enforceable_workflow",
            summary="Guidance that should be verified through checks, validation commands, or workflow tooling instead of prose alone.",
            default_owner="scripts/check/, validation workflows, or config plus checks",
            authoritative_kind="enforceable",
            durable_when=[
                "the guidance should be verifiable rather than merely remembered",
                "drift should be detectable through checks or validation",
            ],
            transient_when=[
                "the guidance is still exploratory and not ready for enforcement",
                "prose remains the strongest justified home for now",
            ],
            stronger_home="checks or validation workflows with doctrine left as explanation only",
        ),
        _standing_intent_class_payload(
            intent_class="temporary_local_guidance",
            summary="Useful local guidance that should stay transient unless repetition proves broader durable value.",
            default_owner="current execution context only",
            authoritative_kind="temporary",
            durable_when=[
                "none by default; promote only after repeated reminder cost or broader impact appears",
            ],
            transient_when=[
                "the guidance ends with the current bounded step",
                "the guidance is tool- or model-specific convenience only",
            ],
            stronger_home="reclassify into one of the durable standing-intent classes when warranted",
        ),
    ]

    effective_items = [
        _config_policy_effective_item(config_policy=config_policy),
        _repo_doctrine_effective_item(target_root=target_root),
        _durable_understanding_effective_item(memory_installed=memory_installed),
        _active_directional_intent_effective_item(active_planning=active_planning),
        _enforceable_workflow_effective_item(target_root=target_root),
    ]
    in_force_count = sum(1 for item in effective_items if item["status"] == "present")
    return {
        "canonical_doc": STANDING_INTENT_CANONICAL_DOC,
        "schema_version": "standing-intent-report/v1",
        "promotion_rule": ("Promote durable repo-wide guidance into the strongest existing owner surface instead of leaving it in chat."),
        "precedence_order": _standing_intent_precedence_order(),
        "supersession_rules": _standing_intent_supersession_rules(),
        "stronger_home_model": _standing_intent_stronger_home_model(
            target_root=target_root,
            config_policy=config_policy,
        ),
        "classes": classes,
        "effective_view": {
            "conflict_rule": (
                "Explicit current human instruction outranks all durable standing intent. Within durable repo state, "
                "active lane-local direction may narrow broader doctrine for the current slice, but checked-in policy "
                "and enforceable workflow still outrank broader interpretive guidance."
            ),
            "sources_considered": [
                ".agentic-workspace/config.toml",
                "AGENTS.md",
                "docs/design-principles.md",
                ".agentic-workspace/planning/state.toml and .agentic-workspace/planning/execplans/",
                "Memory report/install state",
                "scripts/check/",
            ],
            "in_force_count": in_force_count,
            "items": effective_items,
        },
    }


def setup_discovery_payload(
    *,
    target_root: Path,
    status_payload: dict[str, Any],
    active_todo_surface: str | None,
) -> dict[str, list[dict[str, Any]]]:
    memory_candidates: list[dict[str, Any]] = []
    planning_candidates: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def _add_candidate(
        bucket: list[dict[str, Any]],
        *,
        surface: str,
        reason: str,
        confidence: float,
        refs: list[str],
    ) -> None:
        key = (surface, reason)
        if key in seen:
            return
        seen.add(key)
        bucket.append(
            {
                "surface": surface,
                "reason": reason,
                "confidence": confidence,
                "refs": refs,
            }
        )

    for surface, reason, confidence, refs in (
        (
            "docs/delegated-judgment-contract.md",
            "bounded human/agent decision boundaries",
            0.94,
            ["docs/delegated-judgment-contract.md"],
        ),
        (
            "docs/resumable-execution-contract.md",
            "restart and continuation boundaries",
            0.91,
            ["docs/resumable-execution-contract.md"],
        ),
        (
            ".agentic-workspace/docs/capability-aware-execution.md",
            "task-shape and capability-fit rules",
            0.89,
            [".agentic-workspace/docs/capability-aware-execution.md"],
        ),
        (
            "docs/execution-summary-contract.md",
            "compact execution outcome and follow-through shape",
            0.87,
            ["docs/execution-summary-contract.md"],
        ),
    ):
        if (target_root / surface).exists():
            _add_candidate(memory_candidates, surface=surface, reason=reason, confidence=confidence, refs=refs)

    if (target_root / ".agentic-workspace" / "planning" / "state.toml").exists():
        _add_candidate(
            planning_candidates,
            surface=".agentic-workspace/planning/state.toml",
            reason="active queue carries the current work slice",
            confidence=0.94,
            refs=[".agentic-workspace/planning/state.toml"],
        )
    if (
        active_todo_surface
        and active_todo_surface != ".agentic-workspace/planning/state.toml"
        and (target_root / active_todo_surface).exists()
    ):
        _add_candidate(
            planning_candidates,
            surface=active_todo_surface,
            reason="active execplan carries the current bounded work slice",
            confidence=0.96,
            refs=[active_todo_surface, ".agentic-workspace/planning/state.toml"],
        )

    pass  # ROADMAP.md is now consolidated in state.toml
    if False:
        _add_candidate(
            ambiguous,
            surface=".agentic-workspace/planning/process.md",
            reason="long-horizon follow-ons should not be seeded without promotion",
            confidence=0.82,
            refs=[".agentic-workspace/planning/process.md"],
        )

    for warning in status_payload.get("warnings", []):
        if isinstance(warning, dict):
            surface = str(warning.get("path") or "workspace")
            message = str(warning.get("message") or "requires review")
        else:
            surface = "workspace"
            message = str(warning)
        _add_candidate(
            ambiguous,
            surface=surface,
            reason=message,
            confidence=0.5,
            refs=[surface],
        )

    return {
        "memory_candidates": memory_candidates,
        "planning_candidates": planning_candidates,
        "ambiguous": ambiguous,
    }


def _standing_intent_class_payload(
    *,
    intent_class: str,
    summary: str,
    default_owner: str,
    authoritative_kind: str,
    durable_when: list[str],
    transient_when: list[str],
    stronger_home: str,
) -> dict[str, Any]:
    return {
        "class": intent_class,
        "summary": summary,
        "default_owner": default_owner,
        "authoritative_kind": authoritative_kind,
        "durable_when": durable_when,
        "transient_when": transient_when,
        "stronger_home": stronger_home,
    }


def _standing_intent_precedence_order() -> list[dict[str, Any]]:
    return [
        {
            "rank": 1,
            "source": "explicit_current_human_instruction",
            "authority": "human-current-intent",
            "rule": "Current explicit user direction outranks durable standing intent when they conflict.",
        },
        {
            "rank": 2,
            "source": "active_directional_intent",
            "authority": "current-lane-direction",
            "rule": "Active planning direction governs the current bounded slice unless it conflicts with checked-in hard policy.",
        },
        {
            "rank": 3,
            "source": "config_policy",
            "authority": "checked-in-policy",
            "rule": "Checked-in config policy outranks broader doctrine and interpretive understanding.",
        },
        {
            "rank": 4,
            "source": "enforceable_workflow",
            "authority": "verified-workflow",
            "rule": "Checks and validation rules enforce standing guidance once the repo chooses verification over prose-only handling.",
        },
        {
            "rank": 5,
            "source": "repo_doctrine",
            "authority": "standing-doctrine",
            "rule": "Broad doctrine guides normal work unless a higher-precedence surface narrows or replaces it.",
        },
        {
            "rank": 6,
            "source": "durable_understanding",
            "authority": "interpretive-understanding",
            "rule": "Memory and similar durable understanding inform interpretation but should not override clearer policy or doctrine.",
        },
        {
            "rank": 7,
            "source": "superseded_residue",
            "authority": "historical-only",
            "rule": "Older superseded residue may remain as explanation or archive context but should not govern current work.",
        },
    ]


def _standing_intent_supersession_rules() -> list[dict[str, Any]]:
    return [
        {
            "rule": "newer_same_owner_replaces_older",
            "summary": (
                "When two standing instructions live in the same owner surface for the same concern, "
                "the newer or more specific checked-in instruction replaces the older one."
            ),
        },
        {
            "rule": "stronger_home_replaces_weaker_for_same_concern",
            "summary": (
                "When the same concern moves from doctrine or understanding into config or enforceable "
                "workflow, the stronger home becomes authoritative and the older prose becomes "
                "explanatory or should shrink."
            ),
        },
        {
            "rule": "active_lane_direction_is_slice_scoped",
            "summary": (
                "Active directional intent may narrow broader doctrine for the current slice, but it "
                "should not silently rewrite repo-wide policy beyond that slice."
            ),
        },
        {
            "rule": "superseded_residue_should_stop_governing",
            "summary": (
                "Archived or explicitly superseded residue may remain for history, but reporting should "
                "treat it as non-authoritative once a clearer current owner exists."
            ),
        },
    ]


def _standing_intent_stronger_home_model(*, target_root: Path, config_policy: dict[str, Any]) -> dict[str, Any]:
    examples: list[dict[str, Any]] = []
    if str(config_policy.get("improvement_latitude_source")) == "repo-config":
        examples.append(
            {
                "concern": "repo-friction improvement posture",
                "from_class": "repo_doctrine",
                "to_class": "config_policy",
                "current_owner": ".agentic-workspace/config.toml",
                "status": "already-promoted",
                "why": "The repo's standing cleanup posture is now machine-readable policy instead of prose-only preference.",
                "refs": [".agentic-workspace/config.toml", ".agentic-workspace/docs/standing-intent-contract.md"],
            }
        )
    if str(config_policy.get("optimization_bias_source")) == "repo-config":
        examples.append(
            {
                "concern": "output and residue preference",
                "from_class": "repo_doctrine",
                "to_class": "config_policy",
                "current_owner": ".agentic-workspace/config.toml",
                "status": "already-promoted",
                "why": (
                    "The repo's reporting and residue preference is enforced through config-backed "
                    "defaults rather than reminder text alone."
                ),
                "refs": [".agentic-workspace/config.toml", ".agentic-workspace/docs/reporting-contract.md"],
            }
        )
    for concern, path, refs in (
        (
            "planning surface integrity",
            "scripts/check/check_planning_surfaces.py",
            ["scripts/check/check_planning_surfaces.py", ".agentic-workspace/docs/standing-intent-contract.md"],
        ),
        (
            "source/payload/root-install boundary drift",
            "scripts/check/check_source_payload_operational_install.py",
            ["scripts/check/check_source_payload_operational_install.py", "docs/maintainer/source-payload-operational-install.md"],
        ),
    ):
        if (target_root / path).exists():
            examples.append(
                {
                    "concern": concern,
                    "from_class": "repo_doctrine",
                    "to_class": "enforceable_workflow",
                    "current_owner": path,
                    "status": "already-promoted",
                    "why": "This standing guidance is now detectable through a check instead of relying on prose alone.",
                    "refs": refs,
                }
            )

    return {
        "decision_test": {
            "promote_to_config_when": [
                "the standing guidance should be machine-readable and survive startup without rereading prose",
                "the repo needs a stable selectable default or policy mode rather than free-form explanation",
                "the concern changes repo-wide defaults more than it changes one local workflow",
            ],
            "promote_to_enforceable_workflow_when": [
                "drift should be detectable rather than merely remembered",
                "the repo needs repeatable validation or a failing/warning check for the concern",
                "a check, validation command, or workflow can verify the rule without building a generic automation system",
            ],
            "keep_as_doctrine_when": [
                "the guidance is still broad philosophy or boundary explanation rather than a stable toggle",
                "the stronger home would overfit or overspecify the current doctrine",
                "human legibility still matters more than machine-readable enforcement for the concern",
            ],
        },
        "candidate_classes": [
            {
                "class": "repo_doctrine",
                "preferred_stronger_homes": ["config_policy", "enforceable_workflow"],
                "rule": "Promote doctrine when the concern becomes a stable repo-wide default or a rule that should be verified.",
            },
            {
                "class": "active_directional_intent",
                "preferred_stronger_homes": ["repo_doctrine", "config_policy", "enforceable_workflow"],
                "rule": "Promote only after the direction stops being lane-local and survives beyond the current slice.",
            },
            {
                "class": "durable_understanding",
                "preferred_stronger_homes": ["repo_doctrine", "config_policy", "enforceable_workflow"],
                "rule": "Promote when the understanding has become shared rule or verifiable behavior rather than interpretive context.",
            },
        ],
        "examples": examples,
    }


def _config_policy_effective_item(*, config_policy: dict[str, Any]) -> dict[str, Any]:
    policy_items = [
        {
            "key": key,
            "value": value,
            "source": source,
        }
        for key, value, source in (
            (
                "improvement_latitude",
                str(config_policy["improvement_latitude"]),
                str(config_policy["improvement_latitude_source"]),
            ),
            (
                "optimization_bias",
                str(config_policy["optimization_bias"]),
                str(config_policy["optimization_bias_source"]),
            ),
            (
                "workflow_artifact_profile",
                str(config_policy["workflow_artifact_profile"]),
                str(config_policy["workflow_artifact_profile_source"]),
            ),
        )
    ]
    repo_owned_items = [item for item in policy_items if item["source"] == "repo-config"]
    status = "present" if repo_owned_items else "default-only"
    summary = "Workspace config carries stable repo policy currently in force."
    if status == "default-only":
        summary = "No repo-owned standing config policy is set yet; only product defaults are in force."
    return {
        "class": "config_policy",
        "status": status,
        "authority": "authoritative-policy",
        "owner_surface": ".agentic-workspace/config.toml",
        "summary": summary,
        "items": policy_items,
    }


def _repo_doctrine_effective_item(*, target_root: Path) -> dict[str, Any]:
    refs = [path for path in ("AGENTS.md", "docs/design-principles.md") if (target_root / path).exists()]
    status = "present" if refs else "absent"
    summary = "Repo-owned startup guidance and design doctrine carry standing explanatory intent."
    if status == "absent":
        summary = "No canonical repo-doctrine surface was found."
    return {
        "class": "repo_doctrine",
        "status": status,
        "authority": "authoritative-doctrine",
        "owner_surface": refs[0] if refs else "docs/design-principles.md",
        "summary": summary,
        "refs": refs,
    }


def _durable_understanding_effective_item(*, memory_installed: bool) -> dict[str, Any]:
    return {
        "class": "durable_understanding",
        "status": "present" if memory_installed else "absent",
        "authority": "interpretive-understanding",
        "owner_surface": ".agentic-workspace/memory/repo/",
        "summary": (
            "Memory remains the durable-understanding home for repo-specific interpretive knowledge."
            if memory_installed
            else "Memory is not installed, so durable-understanding guidance has no dedicated owner surface yet."
        ),
        "refs": (
            [
                ".agentic-workspace/memory/repo/",
                "agentic-workspace memory report --target ./repo --format json",
            ]
            if memory_installed
            else []
        ),
    }


def _active_directional_intent_effective_item(*, active_planning: dict[str, Any] | None) -> dict[str, Any]:
    if not active_planning:
        return {
            "class": "active_directional_intent",
            "status": "absent",
            "authority": "active-direction",
            "owner_surface": ".agentic-workspace/planning/state.toml",
            "summary": "No active planning slice is in force right now.",
            "refs": [".agentic-workspace/planning/state.toml", ".agentic-workspace/planning/execplans/"],
        }
    refs = [ref for ref in active_planning.get("refs", []) if isinstance(ref, str) and ref]
    return {
        "class": "active_directional_intent",
        "status": "present",
        "authority": "active-direction",
        "owner_surface": str(active_planning.get("owner_surface") or ".agentic-workspace/planning/state.toml"),
        "summary": str(active_planning.get("summary") or "Active planning carries the current bounded direction."),
        "requested_outcome": str(active_planning.get("requested_outcome") or ""),
        "refs": refs,
    }


def _enforceable_workflow_effective_item(*, target_root: Path) -> dict[str, Any]:
    refs = [
        path
        for path in (
            "scripts/check/check_planning_surfaces.py",
            "scripts/check/check_source_payload_operational_install.py",
        )
        if (target_root / path).exists()
    ]
    status = "present" if refs else "absent"
    summary = "Checks and validation scripts provide enforceable workflow homes for standing guidance."
    if status == "absent":
        summary = "No enforceable workflow surface was found."
    return {
        "class": "enforceable_workflow",
        "status": status,
        "authority": "enforceable",
        "owner_surface": refs[0] if refs else "scripts/check/",
        "summary": summary,
        "refs": refs,
    }


def repo_friction_payload(
    *,
    target_root: Path,
    improvement_latitude: str,
    improvement_latitude_source: str,
    policy_payload: dict[str, Any],
    boundary_test_payload: dict[str, Any],
    external_setup_findings_payload: dict[str, Any] | None,
    incidental_finding_policy: dict[str, Any] | None = None,
    validation_friction_policy: dict[str, Any] | None = None,
    cli_invoke: str = DEFAULT_CLI_INVOKE,
) -> dict[str, Any]:
    hotspots = _repo_friction_hotspots(target_root=target_root, cli_invoke=cli_invoke)
    regenerable_cache_hotspots = _repo_friction_regenerable_cache_hotspots(target_root=target_root, cli_invoke=cli_invoke)
    large_file_hotspots = [item.copy() for item in hotspots if int(item["line_count"]) >= REPO_FRICTION_LARGE_FILE_THRESHOLD][
        :REPO_FRICTION_MAX_HOTSPOTS
    ]
    concept_hotspots = [item.copy() for item in hotspots if item["kind"] in {"docs", "config"}][:REPO_FRICTION_MAX_HOTSPOTS]
    external_evidence: list[dict[str, Any]] = []
    external_codebase_map = _repo_friction_external_codebase_map_payload(target_root=target_root)
    if external_codebase_map is not None:
        external_evidence.append(external_codebase_map)
    if external_setup_findings_payload is not None:
        external_evidence.append(external_setup_findings_payload)
    evidence_classes = ["large_file_hotspots", "concept_surface_hotspots", "planning_friction", "validation_friction"]
    if external_evidence:
        evidence_classes.append("external_evidence")
    return {
        "owner_surface": "workspace",
        "owner_rule": (
            "Repo-friction policy and evidence stay workspace-level shared surfaces unless a future "
            "independent lifecycle justifies a new module."
        ),
        "policy_mode": improvement_latitude,
        "policy_source": improvement_latitude_source,
        "policy_target": "repo-directed-improvement",
        "scan_budget": {
            "status": "bounded",
            "max_files": REPO_FRICTION_MAX_SCAN_FILES,
            "sample_rule": "Repo-friction report samples are capped for ordinary chat-agent inspection; use focused path-specific tools for deeper review.",
        },
        "policy_target_rule": (
            "The improvement-latitude mode governs repo-directed initiative; bounded workspace-self-adaptation "
            "inside Agentic Workspace-owned surfaces remains allowed under every mode."
        ),
        "workspace_self_adaptation": {
            "status": "allowed-with-bounds",
            "bounded_by": ["correctness", "ownership", "proof", "portability"],
        },
        "friction_response_order": [
            {
                "step": 1,
                "action": "adapt-inside-workspace-first",
            },
            {
                "step": 2,
                "action": "promote-repo-directed-improvement-when-external",
            },
            {
                "step": 3,
                "action": "avoid-externalizing-honestly-absorbable-friction",
            },
        ],
        "memory_capture_options": {
            "kind": "agentic-workspace/dogfooding-memory-capture-options/v1",
            "status": "available",
            "rule": "Use Memory for repeated AW friction that should shape future agent behavior but does not yet need a standalone issue.",
            "quiet_when": "no concrete repeated friction, proof, routing, restart, handoff, or validation signal was observed",
            "options": [
                {
                    "id": "capture-memory",
                    "allowed": True,
                    "command": (
                        f"{cli_invoke} memory capture-note --slug <slug> --summary "
                        '"AW dogfooding finding: <evidence-backed lesson>" --files <relevant paths> --format json'
                    ),
                    "why": "repeated dogfooding evidence should be available to future tasks without relying on chat recall",
                },
                {
                    "id": "create-issue",
                    "allowed": True,
                    "why": "use when the finding needs product work, prioritization, or review",
                },
                {
                    "id": "fix-directly",
                    "allowed": True,
                    "why": "use when the current bounded task already owns the AW surface and proof remains narrow",
                },
                {
                    "id": "report-only",
                    "allowed": True,
                    "why": "use when evidence is useful but not yet repeated enough for Memory or issue routing",
                },
            ],
        },
        "guardrail_test": {
            "adapt_when": [
                "workspace fit and contract clarity are the real friction source",
                "one bounded workspace change removes the friction without hiding repo-owned structural problems",
            ],
            "surface_repo_friction_when": [
                "the root problem is really repo seams, tranche boundaries, validation friction, or ownership",
                "the alternative would be accumulating narrow workspace compensations",
            ],
            "prefer": "one clear adaptation over accumulating many narrow special cases",
        },
        "repo_directed_improvement_threshold": {
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
        },
        "initiative_posture": policy_payload["initiative_posture"],
        "rule": policy_payload["reporting_rule"],
        "reporting_destinations": policy_payload["reporting_destinations"],
        "incidental_finding_policy": copy.deepcopy(incidental_finding_policy)
        if isinstance(incidental_finding_policy, dict)
        else {
            "status": "required-reporting",
            "rule": "Agents should report incidental improvement findings they encounter, even when they do not act on them immediately.",
        },
        "decision_test": boundary_test_payload,
        "evidence_classes": evidence_classes,
        "large_file_hotspots": {
            "threshold_lines": REPO_FRICTION_LARGE_FILE_THRESHOLD,
            "count": len(large_file_hotspots),
            "items": large_file_hotspots,
            "ignored_regenerable_cache_count": len(regenerable_cache_hotspots),
            "ignored_regenerable_caches": regenerable_cache_hotspots,
            "cache_rule": "Regenerable local cache files are context-size evidence, not repo-directed refactor candidates.",
        },
        "concept_surface_hotspots": {
            "threshold_lines": REPO_FRICTION_CONCEPT_SURFACE_THRESHOLD,
            "count": len(concept_hotspots),
            "items": concept_hotspots,
        },
        "planning_friction": {
            "status": "explicit-contract",
            "rule": (
                "Treat planning friction as repo-friction evidence only when the smallest safe slice, proof boundary, "
                "ownership boundary, or minimum read set stays unclear after the normal compact recovery path."
            ),
            "distinguish_from": [
                "ordinary task difficulty with otherwise clear seams",
                "one-off weak-model confusion",
                "broad refactor desire without bounded operational evidence",
            ],
            "subtypes": [
                "unclear_seam",
                "unclear_proof_boundary",
                "ownership_ambiguity",
                "chunking_instability",
                "reread_pressure",
            ],
            "reporting_destinations": [
                "repo_friction review output",
                "bounded planning residue when a follow-on slice is justified",
                "ordinary report output without implicit active work",
            ],
        },
        "validation_friction": copy.deepcopy(validation_friction_policy)
        if isinstance(validation_friction_policy, dict)
        else {
            "status": "explicit-contract",
            "rule": (
                "Treat validation friction as repo-friction evidence only when otherwise straightforward work keeps "
                "stalling at validation because repo seams, tranche boundaries, proof expectations, or rerun/re-entry "
                "paths stay unclear."
            ),
            "failure_classification": [
                {
                    "class": "user_or_content_error",
                    "route": "fix content or implementation directly unless the same shape failure keeps recurring",
                    "interface_design_signal": False,
                },
                {
                    "class": "environment_or_dependency_error",
                    "route": "repair setup or dependency guidance only when the failure repeats across environments",
                    "interface_design_signal": False,
                },
                {
                    "class": "interface_design_error",
                    "route": "promote to correct-by-design remediation such as scaffold, writer helper, alias, lifecycle command, command, or agent aid",
                    "interface_design_signal": True,
                },
                {
                    "class": "unclear_proof_contract",
                    "route": "tighten proof selection or recovery guidance before adding more validation prose",
                    "interface_design_signal": True,
                },
            ],
            "correct_by_design_remedy_order": [
                "scaffold",
                "writer_helper",
                "alias",
                "lifecycle_command",
                "command",
                "agent_aid",
                "validation",
                "docs",
            ],
            "repeated_failure_signal": (
                "Repeated interface-design or unclear-proof validation failures should produce an improvement signal "
                "with suspected_owner, likely_remediation, recurrence, and retention instead of only another repair note."
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
        },
        "external_evidence": external_evidence,
    }


def _repo_friction_kind_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt", ".text"}:
        return "docs"
    if suffix in {".toml", ".json", ".yaml", ".yml", ".ini", ".cfg"}:
        return "config"
    return "code"


def _repo_friction_surface_role(relative_path: str) -> str:
    if _repo_friction_is_regenerable_cache(relative_path):
        return "regenerable-local-cache"
    if relative_path in {
        "AGENTS.md",
        ".agentic-workspace/planning/state.toml",
        ".agentic-workspace/planning/process.md",
        ".agentic-workspace/config.toml",
    }:
        return "front-door"
    if relative_path.startswith(".agentic-workspace/planning/execplans/"):
        return "planning-state"
    if relative_path.startswith("docs/"):
        return "canonical-doc"
    if relative_path.startswith("tools/"):
        return "generated-maintainer-surface"
    if relative_path.startswith(".agentic-workspace/"):
        return "managed-surface"
    return "repo-surface"


def _repo_friction_is_regenerable_cache(relative_path: str) -> bool:
    return any(relative_path.startswith(prefix) for prefix in REPO_FRICTION_REGENERABLE_CACHE_PREFIXES)


def _repo_friction_context_strategy(*, relative_path: str, kind: str, surface_role: str) -> dict[str, Any]:
    if surface_role == "regenerable-local-cache":
        return {
            "classification": "ignore-or-refresh-cache",
            "suggested_action": "do-not-refactor",
            "context_strategy": "Do not open broadly; refresh or delete the local cache if stale.",
            "likely_remediation": "remove",
        }
    if relative_path.startswith("tests/") or "/tests/" in relative_path:
        return {
            "classification": "test-hotspot",
            "suggested_action": "split-focused-tests",
            "context_strategy": "Use test selectors and extract focused test modules before reading the whole file.",
            "likely_remediation": "tests",
            "recurrence": "human_confirmed",
            "owner_decision": {
                "status": "bounded-slice-required",
                "owner": "test owner for the reported path",
                "decision": "Split only a cohesive behavior cluster with a named selector; do not split test files from line count alone.",
                "next_slice_rule": "Promote a focused test split when a touched behavior cluster has a target file boundary and proof selector.",
                "retention": "shrink_after_fix",
            },
        }
    if relative_path == "generated/workspace/python/cli.py":
        return {
            "classification": "root-cli-runtime-hotspot",
            "suggested_action": "extract-runtime-or-renderer-helper",
            "context_strategy": "Inspect symbols first; move bounded runtime/rendering helpers behind existing contracts before broad edits.",
            "likely_remediation": "module_split",
            "recurrence": "human_confirmed",
            "owner_decision": {
                "status": "retained-with-rationale",
                "owner": "issue #627",
                "decision": (
                    "Keep the root CLI hotspot visible as a human-confirmed architecture-cost signal, but do not promote "
                    "a broad split from size alone."
                ),
                "next_slice_rule": (
                    "Promote only a bounded helper extraction when a touched command, renderer, or runtime primitive has "
                    "a named boundary and proof command."
                ),
                "retention": "keep_with_justification",
            },
        }
    if relative_path.endswith("/installer.py"):
        return {
            "classification": "module-installer-hotspot",
            "suggested_action": "extract-module-helper",
            "context_strategy": "Inspect the relevant function range and extract cohesive helpers only inside the owning package boundary.",
            "likely_remediation": "module_split",
            "recurrence": "human_confirmed",
            "owner_decision": {
                "status": "bounded-slice-required",
                "owner": "installer package owner for the reported path",
                "decision": (
                    "Use the installer hotspot as routing pressure for cohesive helper extraction inside the owning package, "
                    "not as permission for a broad installer rewrite."
                ),
                "next_slice_rule": "Promote a helper extraction only when the touched installer behavior has a named boundary and package proof command.",
                "retention": "shrink_after_fix",
            },
        }
    if kind == "docs":
        return {
            "classification": "concept-surface-hotspot",
            "suggested_action": "compress-or-route",
            "context_strategy": "Prefer compact selectors, summaries, or section routing before adding more prose.",
            "likely_remediation": "docs",
        }
    if kind == "config":
        return {
            "classification": "structured-surface-hotspot",
            "suggested_action": "query-or-schema-route",
            "context_strategy": "Use structured queries and schema-backed selectors instead of manual broad reads.",
            "likely_remediation": "validation",
            "recurrence": "human_confirmed",
            "owner_decision": {
                "status": "retained-with-rationale",
                "owner": "schema/check owner for the reported path",
                "decision": "Retain large structured artifacts when schema-backed selectors and freshness checks avoid broad manual reads.",
                "next_slice_rule": "Promote only if agents still need to inspect the full artifact after selectors and checks are used.",
                "retention": "keep_with_justification",
            },
        }
    return {
        "classification": "large-source-hotspot",
        "suggested_action": "inspect-symbols-before-refactor",
        "context_strategy": "Use search and focused symbols first; promote a bounded refactor only after repeated evidence.",
        "likely_remediation": "refactor",
    }


def _repo_friction_hotspot_payload(
    *, path: Path, target_root: Path, line_count: int, cli_invoke: str = DEFAULT_CLI_INVOKE
) -> dict[str, Any]:
    relative = path.relative_to(target_root).as_posix()
    kind = _repo_friction_kind_for_path(path)
    surface_role = _repo_friction_surface_role(relative)
    strategy = _repo_friction_context_strategy(relative_path=relative, kind=kind, surface_role=surface_role)
    primary_action = {
        "action": strategy["suggested_action"],
        "summary": strategy["context_strategy"],
        "command": str(
            _command_with_cli_invoke(
                command="agentic-workspace report --target ./repo --section repo_friction --format json",
                cli_invoke=cli_invoke,
            )
        ),
        "risk": "read-only routing unless a bounded refactor is explicitly promoted",
        "required_inputs": ["target path", "line count", "surface role", "repeated friction evidence"],
        "next_proof": "use proof selection after changed paths are known",
    }
    primary_action["run"] = primary_action["command"]
    return {
        "path": relative,
        "line_count": line_count,
        "kind": kind,
        "surface_role": surface_role,
        **strategy,
        "primary_next_action": primary_action,
    }


def _repo_friction_hotspots(*, target_root: Path, cli_invoke: str = DEFAULT_CLI_INVOKE) -> list[dict[str, Any]]:
    hotspots: list[dict[str, Any]] = []
    for path in repository_scan_files(
        target_root,
        include_untracked=True,
        include_managed_workspace=True,
        suffixes=REPO_FRICTION_SCAN_SUFFIXES,
        max_files=REPO_FRICTION_MAX_SCAN_FILES,
    ):
        try:
            line_count = sum(1 for _ in path.open("r", encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
        if line_count < REPO_FRICTION_CONCEPT_SURFACE_THRESHOLD:
            continue
        relative = path.relative_to(target_root).as_posix()
        if _repo_friction_is_regenerable_cache(relative):
            continue
        hotspots.append(_repo_friction_hotspot_payload(path=path, target_root=target_root, line_count=line_count, cli_invoke=cli_invoke))
    hotspots.sort(key=lambda item: (-int(item["line_count"]), str(item["path"])))
    return hotspots


def _repo_friction_regenerable_cache_hotspots(*, target_root: Path, cli_invoke: str = DEFAULT_CLI_INVOKE) -> list[dict[str, Any]]:
    hotspots: list[dict[str, Any]] = []
    for path in repository_scan_files(
        target_root,
        relative_roots=[prefix.rstrip("/") for prefix in REPO_FRICTION_REGENERABLE_CACHE_PREFIXES],
        include_untracked=True,
        include_managed_workspace=True,
        suffixes=REPO_FRICTION_SCAN_SUFFIXES,
        max_files=REPO_FRICTION_MAX_SCAN_FILES,
    ):
        try:
            line_count = sum(1 for _ in path.open("r", encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
        if line_count < REPO_FRICTION_LARGE_FILE_THRESHOLD:
            continue
        hotspots.append(_repo_friction_hotspot_payload(path=path, target_root=target_root, line_count=line_count, cli_invoke=cli_invoke))
    hotspots.sort(key=lambda item: (-int(item["line_count"]), str(item["path"])))
    return hotspots[:REPO_FRICTION_MAX_HOTSPOTS]


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _repo_friction_external_codebase_map_payload(*, target_root: Path) -> dict[str, Any] | None:
    path = target_root / "tools" / "codebase-map.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {
            "kind": "codebase-map",
            "path": "tools/codebase-map.json",
            "status": "unreadable",
            "items": [],
        }
    if not isinstance(payload, dict):
        return {
            "kind": "codebase-map",
            "path": "tools/codebase-map.json",
            "status": "unsupported-shape",
            "items": [],
        }

    candidate_lists: list[Any] = []
    for key in ("large_modules", "hotspots", "modules"):
        value = payload.get(key)
        if isinstance(value, list):
            candidate_lists.append(value)

    items: list[dict[str, Any]] = []
    for candidate_list in candidate_lists:
        for entry in candidate_list:
            if not isinstance(entry, dict):
                continue
            path_value = entry.get("path") or entry.get("module") or entry.get("name")
            if not isinstance(path_value, str) or not path_value.strip():
                continue
            line_count = _int_or_none(entry.get("line_count"))
            if line_count is None:
                line_count = _int_or_none(entry.get("lines"))
            normalized: dict[str, Any] = {
                "path": path_value.strip().replace("\\", "/"),
                "line_count": line_count,
            }
            function_count = _int_or_none(entry.get("function_count"))
            if function_count is None:
                function_count = _int_or_none(entry.get("functions"))
            if function_count is not None:
                normalized["function_count"] = function_count
            class_count = _int_or_none(entry.get("class_count"))
            if class_count is None:
                class_count = _int_or_none(entry.get("classes"))
            if class_count is not None:
                normalized["class_count"] = class_count
            items.append(normalized)

    items.sort(
        key=lambda item: (
            -(item["line_count"] if isinstance(item.get("line_count"), int) else -1),
            str(item["path"]),
        )
    )
    return {
        "kind": "codebase-map",
        "path": "tools/codebase-map.json",
        "status": "loaded",
        "items": items[:REPO_FRICTION_MAX_HOTSPOTS],
    }
