from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_FRICTION_LARGE_FILE_THRESHOLD = 400
REPO_FRICTION_CONCEPT_SURFACE_THRESHOLD = 200
REPO_FRICTION_MAX_HOTSPOTS = 5
REPO_FRICTION_SCAN_SUFFIXES = {
    ".md",
    ".py",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
}
REPO_FRICTION_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
    "dist",
    "build",
}


def output_contract_payload(
    *,
    optimization_bias: str,
    optimization_bias_source: str,
    bias_payload: dict[str, Any],
    surface: str,
) -> dict[str, Any]:
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
        "report_density": bias_payload["report_density"],
        "residue_density": bias_payload["residue_density"],
        "rendered_view_style": bias_payload["rendered_view_style"],
        "must_not_change": list(bias_payload["does_not_affect"]),
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
            "docs/capability-aware-execution.md",
            "task-shape and capability-fit rules",
            0.89,
            ["docs/capability-aware-execution.md"],
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

    if (target_root / "TODO.md").exists():
        _add_candidate(
            planning_candidates,
            surface="TODO.md",
            reason="active queue carries the current work slice",
            confidence=0.94,
            refs=["TODO.md"],
        )
    if active_todo_surface and active_todo_surface != "TODO.md" and (target_root / active_todo_surface).exists():
        _add_candidate(
            planning_candidates,
            surface=active_todo_surface,
            reason="active execplan carries the current bounded work slice",
            confidence=0.96,
            refs=[active_todo_surface, "TODO.md"],
        )

    if (target_root / "ROADMAP.md").exists():
        _add_candidate(
            ambiguous,
            surface="ROADMAP.md",
            reason="long-horizon follow-ons should not be seeded without promotion",
            confidence=0.82,
            refs=["ROADMAP.md"],
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


def repo_friction_payload(
    *,
    target_root: Path,
    improvement_latitude: str,
    improvement_latitude_source: str,
    policy_payload: dict[str, Any],
    boundary_test_payload: dict[str, Any],
    external_setup_findings_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    hotspots = _repo_friction_hotspots(target_root=target_root)
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
    evidence_classes = ["large_file_hotspots", "concept_surface_hotspots"]
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
        "initiative_posture": policy_payload["initiative_posture"],
        "rule": policy_payload["reporting_rule"],
        "reporting_destinations": policy_payload["reporting_destinations"],
        "decision_test": boundary_test_payload,
        "evidence_classes": evidence_classes,
        "large_file_hotspots": {
            "threshold_lines": REPO_FRICTION_LARGE_FILE_THRESHOLD,
            "count": len(large_file_hotspots),
            "items": large_file_hotspots,
        },
        "concept_surface_hotspots": {
            "threshold_lines": REPO_FRICTION_CONCEPT_SURFACE_THRESHOLD,
            "count": len(concept_hotspots),
            "items": concept_hotspots,
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
    if relative_path in {
        "AGENTS.md",
        "TODO.md",
        "ROADMAP.md",
        "llms.txt",
        "agentic-workspace.toml",
    }:
        return "front-door"
    if relative_path.startswith("docs/execplans/"):
        return "planning-state"
    if relative_path.startswith("docs/"):
        return "canonical-doc"
    if relative_path.startswith("tools/"):
        return "generated-maintainer-surface"
    if relative_path.startswith(".agentic-workspace/"):
        return "managed-surface"
    return "repo-surface"


def _repo_friction_hotspots(*, target_root: Path) -> list[dict[str, Any]]:
    hotspots: list[dict[str, Any]] = []
    for path in sorted(target_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in REPO_FRICTION_SKIP_DIRS or part.startswith(".uv-cache") for part in path.parts):
            continue
        if path.suffix.lower() not in REPO_FRICTION_SCAN_SUFFIXES:
            continue
        try:
            line_count = sum(1 for _ in path.open("r", encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
        if line_count < REPO_FRICTION_CONCEPT_SURFACE_THRESHOLD:
            continue
        relative = path.relative_to(target_root).as_posix()
        hotspots.append(
            {
                "path": relative,
                "line_count": line_count,
                "kind": _repo_friction_kind_for_path(path),
                "surface_role": _repo_friction_surface_role(relative),
            }
        )
    hotspots.sort(key=lambda item: (-int(item["line_count"]), str(item["path"])))
    return hotspots


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
