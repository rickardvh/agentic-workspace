"""Memory-owned routed-context authority operation."""

from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path
from typing import Any


def _matches(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def _route_matches(selector: str, selected_routes: set[str]) -> bool:
    normalized = selector.strip().strip("/")
    if normalized.endswith("/**"):
        prefix = normalized.removesuffix("/**")
        return any(route == prefix or route.startswith(prefix + "/") for route in selected_routes)
    return normalized in selected_routes


def _curate(
    root: Path,
    *,
    task: str,
    paths: list[str],
    semantic_route_fact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest_path = root / ".agentic-workspace/memory/repo/manifest.toml"
    try:
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        manifest = {}
    notes_raw = manifest.get("notes")
    notes: dict[str, Any] = notes_raw if isinstance(notes_raw, dict) else {}
    selected: list[dict[str, Any]] = []
    stale_count = 0
    review_only_count = 0
    route_fact = semantic_route_fact or {}
    route_fact_current = route_fact.get("status") == "current" and route_fact.get("posture") == "selected"
    selected_routes = {str(item) for item in route_fact.get("routes", [])} if route_fact_current else set()
    task_terms = {term.strip("#.,:;()[]{}").lower() for term in task.split() if len(term.strip("#.,:;()[]{}")) > 2}
    for note_path, raw in notes.items():
        if not isinstance(raw, dict):
            continue
        if str(raw.get("task_relevance") or "") == "review-only":
            review_only_count += 1
            continue
        canonical = str(raw.get("canonical_home") or note_path)
        routes = [str(item) for item in raw.get("routes_from", []) if str(item)]
        stale_when = [str(item) for item in raw.get("stale_when", []) if str(item)]
        semantic_routes = [str(item) for item in raw.get("semantic_routes", []) if str(item)]
        matched = [path for path in paths if _matches(path, routes)]
        stale = [path for path in paths if _matches(path, stale_when)]
        note_terms = {
            str(value).lower() for value in [raw.get("note_type"), *raw.get("subsystems", []), *raw.get("surfaces", [])] if str(value)
        }
        task_matched = bool(task_terms & {part for term in note_terms for part in term.replace("-", " ").split()})
        matched_semantic_routes = [selector for selector in semantic_routes if _route_matches(selector, selected_routes)]
        routing_only = bool(raw.get("routing_only")) or canonical == ".agentic-workspace/memory/repo/index.md"
        # A route declaration replaces lexical task matching for that note. Legacy
        # task terms remain advisory candidate discovery only for unmigrated notes.
        semantic_relevant = bool(matched_semantic_routes)
        legacy_task_relevant = task_matched and not semantic_routes
        if routing_only or matched or semantic_relevant or legacy_task_relevant:
            stale_count += bool(stale)
            selected.append(
                {
                    "path": canonical,
                    "note_type": str(raw.get("note_type") or ""),
                    "authority": str(raw.get("authority") or ""),
                    "task_relevance": str(raw.get("task_relevance") or ""),
                    "routing_only": routing_only,
                    "matched_paths": sorted(matched),
                    "matched_semantic_routes": sorted(matched_semantic_routes),
                    "relevance_evidence": "semantic-task-route"
                    if semantic_relevant
                    else "path"
                    if matched
                    else "routing-baseline"
                    if routing_only
                    else "legacy-task-hint",
                    "stale_when_matched_paths": sorted(stale),
                }
            )
    selected = sorted(selected, key=lambda item: (not bool(item["routing_only"]), str(item["path"])))[:12]
    return {
        "kind": "agentic-workspace/memory-route-curation/v1",
        "status": "stale-review-required" if stale_count else "selected" if selected else "empty",
        "manifest": ".agentic-workspace/memory/repo/manifest.toml",
        "total_note_count": len(notes),
        "selected_note_count": len(selected),
        "selected_notes": selected,
        "stale_when_match_count": stale_count,
        "review_only_excluded_count": review_only_count,
        "semantic_task_routes": {
            "status": str(route_fact.get("status") or "missing"),
            "posture": str(route_fact.get("posture") or "unresolved"),
            "routes": sorted(selected_routes),
            "authority_effect": "relevance-only",
        },
        "legacy_task_hint_disposition": "advisory-candidate-discovery-for-unmigrated-notes",
        "context_budget": {"max_selected_notes": 12, "actual_selected_notes": len(selected)},
        "repair_operation_id": "memory.route.report",
    }


def memory_context_authority_owner_operation(**kwargs: Any) -> dict[str, Any]:
    if kwargs.get("owner_evidence") is not None or kwargs.get("adapter_id") is not None:
        raise ValueError("owner evidence must not carry caller-provided producer identity or receipts")
    if kwargs.get("source_specific"):
        raise ValueError("memory owner operation derives semantic evidence from its canonical subsystem")
    from agentic_workspace._context_authority_owner_protocol import _issue_owner_result
    from agentic_workspace.semantic_task_routes import current_semantic_task_route_fact

    route_fact = current_semantic_task_route_fact(kwargs["root"])
    curation = _curate(
        kwargs["root"],
        task=str(kwargs.get("task") or ""),
        paths=list(kwargs.get("paths") or []),
        semantic_route_fact=route_fact,
    )
    current = curation["status"] == "selected"
    status = "current" if current else "stale"
    reason = "" if current else f"memory-curation-{curation['status']}"
    producer = "agentic_memory.manifest"
    operation_id = "memory.route.report"
    boundary = "Memory route curation contract"
    population = {"status": "present" if current else "invalid"}
    schema = {
        "source_format": "memory-manifest",
        "parse_status": "valid" if current else "invalid",
        "memory_curation": curation,
        "population": population,
    }
    return _issue_owner_result(
        surface="memory",
        producer=producer,
        result_kind="agentic-workspace/memory-route-curation/v1",
        operation_id=operation_id,
        owner=kwargs.get("owner"),
        root=kwargs["root"],
        chosen=kwargs["chosen"],
        revision=kwargs["revision"],
        git_head=kwargs["git_head"],
        selection=kwargs["selection"],
        status=status,
        reason=reason,
        owner_boundary=boundary,
        schema_backing=schema,
        lifecycle={
            "status": "current" if current else "repair-required",
            "reason": reason,
            "owner_boundary": boundary,
            "repair_operation_id": operation_id,
            "repair_owner": producer,
        },
        population=population,
        supersession={
            "status": "not-superseded" if current else "unknown-until-repair",
            "supersedes": "",
            "superseded_by": "",
            "currentness_basis": "Memory manifest route selection and stale_when evaluation",
        },
        surface_specific={"memory_curation": curation},
        executor="repo_memory_bootstrap.context_authority_owner.memory_context_authority_owner_operation",
    )
