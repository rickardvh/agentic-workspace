"""Registered context-authority owner-operation front doors."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

_CONTEXT_AUTHORITY_REGISTRY_RESOURCE = "context_authority_registry.json"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _finalize_owner_result(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **payload,
        "revision": "sha256:"
        + _digest({key: value for key, value in payload.items() if key != "revision" and not str(key).endswith("_debug")}),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _source_owner_authority_contract(
    *,
    surface: str,
    producer: str,
    operation_id: str,
    source_id: str,
    source_revision: str,
    git_head: str,
    status: str,
    schema_backing: dict[str, Any],
    selection: dict[str, Any],
    producer_state: dict[str, Any],
) -> dict[str, Any]:
    schema_status = "valid" if status == "current" else "invalid"
    if schema_backing.get("parse_status") in {"valid", "invalid"}:
        schema_status = str(schema_backing.get("parse_status"))
    lifecycle = _as_dict(producer_state.get("lifecycle"))
    population = _as_dict(producer_state.get("population"))
    supersession = _as_dict(producer_state.get("supersession"))
    if not lifecycle or not population or not supersession:
        raise ValueError("producer owner state must carry lifecycle, population, and supersession")
    return {
        "kind": "agentic-workspace/context-authority-source-owner-contract/v1",
        "surface": surface,
        "producer": producer,
        "operation_id": operation_id,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "selection_revision": "sha256:" + _digest(selection),
        "status": "admitted" if status == "current" else "not-admitted",
        "schema": {
            "status": schema_status,
            "backing_revision": "sha256:" + _digest(schema_backing),
            "source_format": str(schema_backing.get("source_format") or ""),
            "missing_required_keys": [str(item) for item in _as_list(schema_backing.get("missing_required_keys"))],
            "missing_symbols": [str(item) for item in _as_list(schema_backing.get("missing_symbols"))],
        },
        "lifecycle": lifecycle,
        "population": population,
        "supersession": supersession,
        "source_owner_rule": (
            "Every registered context-authority surface must publish schema, lifecycle, population, and supersession "
            "evidence from its producer-owned operation before ordinary consumers may treat it as current."
        ),
    }


def _source_id_for(root: Path, chosen: Path) -> str:
    return chosen.relative_to(root).as_posix() if chosen.is_relative_to(root) else chosen.as_posix()


def _file_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _load_toml_dict(path: Path) -> dict[str, Any]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _text_contract(path: Path, markers: list[str]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return (
            "unavailable",
            "owner-source-unreadable",
            {"source_format": path.suffix.lower().lstrip(".") or "text", "error": str(exc)},
            {"population": {"status": "invalid"}},
        )
    lowered = text.lower()
    missing = [marker for marker in markers if marker.lower() not in lowered]
    backing = {
        "source_format": path.suffix.lower().lstrip(".") or "text",
        "contract_markers": markers,
        "matched_markers": sorted(set(markers) - set(missing)),
        "line_count": len(text.splitlines()),
        "population": {"status": "present" if not missing else "invalid"},
    }
    return ("current", "", backing, {}) if not missing else ("invalid", "owner-source-contract-marker-missing", backing, {})


def _toml_contract(path: Path, required_keys: list[str]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    payload = _load_toml_dict(path)
    missing_keys = [key for key in required_keys if key not in payload]
    backing = {
        "source_format": "toml",
        "parse_status": "valid" if payload else "invalid",
        "top_level_keys": sorted(str(key) for key in payload)[:20],
        "required_keys": required_keys,
        "missing_required_keys": missing_keys,
        "population": {"status": "present" if payload and not missing_keys else "invalid"},
    }
    if not payload:
        return "invalid", "owner-source-schema-invalid", backing, {}
    if missing_keys:
        return "invalid", "owner-source-required-key-missing", backing, {}
    return "current", "", backing, {}


def _module_contract(path: Path, symbols: list[str]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return (
            "unavailable",
            "owner-source-unreadable",
            {"source_format": "python-module", "error": str(exc), "population": {"status": "invalid"}},
            {},
        )
    missing = [symbol for symbol in symbols if symbol not in text]
    backing = {
        "source_format": "python-module",
        "required_symbols": symbols,
        "matched_symbols": sorted(set(symbols) - set(missing)),
        "missing_symbols": missing,
        "population": {"status": "present" if not missing else "invalid"},
    }
    return ("current", "", backing, {}) if not missing else ("invalid", "owner-module-symbol-missing", backing, {})


def _reject_caller_semantic_inputs(kwargs: dict[str, Any]) -> None:
    if "owner_evidence" in kwargs or "adapter_id" in kwargs:
        raise ValueError("owner evidence must not carry caller-provided producer identity or receipts")


def _reject_caller_source_specific(surface: str, kwargs: dict[str, Any]) -> None:
    if _as_dict(kwargs.get("source_specific")):
        raise ValueError(f"{surface} owner operation derives semantic evidence from its canonical subsystem")


def _producer_owner_state(
    *,
    surface: str,
    producer: str,
    operation_id: str,
    source_id: str,
    source_revision: str,
    git_head: str,
    selection: dict[str, Any],
    status: str,
    reason: str,
    owner_boundary: str,
    schema_backing: dict[str, Any],
    surface_specific: dict[str, Any],
) -> dict[str, Any]:
    population = _as_dict(schema_backing.get("population"))
    if not population:
        population = {"status": "present" if status == "current" else "invalid"}
    lifecycle = {
        "status": "current" if status == "current" else "repair-required",
        "reason": reason,
        "owner_boundary": owner_boundary,
        "repair_operation_id": operation_id,
        "repair_owner": producer,
    }
    supersession = {
        "status": "not-superseded" if status == "current" else "unknown-until-repair",
        "supersedes": "",
        "superseded_by": "",
        "currentness_basis": "selected source id + source revision + git head + selection revision",
    }
    producer_result_identity = {
        "surface": surface,
        "producer": producer,
        "operation_id": operation_id,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "selection_revision": "sha256:" + _digest(selection),
        "status": status,
        "schema_backing_revision": "sha256:" + _digest(schema_backing),
        "surface_specific_revision": "sha256:" + _digest(surface_specific),
        "lifecycle": lifecycle,
        "population": population,
        "supersession": supersession,
    }
    return {
        "kind": "agentic-workspace/context-authority-producer-owner-state/v1",
        "status": status,
        "producer": producer,
        "operation_id": operation_id,
        "surface": surface,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "selection_revision": producer_result_identity["selection_revision"],
        "revision": "sha256:" + _digest(producer_result_identity),
        "lifecycle": lifecycle,
        "population": population,
        "supersession": supersession,
        "rule": "Producer owner state is issued by the selected owner-operation adapter before shared context admission.",
    }


def _path_matches_any(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def _memory_route_curation(root: Path, *, task: str, paths: list[str]) -> dict[str, Any]:
    manifest_path = root / ".agentic-workspace/memory/repo/manifest.toml"
    manifest = _load_toml_dict(manifest_path)
    notes = _as_dict(manifest.get("notes"))
    selected: list[dict[str, Any]] = []
    stale_match_count = 0
    review_only_excluded_count = 0
    routing_index = ".agentic-workspace/memory/repo/index.md"
    task_terms = {term.strip("#.,:;()[]{}").lower() for term in task.split() if len(term.strip("#.,:;()[]{}")) > 2}
    for note_path, raw_note in notes.items():
        if not isinstance(raw_note, dict):
            continue
        if str(raw_note.get("task_relevance") or "").strip() == "review-only":
            review_only_excluded_count += 1
            continue
        canonical_home = str(raw_note.get("canonical_home") or note_path)
        routes_from = [str(pattern) for pattern in _as_list(raw_note.get("routes_from")) if str(pattern)]
        stale_when = [str(pattern) for pattern in _as_list(raw_note.get("stale_when")) if str(pattern)]
        matched_paths = [path for path in paths if _path_matches_any(path, routes_from)]
        stale_paths = [path for path in paths if _path_matches_any(path, stale_when)]
        note_terms = {
            str(value).lower()
            for value in [
                raw_note.get("note_type"),
                *[str(item) for item in _as_list(raw_note.get("subsystems"))],
                *[str(item) for item in _as_list(raw_note.get("surfaces"))],
            ]
            if str(value)
        }
        task_matched = bool(task_terms & {part for term in note_terms for part in term.replace("-", " ").split()})
        routing_only = bool(raw_note.get("routing_only")) or canonical_home == routing_index
        if routing_only or matched_paths or task_matched:
            if stale_paths:
                stale_match_count += 1
            selected.append(
                {
                    "path": canonical_home,
                    "note_type": str(raw_note.get("note_type") or ""),
                    "authority": str(raw_note.get("authority") or ""),
                    "task_relevance": str(raw_note.get("task_relevance") or ""),
                    "routing_only": routing_only,
                    "matched_paths": sorted(matched_paths),
                    "stale_when_matched_paths": sorted(stale_paths),
                }
            )
    if not selected and (root / routing_index).exists():
        selected.append(
            {
                "path": routing_index,
                "note_type": "routing",
                "authority": "canonical",
                "task_relevance": "required",
                "routing_only": True,
                "matched_paths": [],
                "stale_when_matched_paths": [],
                "fallback": "legacy-manifest-routing-index",
            }
        )
    selected = sorted(selected, key=lambda item: (not bool(item.get("routing_only")), str(item.get("path") or "")))[:12]
    return {
        "kind": "agentic-workspace/memory-route-curation/v1",
        "status": "stale-review-required" if stale_match_count else "selected" if selected else "empty",
        "manifest": ".agentic-workspace/memory/repo/manifest.toml",
        "total_note_count": len(notes),
        "selected_note_count": len(selected),
        "selected_notes": selected,
        "stale_when_match_count": stale_match_count,
        "review_only_excluded_count": review_only_excluded_count,
        "context_budget": {"max_selected_notes": 12, "actual_selected_notes": len(selected)},
        "repair_operation_id": "memory.route.report",
        "rule": (
            "Memory authority is admitted as a compact manifest-routed note set. A selected note with stale_when matches is "
            "review-required and must not be admitted as current context until the Memory owner refreshes or excludes it."
        ),
    }


def _load_registry_contract() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "contracts" / _CONTEXT_AUTHORITY_REGISTRY_RESOURCE
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


_REGISTRY_CONTRACT = _load_registry_contract()
_OWNER_OPERATION_SPECS: dict[str, dict[str, str]] = {}
for _item in _as_list(_REGISTRY_CONTRACT.get("surfaces")):
    if not isinstance(_item, dict):
        continue
    _surface = str(_item.get("surface") or "")
    _owner_contract = _as_dict(_item.get("source_owner_contract"))
    if not _surface:
        continue
    _OWNER_OPERATION_SPECS[_surface] = {
        "producer": str(_owner_contract.get("owner_module") or ""),
        "result_kind": str(_owner_contract.get("owner_result_kind") or ""),
        "operation_id": str(_owner_contract.get("repair_operation_id") or f"context-authority.{_surface}.refresh-source"),
    }


def _admit_context_owner_operation_result(
    *,
    surface: str,
    owner: str | None,
    root: Path,
    chosen: Path,
    source_revision: str,
    git_head: str,
    selection: dict[str, Any],
    adapter_id: str,
    owner_result: dict[str, Any],
) -> dict[str, Any]:
    """Admit a result produced by a registered concrete owner adapter."""

    spec = _OWNER_OPERATION_SPECS.get(surface)
    if not spec or not spec.get("producer") or not spec.get("result_kind") or not spec.get("operation_id"):
        raise ValueError(f"context owner operation is not registered for surface {surface!r}")
    producer = spec["producer"]
    result_kind = spec["result_kind"]
    operation_id = spec["operation_id"]
    source_id = chosen.relative_to(root).as_posix() if chosen.is_relative_to(root) else chosen.as_posix()
    owner_result = dict(owner_result)
    if owner_result.get("producer") != producer:
        raise ValueError("owner operation result producer does not match registered owner")
    if owner_result.get("kind") != result_kind:
        raise ValueError("owner operation result kind does not match registered owner")
    if owner_result.get("repair_operation_id") != operation_id:
        raise ValueError("owner operation result id does not match registered owner")
    if owner_result.get("source_revision") != source_revision:
        raise ValueError("owner operation result source revision is stale")
    if owner_result.get("git_head") != git_head:
        raise ValueError("owner operation result git head is stale")
    if owner_result.get("adapter_id") != adapter_id:
        raise ValueError("owner operation result adapter id does not match selected owner adapter")
    if owner_result.get("owner_operation") or owner_result.get("owner_execution_receipt"):
        raise ValueError("owner operation result must not carry caller-provided operation receipts")
    adapter_receipt = _as_dict(owner_result.get("owner_adapter_receipt"))
    if adapter_receipt.get("kind") != "agentic-workspace/context-authority-owner-adapter-result/v1":
        raise ValueError("owner operation result is missing concrete adapter receipt")
    if adapter_receipt.get("status") != "produced":
        raise ValueError("owner operation adapter receipt was not produced")
    adapter_expectations = {
        "producer": producer,
        "surface": surface,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "operation_id": operation_id,
        "selection_revision": "sha256:" + _digest(selection),
    }
    for key, expected in adapter_expectations.items():
        if adapter_receipt.get(key) != expected:
            raise ValueError(f"owner operation adapter receipt {key.replace('_', ' ')} does not match")
    structural_backing = _as_dict(owner_result.get("schema_backing"))
    boundary = str(owner_result.get("owner_boundary") or "")
    if not structural_backing or not boundary:
        raise ValueError("context owner operation payload must provide owner boundary and schema backing")
    producer_state = _as_dict(owner_result.get("producer_owner_state"))
    if producer_state.get("kind") != "agentic-workspace/context-authority-producer-owner-state/v1":
        raise ValueError("owner operation result is missing producer owner state")
    producer_state_expectations = {
        "producer": producer,
        "surface": surface,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "operation_id": operation_id,
        "selection_revision": "sha256:" + _digest(selection),
    }
    for key, expected in producer_state_expectations.items():
        if producer_state.get(key) != expected:
            raise ValueError(f"producer owner state {key.replace('_', ' ')} does not match")
    if producer_state.get("status") != owner_result.get("status"):
        raise ValueError("producer owner state status does not match owner result")
    expected_state_revision = "sha256:" + _digest(
        {
            "surface": surface,
            "producer": producer,
            "operation_id": operation_id,
            "source_id": source_id,
            "source_revision": source_revision,
            "git_head": git_head,
            "selection_revision": "sha256:" + _digest(selection),
            "status": owner_result.get("status"),
            "schema_backing_revision": "sha256:" + _digest(structural_backing),
            "surface_specific_revision": "sha256:"
            + _digest(
                {
                    key: value
                    for key, value in owner_result.items()
                    if key
                    not in {
                        "kind",
                        "producer",
                        "status",
                        "surface",
                        "owner",
                        "source_id",
                        "source_revision",
                        "git_head",
                        "selection",
                        "adapter_id",
                        "repair_operation_id",
                        "owner_boundary",
                        "schema_backing",
                        "producer_owner_state",
                        "source_owner_contract",
                        "owner_adapter_receipt",
                        "revision",
                        "reason",
                    }
                }
            ),
            "lifecycle": _as_dict(producer_state.get("lifecycle")),
            "population": _as_dict(producer_state.get("population")),
            "supersession": _as_dict(producer_state.get("supersession")),
        }
    )
    if producer_state.get("revision") != expected_state_revision:
        raise ValueError("producer owner state revision does not match current producer payload")
    source_owner_contract = _as_dict(owner_result.get("source_owner_contract"))
    if source_owner_contract.get("kind") != "agentic-workspace/context-authority-source-owner-contract/v1":
        raise ValueError("owner operation result is missing source owner authority contract")
    contract_expectations = {
        "surface": surface,
        "producer": producer,
        "operation_id": operation_id,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "selection_revision": "sha256:" + _digest(selection),
    }
    for key, expected in contract_expectations.items():
        if source_owner_contract.get(key) != expected:
            raise ValueError(f"source owner authority contract {key.replace('_', ' ')} does not match")
    if source_owner_contract.get("status") != "admitted":
        raise ValueError("source owner authority contract was not admitted")
    if not _as_dict(source_owner_contract.get("schema")) or not _as_dict(source_owner_contract.get("lifecycle")):
        raise ValueError("source owner authority contract must carry schema and lifecycle evidence")
    if not _as_dict(source_owner_contract.get("population")) or not _as_dict(source_owner_contract.get("supersession")):
        raise ValueError("source owner authority contract must carry population and supersession evidence")
    if adapter_receipt.get("source_owner_contract_revision") != "sha256:" + _digest(source_owner_contract):
        raise ValueError("owner operation adapter receipt source owner contract revision does not match")
    if adapter_receipt.get("producer_state_revision") != producer_state.get("revision"):
        raise ValueError("owner operation adapter receipt producer state revision does not match")
    result_payload_revision = str(owner_result.get("revision") or "")
    schema_backing_revision = "sha256:" + _digest(structural_backing)
    adapter_receipt_revision = "sha256:" + _digest(adapter_receipt)
    source_owner_contract_revision = "sha256:" + _digest(source_owner_contract)
    operation_identity = {
        "operation_id": operation_id,
        "producer": producer,
        "surface": surface,
        "owner": owner,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "selection_revision": "sha256:" + _digest(selection),
        "schema_backing_revision": schema_backing_revision,
        "adapter_receipt_revision": adapter_receipt_revision,
        "source_owner_contract_revision": source_owner_contract_revision,
        "result_payload_revision": result_payload_revision,
    }
    run_id = "sha256:" + _digest(operation_identity)
    receipt_identity = {
        **operation_identity,
        "run_id": run_id,
        "executor": f"agentic_workspace.context_authority_owner_operations.{operation_id}",
        "receipt_schema": "src/agentic_workspace/contracts/schemas/context_authority_owner_result.schema.json",
    }
    receipt_id = "sha256:" + _digest(receipt_identity)
    owner_execution_receipt = {
        "kind": "agentic-workspace/context-authority-owner-execution-receipt/v1",
        "status": "executed",
        "current_state": "current",
        "receipt_id": receipt_id,
        "run_id": run_id,
        "operation_id": operation_id,
        "producer": producer,
        "surface": surface,
        "owner": owner,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "selection_revision": operation_identity["selection_revision"],
        "schema_backing_revision": schema_backing_revision,
        "adapter_receipt_revision": adapter_receipt_revision,
        "source_owner_contract_revision": source_owner_contract_revision,
        "result_payload_revision": result_payload_revision,
        "executor": receipt_identity["executor"],
        "receipt_schema": receipt_identity["receipt_schema"],
        "supersedes": "",
        "current_resolution": {
            "kind": "agentic-workspace/context-authority-current-resolution/v1",
            "status": "current",
            "resolution_mode": "deterministic-source-revision",
            "receipt_index_ref": f"context-authority-current:{surface}:{source_id}",
            "recompute_inputs": [
                "operation_id",
                "producer",
                "surface",
                "source_id",
                "source_revision",
                "git_head",
                "selection_revision",
                "schema_backing_revision",
                "adapter_receipt_revision",
                "source_owner_contract_revision",
                "result_payload_revision",
            ],
            "rule": "Receipt currentness is re-resolved from producer-owned operation identity and current source revision; no process-local map is authoritative.",
        },
        "admission_rule": "Only this registered owner-operation front door can construct the producer-owned receipt.",
    }
    owner_operation = {
        "kind": "agentic-workspace/context-authority-owner-operation/v1",
        "status": "executed",
        "operation_id": operation_id,
        "run_id": run_id,
        "receipt_id": receipt_id,
        "producer": producer,
        "surface": surface,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "selection_revision": operation_identity["selection_revision"],
        "schema_backing_revision": schema_backing_revision,
        "adapter_receipt_revision": adapter_receipt_revision,
        "source_owner_contract_revision": source_owner_contract_revision,
        "result_payload_revision": result_payload_revision,
        "admission_rule": (
            "Context authority admits current results only from a registered owner-operation front-door receipt. "
            "Checked-in owner-result JSON and caller-constructed receipts are evidence only; currentness is recomputable across processes."
        ),
    }
    admitted_result = _finalize_owner_result(
        {
            **owner_result,
            "owner_boundary": boundary,
            "schema_backing": structural_backing,
            "source_owner_contract": source_owner_contract,
            "owner_operation": owner_operation,
            "owner_execution_receipt": owner_execution_receipt,
        }
    )
    return admitted_result


def _complete_owner_operation_result(
    *,
    surface: str,
    owner: str | None,
    root: Path,
    chosen: Path,
    revision: str,
    git_head: str,
    selection: dict[str, Any],
    status: str,
    reason: str,
    owner_boundary: str,
    schema_backing: dict[str, Any],
    task: str = "",
    paths: list[str] | None = None,
    surface_specific: dict[str, Any] | None = None,
    source_specific: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ = (task, paths)
    if _as_dict(source_specific):
        raise ValueError(f"{surface} owner operation derives semantic evidence from its canonical subsystem")
    source_revision = "sha256:" + revision
    spec = _OWNER_OPERATION_SPECS.get(surface)
    if not spec or not spec.get("producer") or not spec.get("result_kind") or not spec.get("operation_id"):
        raise ValueError(f"context owner operation is not registered for surface {surface!r}")
    expected_source_id = _source_id_for(root, chosen)
    structural_backing = _as_dict(schema_backing)
    owner_boundary = str(owner_boundary or "")
    if not structural_backing or not owner_boundary:
        raise ValueError("context owner operation must provide owner boundary and schema backing")
    adapter_id = f"{surface}.owner-result"
    status = str(status or "current")
    reason = str(reason or "")
    surface_specific = _as_dict(surface_specific)
    producer_state = _producer_owner_state(
        surface=surface,
        producer=spec["producer"],
        operation_id=spec["operation_id"],
        source_id=expected_source_id,
        source_revision=source_revision,
        git_head=git_head,
        selection=selection,
        status=status,
        reason=reason,
        owner_boundary=owner_boundary,
        schema_backing=structural_backing,
        surface_specific=surface_specific,
    )
    semantic_evidence_revision = "sha256:" + _digest(
        {
            "status": status,
            "reason": reason,
            "owner_boundary": owner_boundary,
            "schema_backing": structural_backing,
            "surface_specific": surface_specific,
            "producer_state_revision": producer_state["revision"],
        }
    )
    source_owner_contract = _source_owner_authority_contract(
        surface=surface,
        producer=spec["producer"],
        operation_id=spec["operation_id"],
        source_id=expected_source_id,
        source_revision=source_revision,
        git_head=git_head,
        status=status,
        schema_backing=structural_backing,
        selection=selection,
        producer_state=producer_state,
    )
    adapter_receipt = {
        "kind": "agentic-workspace/context-authority-owner-adapter-result/v1",
        "status": "produced",
        "producer": spec["producer"],
        "surface": surface,
        "source_id": expected_source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "selection_revision": "sha256:" + _digest(selection),
        "semantic_evidence_revision": semantic_evidence_revision,
        "producer_state_revision": producer_state["revision"],
        "source_owner_contract_revision": "sha256:" + _digest(source_owner_contract),
        "operation_id": spec["operation_id"],
        "rule": "Concrete owner-operation front doors produce semantic payloads and adapter receipts from their selected canonical source.",
    }
    owner_result = _finalize_owner_result(
        {
            "kind": spec["result_kind"],
            "producer": spec["producer"],
            "status": status,
            "surface": surface,
            "owner": owner,
            "source_id": expected_source_id,
            "source_revision": source_revision,
            "git_head": git_head,
            "selection": selection,
            "adapter_id": adapter_id,
            "repair_operation_id": spec["operation_id"],
            "owner_boundary": owner_boundary,
            "schema_backing": structural_backing,
            "producer_owner_state": producer_state,
            "source_owner_contract": source_owner_contract,
            "owner_adapter_receipt": adapter_receipt,
            **({"reason": reason} if reason else {}),
            **surface_specific,
        }
    )
    if status != "current":
        return owner_result
    return _admit_context_owner_operation_result(
        surface=surface,
        owner=owner,
        root=root,
        chosen=chosen,
        source_revision=source_revision,
        git_head=git_head,
        selection=selection,
        adapter_id=adapter_id,
        owner_result=owner_result,
    )


def _system_intent_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    status, reason, backing, extra = _text_contract(kwargs["chosen"], ["# System Intent", "## Purpose", "## Governing intents"])
    return _complete_owner_operation_result(
        surface="system-intent",
        status=status,
        reason=reason,
        owner_boundary="system-intent durable-purpose contract",
        schema_backing=backing,
        surface_specific={**extra, **_as_dict(kwargs.get("source_specific"))},
        **kwargs,
    )


def _architecture_principles_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    status, reason, backing, extra = _text_contract(kwargs["chosen"], ["## Governing intents", "generated", "runtime", "contract"])
    return _complete_owner_operation_result(
        surface="architecture-principles",
        status=status,
        reason=reason,
        owner_boundary="system-intent architecture-principles section",
        schema_backing=backing,
        surface_specific={**extra, **_as_dict(kwargs.get("source_specific"))},
        **kwargs,
    )


def _scoped_instructions_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    status, reason, backing, extra = _text_contract(
        kwargs["chosen"], ["Authority marker:", "agentic-workspace:workflow:start", "Ordinary route:"]
    )
    return _complete_owner_operation_result(
        surface="scoped-instructions",
        status=status,
        reason=reason,
        owner_boundary="AGENTS scoped-instruction managed fence",
        schema_backing=backing,
        surface_specific={**extra, **_as_dict(kwargs.get("source_specific"))},
        **kwargs,
    )


def _ownership_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    status, reason, backing, extra = _toml_contract(kwargs["chosen"], ["schema_version", "managed_surfaces", "authority_surfaces"])
    return _complete_owner_operation_result(
        surface="ownership",
        status=status,
        reason=reason,
        owner_boundary="ownership manifest schema and authority surfaces",
        schema_backing=backing,
        surface_specific={**extra, **_as_dict(kwargs.get("source_specific"))},
        **kwargs,
    )


def _assignment_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    status, reason, backing, extra = _toml_contract(kwargs["chosen"], ["schema_version", "workspace"])
    return _complete_owner_operation_result(
        surface="assignment",
        status=status,
        reason=reason,
        owner_boundary="workspace assignment/target routing config",
        schema_backing=backing,
        surface_specific={**extra, **_as_dict(kwargs.get("source_specific"))},
        **kwargs,
    )


def _evaluation_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    status, reason, backing, extra = _module_contract(
        kwargs["chosen"], ["evaluation_collection_match", "record_evaluation_report_delivery_operation"]
    )
    return _complete_owner_operation_result(
        surface="evaluation",
        status=status,
        reason=reason,
        owner_boundary="evaluation runtime operation module",
        schema_backing=backing,
        surface_specific={**extra, **_as_dict(kwargs.get("source_specific"))},
        **kwargs,
    )


def _proof_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    status, reason, backing, extra = _toml_contract(kwargs["chosen"], ["schema_version", "scenarios"])
    return _complete_owner_operation_result(
        surface="proof",
        status=status,
        reason=reason,
        owner_boundary="Verification manifest proof-route contract",
        schema_backing=backing,
        surface_specific={**extra, **_as_dict(kwargs.get("source_specific"))},
        **kwargs,
    )


def _autopilot_executor_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    status, reason, backing, extra = _module_contract(kwargs["chosen"], ["delegated_worker_kernel", "assignment_lifecycle"])
    return _complete_owner_operation_result(
        surface="autopilot-executor",
        status=status,
        reason=reason,
        owner_boundary="workspace runtime primitive delegated-run kernel",
        schema_backing=backing,
        surface_specific={**extra, **_as_dict(kwargs.get("source_specific"))},
        **kwargs,
    )


def _target_guidance_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    status, reason, backing, extra = _toml_contract(kwargs["chosen"], ["schema_version", "workspace", "modules"])
    return _complete_owner_operation_result(
        surface="target-guidance",
        status=status,
        reason=reason,
        owner_boundary="workspace target guidance config",
        schema_backing=backing,
        surface_specific={**extra, **_as_dict(kwargs.get("source_specific"))},
        **kwargs,
    )


def _terminal_outcome_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    status, reason, backing, extra = _module_contract(kwargs["chosen"], ["final_response", "terminal"])
    return _complete_owner_operation_result(
        surface="terminal-outcome",
        status=status,
        reason=reason,
        owner_boundary="workspace runtime primitive terminal outcome admission",
        schema_backing=backing,
        surface_specific={**extra, **_as_dict(kwargs.get("source_specific"))},
        **kwargs,
    )


def _module_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    status, reason, backing, extra = _module_contract(kwargs["chosen"], [])
    return _complete_owner_operation_result(
        surface="module",
        status=status,
        reason=reason,
        owner_boundary="registered module owner operation",
        schema_backing=backing,
        surface_specific={**extra, **_as_dict(kwargs.get("source_specific"))},
        **kwargs,
    )


def _planning_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    chosen = kwargs["chosen"]
    try:
        from agentic_workspace import workspace_runtime_core as runtime_core

        state_data = _load_toml_dict(chosen)
        admission = runtime_core._planning_owner_admission_payload(target_root=kwargs["root"], state_data=state_data)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - defensive, owner adapter availability is environment-specific.
        return _complete_owner_operation_result(
            surface="planning",
            status="unavailable",
            reason="planning-owner-admission-unavailable",
            owner_boundary="Planning current-work admission contract",
            schema_backing={"source_format": "toml", "parse_status": "unavailable"},
            surface_specific={"error": str(exc)},
            **kwargs,
        )
    admission_status = str(admission.get("status") or "")
    accepted_statuses = {"accepted", "admitted", "current", "none"}
    status = "current" if admission_status in accepted_statuses else "stale"
    return _complete_owner_operation_result(
        surface="planning",
        status=status,
        reason="" if status == "current" else f"planning-owner-admission-{admission_status or 'missing'}",
        owner_boundary="Planning current-work admission contract",
        schema_backing={"source_format": "toml", "planning_owner_admission": admission, "accepted_statuses": sorted(accepted_statuses)},
        surface_specific={"planning_owner_admission": admission, "accepted_statuses": sorted(accepted_statuses)},
        **kwargs,
    )


def _memory_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    _reject_caller_source_specific("memory", kwargs)
    paths = [str(path) for path in _as_list(kwargs.get("paths")) if str(path)]
    curation = _memory_route_curation(kwargs["root"], task=str(kwargs.get("task") or ""), paths=paths)
    curation_status = str(curation.get("status") or "")
    current = curation_status == "selected"
    return _complete_owner_operation_result(
        surface="memory",
        status="current" if current else "stale",
        reason="" if current else f"memory-curation-{curation_status or 'missing'}",
        owner_boundary="Memory route curation contract",
        schema_backing={"source_format": "memory-manifest", "memory_curation": curation},
        surface_specific={"memory_curation": curation},
        **kwargs,
    )


def _mutation_baseline_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    _reject_caller_source_specific("mutation-baseline", kwargs)
    paths = [str(path) for path in _as_list(kwargs.get("paths")) if str(path)]
    try:
        from agentic_workspace.authority_envelope import mutation_baseline_payload

        baseline = mutation_baseline_payload(target_root=kwargs["root"], changed_paths=paths)
        admission = {
            "kind": "agentic-workspace/context-authority-owner-admission/v1",
            "owner_module": "agentic_workspace.authority_envelope",
            "status": str(baseline.get("status") or ""),
            "baseline_id": str(baseline.get("baseline_id") or ""),
            "head": str(baseline.get("head") or ""),
            "scope": _as_dict(baseline.get("scope")),
            "identity": _as_dict(baseline.get("identity")),
        }
    except Exception as exc:  # pragma: no cover - defensive, exercised by runtime integration.
        admission = {
            "kind": "agentic-workspace/context-authority-owner-admission/v1",
            "owner_module": "agentic_workspace.authority_envelope",
            "status": "baseline-observation-failed",
            "error": str(exc),
        }
    status = str(admission.get("status") or "")
    accepted_statuses = {"clean", "clean-scope", "dirty-accounted", "scoped-status-current", "current"}
    current = status in accepted_statuses
    return _complete_owner_operation_result(
        surface="mutation-baseline",
        status="current" if current else "stale",
        reason="" if current else f"mutation-baseline-admission-{status or 'missing'}",
        owner_boundary="authority-envelope mutation baseline contract",
        schema_backing={
            "source_format": "mutation-baseline",
            "mutation_baseline_admission": admission,
            "accepted_statuses": sorted(accepted_statuses),
        },
        surface_specific={"mutation_baseline_admission": admission, "accepted_statuses": sorted(accepted_statuses)},
        **kwargs,
    )


def _skills_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    _reject_caller_source_specific("skills", kwargs)
    try:
        from agentic_workspace import workspace_runtime_core as runtime_core

        diagnostics = runtime_core._skill_dependency_diagnostics(target_root=kwargs["root"])  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - defensive, exercised by runtime integration.
        diagnostics = [{"reason_code": "skill-dependency-resolution-failed", "message": str(exc)}]
    closure = {
        "kind": "agentic-workspace/skill-dependency-closure/v1",
        "status": "satisfied" if not diagnostics else "unsatisfied",
        "diagnostic_count": len(diagnostics),
        "diagnostics": diagnostics[:5],
        "resolver": "agentic_workspace.workspace_runtime_core._skill_dependency_diagnostics",
    }
    satisfied = closure.get("status") == "satisfied"
    return _complete_owner_operation_result(
        surface="skills",
        status="current" if satisfied else "stale",
        reason="" if satisfied else "skill-dependency-closure-unsatisfied",
        owner_boundary="workspace skill dependency closure contract",
        schema_backing={"source_format": "skill-registry", "skill_dependency_closure": closure},
        surface_specific={"skill_dependency_closure": closure},
        **kwargs,
    )


def _generated_references_owner_operation(**kwargs: Any) -> dict[str, Any]:
    _reject_caller_semantic_inputs(kwargs)
    chosen = kwargs["chosen"]
    try:
        manifest = json.loads(chosen.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _complete_owner_operation_result(
            surface="generated-references",
            status="invalid",
            reason="generated-source-manifest-invalid",
            owner_boundary="generated command package source manifest",
            schema_backing={"source_format": "json", "parse_status": "invalid"},
            surface_specific={"error": str(exc)},
            **kwargs,
        )
    manifest_current = manifest.get("kind") == "generated-cli-source-manifest/v1"
    return _complete_owner_operation_result(
        surface="generated-references",
        status="current" if manifest_current else "stale",
        reason="" if manifest_current else "generated-source-manifest-stale",
        owner_boundary="generated CLI source manifest contract",
        schema_backing={"source_format": "json", "generated_source_manifest_kind": str(manifest.get("kind") or "")},
        surface_specific={"generated_source_manifest": manifest},
        **kwargs,
    )


_CONTEXT_OWNER_OPERATION_RUNNERS = {
    "system-intent": _system_intent_owner_operation,
    "architecture-principles": _architecture_principles_owner_operation,
    "scoped-instructions": _scoped_instructions_owner_operation,
    "ownership": _ownership_owner_operation,
    "assignment": _assignment_owner_operation,
    "evaluation": _evaluation_owner_operation,
    "proof": _proof_owner_operation,
    "autopilot-executor": _autopilot_executor_owner_operation,
    "target-guidance": _target_guidance_owner_operation,
    "terminal-outcome": _terminal_outcome_owner_operation,
    "module": _module_owner_operation,
    "planning": _planning_owner_operation,
    "memory": _memory_owner_operation,
    "mutation-baseline": _mutation_baseline_owner_operation,
    "skills": _skills_owner_operation,
    "generated-references": _generated_references_owner_operation,
}


def registered_context_owner_operation_runner(surface: str):
    runner = _CONTEXT_OWNER_OPERATION_RUNNERS.get(surface)
    if runner is None:
        raise ValueError(f"context owner operation is not registered for surface {surface!r}")
    return runner


def registered_context_owner_receipt_status(
    *,
    owner_operation: dict[str, Any],
    receipt: dict[str, Any],
    result_revision: str,
    root: Path | None = None,
) -> tuple[bool, str]:
    receipt_id = str(receipt.get("receipt_id") or "")
    if not receipt_id.startswith("sha256:"):
        return False, "owner-operation-receipt-id-missing"
    current_resolution = _as_dict(receipt.get("current_resolution"))
    if current_resolution.get("status") != "current":
        return False, "owner-operation-current-resolution-missing"
    if current_resolution.get("resolution_mode") != "deterministic-source-revision":
        return False, "owner-operation-current-resolution-unsupported"
    operation_identity = {
        "operation_id": receipt.get("operation_id"),
        "producer": receipt.get("producer"),
        "surface": receipt.get("surface"),
        "owner": receipt.get("owner"),
        "source_id": receipt.get("source_id"),
        "source_revision": receipt.get("source_revision"),
        "git_head": receipt.get("git_head"),
        "adapter_id": receipt.get("adapter_id"),
        "selection_revision": receipt.get("selection_revision"),
        "schema_backing_revision": receipt.get("schema_backing_revision"),
        "adapter_receipt_revision": receipt.get("adapter_receipt_revision"),
        "source_owner_contract_revision": receipt.get("source_owner_contract_revision"),
        "result_payload_revision": receipt.get("result_payload_revision"),
    }
    expected_run_id = "sha256:" + _digest(operation_identity)
    receipt_identity = {
        **operation_identity,
        "run_id": expected_run_id,
        "executor": receipt.get("executor"),
        "receipt_schema": receipt.get("receipt_schema"),
    }
    expected_receipt_id = "sha256:" + _digest(receipt_identity)
    if receipt.get("run_id") != expected_run_id or owner_operation.get("run_id") != expected_run_id:
        return False, "owner-operation-current-run-mismatch"
    if receipt_id != expected_receipt_id or owner_operation.get("receipt_id") != expected_receipt_id:
        return False, "owner-operation-current-receipt-mismatch"
    if owner_operation.get("adapter_receipt_revision") != receipt.get("adapter_receipt_revision"):
        return False, "owner-operation-adapter-receipt-revision-mismatch"
    if owner_operation.get("source_owner_contract_revision") != receipt.get("source_owner_contract_revision"):
        return False, "owner-operation-source-owner-contract-revision-mismatch"
    if owner_operation.get("result_payload_revision") != receipt.get("result_payload_revision"):
        return False, "owner-operation-current-result-mismatch"
    if root is not None:
        source_id = str(receipt.get("source_id") or "")
        source_path = root / source_id
        if not source_id or not source_path.exists():
            return False, "owner-operation-current-source-missing"
        try:
            current_source_revision = "sha256:" + (
                _digest(
                    {
                        path.relative_to(source_path).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in sorted(source_path.rglob("*"))
                        if path.is_file()
                    }
                )
                if source_path.is_dir()
                else hashlib.sha256(source_path.read_bytes()).hexdigest()
            )
        except OSError:
            return False, "owner-operation-current-source-unreadable"
        if receipt.get("source_revision") != current_source_revision:
            return False, "owner-operation-current-source-stale"
    if not str(result_revision or "").startswith("sha256:"):
        return False, "owner-operation-current-result-mismatch"
    return True, ""
