"""Runtime-source review helpers for generated-CLI-adjacent workspace code."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path
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

MIRRORED_RUNTIME_PAYLOAD_HELPER_PAIRS = [
    {
        "id": "workspace-runtime-core-primitives-payload-helpers",
        "paths": [
            "src/agentic_workspace/workspace_runtime_core.py",
            "src/agentic_workspace/workspace_runtime_primitives.py",
        ],
        "why": (
            "workspace runtime payload/helper behavior is currently mirrored between the hand-owned core surface "
            "and the generated-CLI primitive runtime surface"
        ),
        "smallest_parity_proof_command": (
            'uv run pytest tests/test_workspace_summary_cli.py -q -k "external_intent_refresh_applies_stale_candidate_reconciliation"'
        ),
        "maintainer_check_command": (
            "uv run python scripts/check/check_generated_command_packages.py --aw-primitive-ownership --format json"
        ),
        "represented_regression": (
            "#1802-style startup path passed while external-intent refresh used the unsynced primitives runtime path"
        ),
        "regions": [
            {
                "id": "external-issue-intake-helper-region",
                "kind": "declared-region",
                "anchors_by_path": {
                    "src/agentic_workspace/workspace_runtime_core.py": {
                        "start_symbol": "_planning_candidate_suggestions_from_external_items",
                        "end_symbol": "_stale_planning_candidate_reconciliation",
                    },
                    "src/agentic_workspace/workspace_runtime_primitives.py": {
                        "start_symbol": "_planning_candidate_suggestions_from_external_items",
                        "end_symbol": "_stale_planning_candidate_reconciliation",
                    },
                },
            },
            {
                "id": "external-intent-refresh-payload",
                "kind": "declared-symbol",
                "symbols_by_path": {
                    "src/agentic_workspace/workspace_runtime_core.py": ["_refresh_github_external_intent_evidence"],
                    "src/agentic_workspace/workspace_runtime_primitives.py": ["_refresh_github_external_intent_evidence"],
                },
            },
            {
                "id": "open-issue-intake-payload",
                "kind": "declared-symbol",
                "symbols_by_path": {
                    "src/agentic_workspace/workspace_runtime_core.py": ["_open_issue_intake_payload"],
                    "src/agentic_workspace/workspace_runtime_primitives.py": ["_open_issue_intake_payload"],
                },
            },
        ],
    }
]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _changed_line_ranges_from_git_diff(*, target_root: Path | None, path: str) -> list[tuple[int, int]]:
    if target_root is None:
        return []
    try:
        command = ["git", "-C", str(target_root), "diff", "--unified=0", "--", path]
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    ranges: list[tuple[int, int]] = []
    hunk_pattern = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
    for line in result.stdout.splitlines():
        match = hunk_pattern.match(line)
        if not match:
            continue
        start = int(match.group(1))
        length = int(match.group(2) or "1")
        if length == 0:
            ranges.append((start, start))
        else:
            ranges.append((start, start + length - 1))
    return ranges


def _python_symbol_spans(*, target_root: Path | None, path: str) -> dict[str, tuple[int, int]]:
    if target_root is None:
        return {}
    source_path = target_root / path
    try:
        module = ast.parse(source_path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return {}
    spans: dict[str, tuple[int, int]] = {}
    for node in ast.walk(module):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            continue
        end_lineno = getattr(node, "end_lineno", node.lineno)
        spans[node.name] = (node.lineno, int(end_lineno))
    return spans


def _ranges_intersect(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] <= right[1] and right[0] <= left[1]


def _region_spans_for_path(*, target_root: Path | None, region: dict[str, Any], path: str) -> list[dict[str, Any]]:
    spans = _python_symbol_spans(target_root=target_root, path=path)
    resolved: list[dict[str, Any]] = []
    symbols_by_path = region.get("symbols_by_path")
    if isinstance(symbols_by_path, dict):
        for symbol in _list_payload(symbols_by_path.get(path)):
            symbol_name = str(symbol).strip()
            if symbol_name in spans:
                resolved.append(
                    {
                        "kind": "declared-symbol",
                        "symbol": symbol_name,
                        "span": spans[symbol_name],
                    }
                )
    anchors_by_path = region.get("anchors_by_path")
    anchors = anchors_by_path.get(path) if isinstance(anchors_by_path, dict) else None
    if isinstance(anchors, dict):
        start_symbol = str(anchors.get("start_symbol", "")).strip()
        end_symbol = str(anchors.get("end_symbol", "")).strip()
        if start_symbol in spans and end_symbol in spans:
            resolved.append(
                {
                    "kind": "declared-region",
                    "start_symbol": start_symbol,
                    "end_symbol": end_symbol,
                    "span": (spans[start_symbol][0], spans[end_symbol][1]),
                }
            )
    return resolved


def _changed_declared_regions(
    *, pair: dict[str, Any], touched_paths: list[str], target_root: Path | None
) -> tuple[list[dict[str, Any]], list[str]]:
    changed: list[dict[str, Any]] = []
    evidence: list[str] = []
    changed_ranges_by_path = {path: _changed_line_ranges_from_git_diff(target_root=target_root, path=path) for path in touched_paths}
    for region in _list_payload(pair.get("regions")):
        if not isinstance(region, dict):
            continue
        region_id = str(region.get("id", "")).strip()
        if not region_id:
            continue
        for path in touched_paths:
            changed_ranges = changed_ranges_by_path.get(path, [])
            if not changed_ranges:
                continue
            for declared_span in _region_spans_for_path(target_root=target_root, region=region, path=path):
                span = declared_span.get("span")
                if not isinstance(span, tuple):
                    continue
                if not any(_ranges_intersect(span, changed_range) for changed_range in changed_ranges):
                    continue
                item = {
                    "id": region_id,
                    "path": path,
                    "kind": declared_span.get("kind", str(region.get("kind", "declared-region"))),
                }
                if declared_span.get("symbol"):
                    item["symbol"] = declared_span["symbol"]
                    evidence.append(f"declared_symbol:{path}:{declared_span['symbol']}")
                else:
                    item["start_symbol"] = declared_span.get("start_symbol", "")
                    item["end_symbol"] = declared_span.get("end_symbol", "")
                    evidence.append(f"declared_region:{path}:{region_id}")
                changed.append(item)
                break
    return changed, _dedupe(evidence)


def _paired_declared_regions_for_missing_paths(*, pair: dict[str, Any], changed_regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paired: list[dict[str, Any]] = []
    pair_paths = [str(path) for path in _list_payload(pair.get("paths")) if str(path).strip()]
    for changed_region in changed_regions:
        region_id = str(changed_region.get("id", "")).strip()
        changed_path = str(changed_region.get("path", "")).strip()
        missing_paths = [path for path in pair_paths if path != changed_path]
        for missing_path in missing_paths:
            paired.append({"id": region_id, "path": missing_path, "kind": changed_region.get("kind", "declared-region")})
    return paired


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
    mirror_review = value.get("mirror_drift_review")
    if isinstance(mirror_review, dict) and mirror_review.get("status") != "not-applicable":
        records = []
        for record in _list_payload(mirror_review.get("records"))[:3]:
            if not isinstance(record, dict):
                continue
            records.append(
                {
                    "id": record.get("id", ""),
                    "mirror_pair_id": record.get("mirror_pair_id", ""),
                    "region_id": record.get("region_id", ""),
                    "status": record.get("status", "unknown"),
                    "changed_paths": record.get("changed_paths", []),
                    "paired_paths": record.get("paired_paths", []),
                    "paired_file_changed": record.get("paired_file_changed", False),
                    "likely_paired_file": record.get("likely_paired_file", ""),
                    "trigger_evidence": record.get("trigger_evidence", []),
                    "changed_regions": record.get("changed_regions", []),
                    "paired_regions": record.get("paired_regions", []),
                    "smallest_parity_proof_command": record.get("smallest_parity_proof_command", ""),
                    "maintainer_check_command": record.get("maintainer_check_command", ""),
                    "expected_action": record.get("expected_action", ""),
                    "represented_regression": record.get("represented_regression", ""),
                }
            )
        payload["mirror_drift_review"] = {
            "kind": mirror_review.get("kind", "agentic-workspace/runtime-mirror-drift-review/v1"),
            "status": mirror_review.get("status", "unknown"),
            "record_count": mirror_review.get("record_count", len(records)),
            "records": records,
            "rule": mirror_review.get("rule", ""),
        }
    return payload


def runtime_mirror_drift_review_for_changed_paths(changed_paths: list[str], *, target_root: Path | None = None) -> dict[str, Any]:
    changed_set = set(changed_paths)
    records: list[dict[str, Any]] = []
    for pair in MIRRORED_RUNTIME_PAYLOAD_HELPER_PAIRS:
        pair_paths = [str(path) for path in _list_payload(pair.get("paths")) if str(path).strip()]
        touched = [path for path in pair_paths if path in changed_set]
        if not touched:
            continue
        changed_regions, trigger_evidence = _changed_declared_regions(pair=pair, touched_paths=touched, target_root=target_root)
        if not changed_regions:
            continue
        region_ids = _dedupe([str(region.get("id", "")) for region in changed_regions if str(region.get("id", "")).strip()])
        for region_id in region_ids:
            region_changes = [region for region in changed_regions if str(region.get("id", "")) == region_id]
            touched_region_paths = _dedupe(
                [str(region.get("path", "")) for region in region_changes if str(region.get("path", "")).strip()]
            )
            paired_paths = [path for path in pair_paths if path not in set(touched_region_paths)]
            paired_file_changed = not paired_paths
            records.append(
                {
                    "id": f"{pair.get('id', '')}:{region_id}",
                    "mirror_pair_id": str(pair.get("id", "")),
                    "region_id": region_id,
                    "status": "paired-change-requires-parity-proof" if paired_file_changed else "warning-asymmetric-mirror-change",
                    "changed_paths": touched_region_paths,
                    "paired_paths": paired_paths,
                    "paired_file_changed": paired_file_changed,
                    "likely_paired_file": paired_paths[0] if len(paired_paths) == 1 else "",
                    "trigger_evidence": [
                        item
                        for item in trigger_evidence
                        if any(str(region.get("path", "")) in item and str(region.get("id", "")) == region_id for region in region_changes)
                    ],
                    "changed_regions": region_changes,
                    "paired_regions": _paired_declared_regions_for_missing_paths(pair=pair, changed_regions=region_changes),
                    "why": str(pair.get("why", "")),
                    "smallest_parity_proof_command": str(pair.get("smallest_parity_proof_command", "")),
                    "maintainer_check_command": str(pair.get("maintainer_check_command", "")),
                    "expected_action": (
                        "mirror the payload/helper change, prove it is intentionally one-sided, "
                        "or run the named parity proof before claiming completion"
                    ),
                    "represented_regression": str(pair.get("represented_regression", "")),
                }
            )
    if not records:
        return {"kind": "agentic-workspace/runtime-mirror-drift-review/v1", "status": "not-applicable", "records": []}
    status = (
        "warning"
        if any(record["status"] == "warning-asymmetric-mirror-change" for record in records)
        else "paired-change-requires-parity-proof"
    )
    return {
        "kind": "agentic-workspace/runtime-mirror-drift-review/v1",
        "status": status,
        "record_count": len(records),
        "records": records,
        "rule": (
            "Known mirrored runtime payload/helper surfaces are declared by exact symbols or regions; "
            "only changed code inside that contract surfaces pair-drift review before completion claims."
        ),
    }


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


def runtime_source_edit_review_for_changed_paths(
    changed_paths: list[str], *, target_root: Path | None = None, task_text: str | None = None
) -> dict[str, Any]:
    mirror_drift_review = runtime_mirror_drift_review_for_changed_paths(changed_paths, target_root=target_root)
    mirror_paths = [
        str(path)
        for record in _list_payload(mirror_drift_review.get("records"))
        if isinstance(record, dict)
        for path in _list_payload(record.get("changed_paths"))
        if str(path).strip()
    ]
    runtime_paths = [path for path in changed_paths if path in GENERATED_CLI_RUNTIME_SOURCE_EDIT_PATHS]
    review_changed_paths = _dedupe([*runtime_paths, *mirror_paths])
    if not review_changed_paths:
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
    if missing_inventory:
        status = "blocked-missing-inventory"
    elif mirror_drift_review.get("status") == "warning":
        status = "mirror-drift-warning"
    else:
        status = "classification-required"
    return {
        "kind": "agentic-workspace/runtime-source-edit-review/v1",
        "status": status,
        "changed_paths": review_changed_paths,
        "review_items": review_items,
        "inventory_source": "src/agentic_workspace/contracts/python_runtime_projection_inventory.json",
        "missing_inventory_paths": missing_inventory,
        "mirror_drift_review": mirror_drift_review,
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
