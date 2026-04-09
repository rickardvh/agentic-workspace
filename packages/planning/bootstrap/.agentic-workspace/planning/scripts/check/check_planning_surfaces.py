#!/usr/bin/env python3
"""Advisory planning-surface health check.

Warn when TODO, active execplans, and ROADMAP drift away from the intended
three-layer planning split. This check is advisory and exits with 0.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[4]
TODO_PATH = REPO_ROOT / "TODO.md"
ROADMAP_PATH = REPO_ROOT / "ROADMAP.md"
EXECPLAN_DIR = REPO_ROOT / "docs" / "execplans"

TODO_MAX_LINES = 150
TODO_MAX_NOW_ITEMS = 3
ROADMAP_MAX_LINES = 260
ROADMAP_MAX_CANDIDATES = 8
ROADMAP_MAX_CANDIDATE_SECTION_LINES = 90
DRIFT_LOG_MAX_ENTRIES = 12
DRIFT_LOG_MAX_LINES = 80

WARNING_TODO_SHAPE_DRIFT = "todo_shape_drift"
WARNING_TODO_ACTIVATION_OVERFLOW = "todo_activation_overflow"
WARNING_TODO_MISSING_EXECPLAN_LINKAGE = "todo_missing_execplan_linkage"
WARNING_TODO_PLAN_REQUIRED_HINT = "todo_plan_required_hint"
WARNING_TODO_BROKEN_SURFACE_REFERENCE = "todo_broken_surface_reference"
WARNING_EXECPLAN_STRUCTURE_DRIFT = "execplan_structure_drift"
WARNING_EXECPLAN_MULTIPLE_ACTIVE = "execplan_multiple_active_milestones"
WARNING_EXECPLAN_IMMEDIATE_ACTION_DRIFT = "execplan_immediate_next_action_drift"
WARNING_EXECPLAN_READINESS_DRIFT = "execplan_readiness_drift"
WARNING_EXECPLAN_LOG_DRIFT = "execplan_log_drift"
WARNING_EXECPLAN_NOTEBOOK_DRIFT = "execplan_notebook_drift"
WARNING_EXECPLAN_UNDER_SPECIFIED = "execplan_under_specified"
WARNING_EXECPLAN_ACTIVE_SET_PRESSURE = "execplan_active_set_pressure"
WARNING_ROADMAP_EXECUTION_DRIFT = "roadmap_execution_drift"
WARNING_ROADMAP_MISSING_PROMOTION_SIGNAL = "roadmap_missing_promotion_signal"
WARNING_ROADMAP_MISSING_REOPEN_SIGNAL = "roadmap_missing_reopen_signal"
WARNING_ROADMAP_STALE_CANDIDATE_PRESSURE = "roadmap_stale_candidate_pressure"
WARNING_PROMOTION_LINKAGE_DRIFT = "promotion_linkage_drift"
WARNING_STARTUP_POLICY_DRIFT = "startup_policy_drift"
WARNING_DOCS_SURFACE_ROLE_DRIFT = "docs_surface_role_drift"
WARNING_GENERATED_DOCS_DRIFT = "generated_docs_drift"
WARNING_ARCHIVE_ACCUMULATION_DRIFT = "archive_accumulation_drift"
WARNING_PLANNING_MEMORY_BOUNDARY_BLUR = "planning_memory_boundary_blur"

EXPECTED_EXECPLAN_SECTIONS = [
    "Goal",
    "Non-Goals",
    "Intent Continuity",
    "Required Continuation",
    "Active Milestone",
    "Immediate Next Action",
    "Blockers",
    "Touched Paths",
    "Invariants",
    "Validation Commands",
    "Completion Criteria",
    "Drift Log",
]

EXECUTION_SHAPED_MARKERS = {
    "## active milestone",
    "## immediate next action",
    "## validation commands",
    "## completion criteria",
    "## drift log",
}

PLANNING_FORBIDDEN_TODO_MARKERS = {
    "## active milestone",
    "## validation commands",
    "## completion criteria",
    "## drift log",
}

TODO_FINISHED_WORK_HEADINGS = {
    "added in this pass",
    "completed work",
    "completed this pass",
    "finished work",
}

PROMOTION_SIGNAL_HINTS = (
    "if",
    "when",
    "until",
    "trigger",
    "signal",
    "queue",
    "report",
    "ready",
    "promote",
    "promotion",
)

PROMOTION_REASON_HINTS = (
    "because",
    "after",
    "repeated",
    "reported",
    "report",
    "feedback",
    "dogfooding",
    "surfaced",
    "exposed",
    "friction",
    "false positive",
    "false-positive",
    "regression",
    "failure",
    "failed",
)

GENERATED_DOC_NOTICE_FRAGMENT = "generated file"


class PlanningWarning(NamedTuple):
    warning_class: str
    path: str
    message: str


def _surface_execplan_reference(surface_value: str) -> str | None:
    """Extract a docs/execplans path from TODO Surface text if present."""

    # Markdown links often keep the relative surface in link text.
    inline_path_match = re.search(r"docs/execplans/[A-Za-z0-9._/\-]+\.md", surface_value)
    if inline_path_match:
        return inline_path_match.group(0)

    markdown_target = re.search(r"\]\(([^)]+)\)", surface_value)
    if markdown_target:
        target = markdown_target.group(1)
        target_match = re.search(r"docs/execplans/[A-Za-z0-9._/\-]+\.md", target)
        if target_match:
            return target_match.group(0)

    return None


def _render_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_render_module():
    render_path = Path(__file__).resolve().parents[1] / "render_agent_docs.py"
    spec = importlib.util.spec_from_file_location("workspace_planning_render_agent_docs", render_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load render module from {render_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _section_content(lines: list[str], section_name: str) -> list[str]:
    start = -1
    target = f"## {section_name}".strip().lower()
    for idx, line in enumerate(lines):
        if line.strip().lower() == target:
            start = idx + 1
            break
    if start < 0:
        return []

    end = len(lines)
    for idx in range(start, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break
    return lines[start:end]


def _heading_titles(lines: list[str]) -> set[str]:
    titles: set[str] = set()
    for line in lines:
        if line.startswith("## "):
            titles.add(line[3:].strip().lower())
    return titles


def _count_todo_now_items(lines: list[str]) -> int:
    section = _section_content(lines, "Now")
    if not section:
        return 0

    id_rows = [line for line in section if re.match(r"^\s*-\s*ID\s*:\s*\S+", line)]
    if id_rows:
        return len(id_rows)

    return sum(1 for line in section if re.match(r"^-\s+", line) and not re.match(r"^-\s+\[[ xX]\]\s+", line))


def _todo_item_blocks(lines: list[str]) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not re.match(r"^\s*-\s*ID\s*:\s*\S+", line):
            i += 1
            continue

        block: dict[str, str] = {}
        while i < len(lines):
            row = lines[i]
            if i != 0 and re.match(r"^\s*-\s*ID\s*:\s*\S+", row) and block:
                i -= 1
                break
            match = re.match(r"^\s*(?:-\s*)?([^:]+):\s*(.*)\s*$", row)
            if match:
                key = match.group(1).strip().lower()
                value = match.group(2).strip()
                block[key] = value
            i += 1
            if i >= len(lines):
                break
            if lines[i].strip() == "":
                break
        blocks.append(block)
        i += 1

    return blocks


def _looks_small_direct_task(block: dict[str, str]) -> bool:
    return bool(block.get("next action") and block.get("done when"))


def _direct_task_has_plan_sized_shape(block: dict[str, str]) -> bool:
    allowed = {"id", "status", "surface", "why now", "next action", "done when"}
    extra_fields = {key for key in block if key not in allowed}
    long_fields = any(len(block.get(key, "")) > 160 for key in ("why now", "next action", "done when"))
    execution_markers = re.search(
        r"\b(blocker|blocked|validation|milestone|scope|invariant|phase|rollback|migration|handoff|resume|resumed|restart|recovery|recover|retry|branch|concurrent)\b",
        " ".join(block.get(key, "") for key in allowed),
        re.IGNORECASE,
    )
    return bool(extra_fields or long_fields or execution_markers)


def _check_todo(path: Path, *, repo_root: Path = REPO_ROOT) -> tuple[list[PlanningWarning], set[str], list[dict[str, str]]]:
    warnings: list[PlanningWarning] = []
    active_ids: set[str] = set()
    active_items: list[dict[str, str]] = []
    lines = _read_lines(path)
    text = "\n".join(lines)

    if not lines:
        warnings.append(
            PlanningWarning(
                WARNING_TODO_SHAPE_DRIFT,
                _render_path(path),
                "TODO.md is missing or empty; keep an explicit activation surface.",
            )
        )
        return warnings, active_ids, active_items

    if len(lines) > TODO_MAX_LINES:
        warnings.append(
            PlanningWarning(
                WARNING_TODO_ACTIVATION_OVERFLOW,
                _render_path(path),
                f"TODO.md has {len(lines)} lines; keep it near {TODO_MAX_LINES} lines.",
            )
        )

    now_items = _count_todo_now_items(lines)
    if now_items > TODO_MAX_NOW_ITEMS:
        warnings.append(
            PlanningWarning(
                WARNING_TODO_ACTIVATION_OVERFLOW,
                _render_path(path),
                f"TODO.md has {now_items} items in the Now section; keep at most {TODO_MAX_NOW_ITEMS}.",
            )
        )

    lowered = text.lower()
    for marker in PLANNING_FORBIDDEN_TODO_MARKERS:
        if marker in lowered:
            warnings.append(
                PlanningWarning(
                    WARNING_TODO_SHAPE_DRIFT,
                    _render_path(path),
                    "TODO.md contains execution-contract sections; keep those in execplans.",
                )
            )
            break

    if _heading_titles(lines) & TODO_FINISHED_WORK_HEADINGS:
        warnings.append(
            PlanningWarning(
                WARNING_TODO_SHAPE_DRIFT,
                _render_path(path),
                (
                    "TODO.md contains a finished-work or retrospective section; "
                    "keep completed detail in archived execplans, workflow notes, "
                    "or git history."
                ),
            )
        )

    if re.search(r"(?m)^\s*-\s*\[[ xX]\]\s+", text):
        warnings.append(
            PlanningWarning(
                WARNING_TODO_SHAPE_DRIFT,
                _render_path(path),
                "TODO.md contains checklist-style implementation detail; keep the surface compact.",
            )
        )

    blocks = _todo_item_blocks(lines)
    required_keys = {"id", "status", "surface", "why now"}
    for block in blocks:
        item_id = block.get("id", "")
        status = block.get("status", "").lower()
        surface_raw = block.get("surface", "")
        why_now = block.get("why now", "")

        if item_id and "in-progress" in status:
            active_ids.add(item_id)
            active_items.append(
                {
                    "id": item_id,
                    "surface": surface_raw,
                    "why_now": why_now,
                }
            )

        missing = sorted(key for key in required_keys if key not in block)
        if missing:
            warnings.append(
                PlanningWarning(
                    WARNING_TODO_SHAPE_DRIFT,
                    _render_path(path),
                    f"TODO item '{item_id or '?'}' is missing required fields: {', '.join(missing)}.",
                )
            )

        execplan_ref = _surface_execplan_reference(surface_raw)

        if "in-progress" in status and execplan_ref:
            ref_path = repo_root / execplan_ref
            if "docs/execplans/archive/" in execplan_ref:
                warnings.append(
                    PlanningWarning(
                        WARNING_TODO_BROKEN_SURFACE_REFERENCE,
                        _render_path(path),
                        (
                            f"TODO item '{item_id or '?'}' Surface points at archived plan "
                            f"'{execplan_ref}'; active work must point at a live execplan."
                        ),
                    )
                )
            elif not ref_path.exists():
                warnings.append(
                    PlanningWarning(
                        WARNING_TODO_BROKEN_SURFACE_REFERENCE,
                        _render_path(path),
                        f"TODO item '{item_id or '?'}' Surface references missing execplan path '{execplan_ref}'.",
                    )
                )

        if "in-progress" in status and not execplan_ref and not _looks_small_direct_task(block):
            warnings.append(
                PlanningWarning(
                    WARNING_TODO_MISSING_EXECPLAN_LINKAGE,
                    _render_path(path),
                    f"TODO item '{item_id or '?'}' is in-progress without an execplan-backed Surface.",
                )
            )
        if "in-progress" in status and _looks_small_direct_task(block) and _direct_task_has_plan_sized_shape(block):
            warnings.append(
                PlanningWarning(
                    WARNING_TODO_PLAN_REQUIRED_HINT,
                    _render_path(path),
                    (
                        f"TODO item '{item_id or '?'}' still uses direct-task fields but already "
                        "looks execplan-sized; promote it to docs/execplans/."
                    ),
                )
            )

        if "completed" in status or "done" in status:
            warnings.append(
                PlanningWarning(
                    WARNING_ARCHIVE_ACCUMULATION_DRIFT,
                    _render_path(path),
                    f"TODO item '{item_id or '?'}' still carries completed detail; remove closed detail quickly.",
                )
            )

        if len(why_now) > 260 or re.search(r"\b(blocker|depends on|milestone|validation|history)\b", why_now, re.IGNORECASE):
            warnings.append(
                PlanningWarning(
                    WARNING_TODO_SHAPE_DRIFT,
                    _render_path(path),
                    f"TODO item '{item_id or '?'}' has overloaded Why now text; keep rationale compact.",
                )
            )

    if "milestone" in lowered and "## next" in lowered:
        warnings.append(
            PlanningWarning(
                WARNING_TODO_SHAPE_DRIFT,
                _render_path(path),
                "TODO.md contains milestone-level narrative; move sequencing into execplans.",
            )
        )

    if _contains_durable_technical_fact_shape(lines):
        warnings.append(
            PlanningWarning(
                WARNING_PLANNING_MEMORY_BOUNDARY_BLUR,
                _render_path(path),
                "TODO.md appears to include durable technical facts; route stable guidance to memory/docs.",
            )
        )

    return warnings, active_ids, active_items


def _surface_basename_tokens(surface_value: str) -> set[str]:
    ref = _surface_execplan_reference(surface_value or "")
    if not ref:
        return set()
    stem = Path(ref).stem.lower()
    raw_tokens = re.split(r"[^a-z0-9]+", stem)
    stop_tokens = {
        "plan",
        "execplans",
        "docs",
        "foundation",
        "vision",
        "workflow",
        "tranche",
        "scope",
    }
    return {token for token in raw_tokens if len(token) >= 4 and not token.isdigit() and token not in stop_tokens}


def _check_promotion_linkage(*, roadmap_path: Path, active_items: list[dict[str, str]]) -> list[PlanningWarning]:
    warnings: list[PlanningWarning] = []
    roadmap_text = "\n".join(_read_lines(roadmap_path)).lower()
    if not roadmap_text:
        return warnings

    signal_hints = ("signal", "trigger", "queue", "report", "when", "if")
    for item in active_items:
        item_id = item.get("id", "?")
        why_now = (item.get("why_now", "") or "").lower()
        surface = item.get("surface", "") or ""
        has_signal_reason = any(hint in why_now for hint in signal_hints)
        has_causal_reason = any(hint in why_now for hint in PROMOTION_REASON_HINTS)
        surface_tokens = _surface_basename_tokens(surface)
        has_surface_link = bool(surface_tokens and any(token in roadmap_text for token in surface_tokens))

        if not has_signal_reason and not has_causal_reason and not has_surface_link:
            warnings.append(
                PlanningWarning(
                    WARNING_PROMOTION_LINKAGE_DRIFT,
                    _render_path(roadmap_path),
                    (f"Active TODO item '{item_id}' lacks clear signal- or reason-driven linkage to ROADMAP framing."),
                )
            )

    return warnings


def _check_startup_policy(repo_root: Path) -> list[PlanningWarning]:
    warnings: list[PlanningWarning] = []
    agents_path = repo_root / "AGENTS.md"
    manifest_path = repo_root / ".agentic-workspace" / "planning" / "agent-manifest.json"
    quickstart_path = repo_root / "tools" / "AGENT_QUICKSTART.md"
    readme_path = repo_root / "README.md"
    contributor_path = repo_root / "docs" / "contributor-playbook.md"

    if not (agents_path.exists() and manifest_path.exists() and quickstart_path.exists()):
        return warnings

    agents_text = "\n".join(_read_lines(agents_path)).lower()
    quickstart_text = "\n".join(_read_lines(quickstart_path)).lower()
    readme_text = "\n".join(_read_lines(readme_path)).lower() if readme_path.exists() else ""
    contributor_text = "\n".join(_read_lines(contributor_path)).lower() if contributor_path.exists() else ""

    required_agents_fragments = (
        "read `todo.md`",
        "read the active feature plan in `docs/execplans/`",
        "read `roadmap.md` only when promoting work",
        "do not bulk-read all planning surfaces",
    )
    if not all(fragment in agents_text for fragment in required_agents_fragments):
        warnings.append(
            PlanningWarning(
                WARNING_STARTUP_POLICY_DRIFT,
                _render_path(agents_path),
                "AGENTS startup policy is missing required minimal-read-order guidance.",
            )
        )

    if (
        "read `roadmap.md` only when promoting work" not in quickstart_text
        or "do not bulk-read all planning surfaces" not in quickstart_text
    ):
        warnings.append(
            PlanningWarning(
                WARNING_STARTUP_POLICY_DRIFT,
                _render_path(quickstart_path),
                "Quickstart conditional reads are missing roadmap/bulk-read startup constraints.",
            )
        )

    required_readme_fragments = (
        "for agent maintainers, the primary operating path is",
        "`agents.md`",
        "`todo.md`",
        "active execplan",
        "`docs/contributor-playbook.md`",
    )
    if readme_text and not all(fragment in readme_text for fragment in required_readme_fragments):
        warnings.append(
            PlanningWarning(
                WARNING_STARTUP_POLICY_DRIFT,
                _render_path(readme_path),
                "README maintainer startup path is missing required agent-startup guidance.",
            )
        )

    required_contributor_fragments = (
        "default startup path for an agent maintainer",
        "read `agents.md`",
        "read `todo.md`",
        "active execplan",
        "package-local `agents.md`",
    )
    if contributor_text and not all(fragment in contributor_text for fragment in required_contributor_fragments):
        warnings.append(
            PlanningWarning(
                WARNING_STARTUP_POLICY_DRIFT,
                _render_path(contributor_path),
                "Contributor playbook startup path is missing required maintainer guidance.",
            )
        )

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        warnings.append(
            PlanningWarning(
                WARNING_STARTUP_POLICY_DRIFT,
                _render_path(manifest_path),
                "agent-manifest.json is invalid JSON; startup policy cannot be validated.",
            )
        )
        return warnings

    bootstrap = manifest.get("bootstrap", {}) if isinstance(manifest, dict) else {}
    first_reads = bootstrap.get("first_reads", []) if isinstance(bootstrap, dict) else []
    conditional_reads = bootstrap.get("conditional_reads", []) if isinstance(bootstrap, dict) else []

    first_reads_lower = [str(item).lower() for item in first_reads]
    conditional_reads_lower = [str(item).lower() for item in conditional_reads]

    if "todo.md" not in first_reads_lower or "roadmap.md" in first_reads_lower:
        warnings.append(
            PlanningWarning(
                WARNING_STARTUP_POLICY_DRIFT,
                _render_path(manifest_path),
                "Manifest first_reads must include TODO.md and must not include ROADMAP.md.",
            )
        )

    if not any(
        "roadmap.md` only when promoting work" in row or "roadmap.md only when promoting work" in row for row in conditional_reads_lower
    ):
        warnings.append(
            PlanningWarning(
                WARNING_STARTUP_POLICY_DRIFT,
                _render_path(manifest_path),
                "Manifest conditional_reads must scope ROADMAP.md to planning/reprioritisation contexts.",
            )
        )

    if not any("do not bulk-read all planning surfaces" in row for row in conditional_reads_lower):
        warnings.append(
            PlanningWarning(
                WARNING_STARTUP_POLICY_DRIFT,
                _render_path(manifest_path),
                "Manifest conditional_reads must include the no-bulk-read startup constraint.",
            )
        )

    return warnings


def _check_docs_surface_roles(repo_root: Path) -> list[PlanningWarning]:
    warnings: list[PlanningWarning] = []
    readme_path = repo_root / "README.md"
    if not readme_path.exists():
        return warnings

    text = "\n".join(_read_lines(readme_path)).lower()
    if "## docs map" not in text:
        return warnings

    required_fragments = (
        "for maintainers:",
        "`docs/contributor-playbook.md`",
        "`docs/maintainer-commands.md`",
        "`docs/collaboration-safety.md`",
        "`docs/installed-contract-design-checklist.md`",
        "`docs/dogfooding-feedback.md`",
        "`docs/workflow-contract-changes.md`",
    )
    if not all(fragment in text for fragment in required_fragments):
        warnings.append(
            PlanningWarning(
                WARNING_DOCS_SURFACE_ROLE_DRIFT,
                _render_path(readme_path),
                "Root README docs map is missing required role separation or maintainer page coverage.",
            )
        )

    return warnings


def _check_generated_agent_docs(repo_root: Path) -> list[PlanningWarning]:
    warnings: list[PlanningWarning] = []
    source_manifest_path = repo_root / ".agentic-workspace" / "planning" / "agent-manifest.json"
    mirror_manifest_path = repo_root / "tools" / "agent-manifest.json"
    quickstart_path = repo_root / "tools" / "AGENT_QUICKSTART.md"
    routing_path = repo_root / "tools" / "AGENT_ROUTING.md"

    if not all(path.exists() for path in (source_manifest_path, mirror_manifest_path, quickstart_path, routing_path)):
        return warnings

    try:
        manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        warnings.append(
            PlanningWarning(
                WARNING_GENERATED_DOCS_DRIFT,
                _render_path(source_manifest_path),
                "Source agent manifest is invalid JSON; generated docs cannot be validated.",
            )
        )
        return warnings

    render_module = _load_render_module()
    expected_manifest = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    expected_quickstart = render_module.render_quickstart(manifest)
    expected_routing = render_module.render_routing(manifest)

    actual_manifest = mirror_manifest_path.read_text(encoding="utf-8")
    actual_quickstart = quickstart_path.read_text(encoding="utf-8")
    actual_routing = routing_path.read_text(encoding="utf-8")

    if actual_manifest != expected_manifest:
        warnings.append(
            PlanningWarning(
                WARNING_GENERATED_DOCS_DRIFT,
                _render_path(mirror_manifest_path),
                "Generated manifest mirror is out of date; rerender agent docs from the source manifest.",
            )
        )

    if actual_quickstart != expected_quickstart:
        warnings.append(
            PlanningWarning(
                WARNING_GENERATED_DOCS_DRIFT,
                _render_path(quickstart_path),
                "Generated quickstart is out of date; rerender agent docs from the source manifest.",
            )
        )

    if actual_routing != expected_routing:
        warnings.append(
            PlanningWarning(
                WARNING_GENERATED_DOCS_DRIFT,
                _render_path(routing_path),
                "Generated routing guide is out of date; rerender agent docs from the source manifest.",
            )
        )

    if GENERATED_DOC_NOTICE_FRAGMENT not in actual_quickstart.lower():
        warnings.append(
            PlanningWarning(
                WARNING_GENERATED_DOCS_DRIFT,
                _render_path(quickstart_path),
                "Generated quickstart is missing the non-manual generated-file marker.",
            )
        )

    if GENERATED_DOC_NOTICE_FRAGMENT not in actual_routing.lower():
        warnings.append(
            PlanningWarning(
                WARNING_GENERATED_DOCS_DRIFT,
                _render_path(routing_path),
                "Generated routing guide is missing the non-manual generated-file marker.",
            )
        )

    return warnings


def _contains_durable_technical_fact_shape(lines: list[str]) -> bool:
    text = "\n".join(lines).lower()
    if "```" in text:
        return True

    dense_tech_signals = sum(
        1
        for token in (
            "api contract",
            "schema",
            "class ",
            "def ",
            "import ",
            "sql",
            "json schema",
            "protobuf",
            "invariant:",
        )
        if token in text
    )
    return dense_tech_signals >= 3


def _active_execplans(execplan_dir: Path) -> list[Path]:
    if not execplan_dir.exists():
        return []

    plans: list[Path] = []
    for path in sorted(execplan_dir.glob("*.md")):
        if path.name in {"README.md", "TEMPLATE.md"}:
            continue
        plans.append(path)
    return plans


def _execplan_status(path: Path) -> str:
    for line in _section_content(_read_lines(path), "Active Milestone"):
        match = re.match(r"^\s*-\s*status\s*:\s*(.*)\s*$", line, re.IGNORECASE)
        if match:
            return match.group(1).strip().lower()
    return ""


def _extract_section_stats(lines: list[str], section_name: str) -> tuple[list[str], int]:
    section = _section_content(lines, section_name)
    bullets = sum(1 for line in section if re.match(r"^\s*[-*]\s+", line))
    return section, bullets


def _extract_kv_fields(lines: list[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^\s*[-*]\s*([^:]+):\s*(.*)\s*$", line)
        if not match:
            continue
        fields[match.group(1).strip().lower()] = match.group(2).strip()
    return fields


def _check_execplan(path: Path) -> tuple[list[PlanningWarning], set[str]]:
    warnings: list[PlanningWarning] = []
    active_signals: set[str] = set()
    lines = _read_lines(path)
    lowered_lines = [line.lower() for line in lines]
    headings = _heading_titles(lines)

    missing_sections = [section for section in EXPECTED_EXECPLAN_SECTIONS if section.lower() not in headings]
    if missing_sections:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_STRUCTURE_DRIFT,
                _render_path(path),
                f"Execplan is missing required sections: {', '.join(missing_sections)}.",
            )
        )

    active_status_rows = [
        line
        for line in lowered_lines
        if re.match(r"^\s*-\s*status\s*:\s*", line)
        and not re.search(r"\b(completed|done|closed|planned|not-started)\b", line)
        and re.search(r"\b(active|in-progress|in progress|current|ongoing)\b", line)
    ]

    all_status_rows = [line for line in lowered_lines if re.match(r"^\s*-\s*status\s*:\s*", line)]
    planned_only_rows = [line for line in all_status_rows if re.search(r"\b(planned|not-started|pending)\b", line)]
    completed_only_rows = [line for line in all_status_rows if re.search(r"\b(completed|done|closed)\b", line)]
    has_only_completed_status = bool(all_status_rows) and len(completed_only_rows) == len(all_status_rows)
    has_only_non_active_status = bool(all_status_rows) and (len(planned_only_rows) == len(all_status_rows) or has_only_completed_status)

    # Enforce exactly one active milestone for active execplans; planned-only contracts are allowed.
    if not has_only_non_active_status and len(active_status_rows) != 1:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_MULTIPLE_ACTIVE,
                _render_path(path),
                f"Execplan should have exactly 1 active milestone/status row, found {len(active_status_rows)}.",
            )
        )

    active_milestone_section = _section_content(lines, "Active Milestone")
    active_milestone_fields = _extract_kv_fields(active_milestone_section)
    intent_continuity_fields = _extract_kv_fields(_section_content(lines, "Intent Continuity"))
    required_continuation_fields = _extract_kv_fields(_section_content(lines, "Required Continuation"))
    is_active_execplan = not has_only_non_active_status
    larger_intended_outcome = intent_continuity_fields.get("larger intended outcome", "").strip()
    completes_larger_outcome = intent_continuity_fields.get("this slice completes the larger intended outcome", "").strip().lower()
    continuation_surface = intent_continuity_fields.get("continuation surface", "").strip()
    required_follow_on = required_continuation_fields.get("required follow-on for the larger intended outcome", "").strip().lower()
    required_owner_surface = required_continuation_fields.get("owner surface", "").strip()
    activation_trigger = required_continuation_fields.get("activation trigger", "").strip()

    if not larger_intended_outcome:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Execplan is missing `Larger intended outcome` in Intent Continuity.",
            )
        )

    if completes_larger_outcome not in {"yes", "no"}:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Execplan must set `This slice completes the larger intended outcome` to yes or no.",
            )
        )
    elif completes_larger_outcome == "yes" and continuation_surface and continuation_surface.lower() not in {"none", "n/a"}:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Execplan marks the larger intended outcome complete but still names a continuation surface.",
            )
        )
    elif completes_larger_outcome == "no" and (not continuation_surface or continuation_surface.lower() in {"none", "n/a"}):
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Execplan leaves the larger intended outcome unfinished without naming a continuation surface.",
            )
        )

    if required_follow_on not in {"yes", "no"}:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Execplan must set `Required follow-on for the larger intended outcome` to yes or no.",
            )
        )
    elif required_follow_on == "yes":
        if not required_owner_surface or required_owner_surface.lower() in {"none", "n/a"}:
            warnings.append(
                PlanningWarning(
                    WARNING_EXECPLAN_UNDER_SPECIFIED,
                    _render_path(path),
                    "Execplan records required follow-on but does not name the owner surface.",
                )
            )
        if not activation_trigger or activation_trigger.lower() in {"none", "n/a"}:
            warnings.append(
                PlanningWarning(
                    WARNING_EXECPLAN_UNDER_SPECIFIED,
                    _render_path(path),
                    "Execplan records required follow-on but does not state the activation trigger.",
                )
            )
    elif required_follow_on == "no" and (
        (required_owner_surface and required_owner_surface.lower() not in {"none", "n/a"})
        or (activation_trigger and activation_trigger.lower() not in {"none", "n/a"})
    ):
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Execplan marks required follow-on absent but still carries an owner surface or activation trigger.",
            )
        )

    if completes_larger_outcome == "no" and required_follow_on != "yes":
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Execplan leaves the larger intended outcome unfinished but does not record required follow-on explicitly.",
            )
        )
    if completes_larger_outcome == "yes" and required_follow_on == "yes":
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Execplan marks the larger intended outcome complete but still records required follow-on.",
            )
        )

    if is_active_execplan:
        ready_value = active_milestone_fields.get("ready", "").strip().lower()
        blocked_value = active_milestone_fields.get("blocked", "").strip().lower()

        if not ready_value:
            warnings.append(
                PlanningWarning(
                    WARNING_EXECPLAN_READINESS_DRIFT,
                    _render_path(path),
                    "Active execplan is missing `Ready` state in Active Milestone.",
                )
            )
        elif ready_value not in {"true", "false", "ready", "blocked", "conditional"}:
            warnings.append(
                PlanningWarning(
                    WARNING_EXECPLAN_READINESS_DRIFT,
                    _render_path(path),
                    "Active execplan has invalid `Ready` state; use one of true/false/ready/blocked/conditional.",
                )
            )

        if ready_value in {"false", "blocked"} and (not blocked_value or blocked_value in {"none", "n/a", ""}):
            warnings.append(
                PlanningWarning(
                    WARNING_EXECPLAN_READINESS_DRIFT,
                    _render_path(path),
                    "Active execplan is blocked but `Blocked` detail is missing.",
                )
            )

    next_action_section, next_action_bullets = _extract_section_stats(lines, "Immediate Next Action")
    non_empty_next_action = [line for line in next_action_section if line.strip() and not line.strip().startswith("#")]
    if not non_empty_next_action:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_IMMEDIATE_ACTION_DRIFT,
                _render_path(path),
                "Execplan is missing an Immediate Next Action.",
            )
        )

    next_action_text = "\n".join(next_action_section)
    prose_multi_step = re.search(
        r"\b(first|second|third|fourth|next|then|after that|finally)\b",
        next_action_text,
        re.IGNORECASE,
    )
    if non_empty_next_action and (
        next_action_bullets > 1 or re.search(r"(?m)^\s*\d+\.\s+", next_action_text) or (prose_multi_step and len(non_empty_next_action) > 1)
    ):
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_IMMEDIATE_ACTION_DRIFT,
                _render_path(path),
                "Immediate Next Action looks multi-step; keep one immediate step by default.",
            )
        )

    touched_paths, touched_path_bullets = _extract_section_stats(lines, "Touched Paths")
    if touched_path_bullets > 14 or len(touched_paths) > 30:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_STRUCTURE_DRIFT,
                _render_path(path),
                "Touched Paths looks inventory-shaped; keep it as a compact scope guard.",
            )
        )
    elif touched_path_bullets == 0:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Touched Paths is empty; add the bounded files or directories this plan is allowed to touch.",
            )
        )

    invariants, _ = _extract_section_stats(lines, "Invariants")
    if len(invariants) > 16 or sum(len(line) for line in invariants) > 900:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_STRUCTURE_DRIFT,
                _render_path(path),
                "Invariants section looks essay-shaped; keep concise contract statements.",
            )
        )
    elif not [line for line in invariants if line.strip()]:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Invariants is empty; record the contract statements that must stay true while executing this plan.",
            )
        )

    blockers, blocker_bullets = _extract_section_stats(lines, "Blockers")
    if len(blockers) > 10 and blocker_bullets <= 1:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_NOTEBOOK_DRIFT,
                _render_path(path),
                "Blockers section looks like status narrative; list explicit blockers only.",
            )
        )

    completion_criteria, completion_bullets = _extract_section_stats(lines, "Completion Criteria")
    if not [line for line in completion_criteria if line.strip()] or completion_bullets == 0:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Completion Criteria is missing or vague.",
            )
        )

    validation_commands, validation_bullets = _extract_section_stats(lines, "Validation Commands")
    if not [line for line in validation_commands if line.strip()] or validation_bullets == 0:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_UNDER_SPECIFIED,
                _render_path(path),
                "Validation Commands is empty; record the narrowest command that proves this plan.",
            )
        )

    drift_log = _section_content(lines, "Drift Log")
    drift_entries = [line for line in drift_log if re.match(r"^\s*[-*]\s+\d{4}-\d{2}-\d{2}:", line)]
    if len(drift_entries) > DRIFT_LOG_MAX_ENTRIES or len(drift_log) > DRIFT_LOG_MAX_LINES:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_LOG_DRIFT,
                _render_path(path),
                "Drift Log is oversized/log-like; keep brief and decision-shaped.",
            )
        )
    elif len(drift_entries) >= 6:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_NOTEBOOK_DRIFT,
                _render_path(path),
                "Drift Log is trending journal-shaped; archive or compress older decision residue.",
            )
        )

    completed_statuses = [line for line in lowered_lines if re.match(r"^\s*-\s*status\s*:\s*.*\bcompleted\b", line)]
    if len(completed_statuses) > 1:
        warnings.append(
            PlanningWarning(
                WARNING_ARCHIVE_ACCUMULATION_DRIFT,
                _render_path(path),
                "Execplan contains multiple completed milestone/status rows; archive-over-accumulation may be drifting.",
            )
        )

    if has_only_completed_status:
        warnings.append(
            PlanningWarning(
                WARNING_ARCHIVE_ACCUMULATION_DRIFT,
                _render_path(path),
                "Completed execplan is still in active execplans space; archive it once it no longer changes future execution.",
            )
        )

    text = "\n".join(lines)
    if len(lines) > 220:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_NOTEBOOK_DRIFT,
                _render_path(path),
                "Execplan is getting long enough to act like a notebook; trim stale narrative or archive completed work.",
            )
        )

    if _contains_durable_technical_fact_shape(lines):
        warnings.append(
            PlanningWarning(
                WARNING_PLANNING_MEMORY_BOUNDARY_BLUR,
                _render_path(path),
                "Execplan appears to include durable technical residue; keep stable knowledge in memory/docs.",
            )
        )

    match = re.search(r"(?im)^\s*-\s*ID\s*:\s*(\S+)\s*$", text)
    if match and re.search(r"(?im)^\s*-\s*Status\s*:\s*.*\b(in-progress|active|ongoing|current)\b", text):
        active_signals.add(match.group(1))

    return warnings, active_signals


def _check_roadmap(path: Path, todo_active_ids: set[str]) -> list[PlanningWarning]:
    warnings: list[PlanningWarning] = []
    lines = _read_lines(path)
    if not lines:
        return warnings

    text = "\n".join(lines)
    lowered = text.lower()

    if len(lines) > ROADMAP_MAX_LINES:
        warnings.append(
            PlanningWarning(
                WARNING_ROADMAP_EXECUTION_DRIFT,
                _render_path(path),
                f"ROADMAP.md has {len(lines)} lines; prune to keep candidate queue compact.",
            )
        )

    if any(marker in lowered for marker in EXECUTION_SHAPED_MARKERS):
        warnings.append(
            PlanningWarning(
                WARNING_ROADMAP_EXECUTION_DRIFT,
                _render_path(path),
                "ROADMAP.md contains execution-contract sections; keep it candidate-oriented.",
            )
        )

    candidate_section = _section_content(lines, "Next Candidate Queue")
    top_level_candidate_bullets = [line.strip() for line in candidate_section if re.match(r"^-\s+", line)]

    if len(top_level_candidate_bullets) > ROADMAP_MAX_CANDIDATES or len(candidate_section) > ROADMAP_MAX_CANDIDATE_SECTION_LINES:
        warnings.append(
            PlanningWarning(
                WARNING_ROADMAP_STALE_CANDIDATE_PRESSURE,
                _render_path(path),
                "ROADMAP candidate queue looks oversized; prune stale or superseded candidate detail.",
            )
        )

    for bullet in top_level_candidate_bullets:
        if len(bullet) < 6:
            continue
        lowered_bullet = bullet.lower()
        if not any(hint in lowered_bullet for hint in PROMOTION_SIGNAL_HINTS):
            warnings.append(
                PlanningWarning(
                    WARNING_ROADMAP_MISSING_PROMOTION_SIGNAL,
                    _render_path(path),
                    "ROADMAP candidate entry is missing an explicit promotion signal/trigger.",
                )
            )
            break

    reopen_section = _section_content(lines, "Reopen Conditions")
    reopen_bullets = [line.strip() for line in reopen_section if re.match(r"^\s*-\s+", line)]
    has_reopen_signal = any(
        any(hint in bullet.lower() for hint in ("when", "if", "trigger", "signal", "queue", "report")) for bullet in reopen_bullets
    )
    if not has_reopen_signal:
        warnings.append(
            PlanningWarning(
                WARNING_ROADMAP_MISSING_REOPEN_SIGNAL,
                _render_path(path),
                "ROADMAP is missing a clear reopen signal in Reopen Conditions.",
            )
        )

    completed_mentions = sum(1 for line in candidate_section if "completed" in line.lower())
    if completed_mentions >= 5 and len(top_level_candidate_bullets) >= 6:
        warnings.append(
            PlanningWarning(
                WARNING_ROADMAP_STALE_CANDIDATE_PRESSURE,
                _render_path(path),
                "ROADMAP candidate queue appears to retain completed residue; compress to candidate stubs.",
            )
        )

    if re.search(r"(?im)^\s*-\s*status\s*:\s*.*\b(in-progress|active)\b", text):
        warnings.append(
            PlanningWarning(
                WARNING_ROADMAP_EXECUTION_DRIFT,
                _render_path(path),
                "ROADMAP.md includes active execution status detail; keep active sequencing in TODO/execplans.",
            )
        )

    if "completed" in lowered and lowered.count("completed") >= 8:
        warnings.append(
            PlanningWarning(
                WARNING_ARCHIVE_ACCUMULATION_DRIFT,
                _render_path(path),
                "ROADMAP.md appears to retain substantial promoted/completed residue.",
            )
        )

    for active_id in sorted(todo_active_ids):
        if active_id and active_id.lower() in lowered and "next candidate queue" in lowered:
            warnings.append(
                PlanningWarning(
                    WARNING_ROADMAP_EXECUTION_DRIFT,
                    _render_path(path),
                    f"Active TODO item '{active_id}' also appears in ROADMAP candidate detail.",
                )
            )
            break

    if _contains_durable_technical_fact_shape(lines):
        warnings.append(
            PlanningWarning(
                WARNING_PLANNING_MEMORY_BOUNDARY_BLUR,
                _render_path(path),
                "ROADMAP.md appears to include durable technical guidance; keep stable details in memory/docs.",
            )
        )

    return warnings


def _check_execplan_active_set(execplan_dir: Path) -> list[PlanningWarning]:
    warnings: list[PlanningWarning] = []
    active_plans = []
    for path in _active_execplans(execplan_dir):
        status = _execplan_status(path)
        if status and status not in {"completed", "done", "closed", "planned", "pending", "not-started"}:
            active_plans.append(path)

    if len(active_plans) > TODO_MAX_NOW_ITEMS:
        warnings.append(
            PlanningWarning(
                WARNING_EXECPLAN_ACTIVE_SET_PRESSURE,
                _render_path(execplan_dir),
                f"Active execplan set has {len(active_plans)} live plans; keep the active set small and feature-scoped.",
            )
        )

    return warnings


def gather_planning_warnings(*, repo_root: Path = REPO_ROOT) -> list[PlanningWarning]:
    todo_path = repo_root / "TODO.md"
    roadmap_path = repo_root / "ROADMAP.md"
    execplan_dir = repo_root / "docs" / "execplans"

    warnings: list[PlanningWarning] = []

    todo_warnings, todo_active_ids, todo_active_items = _check_todo(todo_path, repo_root=repo_root)
    warnings.extend(todo_warnings)

    execplan_active_ids: set[str] = set()
    for plan_path in _active_execplans(execplan_dir):
        plan_warnings, plan_active_ids = _check_execplan(plan_path)
        warnings.extend(plan_warnings)
        execplan_active_ids.update(plan_active_ids)

    warnings.extend(_check_execplan_active_set(execplan_dir))
    warnings.extend(_check_roadmap(roadmap_path, todo_active_ids | execplan_active_ids))
    warnings.extend(_check_promotion_linkage(roadmap_path=roadmap_path, active_items=todo_active_items))
    warnings.extend(_check_startup_policy(repo_root))
    warnings.extend(_check_docs_surface_roles(repo_root))
    warnings.extend(_check_generated_agent_docs(repo_root))
    return warnings


def gather_planning_summary(*, repo_root: Path = REPO_ROOT) -> dict[str, object]:
    todo_path = repo_root / "TODO.md"
    roadmap_path = repo_root / "ROADMAP.md"
    execplan_dir = repo_root / "docs" / "execplans"

    todo_lines = _read_lines(todo_path)
    todo_items = _todo_item_blocks(todo_lines)
    active_items = []
    for block in todo_items:
        status = block.get("status", "").lower()
        if "in-progress" in status or "active" in status or "ongoing" in status:
            active_items.append(
                {
                    "id": block.get("id", ""),
                    "surface": block.get("surface", ""),
                    "why_now": block.get("why now", ""),
                }
            )

    active_execplans = []
    for plan_path in _active_execplans(execplan_dir):
        status = _execplan_status(plan_path)
        if status and status not in {"completed", "done", "closed", "planned", "pending", "not-started"}:
            active_execplans.append({"path": _render_path(plan_path), "status": status})

    candidate_section = _section_content(_read_lines(roadmap_path), "Next Candidate Queue")
    warnings = gather_planning_warnings(repo_root=repo_root)

    return {
        "warning_count": len(warnings),
        "warnings": [warning._asdict() for warning in warnings],
        "todo": {
            "line_count": len(todo_lines),
            "item_count": len(todo_items),
            "active_count": len(active_items),
            "active_items": active_items,
        },
        "execplans": {
            "active_count": len(active_execplans),
            "active_execplans": active_execplans,
            "archived_count": sum(1 for path in (execplan_dir / "archive").glob("*.md") if path.is_file())
            if (execplan_dir / "archive").exists()
            else 0,
        },
        "roadmap": {
            "candidate_count": sum(1 for line in candidate_section if re.match(r"^\s*-\s+", line)),
        },
    }


def _print_warnings(warnings: list[PlanningWarning]) -> None:
    print("Planning surface health report")
    if not warnings:
        print("- No planning-surface drift warnings detected.")
        return

    for warning in warnings:
        print(f"- [{warning.warning_class}] {warning.path}: {warning.message}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Advisory planning-surface health checker.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero exit status when warnings are present.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = gather_planning_summary(repo_root=REPO_ROOT)
    warnings = [PlanningWarning(**warning) for warning in summary["warnings"]]

    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        _print_warnings(warnings)

    return 1 if args.strict and warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
