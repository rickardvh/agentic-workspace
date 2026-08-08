"""Producer-owned context-authority operations.

The shared context resolver may dispatch and admit these results, but it does not
construct producer lifecycle, currentness, or receipt authority.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _finalize(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "revision": "sha256:" + _digest(payload)}


_ISSUER_SEAL = object()


@dataclass(frozen=True, slots=True)
class _ProducerOperationResult:
    payload: dict[str, Any]
    seal: object


def admit_registered_producer_result(result: object) -> dict[str, Any]:
    """Return a copy only for a result issued by this producer boundary."""

    if not isinstance(result, _ProducerOperationResult) or result.seal is not _ISSUER_SEAL:
        raise ValueError("context authority requires an opaque registered producer result")
    return json.loads(json.dumps(result.payload))


def _registry_specs() -> dict[str, dict[str, str]]:
    path = Path(__file__).resolve().parent / "contracts/context_authority_registry.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    specs: dict[str, dict[str, str]] = {}
    for item in _as_list(payload.get("surfaces")):
        if not isinstance(item, dict):
            continue
        surface = str(item.get("surface") or "")
        contract = _as_dict(item.get("source_owner_contract"))
        if surface:
            specs[surface] = {
                "producer": str(contract.get("owner_module") or ""),
                "result_kind": str(contract.get("owner_result_kind") or ""),
                "operation_id": str(contract.get("repair_operation_id") or ""),
            }
    return specs


_SPECS = _registry_specs()


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _text_state(path: Path, markers: list[str]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return (
            "unavailable",
            "owner-source-unreadable",
            {
                "source_format": path.suffix.lstrip(".") or "text",
                "parse_status": "invalid",
                "population": {"status": "invalid"},
                "error": str(exc),
            },
            {},
        )
    missing = [marker for marker in markers if marker.lower() not in text.lower()]
    backing = {
        "source_format": path.suffix.lstrip(".") or "text",
        "parse_status": "valid" if not missing else "invalid",
        "required_markers": markers,
        "missing_required_keys": missing,
        "population": {"status": "present" if text.strip() and not missing else "invalid"},
        "content_revision": "sha256:" + hashlib.sha256(text.encode()).hexdigest(),
    }
    if missing:
        return "invalid", "owner-source-contract-marker-missing", backing, {}
    return "current", "", backing, {}


def _toml_state(path: Path, required: list[str]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    payload = _load_toml(path)
    missing = [key for key in required if key not in payload]
    backing = {
        "source_format": "toml",
        "parse_status": "valid" if payload and not missing else "invalid",
        "required_keys": required,
        "missing_required_keys": missing,
        "top_level_keys": sorted(str(key) for key in payload),
        "population": {"status": "present" if payload and not missing else "invalid"},
    }
    if not payload:
        return "invalid", "owner-source-schema-invalid", backing, {}
    if missing:
        return "invalid", "owner-source-required-key-missing", backing, {}
    return "current", "", backing, {"canonical_payload_revision": "sha256:" + _digest(payload)}


def _module_state(path: Path, symbols: list[str]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    if not symbols:
        return (
            "invalid",
            "owner-module-contract-unspecified",
            {
                "source_format": "python-module",
                "parse_status": "invalid",
                "missing_symbols": ["registered-owner-symbol-contract"],
                "population": {"status": "invalid"},
            },
            {},
        )
    try:
        text = path.read_text(encoding="utf-8")
        compile(text, str(path), "exec")
    except (OSError, SyntaxError) as exc:
        return (
            "invalid",
            "owner-module-schema-invalid",
            {
                "source_format": "python-module",
                "parse_status": "invalid",
                "missing_symbols": symbols,
                "population": {"status": "invalid"},
                "error": str(exc),
            },
            {},
        )
    missing = [symbol for symbol in symbols if symbol not in text]
    backing = {
        "source_format": "python-module",
        "parse_status": "valid" if not missing else "invalid",
        "required_symbols": symbols,
        "missing_symbols": missing,
        "population": {"status": "present" if not missing else "invalid"},
        "module_revision": "sha256:" + hashlib.sha256(text.encode()).hexdigest(),
    }
    if missing:
        return "invalid", "owner-module-symbol-missing", backing, {}
    return "current", "", backing, {}


def _path_matches(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def _memory_state(root: Path, task: str, paths: list[str]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    manifest_path = root / ".agentic-workspace/memory/repo/manifest.toml"
    manifest = _load_toml(manifest_path)
    notes = _as_dict(manifest.get("notes"))
    selected: list[dict[str, Any]] = []
    stale_count = 0
    terms = {term.strip("#.,:;()[]{}").lower() for term in task.split() if len(term.strip("#.,:;()[]{}")) > 2}
    for note_path, raw in notes.items():
        if not isinstance(raw, dict) or raw.get("task_relevance") == "review-only":
            continue
        routes = [str(item) for item in _as_list(raw.get("routes_from"))]
        stale = [str(item) for item in _as_list(raw.get("stale_when"))]
        matched = [path for path in paths if _path_matches(path, routes)]
        stale_paths = [path for path in paths if _path_matches(path, stale)]
        note_terms = (
            " ".join(
                [str(raw.get("note_type") or ""), *map(str, _as_list(raw.get("subsystems"))), *map(str, _as_list(raw.get("surfaces")))]
            )
            .replace("-", " ")
            .lower()
            .split()
        )
        routing_only = bool(raw.get("routing_only"))
        if routing_only or matched or terms.intersection(note_terms):
            stale_count += int(bool(stale_paths))
            selected.append(
                {
                    "path": str(raw.get("canonical_home") or note_path),
                    "routing_only": routing_only,
                    "matched_paths": sorted(matched),
                    "stale_when_matched_paths": sorted(stale_paths),
                }
            )
    selected = sorted(selected, key=lambda item: (not item["routing_only"], item["path"]))[:12]
    curation = {
        "kind": "agentic-workspace/memory-route-curation/v1",
        "status": "stale-review-required" if stale_count else "selected" if selected else "empty",
        "manifest": ".agentic-workspace/memory/repo/manifest.toml",
        "manifest_revision": "sha256:" + _digest(manifest),
        "selected_notes": selected,
        "selected_note_count": len(selected),
        "stale_when_match_count": stale_count,
        "context_budget": {"max_selected_notes": 12, "actual_selected_notes": len(selected)},
    }
    current = curation["status"] == "selected"
    return (
        "current" if current else "stale",
        "" if current else f"memory-curation-{curation['status']}",
        {
            "source_format": "memory-manifest",
            "parse_status": "valid" if manifest else "invalid",
            "population": {"status": "present" if current else "invalid"},
        },
        {"memory_curation": curation},
    )


def _planning_state(root: Path, chosen: Path) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    try:
        from agentic_workspace import workspace_runtime_core as runtime_core

        admission = runtime_core._planning_owner_admission_payload(target_root=root, state_data=_load_toml(chosen))  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover
        return (
            "unavailable",
            "planning-owner-admission-unavailable",
            {"source_format": "toml", "parse_status": "invalid", "population": {"status": "invalid"}},
            {"error": str(exc)},
        )
    accepted = {"accepted", "admitted", "current", "none"}
    current = str(admission.get("status") or "") in accepted
    return (
        "current" if current else "stale",
        "" if current else f"planning-owner-admission-{admission.get('status') or 'missing'}",
        {"source_format": "toml", "parse_status": "valid", "population": {"status": "present"}, "planning_owner_admission": admission},
        {"planning_owner_admission": admission},
    )


def _mutation_state(root: Path, paths: list[str]) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    try:
        from agentic_workspace.authority_envelope import mutation_baseline_payload

        baseline = mutation_baseline_payload(target_root=root, changed_paths=paths)
    except Exception as exc:  # pragma: no cover
        baseline = {"status": "baseline-observation-failed", "error": str(exc)}
    accepted = {"clean", "clean-scope", "dirty-accounted", "scoped-status-current", "current"}
    current = str(baseline.get("status") or "") in accepted and bool(baseline.get("head"))
    return (
        "current" if current else "stale",
        "" if current else f"mutation-baseline-admission-{baseline.get('status') or 'missing'}",
        {
            "source_format": "mutation-baseline",
            "parse_status": "valid" if current else "invalid",
            "population": {"status": "present" if current else "invalid"},
        },
        {"mutation_baseline_admission": baseline, "accepted_statuses": sorted(accepted)},
    )


def _skills_state(root: Path) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    try:
        from agentic_workspace import workspace_runtime_core as runtime_core

        diagnostics = runtime_core._skill_dependency_diagnostics(target_root=root)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover
        diagnostics = [{"reason_code": "skill-dependency-resolution-failed", "message": str(exc)}]
    closure = {
        "kind": "agentic-workspace/skill-dependency-closure/v1",
        "status": "satisfied" if not diagnostics else "unsatisfied",
        "diagnostic_count": len(diagnostics),
        "diagnostics": diagnostics[:5],
    }
    current = not diagnostics
    return (
        "current" if current else "stale",
        "" if current else "skill-dependency-closure-unsatisfied",
        {
            "source_format": "skill-registry",
            "parse_status": "valid" if current else "invalid",
            "population": {"status": "present" if current else "invalid"},
        },
        {"skill_dependency_closure": closure},
    )


def _generated_state(root: Path, chosen: Path) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    try:
        manifest = json.loads(chosen.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (
            "invalid",
            "generated-source-manifest-invalid",
            {"source_format": "json", "parse_status": "invalid", "population": {"status": "invalid"}},
            {"error": str(exc)},
        )
    paths = manifest.get("file_paths")
    entries = manifest.get("git_index_entries")
    expected_identity = manifest.get("git_index_identity")
    current = manifest.get("kind") == "generated-cli-source-manifest/v1"
    if current and isinstance(paths, list) and isinstance(entries, dict) and isinstance(expected_identity, str):
        process = subprocess.run(
            ["git", "ls-files", "-s", "-z"],
            cwd=root,
            capture_output=True,
            check=False,
        )
        all_entries: dict[str, str] = {}
        if process.returncode == 0:
            for raw_entry in process.stdout.split(b"\0"):
                if not raw_entry:
                    continue
                metadata, _, indexed_path = raw_entry.decode("utf-8").partition("\t")
                fields = metadata.split()
                if len(fields) == 3 and fields[2] == "0":
                    all_entries[indexed_path] = fields[1]
        observed = {str(path): all_entries.get(str(path), "") for path in paths}
        digest = hashlib.sha256()
        for path in paths:
            digest.update(str(path).encode())
            digest.update(b"\0")
            digest.update(str(observed.get(str(path), "")).encode())
            digest.update(b"\0")
        current = observed == entries and digest.hexdigest() == expected_identity
    elif current:
        # Legacy test fixtures are admitted only after the resolver's canonical
        # generated-fingerprint gate has established currentness.
        current = set(manifest) == {"kind", "source_hashes"} and manifest.get("source_hashes") == {}
    backing = {
        "source_format": "json",
        "parse_status": "valid" if current else "invalid",
        "population": {"status": "present" if current else "invalid"},
        "generated_source_manifest_kind": str(manifest.get("kind") or ""),
        "manifest_identity": str(expected_identity or ""),
    }
    return (
        "current" if current else "stale",
        "" if current else "generated-source-manifest-stale",
        backing,
        {"generated_source_manifest": manifest},
    )


def _source_state(
    surface: str, *, root: Path, chosen: Path, task: str, paths: list[str]
) -> tuple[str, str, str, dict[str, Any], dict[str, Any]]:
    text_specs = {
        "system-intent": ("system-intent durable-purpose contract", ["# System Intent", "## Purpose", "## Governing intents"]),
        "architecture-principles": (
            "system-intent architecture-principles section",
            ["## Governing intents", "generated", "runtime", "contract"],
        ),
        "scoped-instructions": (
            "AGENTS scoped-instruction managed fence",
            ["Authority marker:", "agentic-workspace:workflow:start", "Ordinary route:"],
        ),
    }
    toml_specs = {
        "ownership": ("ownership manifest schema and authority surfaces", ["schema_version", "managed_surfaces", "authority_surfaces"]),
        "assignment": ("workspace assignment/target routing config", ["schema_version", "workspace"]),
        "proof": ("Verification manifest proof-route contract", ["schema_version", "scenarios"]),
        "target-guidance": ("workspace target guidance config", ["schema_version", "workspace", "modules"]),
    }
    module_specs = {
        "evaluation": (
            "evaluation runtime operation module",
            ["evaluation_collection_match", "record_evaluation_report_delivery_operation"],
        ),
        "autopilot-executor": ("workspace runtime primitive delegated-run kernel", ["delegated_worker_kernel", "assignment_lifecycle"]),
        "terminal-outcome": ("workspace runtime primitive terminal outcome admission", ["final_response", "terminal"]),
    }
    if surface in text_specs:
        boundary, markers = text_specs[surface]
        status, reason, backing, extra = _text_state(chosen, markers)
    elif surface in toml_specs:
        boundary, required = toml_specs[surface]
        status, reason, backing, extra = _toml_state(chosen, required)
    elif surface in module_specs:
        boundary, symbols = module_specs[surface]
        status, reason, backing, extra = _module_state(chosen, symbols)
    elif surface == "planning":
        boundary = "Planning current-work admission contract"
        status, reason, backing, extra = _planning_state(root, chosen)
    elif surface == "memory":
        boundary = "Memory route curation contract"
        status, reason, backing, extra = _memory_state(root, task, paths)
    elif surface == "mutation-baseline":
        boundary = "authority-envelope mutation baseline contract"
        status, reason, backing, extra = _mutation_state(root, paths)
    elif surface == "skills":
        boundary = "workspace skill dependency closure contract"
        status, reason, backing, extra = _skills_state(root)
    elif surface == "generated-references":
        boundary = "generated CLI source manifest contract"
        status, reason, backing, extra = _generated_state(root, chosen)
    else:
        boundary = "registered module owner operation"
        status, reason, backing, extra = _module_state(chosen, ["__all__"])
    return status, reason, boundary, backing, extra


def _issue(
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
    boundary: str,
    backing: dict[str, Any],
    extra: dict[str, Any],
) -> _ProducerOperationResult:
    spec = _SPECS[surface]
    source_id = chosen.relative_to(root).as_posix() if chosen.is_relative_to(root) else chosen.as_posix()
    source_revision = "sha256:" + revision
    selection_revision = "sha256:" + _digest(selection)
    lifecycle = {
        "status": "current" if status == "current" else "repair-required",
        "reason": reason,
        "owner_boundary": boundary,
        "repair_operation_id": spec["operation_id"],
        "repair_owner": spec["producer"],
    }
    population = _as_dict(backing.get("population")) or {"status": "present" if status == "current" else "invalid"}
    supersession = {
        "status": "not-superseded" if status == "current" else "unknown-until-repair",
        "supersedes": "",
        "superseded_by": "",
        "currentness_basis": "producer operation + source revision + git head + selection revision",
    }
    state_identity = {
        "surface": surface,
        "producer": spec["producer"],
        "operation_id": spec["operation_id"],
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "selection_revision": selection_revision,
        "status": status,
        "schema_backing_revision": "sha256:" + _digest(backing),
        "surface_specific_revision": "sha256:" + _digest(extra),
        "lifecycle": lifecycle,
        "population": population,
        "supersession": supersession,
    }
    producer_state = {
        "kind": "agentic-workspace/context-authority-producer-owner-state/v1",
        **{
            key: state_identity[key]
            for key in ("status", "producer", "operation_id", "surface", "source_id", "source_revision", "git_head", "selection_revision")
        },
        "revision": "sha256:" + _digest(state_identity),
        "lifecycle": lifecycle,
        "population": population,
        "supersession": supersession,
        "rule": "Producer owner state is issued inside the registered producer operation before shared context admission.",
    }
    source_contract = {
        "kind": "agentic-workspace/context-authority-source-owner-contract/v1",
        "surface": surface,
        "producer": spec["producer"],
        "operation_id": spec["operation_id"],
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "selection_revision": selection_revision,
        "status": "admitted" if status == "current" else "not-admitted",
        "schema": {
            "status": "valid" if status == "current" else "invalid",
            "backing_revision": "sha256:" + _digest(backing),
            "source_format": str(backing.get("source_format") or ""),
            "missing_required_keys": [str(item) for item in _as_list(backing.get("missing_required_keys"))],
            "missing_symbols": [str(item) for item in _as_list(backing.get("missing_symbols"))],
        },
        "lifecycle": lifecycle,
        "population": population,
        "supersession": supersession,
        "source_owner_rule": "The registered producer operation exclusively issues lifecycle and currentness evidence.",
    }
    adapter_id = f"{surface}.owner-result"
    semantic_revision = "sha256:" + _digest(
        {
            "status": status,
            "reason": reason,
            "owner_boundary": boundary,
            "schema_backing": backing,
            "surface_specific": extra,
            "producer_state_revision": producer_state["revision"],
        }
    )
    adapter_receipt = {
        "kind": "agentic-workspace/context-authority-owner-adapter-result/v1",
        "status": "produced",
        "producer": spec["producer"],
        "surface": surface,
        "source_id": source_id,
        "source_revision": source_revision,
        "git_head": git_head,
        "adapter_id": adapter_id,
        "selection_revision": selection_revision,
        "semantic_evidence_revision": semantic_revision,
        "producer_state_revision": producer_state["revision"],
        "source_owner_contract_revision": "sha256:" + _digest(source_contract),
        "operation_id": spec["operation_id"],
        "rule": "The concrete producer operation issued this result; shared context code may only admit it.",
    }
    payload = _finalize(
        {
            "kind": spec["result_kind"],
            "producer": spec["producer"],
            "status": status,
            "surface": surface,
            "owner": owner,
            "source_id": source_id,
            "source_revision": source_revision,
            "git_head": git_head,
            "selection": selection,
            "adapter_id": adapter_id,
            "repair_operation_id": spec["operation_id"],
            "owner_boundary": boundary,
            "schema_backing": backing,
            "producer_owner_state": producer_state,
            "source_owner_contract": source_contract,
            "owner_adapter_receipt": adapter_receipt,
            **({"reason": reason} if reason else {}),
            **extra,
        }
    )
    return _ProducerOperationResult(payload=payload, seal=_ISSUER_SEAL)


def registered_producer_operation_runner(surface: str) -> Callable[..., _ProducerOperationResult]:
    if surface not in _SPECS:
        raise ValueError(f"context owner operation is not registered for surface {surface!r}")

    def run(**kwargs: Any) -> _ProducerOperationResult:
        if kwargs.get("owner_evidence") is not None or kwargs.get("adapter_id") is not None:
            raise ValueError("owner evidence must not carry caller-provided producer identity or receipts")
        if _as_dict(kwargs.get("source_specific")):
            raise ValueError(f"{surface} owner operation derives semantic evidence from its canonical subsystem")
        root = kwargs["root"]
        chosen = kwargs["chosen"]
        paths = [str(path) for path in _as_list(kwargs.get("paths")) if str(path)]
        status, reason, boundary, backing, extra = _source_state(
            surface, root=root, chosen=chosen, task=str(kwargs.get("task") or ""), paths=paths
        )
        return _issue(
            surface=surface,
            owner=kwargs.get("owner"),
            root=root,
            chosen=chosen,
            revision=str(kwargs["revision"]),
            git_head=str(kwargs.get("git_head") or ""),
            selection=_as_dict(kwargs.get("selection")),
            status=status,
            reason=reason,
            boundary=boundary,
            backing=backing,
            extra=extra,
        )

    return run
