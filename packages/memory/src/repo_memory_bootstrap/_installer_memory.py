from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from repo_memory_bootstrap._installer_output import _current_note_structure_findings
from repo_memory_bootstrap._installer_shared import (
    ALLOWED_HIGH_LEVEL_NOTES,
    ALWAYS_READ_SURFACE,
    DEFAULT_CORE_DOC_EXCLUDE_GLOBS,
    DEFAULT_CORE_DOC_GLOBS,
    MANIFEST_PATH,
    MARKDOWN_MEMORY_LINK_RE,
    MEMORY_PATH_RE,
    NOTE_TYPE_LINE_LIMITS,
    ROUTE_WORKING_SET_STRONG_WARNING,
    ROUTE_WORKING_SET_TARGET,
    ROUTING_FEEDBACK_MAX_LINES,
    ROUTING_FEEDBACK_MAX_RESOLVED,
    SHADOW_DOC_MIN_SHARED_TERMS,
    VALID_CANONICALITY_VALUES,
    VALID_ELIMINATION_TARGET_VALUES,
    VALID_MEMORY_ROLE_VALUES,
    VALID_PREFERRED_REMEDIATION_VALUES,
    VALID_SYMPTOM_OF_VALUES,
    VALID_TASK_RELEVANCE_VALUES,
    InstallResult,
    MemoryManifest,
    MemoryNoteRecord,
    RemediationRecommendation,
)

H2_RE = re.compile(r"^\s{0,3}##\s+(.+?)\s*$")
H3_RE = re.compile(r"^\s{0,3}###\s+(?:Case:\s*)?(.+?)\s*$")
RECURRING_FRICTION_ENTRY_RE = re.compile(r"^\s{0,3}###\s+Friction:\s*(.+?)\s*$")
INVARIANT_SIGNAL_RE = re.compile(r"\b(?:must|must not|never|always|cannot|do not|invariant)\b", re.IGNORECASE)
RATIONALE_SIGNAL_RE = re.compile(r"\b(?:because|therefore|trade-?off|rejected|decision|rationale)\b", re.IGNORECASE)
NOTE_METADATA_SECTION_TITLES = {
    "status",
    "purpose",
    "load when",
    "review when",
    "failure signals",
    "verify",
    "last confirmed",
    "companion skill",
}


@dataclass(frozen=True, slots=True)
class RoutingFeedbackCase:
    case_id: str
    case_type: str
    task_surface_summary: str
    files: tuple[str, ...]
    surfaces: tuple[str, ...]
    routed_notes_returned: tuple[str, ...]
    expected_notes: tuple[str, ...]
    why_text: str
    expected_routing_signal: str
    status: str


def _load_memory_manifest(path: Path) -> MemoryManifest | None:
    if not path.exists():
        return None

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None
    notes_table = data.get("notes", {})
    rules_table = data.get("rules", {})
    version = int(data.get("version", 1))

    notes: list[MemoryNoteRecord] = []
    for note_path, raw in notes_table.items():
        if not isinstance(raw, dict):
            continue
        notes.append(
            MemoryNoteRecord(
                path=Path(note_path),
                note_type=str(raw.get("note_type", "memory-note")),
                canonical_home=Path(str(raw.get("canonical_home", note_path))),
                authority=str(raw.get("authority", "supporting")),
                audience=str(raw.get("audience", "human+agent")),
                canonicality=str(raw.get("canonicality", "agent_only")),
                task_relevance=str(raw.get("task_relevance", "optional")),
                subsystems=tuple(_string_list(raw.get("subsystems"))),
                surfaces=tuple(_normalise_surface_name(value) for value in _string_list(raw.get("surfaces"))),
                routes_from=tuple(_string_list(raw.get("routes_from"))),
                stale_when=tuple(_string_list(raw.get("stale_when"))),
                related_validations=tuple(_string_list(raw.get("related_validations"))),
                routing_only=bool(raw.get("routing_only", False)),
                high_level=bool(raw.get("high_level", False)),
                memory_role=str(raw.get("memory_role", "") or "").strip(),
                symptom_of=str(raw.get("symptom_of", "") or "").strip(),
                preferred_remediation=str(raw.get("preferred_remediation", "") or "").strip(),
                improvement_candidate=bool(raw.get("improvement_candidate", False)),
                improvement_note=str(raw.get("improvement_note", "") or "").strip(),
                elimination_target=str(raw.get("elimination_target", "") or "").strip(),
                retention_justification=str(raw.get("retention_justification", "") or "").strip(),
            )
        )

    return MemoryManifest(
        path=path,
        version=version,
        notes=tuple(notes),
        routing_only=tuple(Path(value) for value in _string_list(rules_table.get("routing_only"))),
        high_level=tuple(Path(value) for value in _string_list(rules_table.get("high_level"))),
        canonical_dirs=tuple(Path(value) for value in _string_list(rules_table.get("canonical_dirs"))),
        task_board_globs=tuple(_string_list(rules_table.get("task_board_globs"))),
        core_doc_globs=tuple(_string_list(rules_table.get("core_doc_globs")) or list(DEFAULT_CORE_DOC_GLOBS)),
        core_doc_exclude_globs=tuple(_string_list(rules_table.get("core_doc_exclude_globs")) or list(DEFAULT_CORE_DOC_EXCLUDE_GLOBS)),
        forbid_core_docs_depend_on_memory=bool(rules_table.get("forbid_core_docs_depend_on_memory", False)),
    )


def _routing_baseline_paths(manifest: MemoryManifest | None) -> tuple[Path, ...]:
    if manifest is None:
        return ALWAYS_READ_SURFACE
    if manifest.routing_only:
        return tuple(dict.fromkeys(manifest.routing_only))
    flagged = tuple(note.path for note in manifest.notes if note.routing_only)
    if flagged:
        return tuple(dict.fromkeys(flagged))
    return ALWAYS_READ_SURFACE


def _high_level_paths(manifest: MemoryManifest | None) -> tuple[Path, ...]:
    if manifest is None:
        return ()
    if manifest.high_level:
        return tuple(dict.fromkeys(manifest.high_level))
    return tuple(dict.fromkeys(note.path for note in manifest.notes if note.high_level))


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _is_note_under_declared_canonical_dir(path: Path, canonical_dirs: tuple[Path, ...]) -> bool:
    return any(path == canonical_dir or canonical_dir in path.parents for canonical_dir in canonical_dirs)


def _routes_to_canonical_doc(note: MemoryNoteRecord) -> bool:
    if note.canonicality != "canonical_elsewhere":
        return False
    return _is_non_memory_canonical_home(note.canonical_home, note.path)


def _is_non_memory_canonical_home(canonical_home: Path, note_path: Path) -> bool:
    if canonical_home == note_path:
        return False
    canonical_str = canonical_home.as_posix()
    return not (canonical_str.startswith(".agentic-workspace/memory/") or canonical_str.startswith("memory/"))


def _manifest_note_path_family_warning(note: MemoryNoteRecord) -> str:
    path_str = note.path.as_posix()
    if path_str == ".agentic-workspace/memory/repo/index.md" and note.note_type != "routing":
        return ".agentic-workspace/memory/repo/index.md should keep note_type = routing"
    if path_str == ".agentic-workspace/memory/repo/current/project-state.md" and note.note_type != "current-overview":
        return ".agentic-workspace/memory/repo/current/project-state.md should keep note_type = current-overview"
    if path_str == ".agentic-workspace/memory/repo/current/task-context.md" and note.note_type != "current-context":
        return ".agentic-workspace/memory/repo/current/task-context.md should keep note_type = current-context"
    if path_str == ".agentic-workspace/memory/repo/current/routing-feedback.md" and note.note_type != "routing-feedback":
        return ".agentic-workspace/memory/repo/current/routing-feedback.md should keep note_type = routing-feedback"
    if path_str.startswith(".agentic-workspace/memory/repo/domains/") and note.note_type != "domain":
        return "notes under .agentic-workspace/memory/repo/domains/ should keep note_type = domain"
    if path_str.startswith(".agentic-workspace/memory/repo/invariants/") and note.note_type != "invariant":
        return "notes under .agentic-workspace/memory/repo/invariants/ should keep note_type = invariant"
    if path_str.startswith(".agentic-workspace/memory/repo/runbooks/") and note.note_type != "runbook":
        return "notes under .agentic-workspace/memory/repo/runbooks/ should keep note_type = runbook"
    if path_str == ".agentic-workspace/memory/repo/mistakes/recurring-failures.md" and note.note_type != "recurring-failures":
        return ".agentic-workspace/memory/repo/mistakes/recurring-failures.md should keep note_type = recurring-failures"
    if path_str.startswith(".agentic-workspace/memory/repo/decisions/") and note.note_type != "decision":
        return "notes under .agentic-workspace/memory/repo/decisions/ should keep note_type = decision"
    return ""


def _canonical_dir_warning(*, note: MemoryNoteRecord, manifest: MemoryManifest) -> str:
    if not manifest.canonical_dirs:
        return ""
    path_str = note.path.as_posix()
    if not (path_str.startswith(".agentic-workspace/memory/repo/") or path_str.startswith("memory/")):
        return ""
    if (
        note.path in {Path(".agentic-workspace/memory/repo/index.md"), Path("memory/index.md")}
        or path_str.startswith(".agentic-workspace/memory/repo/current/")
        or path_str.startswith("memory/current/")
        or path_str.startswith(".agentic-workspace/memory/repo/templates/")
        or path_str.startswith("memory/templates/")
    ):
        return ""
    if not _is_note_under_declared_canonical_dir(note.path, manifest.canonical_dirs):
        return "durable memory notes should live under rules.canonical_dirs or move out of memory/"
    canonical_str = note.canonical_home.as_posix()
    if (
        canonical_str.startswith(".agentic-workspace/memory/repo/") or canonical_str.startswith("memory/")
    ) and note.canonical_home != note.path:
        if not _is_note_under_declared_canonical_dir(note.canonical_home, manifest.canonical_dirs):
            return "memory canonical_home should also remain inside rules.canonical_dirs"
    return ""


def _task_board_dependency_warning(*, note: MemoryNoteRecord, manifest: MemoryManifest) -> str:
    if not manifest.task_board_globs:
        return ""
    if note.path.as_posix().startswith(".agentic-workspace/memory/repo/current/"):
        return ""
    route_patterns = set(note.routes_from) | set(note.stale_when)
    if route_patterns & set(manifest.task_board_globs):
        return "task-board globs should not drive durable memory routing or staleness outside .agentic-workspace/memory/repo/current/"
    return ""


def _audit_memory_doc_ownership(*, target_root: Path, result, force_enforcement: bool = False) -> None:
    manifest = _load_memory_manifest(target_root / MANIFEST_PATH)
    if manifest is None:
        return

    routing_only = _routing_baseline_paths(manifest)
    high_level = _high_level_paths(manifest)

    if routing_only and tuple(routing_only) != ALWAYS_READ_SURFACE:
        result.add(
            "manual review",
            target_root / MANIFEST_PATH,
            "rules.routing_only should contain only .agentic-workspace/memory/repo/index.md so the always-read surface stays small",
            role="memory-manifest",
            safety="manual",
            source=MANIFEST_PATH.as_posix(),
            category="contract-drift",
        )
    if Path(".agentic-workspace/memory/repo/current/task-context.md") in high_level:
        result.add(
            "manual review",
            target_root / MANIFEST_PATH,
            "rules.high_level should not include .agentic-workspace/memory/repo/current/task-context.md; keep continuation notes opt-in",
            role="memory-manifest",
            safety="manual",
            source=MANIFEST_PATH.as_posix(),
            category="contract-drift",
        )
    if len(set(high_level)) > len(ALLOWED_HIGH_LEVEL_NOTES):
        result.add(
            "manual review",
            target_root / MANIFEST_PATH,
            (
                "rules.high_level is expanding beyond the intended compact always-read "
                "surface; keep only .agentic-workspace/memory/repo/index.md and optional project-state-level "
                "context there"
            ),
            role="memory-manifest",
            safety="manual",
            source=MANIFEST_PATH.as_posix(),
            category="contract-drift",
        )

    for note in manifest.notes:
        if note.canonicality not in VALID_CANONICALITY_VALUES:
            result.add(
                "manual review",
                target_root / note.path,
                ("manifest canonicality must be one of: agent_only, candidate_for_promotion, canonical_elsewhere, deprecated"),
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.task_relevance not in VALID_TASK_RELEVANCE_VALUES:
            result.add(
                "manual review",
                target_root / note.path,
                "manifest task_relevance must be required or optional",
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.memory_role and note.memory_role not in VALID_MEMORY_ROLE_VALUES:
            result.add(
                "manual review",
                target_root / note.path,
                "manifest memory_role must be durable_truth or improvement_signal when present",
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.symptom_of and note.symptom_of not in VALID_SYMPTOM_OF_VALUES:
            result.add(
                "manual review",
                target_root / note.path,
                (
                    "manifest symptom_of must be one of: workflow_friction, "
                    "guidance_drift, missing_guardrail, architecture_friction, "
                    "operator_complexity"
                ),
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.preferred_remediation and note.preferred_remediation not in VALID_PREFERRED_REMEDIATION_VALUES:
            result.add(
                "manual review",
                target_root / note.path,
                "manifest preferred_remediation must be one of: docs, skill, script, test, validation, refactor, code",
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.elimination_target and note.elimination_target not in VALID_ELIMINATION_TARGET_VALUES:
            result.add(
                "manual review",
                target_root / note.path,
                "manifest elimination_target must be one of: shrink, promote, automate, refactor_away",
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.memory_role == "improvement_signal":
            has_remediation = bool(note.preferred_remediation and note.improvement_note)
            has_retention_justification = bool(note.retention_justification)
            if not has_remediation and not has_retention_justification:
                result.add(
                    "manual review",
                    target_root / note.path,
                    (
                        "improvement-signal notes should declare either "
                        "preferred_remediation plus improvement_note, or "
                        "retention_justification explaining why the note should remain"
                    ),
                    role="memory-manifest",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="manual-review",
                )
            if not note.elimination_target:
                result.add(
                    "manual review",
                    target_root / note.path,
                    (
                        "improvement-signal note is missing elimination_target; add one "
                        "to clarify whether the note should shrink, promote, automate, "
                        "or refactor away after remediation"
                    ),
                    role="memory-manifest",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="manual-review",
                )
        if note.canonicality == "canonical_elsewhere" and not _is_non_memory_canonical_home(note.canonical_home, note.path):
            result.add(
                "manual review",
                target_root / note.path,
                "canonical_elsewhere notes must point canonical_home at a checked-in canonical doc outside memory/",
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.path == Path(".agentic-workspace/memory/WORKFLOW.md") and note.task_relevance == "required":
            result.add(
                "manual review",
                target_root / note.path,
                "WORKFLOW.md should remain reference policy, not default required reading for every task",
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.path == Path(".agentic-workspace/memory/repo/current/project-state.md") and note.task_relevance != "optional":
            result.add(
                "manual review",
                target_root / note.path,
                "project-state should stay optional high-level context rather than required task setup",
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.path.as_posix().startswith(".agentic-workspace/memory/repo/current/") and note.authority not in {"advisory", "supporting"}:
            result.add(
                "manual review",
                target_root / note.path,
                "current-memory notes should stay weak-authority context rather than canonical durable authority",
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.path.as_posix().startswith(".agentic-workspace/memory/repo/current/") and note.memory_role:
            result.add(
                "manual review",
                target_root / note.path,
                (
                    "current-memory notes should not declare durable-truth or "
                    "improvement-signal memory roles; move durable facts to a "
                    "primary home"
                ),
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.path == Path(".agentic-workspace/memory/repo/current/task-context.md"):
            if note.task_relevance != "optional":
                result.add(
                    "manual review",
                    target_root / note.path,
                    "task-context should stay optional continuation compression rather than required task setup",
                    role="memory-manifest",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="contract-drift",
                )
            if note.surfaces or note.routes_from:
                result.add(
                    "manual review",
                    target_root / note.path,
                    (
                        "task-context should not advertise broad routing metadata; load "
                        "it only when active continuation context is genuinely needed"
                    ),
                    role="memory-manifest",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="contract-drift",
                )
            if note.canonicality != "agent_only":
                result.add(
                    "manual review",
                    target_root / note.path,
                    "current-memory notes should stay agent_only rather than becoming promotion or canonical-doc targets",
                    role="memory-manifest",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="contract-drift",
                )
        if note.path == Path(".agentic-workspace/memory/repo/current/routing-feedback.md"):
            if note.task_relevance != "optional":
                result.add(
                    "manual review",
                    target_root / note.path,
                    "routing-feedback should stay optional calibration context rather than required task setup",
                    role="memory-manifest",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="contract-drift",
                )
            if note.canonicality != "agent_only":
                result.add(
                    "manual review",
                    target_root / note.path,
                    "routing-feedback should stay agent_only calibration context rather than a promotion or canonical-doc target",
                    role="memory-manifest",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="contract-drift",
                )
            if note.memory_role:
                result.add(
                    "manual review",
                    target_root / note.path,
                    "routing-feedback should stay calibration-only rather than declaring durable truth or improvement-signal memory",
                    role="memory-manifest",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="contract-drift",
                )
            if note.surfaces or note.routes_from or note.stale_when:
                result.add(
                    "manual review",
                    target_root / note.path,
                    (
                        "routing-feedback should not advertise broad routing or freshness metadata; "
                        "keep it as a compact calibration surface only"
                    ),
                    role="memory-manifest",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="contract-drift",
                )
        if note.path == Path(".agentic-workspace/memory/repo/current/project-state.md") and note.canonicality != "agent_only":
            result.add(
                "manual review",
                target_root / note.path,
                "project-state should stay agent_only current context rather than a promotion or canonical-doc target",
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
            if note.surfaces or note.routes_from:
                result.add(
                    "manual review",
                    target_root / note.path,
                    (
                        "task-context should not advertise broad routing metadata; load "
                        "it only when active continuation context is genuinely needed"
                    ),
                    role="memory-manifest",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="contract-drift",
                )
        if path_family_warning := _manifest_note_path_family_warning(note):
            result.add(
                "manual review",
                target_root / note.path,
                path_family_warning,
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if canonical_dir_warning := _canonical_dir_warning(note=note, manifest=manifest):
            result.add(
                "manual review",
                target_root / note.path,
                canonical_dir_warning,
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if task_board_warning := _task_board_dependency_warning(note=note, manifest=manifest):
            result.add(
                "manual review",
                target_root / note.path,
                task_board_warning,
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )

    required_high_level = [note.path for note in manifest.notes if note.path in high_level and note.task_relevance == "required"]
    if len(required_high_level) > len(ALLOWED_HIGH_LEVEL_NOTES):
        result.add(
            "manual review",
            target_root / MANIFEST_PATH,
            "too many notes are both high-level and required; keep the default read surface compact and route the rest on demand",
            role="memory-manifest",
            safety="manual",
            source=MANIFEST_PATH.as_posix(),
            category="contract-drift",
        )

    _audit_index_compactness(target_root=target_root, manifest=manifest, result=result)
    _audit_note_overlap(target_root=target_root, manifest=manifest, result=result)

    if not manifest.forbid_core_docs_depend_on_memory and not force_enforcement:
        return

    core_docs = tuple(
        _iter_core_docs(
            target_root=target_root,
            include_globs=manifest.core_doc_globs,
            exclude_globs=manifest.core_doc_exclude_globs,
        )
    )

    for doc_path in core_docs:
        matches = _extract_memory_references(doc_path.read_text(encoding="utf-8"))
        if not matches:
            continue
        detail = ", ".join(matches[:3])
        if len(matches) > 3:
            detail = f"{detail}, ..."
        result.add(
            "manual review",
            doc_path,
            (
                f"core doc depends on memory ({detail}); promote stable guidance "
                "into checked-in canonical docs and leave memory as assistive residue or stubs"
            ),
            role="doc-ownership-audit",
            safety="manual",
            source=doc_path.relative_to(target_root).as_posix(),
            category="manual-review",
        )

    for note in manifest.notes:
        note_path = target_root / note.path
        if not note_path.exists():
            continue
        overlaps = _find_shadow_doc_matches(
            note_path=note_path,
            canonical_home=target_root / note.canonical_home,
            core_docs=core_docs,
            target_root=target_root,
        )
        for canonical_doc, shared_terms in overlaps:
            result.add(
                "manual review",
                note_path,
                (
                    f"shadow-doc overlap with {canonical_doc.relative_to(target_root).as_posix()} "
                    f"({', '.join(shared_terms[:8])}); consolidate stable guidance into canonical docs "
                    "and leave memory as residue or a stub"
                ),
                role="shadow-doc-audit",
                safety="manual",
                source=note.path.as_posix(),
                category="manual-review",
            )


def _iter_core_docs(*, target_root: Path, include_globs: tuple[str, ...], exclude_globs: tuple[str, ...]) -> Iterable[Path]:
    seen: set[Path] = set()
    for pattern in include_globs:
        for path in target_root.glob(pattern):
            if not path.is_file():
                continue
            relative = path.relative_to(target_root)
            relative_str = relative.as_posix()
            if any(_path_matches_pattern(relative_str, glob) for glob in exclude_globs):
                continue
            if path in seen:
                continue
            seen.add(path)
            yield path


def _audit_index_compactness(*, target_root: Path, manifest: MemoryManifest, result) -> None:
    index_path = target_root / ".agentic-workspace/memory/repo/index.md"
    if not index_path.exists():
        return
    lines = index_path.read_text(encoding="utf-8").splitlines()
    if len(lines) > 140:
        result.add(
            "manual review",
            index_path,
            ".agentic-workspace/memory/repo/index.md is getting summary-heavy; keep it short, routing-shaped, and focused on the smallest useful note bundles",
            role="memory-index-audit",
            safety="manual",
            source=index_path.relative_to(target_root).as_posix(),
            category="manual-review",
        )


def _audit_note_overlap(*, target_root: Path, manifest: MemoryManifest, result) -> None:
    adjacent_categories = {
        ("domain", "invariant"),
        ("runbook", "recurring-failures"),
        ("domain", "decision"),
    }
    comparable_notes = [
        note
        for note in manifest.notes
        if note.path.as_posix().startswith(".agentic-workspace/memory/repo/")
        and not note.path.as_posix().startswith(".agentic-workspace/memory/repo/current/")
        and note.path.name != "index.md"
        and note.path.name != "README.md"
        and (target_root / note.path).exists()
    ]
    for idx, left in enumerate(comparable_notes):
        left_path = target_root / left.path
        left_text = left_path.read_text(encoding="utf-8")
        left_terms = _significant_terms(left_text)
        left_title_terms = _primary_heading_terms(path=left.path, text=left_text)
        left_refs = set(_extract_memory_references(left_text))
        if len(left_terms) < SHADOW_DOC_MIN_SHARED_TERMS:
            continue
        for right in comparable_notes[idx + 1 :]:
            categories = tuple(sorted({left.note_type, right.note_type}))
            same_family = left.path.parent == right.path.parent or categories in adjacent_categories
            shared_surfaces = set(left.surfaces) & set(right.surfaces)
            shared_routes = set(left.routes_from) & set(right.routes_from)
            if _is_distinct_package_context_pair(left, right):
                continue
            if _is_package_context_companion_pair(left.path, right.path):
                continue
            if not same_family and not shared_routes and len(shared_surfaces) < 2:
                continue
            if not same_family and not shared_surfaces and not shared_routes:
                continue
            right_path = target_root / right.path
            right_text = right_path.read_text(encoding="utf-8")
            right_title_terms = _primary_heading_terms(path=right.path, text=right_text)
            right_refs = set(_extract_memory_references(right_text))
            if right.path.as_posix() in left_refs or left.path.as_posix() in right_refs:
                continue
            if "decision" in categories and not (left_title_terms & right_title_terms):
                continue
            shared_terms = sorted(left_terms & _significant_terms(right_text))
            if len(shared_terms) < SHADOW_DOC_MIN_SHARED_TERMS + 2:
                continue
            recommendation = "reclassify" if left.note_type != right.note_type else "merge"
            if shared_routes and not same_family:
                recommendation = "keep separate with distinct primary homes"
            result.add(
                "consider",
                left_path,
                (
                    f"possible note overlap with {right.path.as_posix()} "
                    f"({', '.join(shared_terms[:8])}); recommend {recommendation} or explicitly keeping distinct primary homes"
                ),
                role="memory-overlap-audit",
                safety="manual",
                source=left.path.as_posix(),
                category="manual-review",
            )


def _extract_memory_references(text: str) -> list[str]:
    matches = {match.group(0) for match in MEMORY_PATH_RE.finditer(text)}
    matches.update(match.group(1) for match in MARKDOWN_MEMORY_LINK_RE.finditer(text))
    return sorted(match.rstrip(").,`") for match in matches if match.strip())


def _is_package_context_note(path: Path) -> bool:
    return path.as_posix().startswith(".agentic-workspace/memory/repo/domains/") and path.stem.endswith("package-context")


def _is_package_context_companion_pair(left_path: Path, right_path: Path) -> bool:
    package_context_runbook = Path(".agentic-workspace/memory/repo/runbooks/package-context-inspection.md")
    return (left_path == package_context_runbook and _is_package_context_note(right_path)) or (
        right_path == package_context_runbook and _is_package_context_note(left_path)
    )


def _package_route_roots(note: MemoryNoteRecord) -> set[str]:
    roots: set[str] = set()
    for route in note.routes_from:
        if not route.startswith("packages/"):
            continue
        parts = route.split("/")
        if len(parts) >= 2:
            roots.add("/".join(parts[:2]))
    return roots


def _is_distinct_package_context_pair(left: MemoryNoteRecord, right: MemoryNoteRecord) -> bool:
    if not (_is_package_context_note(left.path) and _is_package_context_note(right.path)):
        return False
    left_roots = _package_route_roots(left)
    right_roots = _package_route_roots(right)
    return bool(left_roots and right_roots and left_roots.isdisjoint(right_roots))


def _iter_promotion_candidates(
    *,
    target_root: Path,
    manifest: MemoryManifest | None,
    requested: set[Path],
) -> list[tuple[Path, MemoryNoteRecord | None, str, RemediationRecommendation | None]]:
    candidates: list[tuple[Path, MemoryNoteRecord | None, str, RemediationRecommendation | None]] = []

    if manifest is not None:
        for note in manifest.notes:
            note_path = target_root / note.path
            if requested and note.path not in requested:
                continue
            if (
                note.canonicality
                not in {
                    "candidate_for_promotion",
                    "canonical_elsewhere",
                }
                and not note.improvement_candidate
            ):
                continue
            if note.canonicality == "candidate_for_promotion":
                destination = (
                    note.canonical_home.as_posix()
                    if note.canonical_home != note.path
                    else _suggest_canonical_doc_path(note.path).as_posix()
                )
                detail = (
                    f"promotion candidate; suggested canonical doc {destination}. "
                    "Promote stable guidance there, then leave this memory note as a short stub, "
                    "backlink, or fallback summary."
                )
            else:
                if note.canonicality == "canonical_elsewhere":
                    detail = (
                        f"canonical truth should live in {note.canonical_home.as_posix()}. "
                        "Keep this memory note compact and non-authoritative."
                    )
                else:
                    detail = (
                        "improvement candidate; this note looks like a signal that the repo may need an "
                        "upstream change rather than more memory."
                    )
            improvement_hint = _first_improvement_hint(
                note,
                note_path,
                note_path.read_text(encoding="utf-8") if note_path.exists() else "",
                for_report=True,
            )
            recommendation = _build_remediation_recommendation(
                note,
                note_path,
                note_path.read_text(encoding="utf-8") if note_path.exists() else "",
                for_report=True,
            )
            if improvement_hint:
                detail = f"{detail} Also consider {improvement_hint}."
            if recommendation:
                detail = f"{detail} Recommended remediation: {_format_remediation_detail(recommendation)}."
            candidates.append((note_path, note, detail, recommendation))

    for requested_note in requested:
        if any(candidate[0] == target_root / requested_note for candidate in candidates):
            continue
        requested_path = target_root / requested_note
        if not requested_path.exists():
            candidates.append(
                (
                    requested_path,
                    None,
                    "explicit note supplied for promotion review, but the file does not exist",
                    None,
                )
            )
            continue
        detail = _explicit_note_review_detail(requested_note)
        recommendation = _build_remediation_recommendation(
            _lookup_manifest_note(manifest, requested_note),
            requested_path,
            requested_path.read_text(encoding="utf-8") if requested_path.exists() else "",
            for_report=True,
        )
        improvement_hint = _first_improvement_hint(
            _lookup_manifest_note(manifest, requested_note),
            requested_path,
            requested_path.read_text(encoding="utf-8") if requested_path.exists() else "",
            for_report=True,
        )
        if improvement_hint:
            detail = f"{detail} Also consider {improvement_hint}."
        if recommendation:
            detail = f"{detail} Recommended remediation: {_format_remediation_detail(recommendation)}."
        candidates.append((requested_path, None, detail, recommendation))

    return candidates


def _lookup_manifest_note(manifest: MemoryManifest | None, note_path: Path) -> MemoryNoteRecord | None:
    if manifest is None:
        return None
    for note in manifest.notes:
        if note.path == note_path:
            return note
    return None


def _line_limit_for_note(note: MemoryNoteRecord | None, note_path: Path) -> tuple[str, int]:
    if note is not None and note.note_type in NOTE_TYPE_LINE_LIMITS:
        return note.note_type, NOTE_TYPE_LINE_LIMITS[note.note_type]
    relative_str = note_path.as_posix()
    if ".agentic-workspace/memory/repo/invariants/" in relative_str:
        return "invariant", NOTE_TYPE_LINE_LIMITS["invariant"]
    if ".agentic-workspace/memory/repo/domains/" in relative_str:
        return "domain", NOTE_TYPE_LINE_LIMITS["domain"]
    if ".agentic-workspace/memory/repo/runbooks/" in relative_str:
        return "runbook", NOTE_TYPE_LINE_LIMITS["runbook"]
    if relative_str.endswith(".agentic-workspace/memory/repo/mistakes/recurring-failures.md"):
        return "recurring-failures", NOTE_TYPE_LINE_LIMITS["recurring-failures"]
    if ".agentic-workspace/memory/repo/decisions/" in relative_str:
        return "decision", NOTE_TYPE_LINE_LIMITS["decision"]
    if relative_str.endswith(".agentic-workspace/memory/repo/current/project-state.md"):
        return "current-overview", NOTE_TYPE_LINE_LIMITS["current-overview"]
    if relative_str.endswith(".agentic-workspace/memory/repo/current/task-context.md"):
        return "current-context", NOTE_TYPE_LINE_LIMITS["current-context"]
    return "memory-note", 200


def _size_warning_for_note(note: MemoryNoteRecord | None, note_path: Path, text: str) -> str | None:
    note_type, limit = _line_limit_for_note(note, note_path)
    line_count = len(text.splitlines())
    if line_count <= limit:
        return None
    remediation = {
        "invariant": "split by primary home or promote stable explanatory prose into canonical docs so the invariant stays tight",
        "domain": "split by primary home, promote stable guidance into canonical docs, or review whether refactor pressure is accumulating",
        "runbook": "move repeated mechanics into a checked-in skill and keep the runbook procedural only",
        "recurring-failures": "convert repeated failure memory into tests, validation, or linting before growing the note further",
        "decision": "reduce historical detail and keep only durable consequences or still-relevant rejected paths",
        "current-overview": "reduce stale history and keep only a compact repo overview",
        "current-context": (
            "remove planner/log spillover and keep only active goal, touched "
            "surfaces, blocking assumptions, next validation, and resume cues"
        ),
        "memory-note": "split by primary home or reduce stable guidance to a shorter residue note",
    }[note_type]
    return f"{note_type} note is oversized ({line_count} lines, expected <= {limit}); {remediation}"


def _post_remediation_shape_advice(recommendation: RemediationRecommendation) -> str:
    advice = {
        "promote": "leave memory as a short stub, backlink, or fallback summary",
        "keep_stub": "keep the memory note as short assistive residue only",
        "automate": "remove repeated mechanics from the note and keep only minimal residue if any context still saves rediscovery cost",
        "refactor_away": "remove the note or reduce it to a brief boundary reminder once the underlying friction is gone",
        "shrink": "keep only the durable residue that still saves rediscovery cost",
    }
    return advice.get(recommendation.memory_action, "keep only the smallest memory shape that remains justified")


def _note_lifecycle_findings(
    note: MemoryNoteRecord,
    *,
    note_path: Path,
    text: str,
    recommendation: RemediationRecommendation | None,
) -> list[tuple[str, str, str, str, str]]:
    if recommendation is None:
        return []

    line_count = len(text.splitlines())
    findings: list[tuple[str, str, str, str, str]] = []
    shape_advice = _post_remediation_shape_advice(recommendation)

    if note.canonicality == "candidate_for_promotion" and line_count >= 40:
        findings.append(
            (
                (
                    f"promotion candidate is still carrying substantial prose in memory ({line_count} lines); move canonical guidance into "
                    f"{recommendation.target_path_hint} and {shape_advice}"
                ),
                recommendation.kind,
                recommendation.target_path_hint,
                recommendation.confidence,
                recommendation.memory_action,
            )
        )
    if note.canonicality == "canonical_elsewhere" and line_count >= 30:
        findings.append(
            (
                (
                    f"canonical_elsewhere note is too large for assistive residue ({line_count} lines); "
                    f"reduce it and {shape_advice} while pointing at {recommendation.target_path_hint}"
                ),
                recommendation.kind,
                recommendation.target_path_hint,
                recommendation.confidence,
                recommendation.memory_action,
            )
        )
    if note.memory_role == "improvement_signal" and recommendation.memory_action in {"automate", "refactor_away"} and line_count >= 20:
        findings.append(
            (
                (
                    f"improvement-signal note should not become the long-term endpoint; once {recommendation.target_path_hint} lands, "
                    f"{shape_advice}"
                ),
                recommendation.kind,
                recommendation.target_path_hint,
                recommendation.confidence,
                recommendation.memory_action,
            )
        )
    if recommendation.kind == "skill" and line_count >= 20:
        findings.append(
            (
                (
                    f"repeatable procedural prose is accumulating here; move the workflow into {recommendation.target_path_hint} and "
                    f"{shape_advice}"
                ),
                recommendation.kind,
                recommendation.target_path_hint,
                recommendation.confidence,
                recommendation.memory_action,
            )
        )

    deduped: list[tuple[str, str, str, str, str]] = []
    seen_details: set[str] = set()
    for finding in findings:
        if finding[0] in seen_details:
            continue
        seen_details.add(finding[0])
        deduped.append(finding)
    return deduped


def _note_multi_home_findings(
    note: MemoryNoteRecord,
    *,
    note_path: Path,
    text: str,
) -> list[tuple[str, str, str, str, str]]:
    lines = _analysis_lines(text)
    line_count = len(lines)
    imperative_lines = sum(1 for line in lines if re.match(r"^\s*(?:-|\*|\d+\.)\s+", line) or line.strip().startswith("`"))
    command_lines = sum(1 for line in lines if re.search(r"`[^`]+`", line) or re.match(r"^\s*(?:run|execute|call)\b", line.strip().lower()))
    invariant_lines = sum(1 for line in lines if INVARIANT_SIGNAL_RE.search(line))
    rationale_lines = sum(1 for line in lines if RATIONALE_SIGNAL_RE.search(line))
    findings: list[tuple[str, str, str, str, str]] = []

    if note.note_type in {"domain", "decision"} and imperative_lines >= 6 and command_lines >= 4:
        findings.append(
            (
                (
                    f"{note.note_type} note is accumulating repeatable procedure ({imperative_lines} imperative lines); "
                    f"extract the workflow into {_infer_skill_target(note, note_path)}"
                    " or a sibling runbook and keep this note focused on durable boundaries"
                ),
                "skill",
                _infer_skill_target(note, note_path),
                "medium",
                "automate",
            )
        )
    if note.note_type in {"domain", "decision", "runbook"} and invariant_lines >= 5 and line_count >= 8:
        invariant_target = f".agentic-workspace/memory/repo/invariants/{note_path.stem}.md"
        findings.append(
            (
                (
                    "must-stay-true rules are accumulating outside .agentic-workspace/memory/repo/invariants/; "
                    f"extract the invariant content into {invariant_target} and leave the remaining note in one primary home"
                ),
                "docs",
                invariant_target,
                "medium",
                "shrink",
            )
        )
    if note.note_type == "runbook" and rationale_lines >= 4 and line_count >= 30:
        decision_target = f".agentic-workspace/memory/repo/decisions/{note_path.stem}.md"
        findings.append(
            (
                (
                    f"runbook is accumulating rationale or trade-off prose; move durable why/why-not context into {decision_target} "
                    "and keep this note procedural only"
                ),
                "docs",
                decision_target,
                "low",
                "shrink",
            )
        )

    deduped: list[tuple[str, str, str, str, str]] = []
    seen_details: set[str] = set()
    for finding in findings:
        if finding[0] in seen_details:
            continue
        seen_details.add(finding[0])
        deduped.append(finding)
    return deduped


def _explicit_note_review_detail(requested_note: Path) -> str:
    requested_str = requested_note.as_posix()
    if requested_str.startswith(".agentic-workspace/memory/repo/runbooks/"):
        return (
            "explicit note supplied; review whether the durable facts should stay in memory, "
            "the repeated workflow should become a checked-in skill, or the mechanics now "
            "justify a repo-owned script or command."
        )
    if requested_str.startswith(".agentic-workspace/memory/repo/mistakes/"):
        return (
            "explicit note supplied; review whether the recurring failure should stay documented "
            "in memory or now justify a regression test, validation, or lint rule."
        )
    if requested_str.startswith(".agentic-workspace/memory/repo/domains/"):
        return (
            "explicit note supplied; review whether the stable parts belong in canonical docs "
            "or whether the note is signalling a refactor or clearer boundary need."
        )
    if requested_str.startswith(".agentic-workspace/memory/repo/invariants/"):
        return (
            "explicit note supplied; review whether the invariant should stay in memory, move "
            "into canonical docs, or be enforced more directly in code or validation."
        )
    if requested_str.startswith(".agentic-workspace/memory/repo/decisions/"):
        return (
            "explicit note supplied; review whether the durable rationale should stay in memory, "
            "move into canonical docs, or be reduced after the underlying boundary becomes clearer."
        )
    return (
        "explicit note supplied; review whether the stable parts belong in canonical docs "
        f"({_suggest_canonical_doc_path(requested_note).as_posix()}), whether the note should "
        "stay compact in memory, or whether it is signalling a better target such as a skill, "
        "script, test, validation, or refactor review."
    )


def _first_improvement_hint(
    note: MemoryNoteRecord | None,
    note_path: Path,
    text: str,
    *,
    for_report: bool,
) -> str:
    hints = _collect_improvement_hints(note, note_path, text, for_report=for_report)
    return hints[0] if hints else ""


def _format_remediation_detail(recommendation: RemediationRecommendation) -> str:
    return (
        f"{recommendation.kind} -> {recommendation.target_path_hint} "
        f"({recommendation.confidence} confidence; then {recommendation.memory_action})"
    )


def _build_remediation_recommendation(
    note: MemoryNoteRecord | None,
    note_path: Path,
    text: str,
    *,
    for_report: bool,
) -> RemediationRecommendation | None:
    relative = note.path if note is not None else note_path
    relative_str = relative.as_posix()
    lines = _analysis_lines(text)
    line_count = len(lines)
    imperative_lines = sum(1 for line in lines if re.match(r"^\s*(?:-|\*|\d+\.)\s+", line) or line.strip().startswith("`"))
    command_lines = sum(1 for line in lines if re.search(r"`[^`]+`", line) or re.match(r"^\s*(?:run|execute|call)\b", line.strip().lower()))
    has_failure_entries = _has_concrete_failure_entries(text)

    if note is not None:
        explicit = _explicit_remediation_recommendation(
            note,
            note_path=note_path,
            has_failure_entries=has_failure_entries,
        )
        if explicit is not None:
            return explicit

    if ".agentic-workspace/memory/repo/mistakes/" in relative_str and has_failure_entries:
        return RemediationRecommendation(
            kind="test",
            target_path_hint=_infer_test_target(note, note_path),
            reason="Recurring failures should usually be displaced by an executable guardrail.",
            confidence="medium",
            memory_action="shrink",
        )

    if ".agentic-workspace/memory/repo/runbooks/" in relative_str and line_count >= 12 and imperative_lines >= 6:
        if command_lines >= 6 and line_count <= 90:
            return RemediationRecommendation(
                kind="script",
                target_path_hint=_infer_script_target(note, note_path),
                reason="This runbook is mechanical enough that a repo-owned script or command is likely a better long-term home.",
                confidence="medium",
                memory_action="automate",
            )
        return RemediationRecommendation(
            kind="skill",
            target_path_hint=_infer_skill_target(note, note_path),
            reason=(
                "This procedure is repeated operational choreography that should be "
                "executed through a checked-in skill before more prose is added."
            ),
            confidence="medium",
            memory_action="automate",
        )

    if ".agentic-workspace/memory/repo/domains/" in relative_str and line_count >= 140:
        remediation_kind = "refactor"
        target = _infer_code_target(note, note_path)
        reason = "This domain note is compensating for a high-discovery-cost subsystem and likely needs clearer ownership or structure."
        if note is not None and note.canonicality == "candidate_for_promotion":
            remediation_kind = "docs"
            target = _infer_docs_target(note, note_path)
            reason = "This domain note appears to be stabilising into normal checked-in documentation."
        return RemediationRecommendation(
            kind=remediation_kind,
            target_path_hint=target,
            reason=reason,
            confidence="medium",
            memory_action="refactor_away" if remediation_kind == "refactor" else "promote",
        )

    if relative_str.endswith(".agentic-workspace/memory/repo/index.md") and line_count >= 120:
        return RemediationRecommendation(
            kind="refactor",
            target_path_hint="memory/ plus the awkward routed subsystem surface",
            reason=(
                "The routing layer is compensating for friction that should usually be "
                "resolved through note consolidation or clearer repo boundaries."
            ),
            confidence="low",
            memory_action="shrink",
        )

    if ".agentic-workspace/memory/repo/current/" in relative_str and line_count >= 80 and not for_report:
        return RemediationRecommendation(
            kind="docs",
            target_path_hint="the repo planning/status surface",
            reason="The current-memory note is growing beyond re-orientation support and likely reflects planner or workflow spillover.",
            confidence="low",
            memory_action="shrink",
        )
    return None


def _analysis_lines(text: str) -> list[str]:
    lines = text.splitlines()
    filtered: list[str] = []
    current_h2 = ""
    for line in lines:
        match = H2_RE.match(line)
        if match:
            current_h2 = match.group(1).strip().lower()
            continue
        if current_h2 in NOTE_METADATA_SECTION_TITLES:
            continue
        filtered.append(line)
    return filtered


def _explicit_remediation_recommendation(
    note: MemoryNoteRecord,
    *,
    note_path: Path,
    has_failure_entries: bool,
) -> RemediationRecommendation | None:
    relative_str = note.path.as_posix()
    confidence = "high"
    memory_action = "shrink"

    if note.canonicality == "candidate_for_promotion":
        return RemediationRecommendation(
            kind="docs",
            target_path_hint=_infer_docs_target(note, note_path),
            reason="This note is explicitly marked as a promotion candidate for canonical checked-in docs.",
            confidence=confidence,
            memory_action="promote",
        )
    if note.canonicality == "canonical_elsewhere":
        return RemediationRecommendation(
            kind="docs",
            target_path_hint=_infer_docs_target(note, note_path),
            reason="This note is explicitly marked as assistive residue while canonical truth lives elsewhere.",
            confidence=confidence,
            memory_action="keep_stub",
        )

    kind = note.preferred_remediation
    if not kind and note.memory_role != "improvement_signal":
        return None

    if not kind:
        return None

    target_map = {
        "docs": _infer_docs_target(note, note_path),
        "skill": _infer_skill_target(note, note_path),
        "script": _infer_script_target(note, note_path),
        "test": _infer_test_target(note, note_path),
        "validation": _infer_validation_target(note, note_path),
        "refactor": _infer_code_target(note, note_path),
        "code": _infer_code_target(note, note_path),
    }
    reason_map = {
        "docs": "The manifest marks canonical checked-in docs as the preferred upstream home.",
        "skill": "The manifest marks a checked-in skill as the preferred replacement for this repeated workflow.",
        "script": "The manifest marks a repo-owned script or command as the preferred replacement for this repeated workflow.",
        "test": "The manifest marks an executable regression test as the preferred replacement for this remembered failure mode.",
        "validation": "The manifest marks validation or linting as the preferred replacement for this missing guardrail.",
        "refactor": "The manifest marks refactor or ownership cleanup as the preferred way to remove this recurring friction.",
        "code": "The manifest marks direct implementation enforcement as the preferred way to remove this recurring friction.",
    }
    if kind == "test" and ".agentic-workspace/memory/repo/mistakes/" in relative_str and not has_failure_entries:
        return None
    return RemediationRecommendation(
        kind=kind,
        target_path_hint=target_map[kind],
        reason=reason_map[kind],
        confidence=confidence,
        memory_action=note.elimination_target or ("promote" if kind == "docs" else memory_action),
    )


def _collect_improvement_hints(
    note: MemoryNoteRecord | None,
    note_path: Path,
    text: str,
    *,
    for_report: bool,
) -> list[str]:
    hints: list[str] = []
    relative = note.path if note is not None else note_path
    relative_str = relative.as_posix()
    lines = _analysis_lines(text)
    line_count = len(lines)
    imperative_lines = sum(1 for line in lines if re.match(r"^\s*(?:-|\*|\d+\.)\s+", line) or line.strip().startswith("`"))
    has_failure_entries = _has_concrete_failure_entries(text)

    if note is not None:
        manifest_hint = _manifest_improvement_hint(note, has_failure_entries=has_failure_entries)
        if manifest_hint:
            hints.append(manifest_hint)

    if ".agentic-workspace/memory/repo/mistakes/" in relative_str and has_failure_entries:
        hints.append("a regression test, validation, or lint rule if the recurring failure remains active")
    if ".agentic-workspace/memory/repo/runbooks/" in relative_str and line_count >= 35 and imperative_lines >= 6:
        hints.append("a checked-in skill first, then a repo-owned script or command if the workflow stays mechanical")
    if ".agentic-workspace/memory/repo/domains/" in relative_str and line_count >= 140:
        hints.append(("clearer canonical docs or refactor review if this note keeps compensating for a high-discovery-cost subsystem"))
    if relative_str.endswith(".agentic-workspace/memory/repo/index.md") and line_count >= 120:
        hints.append(("clearer repo boundaries or note consolidation if routing keeps expanding to explain one awkward area"))
    if ".agentic-workspace/memory/repo/current/" in relative_str and line_count >= 80 and not for_report:
        hints.append(("shrinking planning/status spillover or unresolved structure friction before growing current-memory notes further"))

    deduped: list[str] = []
    seen: set[str] = set()
    for hint in hints:
        if hint in seen:
            continue
        seen.add(hint)
        deduped.append(hint)
    return deduped


def _manifest_improvement_hint(
    note: MemoryNoteRecord,
    *,
    has_failure_entries: bool = True,
) -> str:
    remediation_map = {
        "docs": "promoting the stable parts into canonical docs",
        "skill": "a checked-in skill for the repeated workflow",
        "script": "a repo-owned script or command if the workflow is stable and mechanical",
        "test": "a regression test that removes the need to remember this failure mode manually",
        "validation": ("stronger validation or linting so the note stops compensating for missing guardrails"),
        "refactor": "refactor review or clearer ownership boundaries in the underlying subsystem",
        "code": "encoding the constraint directly in the implementation",
    }
    elimination_map = {
        "shrink": "shrinking the note after the upstream improvement lands",
        "promote": "promoting the durable human-facing parts and leaving only a short stub",
        "automate": "automating the repeated mechanics so the note can stay minimal",
        "refactor_away": "refactoring the underlying friction away so the note becomes unnecessary",
    }

    parts: list[str] = []
    if ".agentic-workspace/memory/repo/mistakes/" in note.path.as_posix() and not has_failure_entries:
        return ""

    if note.preferred_remediation:
        parts.append(
            remediation_map.get(
                note.preferred_remediation,
                f"{note.preferred_remediation} as the preferred remediation target",
            )
        )

    if note.elimination_target:
        parts.append(
            elimination_map.get(
                note.elimination_target,
                f"{note.elimination_target} as the intended elimination path",
            )
        )

    if note.improvement_note:
        parts.append(note.improvement_note.rstrip("."))
    if note.retention_justification:
        parts.append(f"retention justification: {note.retention_justification.rstrip('.')}")

    if note.memory_role == "improvement_signal" and not parts:
        parts.append(("an upstream repo improvement rather than treating the memory note as the long-term endpoint"))

    return "; ".join(parts)


def _has_concrete_failure_entries(text: str) -> bool:
    # Treat non-template recurring-failure notes with list entries as concrete
    # signal, even when they do not yet follow the full "### Failure:" block.
    if "<short symptom-first label>" not in text:
        for line in text.splitlines():
            if re.match(r"^\s*(?:-|\*|\d+\.)\s+\S", line):
                return True

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("### Failure:"):
            continue
        if "<short symptom-first label>" in stripped:
            continue
        return True
    return False


def _emit_improvement_pressure(
    *,
    target_root: Path,
    manifest: MemoryManifest | None,
    result,
) -> None:
    if manifest is None:
        return

    for note in manifest.notes:
        note_path = target_root / note.path
        if not note_path.exists():
            continue
        text = note_path.read_text(encoding="utf-8")
        recommendation = _build_remediation_recommendation(note, note_path, text, for_report=False)
        seen_hints: set[str] = set()
        for hint in _collect_improvement_hints(note, note_path, text, for_report=False):
            if hint in seen_hints:
                continue
            seen_hints.add(hint)
            result.add(
                "consider",
                note_path,
                f"improvement candidate: consider {hint}",
                role="improvement-pressure",
                safety="advisory",
                source=note.path.as_posix(),
                category="manual-review",
                remediation_kind=recommendation.kind if recommendation else "",
                remediation_target=recommendation.target_path_hint if recommendation else "",
                remediation_reason=recommendation.reason if recommendation else "",
                remediation_confidence=recommendation.confidence if recommendation else "",
                memory_action=recommendation.memory_action if recommendation else "",
            )


def _emit_memory_shape_pressure(
    *,
    target_root: Path,
    manifest: MemoryManifest | None,
    result,
) -> None:
    note_records = {note.path: note for note in manifest.notes} if manifest is not None else {}
    for note_path in sorted((target_root / ".agentic-workspace" / "memory" / "repo").glob("**/*.md")):
        relative = note_path.relative_to(target_root)
        if relative.as_posix().startswith(".agentic-workspace/memory/repo/templates/"):
            continue
        if relative == Path(".agentic-workspace/memory/repo/index.md"):
            continue
        if relative.name == "README.md" and relative.parts[1] in {"domains", "invariants", "runbooks", "decisions"}:
            continue
        text = note_path.read_text(encoding="utf-8")
        warning = _size_warning_for_note(note_records.get(relative), note_path, text)
        if not warning:
            continue
        result.add(
            "consider" if relative.as_posix().startswith(".agentic-workspace/memory/repo/current/") else "manual review",
            note_path,
            warning,
            role="memory-size-audit",
            safety="manual",
            source=relative.as_posix(),
            category="manual-review",
        )


def _emit_note_lifecycle_pressure(
    *,
    target_root: Path,
    manifest: MemoryManifest | None,
    result,
) -> None:
    if manifest is None:
        return

    for note in manifest.notes:
        note_path = target_root / note.path
        if not note_path.exists():
            continue
        text = note_path.read_text(encoding="utf-8")
        recommendation = _build_remediation_recommendation(note, note_path, text, for_report=False)
        for detail, remediation_kind, remediation_target, remediation_confidence, memory_action in _note_lifecycle_findings(
            note,
            note_path=note_path,
            text=text,
            recommendation=recommendation,
        ):
            result.add(
                "manual review",
                note_path,
                detail,
                role="memory-lifecycle",
                safety="manual",
                source=note.path.as_posix(),
                category="manual-review",
                remediation_kind=remediation_kind,
                remediation_target=remediation_target,
                remediation_confidence=remediation_confidence,
                memory_action=memory_action,
            )


def _emit_multi_home_pressure(
    *,
    target_root: Path,
    manifest: MemoryManifest | None,
    result,
) -> None:
    if manifest is None:
        return

    for note in manifest.notes:
        note_path = target_root / note.path
        if not note_path.exists():
            continue
        text = note_path.read_text(encoding="utf-8")
        for detail, remediation_kind, remediation_target, remediation_confidence, memory_action in _note_multi_home_findings(
            note,
            note_path=note_path,
            text=text,
        ):
            result.add(
                "manual review",
                note_path,
                detail,
                role="memory-multi-home",
                safety="manual",
                source=note.path.as_posix(),
                category="manual-review",
                remediation_kind=remediation_kind,
                remediation_target=remediation_target,
                remediation_confidence=remediation_confidence,
                memory_action=memory_action,
            )


def _load_routing_feedback_cases(path: Path) -> list[RoutingFeedbackCase]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    current_h2 = ""
    current_case_id: str | None = None
    case_lines: list[str] = []
    cases: list[RoutingFeedbackCase] = []

    def flush_case() -> None:
        nonlocal current_case_id, case_lines
        if current_case_id is None:
            return
        case = _parse_routing_feedback_case(
            case_id=current_case_id,
            case_type="missed_note" if current_h2 == "Missed-note entries" else "over_routing",
            lines=case_lines,
        )
        if case is not None:
            cases.append(case)
        current_case_id = None
        case_lines = []

    for line in lines:
        h2_match = H2_RE.match(line)
        if h2_match:
            flush_case()
            current_h2 = h2_match.group(1).strip()
            continue
        h3_match = H3_RE.match(line)
        if h3_match and current_h2 in {"Missed-note entries", "Over-routing entries"}:
            flush_case()
            current_case_id = h3_match.group(1).strip()
            case_lines = []
            continue
        if current_case_id is not None:
            case_lines.append(line)
    flush_case()
    return cases


def _audit_routing_feedback_note(*, target_root: Path, result) -> None:
    note_path = target_root / ".agentic-workspace/memory/repo/current/routing-feedback.md"
    if not note_path.exists():
        return
    text = note_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) > ROUTING_FEEDBACK_MAX_LINES:
        result.add(
            "manual review",
            note_path,
            (
                f"routing-feedback note is oversized ({len(lines)} lines); keep "
                "routing calibration notes short and current rather than archival"
            ),
            role="routing-feedback-audit",
            safety="manual",
            source=note_path.relative_to(target_root).as_posix(),
            category="manual-review",
        )
    cases = _load_routing_feedback_cases(note_path)
    resolved = sum(1 for case in cases if case.status in {"tuned", "rejected"})
    if resolved > ROUTING_FEEDBACK_MAX_RESOLVED:
        result.add(
            "manual review",
            note_path,
            "routing-feedback note contains too many resolved entries; compress tuned or rejected cases into synthesis or remove them",
            role="routing-feedback-audit",
            safety="manual",
            source=note_path.relative_to(target_root).as_posix(),
            category="manual-review",
        )
    for case in cases:
        if not case.task_surface_summary:
            result.add(
                "manual review",
                note_path,
                f"routing-feedback case '{case.case_id}' is missing task surface summary",
                role="routing-feedback-audit",
                safety="manual",
                source=note_path.relative_to(target_root).as_posix(),
                category="manual-review",
            )
        if not case.expected_notes:
            result.add(
                "manual review",
                note_path,
                f"routing-feedback case '{case.case_id}' is missing expected missing/unexpected note entries",
                role="routing-feedback-audit",
                safety="manual",
                source=note_path.relative_to(target_root).as_posix(),
                category="manual-review",
            )
        if not case.status:
            result.add(
                "manual review",
                note_path,
                f"routing-feedback case '{case.case_id}' is missing status",
                role="routing-feedback-audit",
                safety="manual",
                source=note_path.relative_to(target_root).as_posix(),
                category="manual-review",
            )


def _parse_recurring_friction_entries(text: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    lines = text.splitlines()
    idx = 0
    while idx < len(lines):
        match = RECURRING_FRICTION_ENTRY_RE.match(lines[idx])
        if not match:
            idx += 1
            continue
        label = match.group(1).strip()
        sections: dict[str, int] = {
            "observed recurrences": 0,
            "keep now": 0,
            "promote when": 0,
            "most likely remediation": 0,
            "last seen": 0,
        }
        current_section = ""
        idx += 1
        while idx < len(lines) and not RECURRING_FRICTION_ENTRY_RE.match(lines[idx]):
            stripped = lines[idx].strip()
            lowered = stripped.lower()
            if lowered in sections:
                current_section = lowered
            elif current_section == "observed recurrences" and re.match(r"^(?:-|\*|\d+\.)\s+\S", stripped):
                sections["observed recurrences"] += 1
            elif current_section and stripped:
                sections[current_section] += 1
            idx += 1
        entries.append({"label": label, **sections})
    return entries


def _recurring_friction_structure_findings(text: str) -> list[str]:
    findings = _current_note_structure_findings(
        text=text,
        expected_sections=(
            "Status",
            "Scope",
            "Load when",
            "Review when",
            "Failure signals",
            "When to use this",
            "Rules",
            "Entry format",
            "Verification",
            "Boundary reminder",
            "Last confirmed",
        ),
        note_name="recurring-friction ledger",
    )
    entries = [entry for entry in _parse_recurring_friction_entries(text) if "<short recurring friction label>" not in str(entry["label"])]
    for entry in entries:
        label = str(entry["label"])
        if not int(entry["observed recurrences"]):
            findings.append(
                f"recurring-friction entry '{label}' is missing observed recurrence bullets; add short dated evidence before treating it as durable pressure"
            )
        if not int(entry["keep now"]):
            findings.append(
                f"recurring-friction entry '{label}' is missing Keep now guidance; explain why the signal should stay below issue or active-plan level for now"
            )
        if not int(entry["promote when"]):
            findings.append(
                f"recurring-friction entry '{label}' is missing Promote when guidance; record the trigger that should move this friction into planning or stronger remediation"
            )
        if not int(entry["most likely remediation"]):
            findings.append(
                f"recurring-friction entry '{label}' is missing Most likely remediation; name the preferred upstream fix direction before the signal compounds"
            )
        if not int(entry["last seen"]):
            findings.append(
                f"recurring-friction entry '{label}' is missing Last seen; keep the evidence reviewable instead of letting recurrence timing drift into chat"
            )
    return findings


def _recurring_friction_promotion_findings(text: str) -> list[str]:
    findings: list[str] = []
    entries = [entry for entry in _parse_recurring_friction_entries(text) if "<short recurring friction label>" not in str(entry["label"])]
    for entry in entries:
        recurrence_count = int(entry["observed recurrences"])
        if recurrence_count >= 2:
            findings.append(
                f"recurring-friction entry '{entry['label']}' has {recurrence_count} observed recurrences; promote it into planning, docs, tests, validation, or automation before the same friction resets again"
            )
    return findings


def _parse_routing_feedback_case(*, case_id: str, case_type: str, lines: list[str]) -> RoutingFeedbackCase | None:
    labels = _parse_labelled_sections(lines)
    if not labels:
        return None
    expected_label = "Expected missing note" if case_type == "missed_note" else "Unexpected notes"
    why_label = "Why it was needed" if case_type == "missed_note" else "Why they were unnecessary"
    return RoutingFeedbackCase(
        case_id=case_id,
        case_type=case_type,
        task_surface_summary=_first_value(labels.get("Task surface summary", [])),
        files=tuple(labels.get("Files", [])),
        surfaces=tuple(labels.get("Surfaces", [])),
        routed_notes_returned=tuple(labels.get("Routed notes returned", [])),
        expected_notes=tuple(labels.get(expected_label, [])),
        why_text=_first_value(labels.get(why_label, [])),
        expected_routing_signal=_first_value(labels.get("Expected routing signal", [])),
        status=_first_value(labels.get("Status", [])).lower(),
    )


def _parse_labelled_sections(lines: list[str]) -> dict[str, list[str]]:
    labels: dict[str, list[str]] = {}
    current_label: str | None = None
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if re.match(r"^[A-Za-z][A-Za-z0-9 \-]+$", line.strip()):
            current_label = line.strip()
            labels.setdefault(current_label, [])
            continue
        if current_label is None:
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            labels[current_label].append(stripped[2:].strip())
        else:
            labels[current_label].append(stripped)
    return labels


def _first_value(values: list[str]) -> str:
    return values[0].strip() if values else ""


def _build_route_review_cases(
    *, target_root: Path, feedback_cases: list[RoutingFeedbackCase], routed_results: dict[str, InstallResult]
) -> tuple[list[dict[str, object]], dict[str, int]]:
    review_cases: list[dict[str, object]] = []
    reviewed_case_count = 0
    still_missed_count = 0
    still_over_routed_count = 0
    unresolved_case_count = 0

    for case in feedback_cases:
        externalized = _routing_case_is_externalized(case.status)
        routed = routed_results.get(case.case_id)
        if routed is None:
            unresolved_case_count += 1
            review_cases.append(
                {
                    "case_id": case.case_id,
                    "case_type": case.case_type,
                    "expected_notes": list(case.expected_notes),
                    "current_routed_notes": [],
                    "matched": False,
                    "status": case.status or "unknown",
                    "unresolved": True,
                    "externalized": externalized,
                }
            )
            continue
        reviewed_case_count += 1
        current_routed = [
            action.path.relative_to(target_root).as_posix() for action in routed.actions if action.kind in {"required", "optional"}
        ]
        expected_set = set(case.expected_notes)
        current_set = set(current_routed)
        if case.case_type == "missed_note":
            matched = expected_set.issubset(current_set)
            if not matched and not externalized:
                still_missed_count += 1
        else:
            matched = expected_set.isdisjoint(current_set)
            if not matched and not externalized:
                still_over_routed_count += 1
        review_cases.append(
            {
                "case_id": case.case_id,
                "case_type": case.case_type,
                "expected_notes": list(case.expected_notes),
                "current_routed_notes": current_routed,
                "matched": matched,
                "status": case.status or "unknown",
                "unresolved": False,
                "externalized": externalized,
            }
        )

    return review_cases, {
        "reviewed_case_count": reviewed_case_count,
        "still_missed_count": still_missed_count,
        "still_over_routed_count": still_over_routed_count,
        "unresolved_case_count": unresolved_case_count,
    }


def _build_route_report_feedback_summary(
    *,
    feedback_cases: list[RoutingFeedbackCase],
    review_cases: list[dict[str, object]],
) -> dict[str, object]:
    live_feedback_cases = [case for case in feedback_cases if not _routing_case_is_externalized(case.status)]
    return {
        "total_feedback_case_count": len(live_feedback_cases),
        "reviewed_feedback_case_count": sum(1 for case in review_cases if not case.get("unresolved") and not case.get("externalized")),
        "unresolved_feedback_case_count": sum(1 for case in review_cases if case.get("unresolved") and not case.get("externalized")),
        "externalized_case_count": sum(1 for case in review_cases if case.get("externalized")),
        "missed_note_case_count": sum(1 for case in live_feedback_cases if case.case_type == "missed_note"),
        "still_missed_count": sum(
            1
            for case in review_cases
            if case.get("case_type") == "missed_note"
            and not case.get("matched")
            and not case.get("unresolved")
            and not case.get("externalized")
        ),
        "over_routing_case_count": sum(1 for case in live_feedback_cases if case.case_type == "over_routing"),
        "still_over_routed_count": sum(
            1
            for case in review_cases
            if case.get("case_type") == "over_routing"
            and not case.get("matched")
            and not case.get("unresolved")
            and not case.get("externalized")
        ),
        "open_case_count": sum(1 for case in live_feedback_cases if case.status == "open"),
        "tuned_case_count": sum(1 for case in live_feedback_cases if case.status == "tuned"),
        "rejected_case_count": sum(1 for case in live_feedback_cases if case.status == "rejected"),
    }


def _build_route_report_case_type_summary(
    *,
    fixture_results: list[dict[str, object]],
    feedback_summary: dict[str, object],
    case_type: str,
) -> dict[str, object]:
    relevant_fixtures = [fixture for fixture in fixture_results if fixture.get("case_type") == case_type and fixture.get("valid")]
    failing_fixtures = [fixture for fixture in relevant_fixtures if not fixture.get("passed")]
    fixture_count = len(relevant_fixtures)
    return {
        "fixture_case_count": fixture_count,
        "failing_fixture_count": len(failing_fixtures),
        "fixture_failure_rate": round(len(failing_fixtures) / fixture_count, 2) if fixture_count else 0.0,
        "feedback_case_count": _int_value(feedback_summary.get(f"{case_type}_case_count")),
        "still_failing_feedback_case_count": _int_value(
            feedback_summary.get("still_missed_count" if case_type == "missed_note" else "still_over_routed_count")
        ),
    }


def _load_route_report_fixtures(fixtures_root: Path) -> list[dict[str, object]]:
    if not fixtures_root.exists():
        return []

    results: list[dict[str, object]] = []
    for path in sorted(fixtures_root.glob("*.json")):
        result = _load_route_report_fixture(path)
        results.append(result)
    return results


def _load_route_report_fixture(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "fixture_name": path.stem,
            "path": path.as_posix(),
            "valid": False,
            "error": f"invalid JSON: {exc.msg}",
        }
    if not isinstance(raw, dict):
        return {
            "fixture_name": path.stem,
            "path": path.as_posix(),
            "valid": False,
            "error": "fixture must be a JSON object",
        }

    required_fields = (
        "name",
        "files",
        "surfaces",
        "expected_required",
        "expected_optional",
        "unexpected_notes",
        "missing_note_candidates",
    )
    missing_fields = [field for field in required_fields if field not in raw]
    if missing_fields:
        return {
            "fixture_name": str(raw.get("name") or path.stem),
            "path": path.as_posix(),
            "valid": False,
            "error": f"missing required fields: {', '.join(missing_fields)}",
        }

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        return {
            "fixture_name": path.stem,
            "path": path.as_posix(),
            "valid": False,
            "error": "fixture name must be a non-empty string",
        }

    list_fields = ("files", "surfaces", "expected_required", "expected_optional", "unexpected_notes", "missing_note_candidates")
    for field in list_fields:
        value = raw.get(field)
        if not isinstance(value, list):
            return {
                "fixture_name": name,
                "path": path.as_posix(),
                "valid": False,
                "error": f"{field} must be a list of strings",
            }
        if not all(isinstance(item, str) for item in value):
            return {
                "fixture_name": name,
                "path": path.as_posix(),
                "valid": False,
                "error": f"{field} must contain only strings",
            }

    return {
        "fixture_name": name.strip(),
        "path": path.as_posix(),
        "valid": True,
        "case_type": str(raw.get("case_type", "general")).strip() or "general",
        "files": list(raw["files"]),
        "surfaces": list(raw["surfaces"]),
        "expected_required": list(raw["expected_required"]),
        "expected_optional": list(raw["expected_optional"]),
        "unexpected_notes": list(raw["unexpected_notes"]),
        "missing_note_candidates": list(raw["missing_note_candidates"]),
    }


def _evaluate_route_report_fixtures(
    *,
    target_root: Path,
    fixtures: list[dict[str, object]],
    route_memory_fn,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    results: list[dict[str, object]] = []
    valid_results: list[dict[str, object]] = []

    for fixture in fixtures:
        if not fixture.get("valid"):
            results.append(
                {
                    "fixture_name": fixture["fixture_name"],
                    "case_type": fixture.get("case_type", "general"),
                    "files": [],
                    "surfaces": [],
                    "passed": False,
                    "valid": False,
                    "error": fixture["error"],
                    "missing_expected_notes": [],
                    "unexpected_returned_notes": [],
                    "current_required_notes": [],
                    "current_optional_notes": [],
                    "routed_note_count": 0,
                    "exceeded_target": "no",
                    "exceeded_strong_warning": "no",
                }
            )
            continue

        routed = _evaluate_route_fixture(target_root=target_root, fixture=fixture, route_memory_fn=route_memory_fn)
        results.append(routed)
        valid_results.append(routed)

    fixture_count = len(fixtures)
    passing_count = sum(1 for item in valid_results if item["passed"])
    failing_count = sum(1 for item in valid_results if not item["passed"])
    invalid_count = sum(1 for item in results if not item["valid"])
    if valid_results:
        average_routed = round(sum(_int_value(item.get("routed_note_count")) for item in valid_results) / len(valid_results), 2)
        average_required = round(sum(_int_value(item.get("required_note_count")) for item in valid_results) / len(valid_results), 2)
        average_optional = round(sum(_int_value(item.get("optional_note_count")) for item in valid_results) / len(valid_results), 2)
        max_routed = max(_int_value(item.get("routed_note_count")) for item in valid_results)
        average_lines = round(sum(_int_value(item.get("routed_line_count")) for item in valid_results) / len(valid_results), 2)
        max_lines = max(_int_value(item.get("routed_line_count")) for item in valid_results)
        over_target = sum(1 for item in valid_results if item["exceeded_target"] == "yes")
        over_strong = sum(1 for item in valid_results if item["exceeded_strong_warning"] == "yes")
    else:
        average_routed = 0.0
        average_required = 0.0
        average_optional = 0.0
        max_routed = 0
        average_lines = 0.0
        max_lines = 0
        over_target = 0
        over_strong = 0

    summary = {
        "fixture_count": fixture_count,
        "passing_fixture_count": passing_count,
        "failing_fixture_count": failing_count,
        "invalid_fixture_count": invalid_count,
        "average_routed_note_count": average_routed,
        "average_required_note_count": average_required,
        "average_optional_note_count": average_optional,
        "max_routed_note_count": max_routed,
        "fixture_count_exceeding_target": over_target,
        "fixture_count_exceeding_strong_warning": over_strong,
        "average_routed_line_count": average_lines,
        "max_routed_line_count": max_lines,
    }
    return results, summary


def _evaluate_route_fixture(*, target_root: Path, fixture: dict[str, object], route_memory_fn) -> dict[str, object]:
    files = _string_sequence(fixture.get("files"))
    surfaces = _string_sequence(fixture.get("surfaces"))
    result = route_memory_fn(target=target_root, files=files, surfaces=surfaces)
    current_required_notes = sorted(
        action.path.relative_to(target_root).as_posix() for action in result.actions if action.kind == "required"
    )
    current_optional_notes = sorted(
        action.path.relative_to(target_root).as_posix() for action in result.actions if action.kind == "optional"
    )
    expected_required = set(_string_sequence(fixture.get("expected_required")))
    expected_optional = set(_string_sequence(fixture.get("expected_optional")))
    unexpected_notes = set(_string_sequence(fixture.get("unexpected_notes")))
    current_required = set(current_required_notes)
    current_optional = set(current_optional_notes)

    missing_expected = sorted((expected_required - current_required) | (expected_optional - current_optional))
    unexpected_returned = sorted(
        (current_required - expected_required)
        | (current_optional - expected_optional)
        | ((current_required | current_optional) & unexpected_notes)
    )
    passed = not missing_expected and not unexpected_returned
    routed_note_count = len(current_required_notes) + len(current_optional_notes)
    routed_paths = [target_root / Path(note) for note in [*current_required_notes, *current_optional_notes]]
    routed_line_count = 0
    for path in routed_paths:
        if path.exists():
            routed_line_count += len(path.read_text(encoding="utf-8").splitlines())
    return {
        "fixture_name": fixture["fixture_name"],
        "case_type": fixture.get("case_type", "general"),
        "files": files,
        "surfaces": surfaces,
        "passed": passed,
        "valid": True,
        "error": "",
        "missing_expected_notes": missing_expected,
        "unexpected_returned_notes": unexpected_returned,
        "current_required_notes": current_required_notes,
        "current_optional_notes": current_optional_notes,
        "required_note_count": len(current_required_notes),
        "optional_note_count": len(current_optional_notes),
        "routed_note_count": routed_note_count,
        "routed_line_count": routed_line_count,
        "exceeded_target": "yes" if routed_note_count > ROUTE_WORKING_SET_TARGET else "no",
        "exceeded_strong_warning": "yes" if routed_note_count > ROUTE_WORKING_SET_STRONG_WARNING else "no",
        "routing_confidence": str(result.route_summary.get("confidence", "")),
    }


def _string_sequence(value: object) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    return [str(item) for item in value]


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _suggest_canonical_doc_path(note_path: Path) -> Path:
    if note_path.parts[:2] == ("memory", "runbooks") and len(note_path.parts) >= 3:
        return Path("docs/runbooks") / note_path.name
    if note_path.parts[:2] == ("memory", "domains") and len(note_path.parts) >= 3:
        return Path("docs") / note_path.name
    if note_path.parts[:2] == ("memory", "invariants") and len(note_path.parts) >= 3:
        return Path("docs/invariants") / note_path.name
    if note_path.parts[:2] == ("memory", "decisions") and len(note_path.parts) >= 3:
        return Path("docs/decisions") / note_path.name
    return Path("docs") / note_path.name


def _infer_docs_target(note: MemoryNoteRecord | None, note_path: Path) -> str:
    if note is not None and note.canonical_home != note.path and note.canonical_home.parts[:1] != ("memory",):
        return note.canonical_home.as_posix()
    return _suggest_canonical_doc_path(note.path if note is not None else note_path).as_posix()


def _infer_skill_target(note: MemoryNoteRecord | None, note_path: Path) -> str:
    stem = (note.path if note is not None else note_path).stem.replace("_", "-")
    return f".agentic-workspace/memory/repo/skills/{stem}/SKILL.md"


def _infer_script_target(note: MemoryNoteRecord | None, note_path: Path) -> str:
    stem = (note.path if note is not None else note_path).stem.replace("_", "-")
    if stem in {"readme", "index"}:
        stem = "memory-workflow"
    return f"scripts/{stem}.py"


def _infer_test_target(note: MemoryNoteRecord | None, note_path: Path) -> str:
    patterns = ()
    if note is not None:
        patterns = note.stale_when or note.routes_from
    for pattern in patterns:
        if pattern.startswith("tests/"):
            return pattern
        if pattern.startswith("scripts/check/"):
            return pattern
        if pattern.startswith("src/"):
            stem = Path(pattern).stem.replace("*", "").replace("_", "-")
            if stem:
                return f"tests/test_{stem}.py"
    stem = (note.path if note is not None else note_path).stem.replace("_", "-")
    return f"tests/test_{stem}.py"


def _infer_validation_target(note: MemoryNoteRecord | None, note_path: Path) -> str:
    patterns = ()
    if note is not None:
        patterns = note.stale_when or note.routes_from
    for pattern in patterns:
        if pattern.startswith("scripts/check/"):
            return pattern
    stem = (note.path if note is not None else note_path).stem.replace("_", "-")
    return f"scripts/check/check_{stem}.py"


def _infer_code_target(note: MemoryNoteRecord | None, note_path: Path) -> str:
    patterns = ()
    if note is not None:
        patterns = note.routes_from or note.stale_when
    for pattern in patterns:
        root = pattern.split("/")[0]
        if root and root not in {"memory", "tests", "docs"}:
            return f"{root}/"
    if note_path.parts[:2] == ("memory", "domains"):
        return "src/"
    return "the affected repo-owned subsystem"


def _find_shadow_doc_matches(
    *,
    note_path: Path,
    canonical_home: Path,
    core_docs: tuple[Path, ...],
    target_root: Path,
) -> list[tuple[Path, list[str]]]:
    note_tokens = _significant_terms(note_path.read_text(encoding="utf-8"))
    if len(note_tokens) < SHADOW_DOC_MIN_SHARED_TERMS:
        return []

    overlaps: list[tuple[Path, list[str]]] = []
    for doc_path in core_docs:
        if doc_path == note_path:
            continue
        if canonical_home.exists() and doc_path == canonical_home:
            continue
        if not _shadow_doc_paths_related(note_path, doc_path):
            continue
        shared_terms = sorted(note_tokens & _significant_terms(doc_path.read_text(encoding="utf-8")))
        if len(shared_terms) >= SHADOW_DOC_MIN_SHARED_TERMS:
            overlaps.append((doc_path, shared_terms))
    return overlaps


def _significant_terms(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower())
    stop_words = {
        "this",
        "that",
        "with",
        "from",
        "after",
        "again",
        "before",
        "during",
        "when",
        "where",
        "should",
        "would",
        "there",
        "their",
        "into",
        "only",
        "keep",
        "note",
        "memory",
        "docs",
        "repo",
        "repository",
        "stable",
        "guidance",
        "canonical",
        "review",
        "using",
        "used",
        "than",
        "then",
        "them",
        "have",
        "will",
        "what",
        "which",
        "while",
        "task",
        "tasks",
        "active",
        "applies",
        "against",
        "behaviour",
        "behaviours",
        "changes",
        "check",
        "checked",
        "cleanup",
        "confirm",
        "consequences",
        "consolidation",
        "contract",
        "contracts",
        "confirmed",
        "current",
        "decision",
        "decisions",
        "docs",
        "durable",
        "entrypoint",
        "explicit",
        "failure",
        "failures",
        "files",
        "install",
        "installed",
        "lifecycle",
        "longer",
        "looks",
        "goal",
        "goals",
        "high",
        "high-level",
        "impact",
        "improvement",
        "improvements",
        "implementation",
        "implemented",
        "last",
        "lesson",
        "lessons",
        "level",
        "load",
        "managed",
        "materially",
        "monorepo",
        "ownership",
        "package",
        "packages",
        "primary",
        "product",
        "progress",
        "read",
        "reading",
        "remain",
        "rule",
        "rules",
        "root",
        "scope",
        "signals",
        "state",
        "status",
        "surface",
        "surfaces",
        "system",
        "systems",
        "workflow",
        "verified",
        "verify",
        "wishlist",
    }
    return {word for word in words if word not in stop_words}


def _primary_heading_terms(*, path: Path, text: str) -> set[str]:
    for line in text.splitlines():
        match = re.match(r"^\s{0,3}#\s+(.+?)\s*$", line)
        if match:
            return _significant_terms(match.group(1))
    return _significant_terms(path.stem.replace("-", " ").replace("_", " "))


def _shadow_doc_paths_related(note_path: Path, doc_path: Path) -> bool:
    note_stem = note_path.stem.lower()
    doc_stem = doc_path.stem.lower()
    if note_stem == doc_stem:
        return True
    return note_stem in doc_stem or doc_stem in note_stem


def _find_manifest_matches(
    manifest: MemoryManifest | None,
    *,
    files: list[str],
    surfaces: set[str],
    use_staleness: bool,
) -> list[tuple[str, str, str, str]]:
    if manifest is None:
        return []

    suggestions: list[tuple[str, str, str, str]] = []
    for note in manifest.notes:
        reasons: list[str] = []
        match_sources: list[str] = []
        if surfaces and any(surface in surfaces for surface in note.surfaces):
            matched = ", ".join(sorted({surface for surface in note.surfaces if surface in surfaces}))
            reasons.append(f"manifest surface match ({matched})")
            match_sources.append("surface")

        globs = note.stale_when if use_staleness else note.routes_from
        if files and globs:
            matched_globs = sorted({pattern for pattern in globs if any(_path_matches_pattern(path, pattern) for path in files)})
            if matched_globs:
                reasons.append(f"manifest path match ({', '.join(matched_globs)})")
                match_sources.append("file-path")

        if reasons:
            reason = "; ".join(reasons)
            match_source = ", ".join(dict.fromkeys(match_sources))
            if _routes_to_canonical_doc(note):
                suggestions.append(
                    (
                        "required",
                        note.canonical_home.as_posix(),
                        f"{reason}; canonical doc takes precedence over memory",
                        match_source,
                    )
                )
                suggestions.append(
                    (
                        "optional",
                        note.path.as_posix(),
                        f"{reason}; memory note is fallback context only",
                        match_source,
                    )
                )
                continue

            recommendation = "required" if note.task_relevance == "required" else "optional"
            suggestions.append((recommendation, note.path.as_posix(), reason, match_source))
    return suggestions


def _dedupe_route_suggestions(
    suggestions: Iterable[tuple[str, str, str, str, int]],
) -> list[tuple[str, str, str, str, int]]:
    by_note: dict[str, tuple[str, str, str, str, int]] = {}
    for recommendation, note, reason, match_source, priority in suggestions:
        current = by_note.get(note)
        if current is None:
            by_note[note] = (recommendation, note, reason, match_source, priority)
            continue
        current_required = current[0] == "required"
        incoming_required = recommendation == "required"
        if incoming_required and not current_required:
            by_note[note] = (recommendation, note, reason, match_source, priority)
            continue
        if incoming_required == current_required and priority < current[4]:
            by_note[note] = (recommendation, note, reason, match_source, priority)
    return sorted(by_note.values(), key=lambda item: (0 if item[0] == "required" else 1, item[4], item[1]))


def _format_route_reason(*, reason: str, match_source: str) -> str:
    if not match_source:
        return reason
    return f"{reason}; match source: {match_source}"


def _first_route_match_source(match_source: str) -> str:
    if not match_source:
        return ""
    return match_source.split(",", 1)[0].strip()


def _route_signal_strength(match_source: str) -> str:
    first = _first_route_match_source(match_source)
    if first in {"file-path", "surface"}:
        return "direct"
    if first in {"index-fallback"}:
        return "fallback"
    if first in {"high-level-fallback", "explicit-current-context"}:
        return "weak"
    if first == "routing-baseline":
        return "baseline"
    return "unknown"


def _build_route_summary(
    kept_suggestions: list[tuple[str, str, str, str, int]],
) -> dict[str, object]:
    required_count = sum(1 for recommendation, *_ in kept_suggestions if recommendation == "required")
    optional_count = sum(1 for recommendation, *_ in kept_suggestions if recommendation == "optional")
    routed_count = len(kept_suggestions)
    exceeded = routed_count > ROUTE_WORKING_SET_TARGET
    direct_matches = 0
    fallback_matches = 0
    weak_matches = 0
    baseline_matches = 0
    weak_signal_notes: list[str] = []
    confidence_reasons: list[str] = []
    for _recommendation, note, _reason, match_source, _priority in kept_suggestions:
        strength = _route_signal_strength(match_source)
        if strength == "direct":
            direct_matches += 1
        elif strength == "fallback":
            fallback_matches += 1
        elif strength == "weak":
            weak_matches += 1
            weak_signal_notes.append(note)
        elif strength == "baseline":
            baseline_matches += 1

    confidence = "high"
    if routed_count > ROUTE_WORKING_SET_STRONG_WARNING:
        confidence = "low"
        confidence_reasons.append("working set exceeded the strong warning threshold")
    elif direct_matches == 0 and (fallback_matches > 0 or weak_matches > 0):
        confidence = "low"
        confidence_reasons.append("routing relied on fallback signals rather than direct manifest matches")
    elif direct_matches == 0:
        confidence = "low"
        confidence_reasons.append("routing returned only the baseline route without task-specific direct matches")
    elif weak_matches > 0 or fallback_matches > 0 or exceeded:
        confidence = "medium"
        if fallback_matches > 0:
            confidence_reasons.append("manifest coverage was incomplete enough to keep index fallbacks")
        if weak_matches > 0:
            confidence_reasons.append("one or more weak-signal notes were retained")
        if exceeded:
            confidence_reasons.append("the routed set exceeded the default working-set target")

    summary: dict[str, object] = {
        "routed_note_count": routed_count,
        "required_count": required_count,
        "optional_count": optional_count,
        "exceeded_target": "yes" if exceeded else "no",
        "confidence": confidence,
        "confidence_reasons": confidence_reasons,
        "direct_match_count": direct_matches,
        "fallback_match_count": fallback_matches,
        "weak_signal_note_count": weak_matches,
        "baseline_note_count": baseline_matches,
        "weak_signal_notes": weak_signal_notes,
    }
    if routed_count > ROUTE_WORKING_SET_TARGET:
        sources = [match_source for _, _, _, match_source, _ in kept_suggestions if match_source]
        justification_bits = ", ".join(dict.fromkeys(sources[:3]))
        summary["justification"] = "working set exceeds the default target because multiple direct routing matches were retained" + (
            f" ({justification_bits})" if justification_bits else ""
        )
    if routed_count > ROUTE_WORKING_SET_STRONG_WARNING:
        summary["warning"] = "routing returned more than five notes; review routing precision and merge pressure"
    elif routed_count > ROUTE_WORKING_SET_TARGET:
        summary["warning"] = "routing exceeded the default three-note target; optional weak matches were trimmed first"
    elif confidence == "low":
        summary["warning"] = "routing confidence is low; capture any missed note and review manifest coverage"
    return summary


def _path_matches_pattern(raw_path: str, pattern: str) -> bool:
    normalised_path = raw_path.replace("\\", "/").strip("./")
    normalised_pattern = pattern.replace("\\", "/").strip().strip("./")
    if not normalised_path or not normalised_pattern:
        return False
    path = Path(normalised_path)
    patterns = [normalised_pattern]
    if "/**/" in normalised_pattern:
        patterns.append(normalised_pattern.replace("/**/", "/"))
    if normalised_pattern.endswith("/**"):
        prefix = normalised_pattern[: -len("/**")].strip("/")
        if prefix and (normalised_path == prefix or normalised_path.startswith(prefix + "/")):
            return True
    return any(path.match(candidate) for candidate in patterns)


def _routing_case_is_externalized(status: str) -> bool:
    status_text = status.strip().lower()
    return status_text.startswith("externalized") or "externalized" in status_text


def _parse_route_sections(index_path: Path) -> list[tuple[str, list[str]]]:
    if not index_path.exists():
        return []
    sections: list[tuple[str, list[str]]] = []
    current_heading: str | None = None
    current_notes: list[str] = []
    in_task_routing = False
    for raw_line in index_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "## Task routing":
            in_task_routing = True
            continue
        if in_task_routing and line.startswith("## "):
            break
        if not in_task_routing:
            continue
        if line.startswith("### "):
            if current_heading is not None:
                sections.append((_normalise_surface_name(current_heading), current_notes))
            current_heading = line.removeprefix("### ").strip()
            current_notes = []
            continue
        if line.startswith("- `") and line.endswith("`"):
            current_notes.append(line[3:-1])
    if current_heading is not None:
        sections.append((_normalise_surface_name(current_heading), current_notes))
    return sections


def _normalise_surface_name(text: str) -> str:
    lowered = text.lower()
    if "runtime" in lowered or "deployment" in lowered:
        return "runtime"
    if "api" in lowered or "interface" in lowered or "tool behaviour" in lowered:
        return "api"
    if "retrieval" in lowered or "search" in lowered:
        return "retrieval"
    if "test" in lowered or "validation" in lowered:
        return "tests"
    if "data model" in lowered or "architecture" in lowered:
        return "architecture"
    if "choosing an approach" in lowered or "multiple subsystems" in lowered:
        return "decision"
    return lowered


def _infer_surfaces_from_paths(paths: list[str]) -> set[str]:
    surfaces: set[str] = set()
    for raw_path in paths:
        path = raw_path.replace("\\", "/").lower()
        if any(token in path for token in ("test", "/tests/", "_test.", "spec.")):
            surfaces.add("tests")
        if any(token in path for token in ("deploy", "infra", "docker", "k8s", "terraform", "compose")):
            surfaces.add("runtime")
        if any(token in path for token in ("api", "route", "contract", "interface", "cli")):
            surfaces.add("api")
        if any(token in path for token in ("search", "retriev", "vector", "index")):
            surfaces.add("retrieval")
        if any(token in path for token in ("schema", "model", "architect", "design", "invariant")):
            surfaces.add("architecture")
    return surfaces


def _git_changed_files(target_root: Path) -> list[str]:
    if not (target_root / ".git").exists():
        return []
    try:
        completed = subprocess.run(
            ["git", "status", "--short", "--porcelain"],
            cwd=target_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(
            f"Warning: git change detection failed in {target_root}: {exc}",
            file=sys.stderr,
        )
        return []

    files: list[str] = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        candidate = line[3:]
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1]
        files.append(candidate)
    return files
