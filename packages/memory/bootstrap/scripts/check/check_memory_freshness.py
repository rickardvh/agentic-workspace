#!/usr/bin/env python3
"""Memory freshness audit.

Scan durable memory notes for missing required metadata, stale confirmations,
and growth signals. By default this script is advisory and exits with 0.
Pass --strict to fail the run when selected finding categories are present.
"""

from __future__ import annotations

import argparse
import re
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

RE_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
RE_H1 = re.compile(r"^\s{0,3}#\s+(.+?)\s*$")
RE_LAST_CONFIRMED_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})\b")
RE_STATUS_VALUE = re.compile(r"^(Stable|Active|Needs verification|Deprecated)\s*$", re.IGNORECASE)
RE_SECTION = re.compile(r"^\s{0,3}##\s+(.+?)\s*$")
RE_CHRONOLOGY = re.compile(r"^\s*(?:-|\*|\d+\.)\s+20\d{2}-\d{2}-\d{2}\b")
RE_PLANNING_RESIDUE = re.compile(r"^\s*(?:-|\*)?\s*Active (?:execplan|plan|milestone)\s*:", re.IGNORECASE | re.MULTILINE)

MEMORY_ROOT = Path("memory")
MANIFEST_PATH = MEMORY_ROOT / "manifest.toml"
MAX_LINES = 200
STALE_DAYS = 180
TYPE_LIMITS = {
    "invariant": 80,
    "domain": 160,
    "runbook": 140,
    "recurring-failures": 140,
    "decision": 160,
    "project-state": 100,
    "task-context": 80,
    "routing-feedback": 120,
}
CURRENT_NOTE_AUTHORITY_VALUES = {"advisory", "supporting"}
CURRENT_NOTE_OVERLAP_MIN_SHARED_TERMS = 8
CURRENT_NOTE_OVERLAP_MIN_LINES = 30
PROJECT_STATE_SECTIONS = {
    "Status",
    "Scope",
    "Applies to",
    "Load when",
    "Review when",
    "Current focus",
    "Recent meaningful progress",
    "Blockers",
    "High-level notes",
    "Failure signals",
    "Verify",
    "Verified against",
    "Last confirmed",
}
TASK_CONTEXT_SECTIONS = {
    "Status",
    "Scope",
    "Active goal",
    "Touched surfaces",
    "Blocking assumptions",
    "Next validation",
    "Resume cues",
    "Last confirmed",
}
ROUTING_FEEDBACK_SECTIONS = {
    "Status",
    "Scope",
    "Load when",
    "Review when",
    "Missed-note entries",
    "Over-routing entries",
    "Synthesis",
    "Last confirmed",
}
SUSPICIOUS_CURRENT_HEADINGS = {
    "backlog",
    "roadmap",
    "done today",
    "completed tasks",
    "timeline",
    "sprint",
    "action items",
    "next steps",
}

SKIP_FILES = {
    MEMORY_ROOT / "index.md",
    MANIFEST_PATH,
    MEMORY_ROOT / "domains" / "README.md",
    MEMORY_ROOT / "invariants" / "README.md",
    MEMORY_ROOT / "runbooks" / "README.md",
    MEMORY_ROOT / "decisions" / "README.md",
}
SKIP_DIRS = {
    MEMORY_ROOT / "bootstrap",
    MEMORY_ROOT / "skills",
    MEMORY_ROOT / "templates",
    MEMORY_ROOT / "system",
}

DEFAULT_STRICT_CATEGORIES = {
    "missing_trigger",
    "missing_last_confirmed",
    "invalid_last_confirmed",
    "old_confirmations",
    "current_authority_drift",
    "current_durable_truth_drift",
    "missing_manifest_entries",
    "manifest_records_for_missing_notes",
    "always_read_creep",
    "manifest_note_type_drift",
    "canonical_dir_drift",
    "task_board_dependence",
}

STRICT_CATEGORY_CHOICES = sorted(
    {
        "needs_verification",
        "missing_trigger",
        "missing_last_confirmed",
        "invalid_last_confirmed",
        "missing_verify",
        "missing_load",
        "missing_review",
        "missing_failure",
        "old_confirmations",
        "oversized_files",
        "current_context_shape",
        "current_authority_drift",
        "current_durable_truth_drift",
        "current_note_overlap_pressure",
        "incomplete_improvement_signals",
        "always_read_creep",
        "manifest_note_type_drift",
        "canonical_dir_drift",
        "task_board_dependence",
        "duplicate_titles",
        "missing_manifest_entries",
        "manifest_records_for_missing_notes",
        "shared_canonical_homes",
        "uncustomised_index_placeholders",
    }
)


@dataclass
class NoteScan:
    path: Path
    title: str | None
    line_count: int
    has_last_confirmed: bool
    has_valid_last_confirmed_date: bool
    has_verify: bool
    has_load_when: bool
    has_review_when: bool
    has_failure_signals: bool
    has_needs_verification: bool
    newest_confirmed_date: datetime | None
    sections: set[str]
    suspicious_current_context: bool
    note_type: str


def _normalise_label(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower().rstrip(":"))


def _label_match(line: str, target: str) -> bool:
    if _normalise_label(line) == target:
        return True
    match = RE_HEADING.match(line)
    return bool(match and _normalise_label(match.group(1)) == target)


def _iter_notes(root: Path) -> list[Path]:
    notes: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        if path in SKIP_FILES:
            continue
        if any(parent in SKIP_DIRS for parent in path.parents):
            continue
        notes.append(path)
    return notes


def _scan_note(path: Path) -> NoteScan:
    lines = path.read_text(encoding="utf-8").splitlines()

    title = None
    for line in lines:
        match = RE_H1.match(line)
        if match:
            title = match.group(1).strip()
            break

    has_last_confirmed = False
    has_valid_last_confirmed_date = False
    has_verify = False
    has_load_when = False
    has_review_when = False
    has_failure_signals = False
    status_value: str | None = None
    dates: list[datetime] = []
    sections: set[str] = set()

    for idx, line in enumerate(lines):
        section_match = RE_SECTION.match(line)
        if section_match:
            sections.add(section_match.group(1).strip())
        if _label_match(line, "status"):
            for follow in lines[idx + 1 :]:
                stripped = follow.strip()
                if not stripped:
                    continue
                if RE_HEADING.match(stripped):
                    break
                match = RE_STATUS_VALUE.match(stripped)
                if match:
                    status_value = match.group(1)
                break

        if _label_match(line, "last confirmed"):
            has_last_confirmed = True
            for follow in lines[idx + 1 :]:
                stripped = follow.strip()
                if not stripped:
                    continue
                match = RE_LAST_CONFIRMED_DATE.match(stripped)
                if match:
                    has_valid_last_confirmed_date = True
                    dates.append(datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=UTC))
                break

        if _label_match(line, "verify") or _label_match(line, "verification"):
            has_verify = True
        if _label_match(line, "load when"):
            has_load_when = True
        if _label_match(line, "review when"):
            has_review_when = True
        if _label_match(line, "failure signals"):
            has_failure_signals = True

    return NoteScan(
        path=path,
        title=title,
        line_count=len(lines),
        has_last_confirmed=has_last_confirmed,
        has_valid_last_confirmed_date=has_valid_last_confirmed_date,
        has_verify=has_verify,
        has_load_when=has_load_when,
        has_review_when=has_review_when,
        has_failure_signals=has_failure_signals,
        has_needs_verification=(status_value or "").strip().lower() == "needs verification",
        newest_confirmed_date=max(dates) if dates else None,
        sections=sections,
        suspicious_current_context=_suspicious_current_context(path, lines, sections),
        note_type=_note_type_for_path(path),
    )


def _render_path(path: Path) -> str:
    return path.as_posix()


def _load_manifest_note_entries(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}
    notes = data.get("notes", {})
    return notes if isinstance(notes, dict) else {}


def _load_manifest_data(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _note_type_for_path(path: Path) -> str:
    path_str = path.as_posix()
    if path_str.startswith("memory/invariants/"):
        return "invariant"
    if path_str.startswith("memory/domains/"):
        return "domain"
    if path_str.startswith("memory/runbooks/"):
        return "runbook"
    if path_str == "memory/mistakes/recurring-failures.md":
        return "recurring-failures"
    if path_str.startswith("memory/decisions/"):
        return "decision"
    if path_str == "memory/current/project-state.md":
        return "project-state"
    if path_str == "memory/current/task-context.md":
        return "task-context"
    if path_str == "memory/current/routing-feedback.md":
        return "routing-feedback"
    return "memory-note"


def _manifest_note_type_expected(path_str: str) -> str | None:
    if path_str == "memory/index.md":
        return "routing"
    if path_str == "memory/current/project-state.md":
        return "current-overview"
    if path_str == "memory/current/task-context.md":
        return "current-context"
    if path_str == "memory/current/routing-feedback.md":
        return "routing-feedback"
    if path_str.startswith("memory/domains/"):
        return "domain"
    if path_str.startswith("memory/invariants/"):
        return "invariant"
    if path_str.startswith("memory/runbooks/"):
        return "runbook"
    if path_str == "memory/mistakes/recurring-failures.md":
        return "recurring-failures"
    if path_str.startswith("memory/decisions/"):
        return "decision"
    return None


def _suspicious_current_context(path: Path, lines: list[str], sections: set[str]) -> bool:
    if path.as_posix() not in {
        "memory/current/project-state.md",
        "memory/current/task-context.md",
        "memory/current/routing-feedback.md",
    }:
        return False
    lowered_sections = {section.lower() for section in sections}
    if lowered_sections & SUSPICIOUS_CURRENT_HEADINGS:
        return True
    if sum(1 for line in lines if RE_CHRONOLOGY.match(line)) >= 3:
        return True
    if path.as_posix() != "memory/current/routing-feedback.md" and RE_PLANNING_RESIDUE.search("\n".join(lines)):
        return True
    return False


def _print_section(title: str, items: list[str]) -> None:
    print(f"\n{title}:")
    if not items:
        print("- none")
        return
    for item in items:
        print(f"- {item}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit memory freshness and structure.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 when selected finding categories are present.",
    )
    parser.add_argument(
        "--strict-categories",
        nargs="*",
        choices=STRICT_CATEGORY_CHOICES,
        help=("Finding categories that should fail strict mode. Defaults to a conservative contract-focused subset."),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not MEMORY_ROOT.exists():
        print("Memory freshness report\n")
        print("Memory root not found: memory/")
        return 1 if args.strict else 0

    scans = [_scan_note(path) for path in _iter_notes(MEMORY_ROOT)]
    manifest_data = _load_manifest_data(MANIFEST_PATH)
    raw_manifest_notes = manifest_data.get("notes", {})
    manifest_notes: dict[str, dict[str, Any]] = (
        {str(k): v for k, v in raw_manifest_notes.items() if isinstance(v, dict)} if isinstance(raw_manifest_notes, dict) else {}
    )
    raw_manifest_rules = manifest_data.get("rules", {})
    manifest_rules: dict[str, Any] = {str(k): v for k, v in raw_manifest_rules.items()} if isinstance(raw_manifest_rules, dict) else {}
    stale_before = datetime.now(UTC) - timedelta(days=STALE_DAYS)

    missing_last_confirmed = sorted(_render_path(scan.path) for scan in scans if not scan.has_last_confirmed)
    invalid_last_confirmed = sorted(
        _render_path(scan.path) for scan in scans if scan.has_last_confirmed and not scan.has_valid_last_confirmed_date
    )
    verification_optional_types = {"task-context", "routing-feedback"}
    trigger_optional_types = {"task-context"}
    failure_optional_types = {"task-context", "routing-feedback"}
    missing_verify = sorted(
        _render_path(scan.path) for scan in scans if not scan.has_verify and scan.note_type not in verification_optional_types
    )
    missing_load = sorted(
        _render_path(scan.path) for scan in scans if not scan.has_load_when and scan.note_type not in trigger_optional_types
    )
    missing_review = sorted(
        _render_path(scan.path) for scan in scans if not scan.has_review_when and scan.note_type not in trigger_optional_types
    )
    missing_failure = sorted(
        _render_path(scan.path) for scan in scans if not scan.has_failure_signals and scan.note_type not in failure_optional_types
    )
    missing_trigger = sorted(
        {
            _render_path(scan.path)
            for scan in scans
            if (scan.note_type == "routing-feedback" and not (scan.has_load_when and scan.has_review_when))
            or (
                scan.note_type not in trigger_optional_types | {"routing-feedback"}
                and not (scan.has_load_when and scan.has_review_when and scan.has_failure_signals)
            )
        }
    )
    needs_verification = sorted(_render_path(scan.path) for scan in scans if scan.has_needs_verification)
    old_confirmations = sorted(
        _render_path(scan.path) for scan in scans if scan.newest_confirmed_date and scan.newest_confirmed_date < stale_before
    )
    oversized_files = sorted(f"{_render_path(scan.path)} ({scan.line_count} lines)" for scan in scans if scan.line_count > MAX_LINES)

    title_map: dict[str, list[str]] = defaultdict(list)
    for scan in scans:
        if scan.title:
            title_map[scan.title.lower()].append(_render_path(scan.path))
    duplicate_titles = sorted(f"{paths[0]} (and {len(paths) - 1} more)" for paths in title_map.values() if len(paths) > 1)
    missing_manifest_entries = sorted(_render_path(scan.path) for scan in scans if _render_path(scan.path) not in manifest_notes)
    manifest_records_for_missing_notes = sorted(note_path for note_path in manifest_notes if not Path(note_path).exists())
    canonical_home_map: dict[str, list[str]] = defaultdict(list)
    for note_path, raw in manifest_notes.items():
        if not isinstance(raw, dict):
            continue
        canonical_home = str(raw.get("canonical_home", note_path))
        canonical_home_map[canonical_home].append(note_path)
    shared_canonical_homes = sorted(f"{home} <- {', '.join(paths)}" for home, paths in canonical_home_map.items() if len(paths) > 1)
    oversized_files = sorted(
        f"{_render_path(scan.path)} ({scan.line_count} lines > {_line_limit(scan.note_type)})"
        for scan in scans
        if scan.line_count > _line_limit(scan.note_type)
    )
    current_context_shape = sorted(_render_path(scan.path) for scan in scans if _missing_sections(scan) or scan.suspicious_current_context)
    current_authority_drift = sorted(
        note_path
        for note_path, raw in manifest_notes.items()
        if isinstance(raw, dict)
        and note_path.startswith("memory/current/")
        and str(raw.get("authority", "")).strip() not in CURRENT_NOTE_AUTHORITY_VALUES
    )
    current_durable_truth_drift = sorted(
        note_path
        for note_path, raw in manifest_notes.items()
        if isinstance(raw, dict) and note_path.startswith("memory/current/") and str(raw.get("memory_role", "")).strip()
    )
    current_note_overlap_pressure = _current_note_overlap_pressure(scans)
    incomplete_improvement_signals = sorted(
        note_path
        for note_path, raw in manifest_notes.items()
        if isinstance(raw, dict)
        and str(raw.get("memory_role", "")).strip() == "improvement_signal"
        and not (
            (str(raw.get("preferred_remediation", "")).strip() and str(raw.get("improvement_note", "")).strip())
            or str(raw.get("retention_justification", "")).strip()
        )
    )
    always_read_creep = _always_read_creep_items(manifest_notes, MANIFEST_PATH)
    manifest_note_type_drift = sorted(
        f"{note_path} should keep note_type = {expected}"
        for note_path, raw in manifest_notes.items()
        if isinstance(raw, dict)
        and (expected := _manifest_note_type_expected(note_path))
        and str(raw.get("note_type", "")).strip() != expected
    )
    canonical_dirs = [Path(item) for item in manifest_rules.get("canonical_dirs", []) if isinstance(item, str)]
    canonical_dir_drift = sorted(
        note_path
        for note_path in manifest_notes
        if note_path.startswith("memory/")
        and note_path not in {"memory/index.md"}
        and not note_path.startswith("memory/current/")
        and not note_path.startswith("memory/templates/")
        and canonical_dirs
        and not any(Path(note_path) == directory or directory in Path(note_path).parents for directory in canonical_dirs)
    )
    task_board_globs = {item for item in manifest_rules.get("task_board_globs", []) if isinstance(item, str)}
    task_board_dependence = sorted(
        note_path
        for note_path, raw in manifest_notes.items()
        if isinstance(raw, dict)
        and not note_path.startswith("memory/current/")
        and task_board_globs.intersection(set(raw.get("routes_from", [])) | set(raw.get("stale_when", [])))
    )
    uncustomised_index_placeholders = _index_placeholder_findings(MEMORY_ROOT / "index.md")

    print("Memory freshness report")
    _print_section("Needs verification", needs_verification)
    _print_section("Missing trigger metadata", missing_trigger)
    _print_section("Missing Last confirmed", missing_last_confirmed)
    _print_section("Invalid Last confirmed date", invalid_last_confirmed)
    _print_section("Missing verification section", missing_verify)
    _print_section("Missing Load when", missing_load)
    _print_section("Missing Review when", missing_review)
    _print_section("Missing Failure signals", missing_failure)
    _print_section(f"Old confirmations (>{STALE_DAYS} days)", old_confirmations)
    _print_section("Oversized files", oversized_files)
    _print_section("Current-context drift signals", current_context_shape)
    _print_section("Current-note authority drift", current_authority_drift)
    _print_section("Current-note durable-truth drift", current_durable_truth_drift)
    _print_section("Current-note overlap pressure", current_note_overlap_pressure)
    _print_section("Incomplete improvement-signal lifecycle", incomplete_improvement_signals)
    _print_section("Always-read surface creep", always_read_creep)
    _print_section("Manifest note-type drift", manifest_note_type_drift)
    _print_section("Canonical-dir drift", canonical_dir_drift)
    _print_section("Task-board dependence", task_board_dependence)
    _print_section("Duplicate titles", duplicate_titles)
    _print_section("Missing manifest entries", missing_manifest_entries)
    _print_section("Manifest records for missing notes", manifest_records_for_missing_notes)
    _print_section("Shared canonical homes", shared_canonical_homes)
    _print_section("Uncustomised routing placeholders", uncustomised_index_placeholders)

    findings = {
        "needs_verification": needs_verification,
        "missing_trigger": missing_trigger,
        "missing_last_confirmed": missing_last_confirmed,
        "invalid_last_confirmed": invalid_last_confirmed,
        "missing_verify": missing_verify,
        "missing_load": missing_load,
        "missing_review": missing_review,
        "missing_failure": missing_failure,
        "old_confirmations": old_confirmations,
        "oversized_files": oversized_files,
        "current_context_shape": current_context_shape,
        "current_authority_drift": current_authority_drift,
        "current_durable_truth_drift": current_durable_truth_drift,
        "current_note_overlap_pressure": current_note_overlap_pressure,
        "incomplete_improvement_signals": incomplete_improvement_signals,
        "always_read_creep": always_read_creep,
        "manifest_note_type_drift": manifest_note_type_drift,
        "canonical_dir_drift": canonical_dir_drift,
        "task_board_dependence": task_board_dependence,
        "duplicate_titles": duplicate_titles,
        "missing_manifest_entries": missing_manifest_entries,
        "manifest_records_for_missing_notes": manifest_records_for_missing_notes,
        "shared_canonical_homes": shared_canonical_homes,
        "uncustomised_index_placeholders": uncustomised_index_placeholders,
    }
    strict_categories = set(args.strict_categories or DEFAULT_STRICT_CATEGORIES)
    if args.strict and any(findings[name] for name in strict_categories):
        return 1
    return 0


def _line_limit(note_type: str) -> int:
    return TYPE_LIMITS.get(note_type, MAX_LINES)


def _missing_sections(scan: NoteScan) -> set[str]:
    if scan.note_type == "project-state":
        return PROJECT_STATE_SECTIONS - scan.sections
    if scan.note_type == "task-context":
        return TASK_CONTEXT_SECTIONS - scan.sections
    if scan.note_type == "routing-feedback":
        return ROUTING_FEEDBACK_SECTIONS - scan.sections
    return set()


def _always_read_creep_items(manifest_notes: dict[str, dict[str, Any]], manifest_path: Path) -> list[str]:
    if not manifest_path.exists():
        return []
    data = _load_manifest_data(manifest_path)
    if not data:
        return []
    raw_rules = data.get("rules", {})
    rules: dict[str, Any] = {str(k): v for k, v in raw_rules.items()} if isinstance(raw_rules, dict) else {}
    items: list[str] = []
    routing_only = rules.get("routing_only", [])
    high_level = rules.get("high_level", [])
    if routing_only and routing_only != ["memory/index.md"]:
        items.append("rules.routing_only should stay limited to memory/index.md")
    if len(high_level) > 2:
        items.append("rules.high_level is expanding beyond the intended compact always-read surface")
    for note_path, raw in manifest_notes.items():
        if not isinstance(raw, dict):
            continue
        if (
            note_path in {"memory/current/project-state.md", "memory/current/task-context.md"}
            and str(raw.get("task_relevance", "")).strip() == "required"
        ):
            items.append(f"{note_path} should remain optional, not required")
    return sorted(set(items))


def _index_placeholder_findings(index_path: Path) -> list[str]:
    if not index_path.exists():
        return []
    text = index_path.read_text(encoding="utf-8")
    findings: list[str] = []
    if "Delete unused routing examples once the repository has concrete notes." in text:
        findings.append("memory/index.md still includes the starter placeholder cleanup instruction")
    if "<runtime-or-deployment-note>.md" in text or "<api-or-interface-note>.md" in text:
        findings.append("memory/index.md still contains starter placeholder route examples")
    return findings


def _current_note_overlap_pressure(scans: list[NoteScan]) -> list[str]:
    current_scans = [scan for scan in scans if scan.path.as_posix().startswith("memory/current/")]
    durable_scans = [
        scan
        for scan in scans
        if scan.path.as_posix().startswith("memory/")
        and not scan.path.as_posix().startswith("memory/current/")
        and scan.path.name not in {"README.md", "index.md"}
    ]
    findings: list[str] = []
    for current_scan in current_scans:
        if current_scan.line_count < CURRENT_NOTE_OVERLAP_MIN_LINES:
            continue
        current_text = current_scan.path.read_text(encoding="utf-8")
        if _delegates_durable_context(current_text):
            continue
        current_terms = _significant_terms(current_text)
        if len(current_terms) < CURRENT_NOTE_OVERLAP_MIN_SHARED_TERMS:
            continue
        for durable_scan in durable_scans:
            shared_terms = sorted(current_terms & _significant_terms(durable_scan.path.read_text(encoding="utf-8")))
            if len(shared_terms) >= CURRENT_NOTE_OVERLAP_MIN_SHARED_TERMS:
                findings.append(
                    (
                        f"{_render_path(current_scan.path)} overlaps durable note "
                        f"{_render_path(durable_scan.path)} "
                        f"({', '.join(shared_terms[:8])})"
                    )
                )
    return sorted(set(findings))


def _significant_terms(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower())
    stop_words = {
        "this",
        "that",
        "with",
        "from",
        "into",
        "when",
        "where",
        "which",
        "should",
        "would",
        "could",
        "there",
        "their",
        "about",
        "only",
        "keep",
        "note",
        "notes",
        "memory",
        "current",
        "state",
        "task",
        "context",
        "routing",
        "feedback",
        "review",
        "load",
        "last",
        "confirmed",
    }
    return {word for word in words if word not in stop_words}


def _delegates_durable_context(text: str) -> bool:
    lowered = text.lower()
    delegation_markers = (
        "instead of expanding this current note",
        "instead of expanding this overview",
        "instead of expanding this context note",
        "not as the primary home for durable knowledge",
        "do not restate durable routing guidance here",
    )
    return any(marker in lowered for marker in delegation_markers)


if __name__ == "__main__":
    raise SystemExit(main())
