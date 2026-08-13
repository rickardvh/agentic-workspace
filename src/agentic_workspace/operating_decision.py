"""Compose current AW authorities into one internal operating decision."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from agentic_workspace.actionability import invocation_decision_input_revision, operation_invocation
from agentic_workspace.context_authority_owner_operations import (
    registered_context_owner_operation_runner,
    registered_context_owner_receipt_status,
    registered_context_owner_result_status,
)

BLOCKER_PRECEDENCE = [
    "missing-authority",
    "stale-revision",
    "conflicting-input",
    "denied-effect",
    "stale-mutation-baseline",
    "stale-proof",
    "context-coverage-gap",
    "missing-capability",
]

_CONTEXT_AUTHORITY_REGISTRY_RESOURCE = "context_authority_registry.json"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _file_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _directory_digest(path: Path) -> str:
    if not path.is_dir():
        return ""
    entries: list[dict[str, str]] = []
    try:
        children = sorted(item for item in path.rglob("*") if item.is_file())
    except OSError:
        return ""
    for child in children[:200]:
        rel = child.relative_to(path).as_posix()
        entries.append({"path": rel, "digest": _file_digest(child)})
    return _digest(entries)


def _load_context_authority_registry_contract() -> dict[str, Any]:
    payload = (Path(__file__).resolve().parent / "contracts" / _CONTEXT_AUTHORITY_REGISTRY_RESOURCE).read_text(encoding="utf-8")
    data = json.loads(payload)
    return data if isinstance(data, dict) else {}


_CONTEXT_AUTHORITY_REGISTRY_CONTRACT = _load_context_authority_registry_contract()
ORDINARY_DECISION_CONSUMERS = [str(item) for item in _as_list(_CONTEXT_AUTHORITY_REGISTRY_CONTRACT.get("ordinary_decision_consumers"))]
ORDINARY_DECISION_CONSUMER_REQUIREMENTS = {
    str(consumer): [str(surface) for surface in _as_list(surfaces)]
    for consumer, surfaces in _as_dict(_CONTEXT_AUTHORITY_REGISTRY_CONTRACT.get("consumer_requirements")).items()
}
CONTEXT_AUTHORITY_REGISTRY = [
    dict(item) for item in _as_list(_CONTEXT_AUTHORITY_REGISTRY_CONTRACT.get("surfaces")) if isinstance(item, dict)
]
CONTEXT_AUTHORITY_REGISTRY_REVISION = "sha256:" + _digest(_CONTEXT_AUTHORITY_REGISTRY_CONTRACT)
CONTEXT_AUTHORITY_SOURCE_SPECS: dict[str, dict[str, Any]] = {
    "system-intent": {
        "source": "SYSTEM_INTENT.md",
        "required": ["SYSTEM_INTENT.md"],
        "routes": ["SYSTEM_INTENT.md"],
        "source_adapter": "system-intent-source-adapter",
    },
    "architecture-principles": {
        "source": "SYSTEM_INTENT.md",
        "required": ["SYSTEM_INTENT.md"],
        "routes": ["SYSTEM_INTENT.md"],
        "source_adapter": "architecture-principles-source-adapter",
    },
    "scoped-instructions": {
        "source": "AGENTS.md",
        "required": ["AGENTS.md", ".agentic-workspace/skills/workspace-startup/SKILL.md"],
        "routes": ["AGENTS.md", ".agentic-workspace/skills/**"],
        "source_adapter": "scoped-instruction-source-adapter",
    },
    "ownership": {
        "source": ".agentic-workspace/OWNERSHIP.toml",
        "required": [".agentic-workspace/OWNERSHIP.toml"],
        "routes": ["*"],
        "source_adapter": "ownership-source-adapter",
    },
    "planning": {
        "source": ".agentic-workspace/planning/state.toml",
        "required": [".agentic-workspace/planning/state.toml"],
        "routes": [".agentic-workspace/planning/**"],
        "source_adapter": "planning-source-adapter",
    },
    "memory": {
        "source": ".agentic-workspace/memory/repo/index.md",
        "required": [".agentic-workspace/memory/repo/index.md", ".agentic-workspace/memory/repo/manifest.toml"],
        "routes": [".agentic-workspace/memory/repo/**"],
        "source_adapter": "memory-route-source-adapter",
    },
    "assignment": {
        "source": ".agentic-workspace/config.toml",
        "required": [".agentic-workspace/config.toml"],
        "routes": ["*"],
        "source_adapter": "assignment-source-adapter",
    },
    "evaluation": {
        "source": "src/agentic_workspace/evaluation.py",
        "required": ["src/agentic_workspace/evaluation.py"],
        "routes": ["src/agentic_workspace/evaluation.py"],
        "source_adapter": "evaluation-source-adapter",
    },
    "proof": {
        "source": ".agentic-workspace/verification/manifest.toml",
        "required": [".agentic-workspace/verification/manifest.toml"],
        "routes": [".agentic-workspace/verification/**", "tests/**"],
        "source_adapter": "proof-source-adapter",
    },
    "mutation-baseline": {
        "source": ".agentic-workspace/planning/state.toml",
        "required": [".agentic-workspace/planning/state.toml"],
        "routes": ["*"],
        "requires_git_head": True,
        "source_adapter": "mutation-baseline-source-adapter",
    },
    "autopilot-executor": {
        "source": "src/agentic_workspace/workspace_runtime_primitives.py",
        "required": ["src/agentic_workspace/workspace_runtime_primitives.py"],
        "routes": ["src/agentic_workspace/workspace_runtime_primitives.py"],
        "source_adapter": "autopilot-executor-source-adapter",
    },
    "skills": {
        "source": ".agentic-workspace/skills/workspace-startup/SKILL.md",
        "required": [".agentic-workspace/skills/workspace-startup/SKILL.md"],
        "routes": [".agentic-workspace/skills/**"],
        "source_adapter": "skill-registry-source-adapter",
    },
    "target-guidance": {
        "source": ".agentic-workspace/config.toml",
        "required": [".agentic-workspace/config.toml"],
        "routes": ["*"],
        "source_adapter": "target-guidance-source-adapter",
    },
    "terminal-outcome": {
        "source": "src/agentic_workspace/workspace_runtime_primitives.py",
        "required": ["src/agentic_workspace/workspace_runtime_primitives.py"],
        "routes": ["src/agentic_workspace/workspace_runtime_primitives.py"],
        "source_adapter": "terminal-outcome-source-adapter",
    },
    "generated-references": {
        "source": "generated/workspace/.agentic-workspace-cli-fingerprint.json",
        "required": [
            "generated/workspace/.agentic-workspace-cli-fingerprint.json",
            "generated/planning/.agentic-workspace-cli-fingerprint.json",
            "generated/memory/.agentic-workspace-cli-fingerprint.json",
            "generated/verification/.agentic-workspace-cli-fingerprint.json",
            "src/agentic_workspace/contracts/structured_file_inventory.json",
        ],
        "routes": ["generated/**", "src/agentic_workspace/contracts/**"],
        "generated_freshness": True,
        "source_adapter": "generated-reference-source-adapter",
    },
}

CONTEXT_AUTHORITY_OWNER_CONTRACTS: dict[str, dict[str, Any]] = {
    str(item.get("surface") or ""): _as_dict(item.get("source_owner_contract"))
    for item in CONTEXT_AUTHORITY_REGISTRY
    if str(item.get("surface") or "") and _as_dict(item.get("source_owner_contract"))
}


def context_authority_declarations() -> list[dict[str, Any]]:
    schema_keys = {
        "surface",
        "owner",
        "authority_class",
        "consumer",
        "activation",
        "editable_by",
        "stale_when",
        "proof_route",
        "disposition",
    }
    return [
        {key: value for key, value in {**item, "consumer": ", ".join(item["consumers"])}.items() if key in schema_keys}
        for item in CONTEXT_AUTHORITY_REGISTRY
    ]


def _context_authority_registry_items(declarations: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if declarations is None:
        return [dict(item) for item in CONTEXT_AUTHORITY_REGISTRY]
    return [dict(item) for item in declarations if isinstance(item, dict)]


def _registry_consumers(item: dict[str, Any]) -> list[str]:
    consumers = item.get("consumers")
    if isinstance(consumers, list):
        return [str(consumer).strip() for consumer in consumers if str(consumer).strip()]
    consumer = str(item.get("consumer") or "").strip()
    return [part.strip() for part in consumer.split(",") if part.strip()]


def _context_source_candidates(surface: str) -> list[str]:
    spec = CONTEXT_AUTHORITY_SOURCE_SPECS.get(surface, {})
    return [str(path) for path in _as_list(spec.get("required") or [spec.get("source")]) if str(path)]


def _task_terms(task: str) -> set[str]:
    return {term.strip("#.,:;()[]{}").lower() for term in task.split() if len(term.strip("#.,:;()[]{}")) > 2}


def _surface_owner_contract(surface: str) -> dict[str, Any]:
    return dict(CONTEXT_AUTHORITY_OWNER_CONTRACTS.get(surface, {}))


def _path_matches_context_routes(*, path: str, patterns: list[str], surface: str, task_matched: bool) -> bool:
    normalized = path.replace("\\", "/").strip()
    for pattern in patterns:
        if pattern == "*":
            if surface in {"ownership", "assignment", "mutation-baseline", "target-guidance"} or task_matched:
                return True
            continue
        if fnmatch.fnmatch(normalized, pattern):
            return True
    return False


def _context_surface_selection(
    *,
    surface: str,
    item: dict[str, Any],
    spec: dict[str, Any],
    consumer: str,
    task: str,
    paths: list[str],
) -> dict[str, Any]:
    owner_contract = _surface_owner_contract(surface)
    route_patterns = [str(pattern) for pattern in _as_list(spec.get("routes")) if str(pattern)]
    terms = _task_terms(task)
    activation_terms = {
        str(term).lower()
        for term in [
            surface,
            *surface.replace("-", " ").split(),
            *[str(term) for term in _as_list(owner_contract.get("activation_terms"))],
        ]
        if str(term).strip()
    }
    task_matched = bool(terms & activation_terms)
    matched_paths = [
        path
        for path in paths
        if _path_matches_context_routes(path=path, patterns=route_patterns, surface=surface, task_matched=task_matched)
    ]
    baseline_for = {str(item) for item in _as_list(owner_contract.get("baseline_for"))}
    baseline_selected = consumer in baseline_for and not paths
    applicable = bool(matched_paths or task_matched or baseline_selected)
    if surface == "memory":
        applicable = bool(matched_paths or task_matched)
    return {
        "applicable": applicable,
        "selected_required": applicable,
        "task_matched": task_matched,
        "matched_paths": sorted(matched_paths),
        "route_patterns": route_patterns,
        "activation_terms": sorted(activation_terms),
        "baseline_selected": baseline_selected,
    }


def _git_head(root: Path) -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _context_owner_operation_admission(
    *,
    owner_result: dict[str, Any],
    root: Path | None,
    surface: str,
    expected_producer: str,
    expected_result_kind: str,
    expected_operation_id: str,
    expected_source_id: str,
    expected_source_revision: str,
) -> tuple[bool, str]:
    owner_operation = _as_dict(owner_result.get("owner_operation"))
    receipt = _as_dict(owner_result.get("owner_execution_receipt"))
    if not owner_operation:
        return False, "owner-operation-missing"
    if not receipt:
        return False, "owner-operation-receipt-missing"
    if receipt.get("kind") != "agentic-workspace/context-authority-owner-execution-receipt/v1":
        return False, "owner-operation-receipt-kind-mismatch"
    if receipt.get("status") != "executed" or receipt.get("current_state") != "current":
        return False, "owner-operation-receipt-not-current"
    expected_adapter_id = f"{surface}.owner-result"
    expectations = {
        "operation_id": expected_operation_id,
        "producer": expected_producer,
        "surface": surface,
        "source_id": expected_source_id,
        "source_revision": expected_source_revision,
        "git_head": owner_result.get("git_head"),
        "adapter_id": expected_adapter_id,
    }
    for key, expected in expectations.items():
        if owner_operation.get(key) != expected or receipt.get(key) != expected:
            return False, f"owner-operation-{key.replace('_', '-')}-mismatch"
    if owner_operation.get("kind") != "agentic-workspace/context-authority-owner-operation/v1":
        return False, "owner-operation-kind-mismatch"
    if owner_operation.get("status") != "executed":
        return False, "owner-operation-status-mismatch"
    if owner_operation.get("run_id") != receipt.get("run_id"):
        return False, "owner-operation-run-id-mismatch"
    if owner_operation.get("receipt_id") != receipt.get("receipt_id"):
        return False, "owner-operation-receipt-id-mismatch"
    if owner_operation.get("selection_revision") != receipt.get("selection_revision"):
        return False, "owner-operation-selection-revision-mismatch"
    if owner_operation.get("schema_backing_revision") != receipt.get("schema_backing_revision"):
        return False, "owner-operation-schema-backing-revision-mismatch"
    if owner_operation.get("adapter_receipt_revision") != receipt.get("adapter_receipt_revision"):
        return False, "owner-operation-adapter-receipt-revision-mismatch"
    if owner_operation.get("result_payload_revision") != receipt.get("result_payload_revision"):
        return False, "owner-operation-result-payload-revision-mismatch"
    if receipt.get("supersedes"):
        return False, "owner-operation-receipt-superseded"
    if (
        owner_result.get("producer") != expected_producer
        or owner_result.get("kind") != expected_result_kind
        or owner_result.get("status") != "current"
        or owner_result.get("adapter_id") != expected_adapter_id
    ):
        return False, "owner-result-identity-mismatch"
    issued, reason = registered_context_owner_result_status(owner_result)
    if not issued:
        return False, reason
    registered, reason = registered_context_owner_receipt_status(
        owner_operation=owner_operation,
        receipt=receipt,
        result_revision=str(owner_result.get("revision") or ""),
        root=root,
    )
    if not registered:
        return False, reason
    return True, ""


def _context_owner_result_from_adapter(
    *,
    surface: str,
    item: dict[str, Any],
    root: Path,
    chosen: Path,
    revision: str,
    git_head: str,
    selection: dict[str, Any],
    task: str,
    paths: list[str],
    source_specific: dict[str, Any],
) -> dict[str, Any]:
    runner = registered_context_owner_operation_runner(surface)
    return runner(
        owner=item.get("owner"),
        root=root,
        chosen=chosen,
        revision=revision,
        git_head=git_head,
        selection=selection,
        task=task,
        paths=paths,
        source_specific=source_specific,
    )


def _resolve_context_authority_source(
    *,
    item: dict[str, Any],
    target_root: Path | None,
    consumer: str = "",
    task: str,
    paths: list[str],
) -> dict[str, Any]:
    surface = str(item.get("surface") or "")
    spec = CONTEXT_AUTHORITY_SOURCE_SPECS.get(surface, {})
    selection = _context_surface_selection(surface=surface, item=item, spec=spec, consumer=consumer, task=task, paths=paths)
    if not selection["applicable"]:
        return {
            "status": "not-applicable",
            "applicable": False,
            "selected_required": False,
            "reason": "not-selected-by-task-or-path",
            "selection": selection,
        }
    if target_root is None:
        return {
            "status": "missing",
            "applicable": True,
            "selected_required": True,
            "reason": "missing-target-root",
            "selection": selection,
        }
    root = target_root
    candidates = _context_source_candidates(surface)
    missing_required = [candidate for candidate in candidates if not (root / candidate).exists()]
    if missing_required:
        return {
            "status": "missing",
            "applicable": True,
            "selected_required": True,
            "reason": "canonical-source-missing",
            "candidates": candidates,
            "missing_required": missing_required,
            "repair_operation_id": str(
                _surface_owner_contract(surface).get("repair_operation_id") or f"context-authority.{surface}.refresh-source"
            ),
            "selection": selection,
        }
    chosen = root / str(spec.get("source") or candidates[0])
    if not chosen.exists():
        return {
            "status": "missing",
            "applicable": True,
            "selected_required": True,
            "reason": "canonical-source-missing",
            "candidates": candidates,
            "selection": selection,
        }
    revision = _directory_digest(chosen) if chosen.is_dir() else _file_digest(chosen)
    if not revision:
        return {
            "status": "stale",
            "applicable": True,
            "selected_required": True,
            "reason": "source-unreadable-or-empty",
            "source_id": chosen.as_posix(),
            "selection": selection,
        }
    if chosen.is_dir() and not any(path.is_file() for path in chosen.rglob("*")):
        return {
            "status": "missing",
            "applicable": True,
            "selected_required": True,
            "reason": "configured-source-empty",
            "source_id": chosen.relative_to(root).as_posix(),
            "selection": selection,
        }
    git_head = _git_head(root) if spec.get("requires_git_head") else ""
    if spec.get("requires_git_head") and not git_head:
        return {
            "status": "missing",
            "applicable": True,
            "selected_required": True,
            "reason": "git-head-unavailable",
            "source_id": chosen.relative_to(root).as_posix(),
            "selection": selection,
        }
    source_adapter = str(spec.get("source_adapter") or f"{surface}-source-adapter")
    owner_contract = _surface_owner_contract(surface)
    path_tokens = {Path(path).parts[0] for path in paths if Path(path).parts}
    source_token = chosen.parts[-1] if chosen.parts else chosen.as_posix()
    source_specific: dict[str, Any] = {}
    owner_result = _context_owner_result_from_adapter(
        surface=surface,
        item=item,
        root=root,
        chosen=chosen,
        revision=revision,
        git_head=git_head,
        selection=selection,
        task=task,
        paths=paths,
        source_specific=source_specific,
    )
    if owner_result.get("status") != "current":
        if surface == "memory" and owner_result.get("reason") == "memory-curation-empty":
            return {
                "status": "not-applicable",
                "applicable": False,
                "selected_required": False,
                "reason": "no-route-selected-memory",
                "selection": {**selection, "memory_curation": _as_dict(owner_result.get("memory_curation"))},
                "owner_result": owner_result,
            }
        return {
            "status": "stale",
            "applicable": True,
            "selected_required": True,
            "reason": str(owner_result.get("reason") or "owner-result-unavailable"),
            "source_id": chosen.relative_to(root).as_posix(),
            "selection": selection,
            "owner_result": owner_result,
        }
    freshness_enforcement = {
        "kind": "agentic-workspace/context-authority-freshness-enforcement/v1",
        "status": "active",
        "surface": surface,
        "source_adapter": source_adapter,
        "owner_module": str(owner_contract.get("owner_module") or source_adapter),
        "owner_result_kind": str(owner_contract.get("owner_result_kind") or ""),
        "freshness": "current",
        "reject_when": [
            "source-missing",
            "source-unreadable",
            "source-revision-changed",
            "generated-projection-stale",
            "registry-revision-mismatch",
            "producer-mismatch",
            "owner-result-kind-mismatch",
        ],
        "repair_operation_id": str(owner_contract.get("repair_operation_id") or f"context-authority.{surface}.refresh-source"),
    }
    owner_admission = {
        "kind": "agentic-workspace/context-authority-owner-admission/v1",
        "producer": str(owner_result.get("producer") or owner_contract.get("owner_module") or source_adapter),
        "result_kind": str(owner_result.get("kind") or owner_contract.get("owner_result_kind") or ""),
        "surface": surface,
        "owner": item.get("owner"),
        "revision": str(owner_result.get("revision") or ""),
        "status": "admitted",
        "owner_result_status": str(owner_result.get("status") or ""),
    }
    return {
        "status": "current",
        "applicable": True,
        "selected_required": True,
        "source_adapter": source_adapter,
        "source_id": chosen.relative_to(root).as_posix() if chosen.is_relative_to(root) else chosen.as_posix(),
        "revision": "sha256:" + _digest({"source": revision, "git_head": git_head}) if git_head else "sha256:" + revision,
        "freshness": "current",
        "selection": {
            "task_digest": _digest(task)[:16],
            "changed_path_count": len(paths),
            "path_tokens": sorted(path_tokens),
            "matched_paths": selection["matched_paths"],
            "route_patterns": selection["route_patterns"],
            "source_token": source_token,
            "task_matched": selection["task_matched"],
            "baseline_selected": selection["baseline_selected"],
            "rule": "source-specific owner adapter resolved current source identity; caller supplied records are diagnostics only",
            **({"memory_curation": owner_result["memory_curation"]} if surface == "memory" and "memory_curation" in owner_result else {}),
            **source_specific,
        },
        "freshness_enforcement": freshness_enforcement,
        "admission": {
            "kind": "agentic-workspace/context-authority-source-receipt/v1",
            "producer": source_adapter,
            "owner_admission": owner_admission,
            "owner_result": owner_result,
            "registry_revision": CONTEXT_AUTHORITY_REGISTRY_REVISION,
            "surface": surface,
            "owner": item.get("owner"),
            "source_revision": "sha256:" + revision,
            "git_head": git_head,
            "repair_operation_id": str(owner_contract.get("repair_operation_id") or f"context-authority.{surface}.refresh-source"),
            "source_specific": source_specific,
            "freshness_enforcement": freshness_enforcement,
        },
    }


def context_authority_coverage(
    *,
    declarations: list[dict[str, Any]] | None = None,
    observed_consumers: list[str] | None = None,
    consumer_requirements: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    registry = _context_authority_registry_items(declarations)
    expected_consumers = sorted({str(item).strip() for item in (observed_consumers or ORDINARY_DECISION_CONSUMERS) if str(item).strip()})
    requirements = {
        str(consumer): [str(surface) for surface in surfaces]
        for consumer, surfaces in (consumer_requirements or ORDINARY_DECISION_CONSUMER_REQUIREMENTS).items()
        if str(consumer).strip()
    }
    consumer_to_surfaces: dict[str, list[str]] = {consumer: [] for consumer in expected_consumers}
    missing_owner_surfaces: list[str] = []
    duplicate_surfaces: list[str] = []
    seen_surfaces: set[str] = set()
    duplicate_canonical_owners: list[str] = []
    owner_to_canonical_surfaces: dict[str, list[str]] = {}
    surfaces: list[str] = []
    for item in registry:
        surface = str(item.get("surface") or "").strip()
        if not surface:
            continue
        if surface in seen_surfaces:
            duplicate_surfaces.append(surface)
        seen_surfaces.add(surface)
        surfaces.append(surface)
        owner = str(item.get("owner") or "").strip()
        if not owner:
            missing_owner_surfaces.append(surface)
        if str(item.get("authority_class") or "") == "canonical":
            owner_to_canonical_surfaces.setdefault(owner, []).append(surface)
        for consumer in _registry_consumers(item):
            if consumer in consumer_to_surfaces:
                consumer_to_surfaces[consumer].append(surface)
    duplicate_canonical_owners = sorted(
        owner for owner, owner_surfaces in owner_to_canonical_surfaces.items() if owner and len(owner_surfaces) > 1
    )
    uncovered_consumers = sorted(consumer for consumer, consumer_surfaces in consumer_to_surfaces.items() if not consumer_surfaces)
    missing_required_sources = {
        consumer: sorted(set(requirements.get(consumer, [])) - set(consumer_to_surfaces.get(consumer, [])))
        for consumer in expected_consumers
        if set(requirements.get(consumer, [])) - set(consumer_to_surfaces.get(consumer, []))
    }
    duplicate_consumer_authorities = sorted(
        consumer
        for consumer, consumer_surfaces in consumer_to_surfaces.items()
        if len(
            [
                surface
                for surface in consumer_surfaces
                if str(next((item.get("authority_class") for item in registry if item.get("surface") == surface), "")) == "canonical"
            ]
        )
        > 4
    )
    status = "measured"
    if uncovered_consumers or missing_required_sources or missing_owner_surfaces or duplicate_surfaces or duplicate_canonical_owners:
        status = "coverage-gap"
    return {
        "kind": "agentic-workspace/context-authority-coverage/v1",
        "status": status,
        "registry_source": f"src/agentic_workspace/contracts/{_CONTEXT_AUTHORITY_REGISTRY_RESOURCE}",
        "registry_revision": CONTEXT_AUTHORITY_REGISTRY_REVISION,
        "registry_authority": "versioned-contract",
        "surface_count": len(surfaces),
        "consumer_count": len(expected_consumers),
        "surfaces": surfaces,
        "ordinary_consumers": expected_consumers,
        "consumer_to_surfaces": consumer_to_surfaces,
        "consumer_requirements": {consumer: requirements.get(consumer, []) for consumer in expected_consumers},
        "missing_required_sources": missing_required_sources,
        "uncovered_consumers": uncovered_consumers,
        "missing_owner_surfaces": missing_owner_surfaces,
        "duplicate_surfaces": sorted(set(duplicate_surfaces)),
        "duplicate_canonical_owners": duplicate_canonical_owners,
        "duplicate_consumer_authorities": duplicate_consumer_authorities,
        "rule": "Operating decisions measure the versioned context-authority registry against ordinary consumers and fail closed on missing owners, duplicate surfaces, missing required sources, or uncovered consumers.",
    }


def resolve_context_authority_projection(
    *,
    consumer: str,
    task: str = "",
    changed_paths: list[str] | None = None,
    target_root: Path | None = None,
    source_records: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve the smallest declared authority set for an ordinary consumer.

    This is deliberately registry-driven: callers receive a revisioned projection
    and a typed repair disposition instead of reimplementing source selection.
    """
    paths = [str(path) for path in (changed_paths or []) if str(path)]
    caller_records = _as_dict(source_records)
    coverage = context_authority_coverage()
    required = set(ORDINARY_DECISION_CONSUMER_REQUIREMENTS.get(consumer, []))
    selected: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for item in CONTEXT_AUTHORITY_REGISTRY:
        surface = str(item.get("surface") or "")
        if surface not in required:
            continue
        record = _resolve_context_authority_source(item=item, target_root=target_root, consumer=consumer, task=task, paths=paths)
        caller_record = _as_dict(caller_records.get(surface))
        record_status = str(record.get("status") or "missing")
        admission = _as_dict(record.get("admission"))
        owner_admission = _as_dict(admission.get("owner_admission"))
        owner_result = _as_dict(admission.get("owner_result"))
        owner_contract = _surface_owner_contract(surface)
        expected_producer = str(owner_contract.get("owner_module") or "")
        expected_result_kind = str(owner_contract.get("owner_result_kind") or "")
        expected_source_id = str(record.get("source_id") or record.get("source") or "")
        expected_source_revision = str(admission.get("source_revision") or "")
        expected_operation_id = str(owner_contract.get("repair_operation_id") or f"context-authority.{surface}.refresh-source")
        owner_operation_valid, owner_operation_reason = _context_owner_operation_admission(
            owner_result=owner_result,
            root=target_root,
            surface=surface,
            expected_producer=expected_producer,
            expected_result_kind=expected_result_kind,
            expected_operation_id=expected_operation_id,
            expected_source_id=expected_source_id,
            expected_source_revision=expected_source_revision,
        )
        owner_identity_valid = (
            owner_admission.get("producer") == expected_producer
            and owner_admission.get("result_kind") == expected_result_kind
            and owner_admission.get("revision") == owner_result.get("revision")
            and owner_operation_valid
        )
        applicable = (
            bool(record)
            and record.get("applicable") is not False
            and record.get("selected_required") is not False
            and record_status == "current"
            and bool(record.get("source_id") or record.get("source"))
            and bool(record.get("revision"))
            and str(record.get("freshness") or "") == "current"
            and admission.get("registry_revision") == CONTEXT_AUTHORITY_REGISTRY_REVISION
            and admission.get("surface") == surface
            and admission.get("owner") == item.get("owner")
            and admission.get("producer") == record.get("source_adapter")
            and owner_admission.get("surface") == surface
            and owner_admission.get("owner") == item.get("owner")
            and owner_identity_valid
            and _as_dict(record.get("freshness_enforcement")).get("status") == "active"
        )
        authority = {
            "surface": surface,
            "owner": str(item.get("owner") or ""),
            "authority_class": str(item.get("authority_class") or ""),
            "activation": str(item.get("activation") or ""),
            "revision_fields": [str(field) for field in _as_list(item.get("revision_fields"))],
            "disposition": str(item.get("disposition") or ""),
            "source": {
                "id": str(record.get("source_id") or record.get("source") or ""),
                "revision": str(record.get("revision") or ""),
                "freshness": str(record.get("freshness") or record_status),
                "selection": _as_dict(record.get("selection")),
                "admission": admission,
                "source_adapter": str(record.get("source_adapter") or ""),
                "freshness_enforcement": _as_dict(record.get("freshness_enforcement")),
            },
            "caller_record_status": "ignored" if caller_record else "absent",
        }
        if applicable:
            selected.append(authority)
        else:
            excluded.append(
                {
                    "surface": surface,
                    "reason": str(
                        record.get("reason")
                        or (owner_operation_reason if record_status == "current" and not owner_identity_valid else record_status)
                    ),
                    "selected_required": bool(record.get("selected_required")),
                    "caller_record_status": authority["caller_record_status"],
                }
            )
    selected_required_missing = {
        str(item.get("surface") or "") for item in excluded if item.get("selected_required") and str(item.get("surface") or "") in required
    }
    missing = sorted(selected_required_missing)
    status = "admitted" if not missing and coverage["status"] == "measured" else "repair-required"
    repairs = [
        {
            "surface": item["surface"],
            "owner": item["owner"],
            "reason_code": next(
                (
                    str(excluded_authority.get("reason") or "missing")
                    for excluded_authority in excluded
                    if excluded_authority.get("surface") == item["surface"]
                ),
                "missing",
            ),
            "action": f"context-authority.{item['surface']}.refresh-source",
            "operation_id": str(
                _surface_owner_contract(str(item["surface"])).get("repair_operation_id")
                or f"context-authority.{item['surface']}.refresh-source"
            ),
            "repair_owner": str(item.get("owner") or "context-authority-source-adapter"),
            "required_record": [
                "canonical repository source",
                "source-owner admission result",
                "source-specific schema/population check",
                "producer-owned admission receipt",
                "freshness=current",
            ],
            "arguments": {"target": ".", "surface": item["surface"], "consumer": consumer, "changed_path_count": len(paths)},
        }
        for item in sorted(
            (item for item in CONTEXT_AUTHORITY_REGISTRY if str(item.get("surface") or "") in missing),
            key=lambda item: str(item.get("surface") or ""),
        )
    ]
    return {
        "kind": "agentic-workspace/context-authority-projection/v1",
        "status": status,
        "consumer": consumer,
        "registry_revision": CONTEXT_AUTHORITY_REGISTRY_REVISION,
        "task_digest": _digest(task)[:16],
        "changed_path_count": len(paths),
        "target_root_status": "present" if target_root is not None else "missing",
        "authorities": selected,
        "excluded_authorities": excluded,
        "missing_required_surfaces": missing,
        "repair_operation": {
            "kind": "agentic-workspace/context-authority-repair/v1",
            "status": "required" if repairs else "not-required",
            "consumer": consumer,
            "repairs": repairs,
            "blocked_claims": ["mutation", "proof-claim", "completion-claim"] if repairs else [],
        },
        "repair": ("repair the registry declaration or consumer requirement before mutation" if status == "repair-required" else ""),
    }


def _surface_gap_class(surface: dict[str, Any]) -> str:
    requirement_status = str(surface.get("requirement_status") or "").strip()
    population_status = str(surface.get("population_status") or "").strip()
    routing_status = str(surface.get("routing_status") or "").strip()
    coverage_status = str(surface.get("coverage_status") or "").strip()
    freshness_status = str(surface.get("freshness_status") or "").strip()
    finding_status = str(surface.get("finding_status") or "").strip()
    source_status = str(surface.get("source_status") or "").strip()
    if source_status == "undeclared":
        return "consumer-without-source"
    if requirement_status == "required" and population_status == "missing":
        return "configured-but-missing"
    if requirement_status == "required" and population_status == "below-minimum":
        return "configured-but-unpopulated"
    if population_status == "present" and routing_status == "unreachable":
        return "declared-but-unroutable"
    if coverage_status == "gap":
        return "coverage-gap"
    if freshness_status == "inference-fallback":
        return "inference-fallback"
    if finding_status == "unresolved":
        return "unresolved-populated-finding"
    return ""


def context_surface_admission(
    *,
    surface: str,
    source_kind: str,
    source_id: str,
    source_revision: str,
    authority_owner: str,
    requirement_status: str = "optional",
    population_status: str = "present",
    routing_status: str = "reachable",
    coverage_status: str = "covered",
    freshness_status: str = "current",
    finding_status: str = "",
    severity: str = "",
    evidence_refs: list[str] | None = None,
    next_route: str = "",
    affected_decisions: list[str] | None = None,
) -> dict[str, Any]:
    """Normalize one specialist-owned context input before gap classification."""

    admitted = bool(surface and source_kind and source_id and source_revision and authority_owner)
    return {
        "kind": "agentic-workspace/context-surface-admission/v1",
        "admission_status": "admitted" if admitted else "rejected",
        "surface": surface,
        "source": {"kind": source_kind, "id": source_id, "revision": source_revision},
        "authority_owner": authority_owner,
        "requirement_status": requirement_status,
        "population_status": population_status,
        "routing_status": routing_status,
        "coverage_status": coverage_status,
        "freshness_status": freshness_status,
        "finding_status": finding_status,
        "severity": severity,
        "evidence_refs": list(evidence_refs or []),
        "next_route": next_route,
        "affected_decisions": list(affected_decisions or []),
        "rule": "Context gaps classify admitted specialist resolver records; callers may not provide blocking status without source identity, authority owner, and source revision.",
    }


def _admitted_context_surface(surface: dict[str, Any]) -> dict[str, Any]:
    admitted = _as_dict(surface.get("admitted_state")) or surface
    if admitted.get("kind") != "agentic-workspace/context-surface-admission/v1":
        return {
            "kind": "agentic-workspace/context-surface-admission/v1",
            "admission_status": "rejected",
            "surface": str(surface.get("surface") or admitted.get("surface") or ""),
            "source_status": "unversioned",
            "coverage_status": "gap",
            "severity": "blocking",
            "authority_owner": "context-authority-coverage",
            "next_route": "resolve this surface through a canonical context-surface adapter before deriving gaps",
            "evidence_refs": ["unversioned-context-surface-input"],
        }
    source = _as_dict(admitted.get("source"))
    missing = [
        field
        for field, value in {
            "surface": admitted.get("surface"),
            "source.kind": source.get("kind"),
            "source.id": source.get("id"),
            "source.revision": source.get("revision"),
            "authority_owner": admitted.get("authority_owner"),
        }.items()
        if not str(value or "").strip()
    ]
    if admitted.get("admission_status") != "admitted" or missing:
        return {
            **admitted,
            "admission_status": "rejected",
            "source_status": "unversioned",
            "coverage_status": "gap",
            "severity": "blocking",
            "next_route": str(admitted.get("next_route") or "resolve missing context source identity and retry"),
            "evidence_refs": [*_as_list(admitted.get("evidence_refs")), *missing],
        }
    return admitted


def derive_context_gaps(*, declarations: list[dict[str, Any]], selected_surfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    declared = {str(item.get("surface") or ""): item for item in declarations if isinstance(item, dict)}
    gaps: list[dict[str, Any]] = []
    for surface in selected_surfaces:
        if not isinstance(surface, dict):
            continue
        admitted_state = _admitted_context_surface(surface)
        surface_id = str(admitted_state.get("surface") or surface.get("surface") or "").strip()
        if surface_id not in declared:
            admitted_state = {**admitted_state, "source_status": "undeclared"}
        gap_class = _surface_gap_class(admitted_state)
        if not gap_class:
            continue
        owner = str(
            admitted_state.get("authority_owner")
            if admitted_state.get("admission_status") == "rejected"
            else _as_dict(declared.get(surface_id)).get("owner") or surface.get("owner") or "workspace-maintainer"
        )
        severity = str(
            admitted_state.get("severity")
            or surface.get("severity")
            or ("blocking" if admitted_state.get("requirement_status") == "required" else "advisory")
        )
        gaps.append(
            {
                "kind": "agentic-workspace/context-gap/v1",
                "id": f"{gap_class}:{surface_id or 'unknown'}",
                "gap_class": gap_class,
                "surface": surface_id,
                "affected_capability": str(surface.get("affected_capability") or "ordinary-operating-decision"),
                "affected_decisions": _as_list(admitted_state.get("affected_decisions"))
                or _as_list(surface.get("affected_decisions"))
                or ["routing", "claim-boundary"],
                "evidence_refs": _as_list(admitted_state.get("evidence_refs")) or _as_list(surface.get("evidence_refs")),
                "confidence": str(surface.get("confidence") or "high"),
                "severity": severity,
                "current_task_effect": str(surface.get("current_task_effect") or "weakens current AW decision input"),
                "owner": owner,
                "next_route": str(
                    admitted_state.get("next_route") or surface.get("next_route") or f"repair or declare lifecycle for {surface_id}"
                ),
            }
        )
    return gaps


def _specialist_blocker(authority: dict[str, Any], *, default_owner: str, default_repair: str = "") -> dict[str, str] | None:
    blocker = _as_dict(authority.get("operating_blocker") or authority.get("blocker"))
    reason_code = str(blocker.get("reason_code") or authority.get("reason_code") or "").strip()
    if not reason_code:
        return None
    return {
        "reason_code": reason_code,
        "owner": str(blocker.get("owner") or authority.get("owner") or default_owner),
        "repair": str(blocker.get("repair") or authority.get("repair") or default_repair or "refresh owning authority"),
    }


def derive_operating_blockers_from_authorities(*, authorities: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    target = _as_dict(authorities.get("target"))
    assignment = _as_dict(authorities.get("assignment_gate") or authorities.get("assignment"))
    transport = _as_dict(authorities.get("manual_transport"))
    mutation = _as_dict(authorities.get("mutation_baseline"))
    evaluation = _as_dict(authorities.get("evaluation"))
    planning = _as_dict(authorities.get("planning_owner") or authorities.get("planning"))
    proof = _as_dict(authorities.get("proof") or authorities.get("proof_obligation"))
    executor = _as_dict(authorities.get("executor") or authorities.get("autopilot_executor"))

    for authority, owner in [
        (target, "assignment target"),
        (assignment, "assignment gate"),
        (transport, "manual transport"),
        (mutation, "mutation authority"),
        (evaluation, "evaluation"),
        (planning, "planning owner"),
        (proof, "proof receipt"),
        (executor, "autopilot executor"),
    ]:
        specialist = _specialist_blocker(authority, default_owner=owner)
        if specialist:
            blockers.append(specialist)

    if str(target.get("status") or "") in {"unknown", "missing", "no-safe-target"}:
        blockers.append({"reason_code": "missing-capability", "owner": "assignment target", "repair": "select a safe target"})
    handoff_admission = str(
        assignment.get("handoff_admission_status")
        or _as_dict(assignment.get("handoff_admission")).get("status")
        or transport.get("handoff_admission_status")
        or _as_dict(transport.get("handoff_admission")).get("status")
        or ""
    )
    assignment_status = str(assignment.get("status") or "")
    transport_status = str(transport.get("status") or "")
    handoff_is_admitted = assignment_status == "handoff-required" and handoff_admission in {
        "admitted",
        "admitted-handoff",
        "manual-required",
    }
    if (transport_status in {"blocked", "disabled"} or assignment_status == "handoff-required") and not handoff_is_admitted:
        blockers.append({"reason_code": "denied-effect", "owner": "manual transport", "repair": "prepare handoff"})
    if str(mutation.get("revalidation_status") or mutation.get("status") or "") in {"stale", "rejected", "failed"}:
        blockers.append({"reason_code": "stale-mutation-baseline", "owner": "mutation authority", "repair": "refresh baseline"})
    evaluation_status = str(evaluation.get("freshness_status") or evaluation.get("status") or "")
    evaluation_required = evaluation.get("required") is True or str(evaluation.get("applicability") or "") == "required"
    if evaluation_status in {"missing", "not-registered"} and evaluation_required:
        blockers.append({"reason_code": "context-coverage-gap", "owner": "evaluation", "repair": "register evaluation"})
    if evaluation_status in {"stale", "superseded", "stale-bound"}:
        blockers.append({"reason_code": "stale-revision", "owner": "evaluation", "repair": "rerun evaluation"})
    if str(planning.get("freshness_status") or planning.get("status") or "") in {"stale", "superseded", "malformed"}:
        blockers.append({"reason_code": "stale-revision", "owner": "planning owner", "repair": "reselect owner"})
    if str(proof.get("receipt_status") or proof.get("status") or "") in {"invalid", "stale", "rejected", "missing"}:
        blockers.append({"reason_code": "stale-proof", "owner": "proof receipt", "repair": "rerun proof"})
    if str(executor.get("availability_status") or _as_dict(executor.get("availability")).get("status") or executor.get("status") or "") in {
        "unavailable",
        "stale-binding",
        "no-valid-executor",
    }:
        blockers.append({"reason_code": "missing-capability", "owner": "autopilot executor", "repair": "rebind executor"})
    return blockers


def _authority_revision(authority: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    revision: dict[str, Any] = {}
    for key in keys:
        if key in authority:
            revision[key] = authority.get(key)
    identity = authority.get("identity")
    if isinstance(identity, dict):
        revision["identity"] = identity
    admission = authority.get("fresh_result_admission") or authority.get("admission")
    if isinstance(admission, dict):
        revision["admission"] = admission
    blocker = authority.get("operating_blocker") or authority.get("blocker")
    if isinstance(blocker, dict):
        revision["blocker"] = blocker
    status = authority.get("status") or authority.get("freshness_status") or authority.get("revalidation_status")
    if status:
        revision["status"] = status
    return revision


def _live_authority_revision_fields(*, authorities: dict[str, Any]) -> dict[str, Any]:
    target = _as_dict(authorities.get("target"))
    assignment = _as_dict(authorities.get("assignment_gate") or authorities.get("assignment"))
    transport = _as_dict(authorities.get("manual_transport"))
    mutation = _as_dict(authorities.get("mutation_baseline"))
    evaluation = _as_dict(authorities.get("evaluation"))
    planning = _as_dict(authorities.get("planning_owner") or authorities.get("planning"))
    proof = _as_dict(authorities.get("proof") or authorities.get("proof_obligation"))
    executor = _as_dict(authorities.get("executor") or authorities.get("autopilot_executor"))
    owner_context_revision = {
        **_authority_revision(planning, ["owner_id", "owner_ref", "owner_revision", "selected_plan_id", "current_work_id"]),
        "target": _authority_revision(target, ["target_identity_ref", "selected_target", "revision"]),
        "assignment": _authority_revision(
            assignment,
            ["assignment_revision", "context_key", "target_identity_ref", "status", "handoff_admission_status"],
        ),
        "transport": _authority_revision(transport, ["status", "policy_revision", "handoff_admission_status"]),
    }
    return {
        "owner_context_revision": owner_context_revision,
        "mutation_boundary": _authority_revision(
            mutation,
            ["baseline_id", "head", "scope", "assignment", "revalidation_status", "mutation_revision"],
        ),
        "proof_requirements": [
            _authority_revision(
                proof,
                ["proof_obligation_id", "proof_subject_fingerprint", "receipt_revision", "receipt_status", "status"],
            )
        ]
        if proof
        else [],
        "evaluation_revision": _authority_revision(
            evaluation,
            ["evaluation_id", "definition_revision", "current_result_identity", "freshness_status", "status", "required"],
        ),
        "executor_revision": _authority_revision(
            executor,
            ["binding_fingerprint", "availability_status", "invocation_revision", "status"],
        ),
    }


def live_decision_input_revision(*, invocation: dict[str, Any], authorities: dict[str, Any]) -> str:
    live_fields = _live_authority_revision_fields(authorities=authorities)
    return invocation_decision_input_revision(
        {
            **invocation,
            **live_fields,
        }
    )


def bind_operation_invocation_to_authorities(*, invocation: dict[str, Any], authorities: dict[str, Any]) -> dict[str, Any]:
    bound = {
        **invocation,
        "requested_mutation_boundary": _as_dict(invocation.get("mutation_boundary")),
        **_live_authority_revision_fields(authorities=authorities),
    }
    bound["expected_input_revision"] = invocation_decision_input_revision(bound)
    bound["producer_revision"] = bound["expected_input_revision"]
    bound["stale_action_rejection"] = {
        **_as_dict(bound.get("stale_action_rejection")),
        "revision_source": "live-authority-resolver",
        "comparison_fields": [
            "expected_input_revision",
            "owner_context_revision",
            "mutation_boundary",
            "proof_requirements",
            "evaluation_revision",
            "executor_revision",
        ],
    }
    return bound


def _invocation_requires_mutation_baseline(invocation: dict[str, Any]) -> bool:
    effect_class = str(invocation.get("effect_class") or "").strip()
    boundary = _as_dict(invocation.get("mutation_boundary"))
    return effect_class in {"repo-mutation", "workspace-state-mutation"} or boundary.get("writes_repo_state") is True


def _mutation_baseline_is_current(mutation: dict[str, Any]) -> bool:
    status = str(mutation.get("revalidation_status") or mutation.get("status") or "").strip()
    scope = _as_dict(mutation.get("scope"))
    observed = _as_dict(mutation.get("observed_state"))
    observation = _as_dict(mutation.get("observation"))
    boundary = _as_dict(mutation.get("boundary_enforcement"))
    stale_revalidation = _as_dict(mutation.get("stale_revalidation"))
    ownership = _as_dict(mutation.get("ownership"))
    return all(
        (
            mutation.get("kind") == "agentic-workspace/mutation-baseline/v1",
            status in {"fresh", "current"},
            bool(mutation.get("baseline_id")),
            bool(mutation.get("head")),
            isinstance(scope.get("allowed_paths"), list),
            observation.get("ok") is True,
            bool(observed.get("enforcement_fingerprint")),
            boundary.get("status") == "fail-closed-contract",
            stale_revalidation.get("status") == "required",
            bool(ownership.get("owner")),
        )
    )


def _scope_fingerprint(paths: list[str]) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(sorted(paths), separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def compile_implement_context_operating_decision(
    *,
    target: str = "",
    task_present: bool = False,
    planning_gate: dict[str, Any] | None = None,
    authority_envelope: dict[str, Any] | None = None,
    mutation_baseline: dict[str, Any] | None = None,
    operating_loop: dict[str, Any] | None = None,
    verification: dict[str, Any] | None = None,
    proof_detail_route: str = "",
    changed_paths: list[str] | None = None,
    allowed_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Emit ordinary implement-context typed invocation and compiled decision."""

    planning_gate = _as_dict(planning_gate)
    authority_envelope = _as_dict(authority_envelope)
    mutation_baseline = _as_dict(mutation_baseline)
    operating_loop = _as_dict(operating_loop)
    verification = _as_dict(verification)
    changed_paths = [str(path) for path in changed_paths or [] if str(path).strip()]
    allowed_paths = [str(path) for path in allowed_paths or [] if str(path).strip()]
    direct_route = (
        planning_gate.get("gate_result") == "direct-work-allowed"
        and planning_gate.get("implementation_allowed") is True
        and planning_gate.get("required_next_action") == "continue-direct"
    )
    if not direct_route:
        return {
            "kind": "agentic-workspace/ordinary-operation-sources/v1",
            "producer_module": "agentic_workspace.operating_decision",
            "status": "inactive",
            "reason": "direct-work-route-not-admitted",
        }
    scope_fingerprint = _scope_fingerprint(changed_paths)
    proof_required = (
        "proof" in proof_detail_route
        and operating_loop.get("safe_claim") == "blocked"
        and "run_or_refresh_proof" in [str(item) for item in operating_loop.get("required_before_full_closure", [])]
        and verification.get("state") == "proof_missing"
    )
    authorities = {
        "target": {"selected_target": "workspace", "revision": str(target or ""), "status": "current"},
        "planning_owner": {
            "owner_id": "direct-work",
            "owner_ref": "planning_safety_gate",
            "owner_revision": _as_dict(planning_gate.get("planning_revision")).get("state_revision")
            or _as_dict(planning_gate.get("route_decision")).get("decision_id")
            or str(planning_gate.get("gate_result") or ""),
            "status": "current",
        },
        "mutation_baseline": {
            "baseline_id": mutation_baseline.get("baseline_id"),
            "head": mutation_baseline.get("head"),
            "scope": {
                "changed_path_count": len(changed_paths),
                "allowed_path_count": len(allowed_paths),
                "changed_scope_fingerprint": scope_fingerprint,
                "allowed_scope_fingerprint": _scope_fingerprint(allowed_paths),
            },
            "revalidation_status": "current" if mutation_baseline.get("status") == "clean-scope" else mutation_baseline.get("status"),
            "mutation_revision": _as_dict(mutation_baseline.get("observed_state")).get("enforcement_fingerprint"),
        },
        "proof": {
            "proof_obligation_id": proof_detail_route,
            "status": "required-before-claim" if proof_required else "not-required",
            "receipt_status": "pending" if proof_required else "not-required",
        },
        "executor": {
            "binding_fingerprint": _as_dict(authority_envelope.get("authority_resolution")).get("resolution_fingerprint")
            or _as_dict(mutation_baseline.get("observed_state")).get("enforcement_fingerprint"),
            "availability_status": "available",
            "invocation_revision": "implement.context",
            "status": "available",
        },
    }
    invocation = operation_invocation(
        operation_id="implement.context",
        arguments={"target": ".", "changed": changed_paths, "task_present": bool(task_present)},
        effect_class="derived-output",
        authority_class="implement-context-owned",
        expected_transition="run-focused-proof" if proof_required else "inspect-changed-paths",
        preconditions={
            "planning_gate_result": str(planning_gate.get("gate_result") or ""),
            "scope_fingerprint": scope_fingerprint,
        },
        command_rendering="agentic-workspace implement --changed <paths> --format json",
    )
    bound_invocation = bind_operation_invocation_to_authorities(invocation=invocation, authorities=authorities)
    decision = compile_operating_decision(
        inputs={
            "revisions": {
                "planning_gate": authorities["planning_owner"]["owner_revision"],
                "mutation": authorities["mutation_baseline"]["mutation_revision"],
                "proof": proof_detail_route,
            },
            "authorities": authorities,
            "current_work": {"id": "direct-work", "changed_scope_fingerprint": scope_fingerprint},
            "selected_owner": {"id": "direct-work", "source": "planning_safety_gate"},
            "terminal_state": "continue",
            "actionability": {"next_action": {"action": "implement", "operation_invocation": bound_invocation}},
            "blocked_claim_classes": ["full_completion_until_proof"],
            "provenance": {
                "typed_invocation": "actionability.operation_invocation",
                "decision_compiler": "operating_decision.compile_operating_decision",
                "authority_sources": [
                    "planning_safety_gate",
                    "authority_envelope",
                    "authority_envelope.mutation_baseline",
                    "operating_loop.verification",
                ],
            },
        }
    )
    return {
        "kind": "agentic-workspace/ordinary-operation-sources/v1",
        "producer_module": "agentic_workspace.operating_decision",
        "status": "admitted" if decision.get("status") == "actionable" else "inactive",
        "typed_invocation": bound_invocation,
        "operating_decision": decision,
    }


def compile_operating_decision(*, inputs: dict[str, Any]) -> dict[str, Any]:
    """Return one primary typed action or one typed external blocker."""

    revisions = _as_dict(inputs.get("revisions"))
    authorities = _as_dict(inputs.get("authorities"))
    actionability = _as_dict(inputs.get("actionability"))
    action = _as_dict(actionability.get("next_action") or inputs.get("primary_action"))
    progress_check = _as_dict(actionability.get("progress_check"))
    invocation = _as_dict(action.get("operation_invocation"))
    invocation_expected_revision = str(invocation.get("expected_input_revision") or "").strip()
    embedded_invocation_revision = invocation_decision_input_revision(invocation) if invocation else ""
    invocation_current_revision = (
        live_decision_input_revision(invocation=invocation, authorities=authorities)
        if invocation and authorities
        else embedded_invocation_revision
    )
    blockers = [item for item in _as_list(inputs.get("blockers")) if isinstance(item, dict)]
    authority_blockers = derive_operating_blockers_from_authorities(authorities=authorities)
    blockers.extend(authority_blockers)
    if (
        invocation
        and not authority_blockers
        and _invocation_requires_mutation_baseline(invocation)
        and not _mutation_baseline_is_current(_as_dict(authorities.get("mutation_baseline")))
    ):
        blockers.append(
            {
                "reason_code": "stale-mutation-baseline",
                "owner": "mutation authority",
                "repair": "resolve and revalidate a live mutation baseline before admitting this typed action",
            }
        )
    for gap in _as_list(inputs.get("context_gaps")):
        if isinstance(gap, dict) and str(gap.get("severity") or "") == "blocking":
            blockers.append({"reason_code": "context-coverage-gap", "owner": gap.get("owner", ""), "repair": gap.get("next_route", "")})
    if (
        not invocation
        and action
        and str(action.get("action") or "") not in {"no-immediate-action", ""}
        and progress_check.get("result") != "rejected-stale-action"
    ):
        blockers.append(
            {
                "reason_code": "missing-authority",
                "owner": "operation-invocation",
                "repair": "attach a typed operation_invocation before treating this action as executable",
            }
        )
    if progress_check.get("result") == "rejected-stale-action" and not authority_blockers:
        blockers.append(
            {
                "reason_code": "stale-revision",
                "owner": "operation-invocation",
                "repair": "refresh the operating decision and rebuild the typed action from current owner/context/proof state",
            }
        )
    elif (
        invocation
        and not authority_blockers
        and (not invocation_expected_revision or invocation_expected_revision != invocation_current_revision)
    ):
        blockers.append(
            {
                "reason_code": "stale-revision",
                "owner": "operation-invocation",
                "repair": "refresh the operating decision and rebuild the typed action from current canonical decision inputs",
            }
        )
    if inputs.get("stale_revision"):
        blockers.append({"reason_code": "stale-revision", "owner": "input-revision", "repair": "refresh authoritative input projection"})
    if inputs.get("conflict"):
        blockers.append(
            {"reason_code": "conflicting-input", "owner": "conflicting authorities", "repair": "resolve specialist input conflict"}
        )
    if inputs.get("denied_effect"):
        blockers.append(
            {"reason_code": "denied-effect", "owner": "effect authority", "repair": "select an allowed effect or request authority"}
        )
    if inputs.get("stale_mutation_baseline"):
        blockers.append({"reason_code": "stale-mutation-baseline", "owner": "mutation authority", "repair": "refresh mutation baseline"})
    if inputs.get("stale_proof"):
        blockers.append({"reason_code": "stale-proof", "owner": "proof authority", "repair": "rerun or re-record selected proof"})
    blockers.sort(
        key=lambda item: (
            BLOCKER_PRECEDENCE.index(str(item.get("reason_code"))) if str(item.get("reason_code")) in BLOCKER_PRECEDENCE else 99
        )
    )
    blocker = blockers[0] if blockers else {}
    if blocker:
        status = "blocked"
        primary_action: dict[str, Any] = {}
        external_blocker = {
            "kind": "agentic-workspace/operating-decision-blocker/v1",
            "reason_code": str(blocker.get("reason_code") or "blocked"),
            "owner": str(blocker.get("owner") or "workspace-maintainer"),
            "repair": str(blocker.get("repair") or "refresh or resolve the owning authority"),
        }
    else:
        status = "actionable" if invocation else "terminal"
        primary_action = action if invocation else {}
        external_blocker = {}
    identity_input = {
        "revisions": revisions,
        "action": invocation,
        "blocker": external_blocker,
        "terminal_state": inputs.get("terminal_state", ""),
        "live_decision_input_revision": invocation_current_revision,
    }
    coverage = context_authority_coverage()
    requested_consumer = str(inputs.get("consumer") or "operating-decision")
    context_authority_projection = resolve_context_authority_projection(
        consumer=requested_consumer,
        task=str(inputs.get("task") or ""),
        changed_paths=[str(path) for path in _as_list(inputs.get("changed_paths"))],
        target_root=Path(str(inputs["target_root"])) if inputs.get("target_root") else None,
        source_records=_as_dict(inputs.get("authority_sources")) or _as_dict(inputs.get("authorities")),
    )
    # Context admission is an authority gate, not advisory route decoration.
    # A typed action cannot remain actionable when one of its registered
    # required inputs is absent, stale, ambiguous, or otherwise unadmitted.
    if context_authority_projection["status"] == "repair-required":
        status = "blocked"
        primary_action = {}
        external_blocker = {
            "kind": "agentic-workspace/operating-decision-blocker/v1",
            "reason_code": "context-authority-unavailable",
            "owner": "context-authority-registry",
            "repair": "run the typed context-authority repair operation before retrying the decision",
        }
        identity_input["blocker"] = external_blocker
    input_revisions = {
        **revisions,
        **(
            {
                "embedded_action_revision": embedded_invocation_revision,
                "live_authority_revision": invocation_current_revision,
            }
            if invocation
            else {}
        ),
    }
    return {
        "kind": "agentic-workspace/operating-decision/v1",
        "producer_module": "agentic_workspace.operating_decision",
        "producer_function": "compile_operating_decision",
        "decision_id": f"operating-decision:{_digest(identity_input)[:16]}",
        "status": status,
        "input_revisions": input_revisions,
        "canonical_decision_input_revision": invocation_current_revision,
        "context_authority_coverage": coverage,
        "context_authority_projection": context_authority_projection,
        "current_work": _as_dict(inputs.get("current_work")),
        "selected_owner": _as_dict(inputs.get("selected_owner")),
        "terminal_state": str(inputs.get("terminal_state") or "CONTINUE"),
        "primary_action": primary_action,
        "action_identity": {
            "kind": "agentic-workspace/typed-action-identity/v1",
            "operation_invocation": invocation,
            "requested_mutation_boundary": _as_dict(invocation.get("requested_mutation_boundary"))
            or _as_dict(invocation.get("mutation_boundary")),
            "expected_input_revision": invocation_current_revision,
            "revision_source": "live-authority-resolver" if authorities else "embedded-invocation",
        }
        if invocation
        else {},
        "external_blocker": external_blocker,
        "blocked_claim_classes": _as_list(inputs.get("blocked_claim_classes")),
        "provenance": _as_dict(inputs.get("provenance")),
        "replacement_map": {
            "next_action.command": "display rendering only; operation_invocation owns executable identity",
            "actionability.progress_check.proposed_operation": "derived from operation_invocation.operation_id",
            "startup/implement/proof claim gates": "consume operating decision status and blocker reason codes",
        },
        "rule": "This compiler composes admitted specialist outputs and preserves their ownership; it does not infer authority from rendered text.",
    }
