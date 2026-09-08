"""Repo-owned semantic task routes and current-work-bound agent selections."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from agentic_workspace.current_work_context import resolve_current_work_context

SELECTION_PATH = Path(".agentic-workspace/local/current-task-routes.json")
_ROUTE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)+$")


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def semantic_route_host_context(root: Path, *, task: str, request: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read host work/source facts for Rust; public callers supply only the request."""
    work = resolve_current_work_context(root=root, task=task)
    catalogue = semantic_route_catalogue(root)
    # Work ownership may survive a task switch. Bind the exact supplied task as
    # well, without interpreting its words or tying selection to aggregate HEAD.
    identity = _digest(json.dumps([work["id"], task], separators=(",", ":")))
    return {
        "current_work": {"kind": "current-work", "id": identity},
        "source": {
            "revision": catalogue["source_revision"],
            "routes": [route["id"] for route in catalogue["routes"]] if catalogue["status"] == "current" else [],
        },
        "request": request,
    }


def _registry_paths(root: Path) -> list[Path]:
    candidates = [root / "tools/skills/REGISTRY.json"]
    workspace = root / ".agentic-workspace"
    if workspace.is_dir():
        candidates.extend(workspace.glob("**/skills/REGISTRY.json"))
    return sorted({path.resolve() for path in candidates if path.is_file()}, key=lambda path: path.as_posix())


def semantic_route_catalogue(root: Path) -> dict[str, Any]:
    """Derive route identities from canonical skill declarations, never a peer route registry."""

    declarations: dict[str, dict[str, Any]] = {}
    diagnostics: list[dict[str, str]] = []
    source_material: list[str] = []
    for registry_path in _registry_paths(root):
        try:
            raw_text = registry_path.read_text(encoding="utf-8")
            payload = json.loads(raw_text)
        except (OSError, json.JSONDecodeError) as exc:
            diagnostics.append({"source_ref": registry_path.as_posix(), "code": "invalid-registry", "message": str(exc)})
            continue
        source_ref = registry_path.relative_to(root.resolve()).as_posix()
        source_material.append(f"{source_ref}\0{_digest(raw_text)}")
        skills = payload.get("skills", []) if isinstance(payload, dict) else []
        for raw_skill in skills if isinstance(skills, list) else []:
            if not isinstance(raw_skill, dict):
                continue
            skill_id = str(raw_skill.get("id") or "").strip()
            for raw_route in raw_skill.get("semantic_routes", []) if isinstance(raw_skill.get("semantic_routes"), list) else []:
                route = {"id": raw_route} if isinstance(raw_route, str) else raw_route if isinstance(raw_route, dict) else {}
                route_id = str(route.get("id") or "").strip()
                match = str(route.get("match") or "exact").strip()
                description = str(route.get("description") or raw_skill.get("summary") or "").strip()
                if not _ROUTE_ID.fullmatch(route_id) or match not in {"exact", "subtree"}:
                    diagnostics.append(
                        {
                            "source_ref": source_ref,
                            "code": "invalid-semantic-route",
                            "message": f"skill '{skill_id}' has invalid route '{route_id}' or match '{match}'",
                        }
                    )
                    continue
                declaration = declarations.setdefault(
                    route_id,
                    {
                        "id": route_id,
                        "description": description,
                        "match": match,
                        "capabilities": [],
                        "capability_bindings": [],
                        "sources": [],
                    },
                )
                if declaration["match"] != match:
                    diagnostics.append(
                        {
                            "source_ref": source_ref,
                            "code": "route-match-conflict",
                            "message": f"route '{route_id}' is declared with conflicting exact/subtree semantics",
                        }
                    )
                    continue
                if description and not declaration["description"]:
                    declaration["description"] = description
                capability = f"skill:{skill_id}"
                if capability not in declaration["capabilities"]:
                    declaration["capabilities"].append(capability)
                    priority = int(route.get("priority", 100)) if str(route.get("priority", 100)).isdigit() else 100
                    declaration["capability_bindings"].append({"capability": capability, "priority": priority})
                declaration["sources"].append({"source_ref": source_ref, "skill_id": skill_id})
    routes = []
    for route_id in sorted(declarations):
        route = declarations[route_id]
        route["capability_bindings"] = sorted(route["capability_bindings"], key=lambda item: (item["priority"], item["capability"]))
        route["capabilities"] = [item["capability"] for item in route["capability_bindings"]]
        route["sources"] = sorted(route["sources"], key=lambda item: (item["source_ref"], item["skill_id"]))
        routes.append(route)
    return {
        "kind": "agentic-workspace/semantic-task-route-catalogue/v1",
        "status": "invalid" if diagnostics else "current",
        "source_revision": _digest("\n".join(source_material)),
        "route_count": len(routes),
        "routes": routes,
        "diagnostics": diagnostics,
        "ownership": "derived-from-canonical-skill-registries",
        "authority_effect": "applicability-only",
    }


def discover_semantic_routes(root: Path, *, parent: str = "", exact: str = "") -> dict[str, Any]:
    catalogue = semantic_route_catalogue(root)
    routes = list(catalogue["routes"])
    normalized_parent = parent.strip().strip("/")
    normalized_exact = exact.strip().strip("/")
    if normalized_exact:
        matches = [route for route in routes if route["id"] == normalized_exact]
        level = "exact"
    else:
        prefix = f"{normalized_parent}/" if normalized_parent else ""
        children: dict[str, dict[str, Any]] = {}
        for route in routes:
            if prefix and not route["id"].startswith(prefix):
                continue
            suffix = route["id"][len(prefix) :]
            child = suffix.split("/", 1)[0]
            if not child:
                continue
            child_id = f"{prefix}{child}".strip("/")
            item = children.setdefault(child_id, {"id": child_id, "leaf": False, "child_count": 0})
            item["leaf"] = item["leaf"] or route["id"] == child_id
            item["child_count"] += int("/" in suffix)
        matches = [children[key] for key in sorted(children)]
        level = "branch" if normalized_parent else "roots"
    return {
        "kind": "agentic-workspace/semantic-task-route-discovery/v1",
        "status": catalogue["status"],
        "level": level,
        "parent": normalized_parent,
        "exact": normalized_exact,
        "source_revision": catalogue["source_revision"],
        "routes": matches,
        "route_count": len(matches),
        "full_catalogue_emitted": bool(normalized_exact),
        "diagnostics": catalogue["diagnostics"],
        "direct_selection_command": "agentic-workspace instructions select-route --route <known-leaf> --expect-source-revision "
        + catalogue["source_revision"]
        + " --target . --format json",
    }


def _current_work_id(root: Path) -> str:
    context = resolve_current_work_context(root=root, task="")
    return str(context.get("id") or "default").strip() or "default"


def select_semantic_task_routes(
    root: Path,
    *,
    posture: str,
    routes: Iterable[str],
    expected_source_revision: str,
    current_work_id: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    catalogue = semantic_route_catalogue(root)
    current_work = _current_work_id(root)
    requested_work = current_work_id.strip() or current_work
    normalized_routes = sorted({str(route).strip().strip("/") for route in routes if str(route).strip()})
    known = {route["id"] for route in catalogue["routes"]}
    failures: list[str] = []
    if posture not in {"selected", "none", "unresolved"}:
        failures.append("unsupported-posture")
    if expected_source_revision != catalogue["source_revision"]:
        failures.append("route-source-revision-mismatch")
    if requested_work != current_work:
        failures.append("current-work-mismatch")
    if posture == "selected" and not normalized_routes:
        failures.append("selected-routes-required")
    if posture == "none" and normalized_routes:
        failures.append("none-posture-rejects-routes")
    if any(route not in known for route in normalized_routes):
        failures.append("unknown-route")
    if failures:
        return {
            "kind": "agentic-workspace/semantic-task-route-selection/v1",
            "status": "blocked",
            "reason_codes": sorted(set(failures)),
            "current_work_id": current_work,
            "source_revision": catalogue["source_revision"],
            "mutation_applied": False,
            "authority_effect": "none",
        }
    fact = {
        "kind": "agentic-workspace/semantic-task-route-fact/v1",
        "posture": posture,
        "routes": normalized_routes,
        "task_identity": {"kind": "current-work", "id": current_work},
        "current_work_id": current_work,
        "source_revision": catalogue["source_revision"],
        "provenance": "agent-selected",
        "authority_effect": "applicability-only",
    }
    destination = root / SELECTION_PATH
    existing = destination.read_text(encoding="utf-8") if destination.is_file() else ""
    rendered = json.dumps(fact, indent=2) + "\n"
    applied_status = {
        "selected": "selected",
        "none": "classified-none",
        "unresolved": "classified-unresolved",
    }[posture]
    status = "already-current" if existing == rendered else "preview" if dry_run else applied_status
    if not dry_run and existing != rendered:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    return {
        "kind": "agentic-workspace/semantic-task-route-selection/v1",
        "status": status,
        "fact": fact,
        "path": SELECTION_PATH.as_posix(),
        "mutation_applied": not dry_run and existing != rendered,
        "authority_effect": "none",
    }


def current_semantic_task_route_fact(root: Path) -> dict[str, Any]:
    catalogue = semantic_route_catalogue(root)
    current_work = _current_work_id(root)
    path = root / SELECTION_PATH
    if not path.is_file():
        return {
            "kind": "agentic-workspace/semantic-task-route-fact/v1",
            "status": "missing",
            "posture": "unresolved",
            "routes": [],
            "current_work_id": current_work,
            "source_revision": catalogue["source_revision"],
            "authority_effect": "applicability-only",
        }
    try:
        fact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fact = {}
    known = {route["id"] for route in catalogue["routes"]}
    routes = [str(route) for route in fact.get("routes", [])] if isinstance(fact.get("routes"), list) else []
    stale_reasons: list[str] = []
    if fact.get("kind") != "agentic-workspace/semantic-task-route-fact/v1":
        stale_reasons.append("invalid-kind")
    if str(fact.get("current_work_id") or "") != current_work:
        stale_reasons.append("current-work-changed")
    if str(fact.get("source_revision") or "") != catalogue["source_revision"]:
        stale_reasons.append("route-source-changed")
    if any(route not in known for route in routes):
        stale_reasons.append("route-removed")
    posture = str(fact.get("posture") or "unresolved")
    if posture not in {"selected", "none", "unresolved"}:
        stale_reasons.append("invalid-posture")
    return {
        **fact,
        "kind": "agentic-workspace/semantic-task-route-fact/v1",
        "status": "stale" if stale_reasons else "current",
        "posture": posture,
        "routes": routes,
        "current_work_id": current_work,
        "current_source_revision": catalogue["source_revision"],
        "stale_reasons": stale_reasons,
        "authority_effect": "applicability-only",
    }


def route_selector_matches(selector: str, selected_routes: Iterable[str]) -> bool:
    normalized = selector.strip().strip("/")
    selected = {str(route).strip().strip("/") for route in selected_routes}
    if normalized.endswith("/**"):
        prefix = normalized.removesuffix("/**")
        return any(route == prefix or route.startswith(prefix + "/") for route in selected)
    return normalized in selected
