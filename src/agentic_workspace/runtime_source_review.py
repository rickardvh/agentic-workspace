"""Runtime-source review helpers for generated-CLI-adjacent workspace code."""

from __future__ import annotations

from typing import Any

from agentic_workspace.contract_tooling import python_runtime_projection_inventory_manifest

GENERATED_CLI_RUNTIME_SOURCE_EDIT_PATHS = {
    "src/agentic_workspace/workspace_runtime_primitives.py",
    "packages/planning/src/repo_planning_bootstrap/installer.py",
    "packages/planning/src/repo_planning_bootstrap/runtime_projection.py",
    "packages/memory/src/repo_memory_bootstrap/installer.py",
    "packages/memory/src/repo_memory_bootstrap/runtime_search.py",
    "packages/memory/src/repo_memory_bootstrap/runtime_primitives.py",
    "packages/verification/src/repo_verification_bootstrap/runtime_primitives.py",
}

GENERATED_CLI_RUNTIME_SOURCE_MODULE_PATHS = {
    "agentic_workspace.workspace_runtime_primitives": "src/agentic_workspace/workspace_runtime_primitives.py",
    "repo_planning_bootstrap.installer": "packages/planning/src/repo_planning_bootstrap/installer.py",
    "repo_planning_bootstrap.runtime_projection": "packages/planning/src/repo_planning_bootstrap/runtime_projection.py",
    "repo_memory_bootstrap.installer": "packages/memory/src/repo_memory_bootstrap/installer.py",
    "repo_memory_bootstrap.runtime_search": "packages/memory/src/repo_memory_bootstrap/runtime_search.py",
    "repo_memory_bootstrap.runtime_primitives": "packages/memory/src/repo_memory_bootstrap/runtime_primitives.py",
    "repo_verification_bootstrap.runtime_primitives": "packages/verification/src/repo_verification_bootstrap/runtime_primitives.py",
}


def _list_payload(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _authority_boundary_payload(
    *,
    surface: str,
    observed_by_aw: list[str] | None = None,
    recommended_by_aw: list[str] | None = None,
    agent_owned_decisions: list[str] | None = None,
    rule: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "kind": "agentic-workspace/authority-boundary/v1",
        "surface": surface,
        "authority_class": "advisory-support",
    }
    if observed_by_aw:
        payload["observed_by_aw"] = observed_by_aw
    if recommended_by_aw:
        payload["recommended_by_aw"] = recommended_by_aw
    if agent_owned_decisions:
        payload["agent_owned_decisions"] = agent_owned_decisions
    if rule:
        payload["rule"] = rule
    return payload


def tiny_generated_cli_freshness_payload(value: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "kind": value.get("kind", "agentic-workspace/generated-cli-freshness/v1"),
        "status": value.get("status", "unknown"),
        "obligation": value.get("obligation", value.get("status", "unknown")),
        "freshness_check_command": value.get("freshness_check_command", ""),
        "refresh_command": value.get("refresh_command", ""),
        "validation_command": value.get("validation_command", ""),
    }
    parity = value.get("generated_target_parity")
    if isinstance(parity, dict):
        payload["generated_target_parity"] = {
            "status": parity.get("status", "unknown"),
            "target_families": parity.get("target_families", []),
            "claim_rule": parity.get("claim_rule", ""),
        }
    return payload


def tiny_runtime_source_edit_review_payload(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    review_items = []
    for item in _list_payload(value.get("review_items"))[:3]:
        if not isinstance(item, dict):
            continue
        symbols = []
        for symbol in _list_payload(item.get("accepted_runtime_symbols"))[:5]:
            if not isinstance(symbol, dict):
                continue
            symbols.append(
                {
                    "source_module": symbol.get("source_module", ""),
                    "source_symbol": symbol.get("source_symbol", ""),
                    "owner": symbol.get("owner", ""),
                    "operation_ids": symbol.get("operation_ids", []),
                    "primitive_refs": symbol.get("primitive_refs", []),
                    "conformance_ref": symbol.get("conformance_ref", ""),
                    "direct_edit_reasons_allowed": symbol.get("direct_edit_reasons_allowed", []),
                }
            )
        review_items.append(
            {
                "changed_path": item.get("changed_path", ""),
                "status": item.get("status", "unknown"),
                "accepted_runtime_symbol_count": item.get("accepted_runtime_symbol_count", 0),
                "sample_accepted_runtime_symbols": symbols,
                "required_evidence": item.get("required_evidence", []),
            }
        )
    payload = {
        key: value.get(key)
        for key in (
            "kind",
            "status",
            "changed_paths",
            "inventory_source",
            "missing_inventory_paths",
            "accepted_direct_edit_reasons",
            "rejected_vague_reasons",
            "completion_claim_rule",
        )
        if key in value
    }
    if review_items:
        payload["review_items"] = review_items
    return payload


def runtime_source_inventory_entries_for_path(changed_path: str) -> list[dict[str, Any]]:
    try:
        inventory = python_runtime_projection_inventory_manifest()
    except Exception:
        return []
    accepted = inventory.get("accepted_runtime_boundaries", {})
    entries = accepted.get("entries", []) if isinstance(accepted, dict) else []
    if not isinstance(entries, list):
        return []
    matched: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        source_module = str(entry.get("source_module", "")).strip()
        if GENERATED_CLI_RUNTIME_SOURCE_MODULE_PATHS.get(source_module) != changed_path:
            continue
        matched.append(
            {
                "binding_kind": str(entry.get("binding_kind", "")),
                "source_module": source_module,
                "source_symbol": str(entry.get("source_symbol", "")),
                "owner": str(entry.get("owner_package", "")),
                "operation_ids": _list_payload(entry.get("operation_ids")),
                "primitive_refs": _list_payload(entry.get("primitive_refs")),
                "conformance_ref": str(entry.get("conformance_ref", "")),
                "runtime_boundary_class": str(entry.get("runtime_boundary_class", "")),
                "minimization_route": str(entry.get("minimization_route", "")),
                "minimization_owner": str(entry.get("minimization_owner", "")),
                "minimization_tracking_issue": str(entry.get("minimization_tracking_issue", "")),
                "direct_edit_reasons_allowed": _list_payload(entry.get("direct_edit_reasons_allowed")),
                "stale_when": str(entry.get("stale_when", "")),
            }
        )
    return sorted(matched, key=lambda item: (str(item["source_module"]), str(item["source_symbol"])))


def runtime_source_edit_review_for_changed_paths(changed_paths: list[str]) -> dict[str, Any]:
    runtime_paths = [path for path in changed_paths if path in GENERATED_CLI_RUNTIME_SOURCE_EDIT_PATHS]
    if not runtime_paths:
        return {"kind": "agentic-workspace/runtime-source-edit-review/v1", "status": "not-applicable", "changed_paths": []}
    inventory_by_path = {path: runtime_source_inventory_entries_for_path(path) for path in runtime_paths}
    review_items = [
        {
            "changed_path": path,
            "status": "inventory-backed" if inventory_by_path[path] else "inventory-missing",
            "accepted_runtime_symbols": inventory_by_path[path],
            "accepted_runtime_symbol_count": len(inventory_by_path[path]),
            "required_evidence": [
                "edit_reason",
                "owner",
                "source_symbol_or_primitive",
                "proof",
                "whether command-generation or AW owns the next change",
            ],
        }
        for path in runtime_paths
    ]
    missing_inventory = [item["changed_path"] for item in review_items if item["status"] == "inventory-missing"]
    status = "blocked-missing-inventory" if missing_inventory else "classification-required"
    return {
        "kind": "agentic-workspace/runtime-source-edit-review/v1",
        "status": status,
        "changed_paths": runtime_paths,
        "review_items": review_items,
        "inventory_source": "src/agentic_workspace/contracts/python_runtime_projection_inventory.json",
        "missing_inventory_paths": missing_inventory,
        "accepted_direct_edit_reasons": [
            "existing-primitive-bugfix",
            "new-primitive-implementation",
        ],
        "suspect_reasons": [
            "generated-command-behavior",
            "interface-behavior-change",
        ],
        "rejected_vague_reasons": [
            "package-domain boundary",
            "runtime code changed",
            "implementation detail",
        ],
        "required_evidence": [
            "changed_path",
            "edit_reason",
            "owner",
            "source_symbol_or_primitive",
            "proof",
            "whether command-generation or AW owns the next change",
        ],
        "review_template": {
            "changed_path": "<runtime source path>",
            "edit_reason": "existing-primitive-bugfix|new-primitive-implementation|generated-command-behavior|interface-behavior-change",
            "owner": "AW primitive implementation|command-generation|deferred issue",
            "source_symbol_or_primitive": "<function, primitive id, or operation id>",
            "proof": "<focused test/check proving the boundary>",
            "residual_risk": "<none or explicit follow-up>",
        },
        "completion_claim_rule": (
            "Do not claim generated-CLI boundary satisfaction from a runtime source edit until the final report states the edit reason, "
            "owner, inventory-backed symbol/primitive, proof, and residual risk."
        ),
        "authority_boundary": _authority_boundary_payload(
            surface="runtime_source_edit_review",
            observed_by_aw=["changed runtime source path", "python_runtime_projection_inventory accepted runtime boundary entries"],
            recommended_by_aw=[
                "classify direct runtime edit before closeout",
                "use exact symbol inventory instead of whole-file boundary wording",
            ],
            agent_owned_decisions=["edit reason", "owner judgment", "whether the change belongs in command-generation"],
            rule="AW reports runtime-source edit evidence and required proof; the agent owns the semantic classification.",
        ),
        "rule": "Vague package-domain boundary wording is insufficient for generated-CLI-adjacent runtime source edits.",
    }
