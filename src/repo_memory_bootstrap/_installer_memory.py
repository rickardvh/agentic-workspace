from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Iterable

from repo_memory_bootstrap._installer_shared import (
    DEFAULT_CORE_DOC_EXCLUDE_GLOBS,
    DEFAULT_CORE_DOC_GLOBS,
    MANIFEST_PATH,
    MARKDOWN_MEMORY_LINK_RE,
    MEMORY_PATH_RE,
    SHADOW_DOC_MIN_SHARED_TERMS,
    VALID_CANONICALITY_VALUES,
    VALID_ELIMINATION_TARGET_VALUES,
    VALID_MEMORY_ROLE_VALUES,
    VALID_PREFERRED_REMEDIATION_VALUES,
    VALID_SYMPTOM_OF_VALUES,
    VALID_TASK_RELEVANCE_VALUES,
    MemoryManifest,
    MemoryNoteRecord,
    RemediationRecommendation,
)


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


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _routes_to_canonical_doc(note: MemoryNoteRecord) -> bool:
    if note.canonicality != "canonical_elsewhere":
        return False
    return _is_non_memory_canonical_home(note.canonical_home, note.path)


def _is_non_memory_canonical_home(canonical_home: Path, note_path: Path) -> bool:
    if canonical_home == note_path:
        return False
    return canonical_home.parts[:1] != ("memory",)


def _audit_memory_doc_ownership(*, target_root: Path, result, force_enforcement: bool = False) -> None:
    manifest = _load_memory_manifest(target_root / MANIFEST_PATH)
    if manifest is None:
        return

    if manifest.routing_only and tuple(manifest.routing_only) != (Path("memory/index.md"),):
        result.add(
            "manual review",
            target_root / MANIFEST_PATH,
            "rules.routing_only should contain only memory/index.md so the always-read surface stays small",
            role="memory-manifest",
            safety="manual",
            source=MANIFEST_PATH.as_posix(),
            category="contract-drift",
        )
    if Path("memory/current/task-context.md") in manifest.high_level:
        result.add(
            "manual review",
            target_root / MANIFEST_PATH,
            "rules.high_level should not include memory/current/task-context.md; keep continuation notes opt-in",
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
        if note.path == Path(".agentic-memory/WORKFLOW.md") and note.task_relevance == "required":
            result.add(
                "manual review",
                target_root / note.path,
                "WORKFLOW.md should remain reference policy, not default required reading for every task",
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.path == Path("memory/current/project-state.md") and note.task_relevance != "optional":
            result.add(
                "manual review",
                target_root / note.path,
                "project-state should stay optional high-level context rather than required task setup",
                role="memory-manifest",
                safety="manual",
                source=note.path.as_posix(),
                category="contract-drift",
            )
        if note.path == Path("memory/current/task-context.md"):
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
                    "task-context should not advertise broad routing metadata; load it only when active continuation context is genuinely needed",
                    role="memory-manifest",
                    safety="manual",
                    source=note.path.as_posix(),
                    category="contract-drift",
                )

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


def _extract_memory_references(text: str) -> list[str]:
    matches = {match.group(0) for match in MEMORY_PATH_RE.finditer(text)}
    matches.update(match.group(1) for match in MARKDOWN_MEMORY_LINK_RE.finditer(text))
    return sorted(match.rstrip(").,`") for match in matches if match.strip())


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


def _explicit_note_review_detail(requested_note: Path) -> str:
    requested_str = requested_note.as_posix()
    if requested_str.startswith("memory/runbooks/"):
        return (
            "explicit note supplied; review whether the durable facts should stay in memory, "
            "the repeated workflow should become a checked-in skill, or the mechanics now "
            "justify a repo-owned script or command."
        )
    if requested_str.startswith("memory/mistakes/"):
        return (
            "explicit note supplied; review whether the recurring failure should stay documented "
            "in memory or now justify a regression test, validation, or lint rule."
        )
    if requested_str.startswith("memory/domains/"):
        return (
            "explicit note supplied; review whether the stable parts belong in canonical docs "
            "or whether the note is signalling a refactor or clearer boundary need."
        )
    if requested_str.startswith("memory/invariants/"):
        return (
            "explicit note supplied; review whether the invariant should stay in memory, move "
            "into canonical docs, or be enforced more directly in code or validation."
        )
    if requested_str.startswith("memory/decisions/"):
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
    lines = text.splitlines()
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

    if "memory/mistakes/" in relative_str and has_failure_entries:
        return RemediationRecommendation(
            kind="test",
            target_path_hint=_infer_test_target(note, note_path),
            reason="Recurring failures should usually be displaced by an executable guardrail.",
            confidence="medium",
            memory_action="shrink",
        )

    if "memory/runbooks/" in relative_str and line_count >= 12 and imperative_lines >= 6:
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
            reason="This procedure is repeated operational choreography that should be executed through a checked-in skill before more prose is added.",
            confidence="medium",
            memory_action="automate",
        )

    if "memory/domains/" in relative_str and line_count >= 140:
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

    if relative_str.endswith("memory/index.md") and line_count >= 120:
        return RemediationRecommendation(
            kind="refactor",
            target_path_hint="memory/ plus the awkward routed subsystem surface",
            reason="The routing layer is compensating for friction that should usually be resolved through note consolidation or clearer repo boundaries.",
            confidence="low",
            memory_action="shrink",
        )

    if "memory/current/" in relative_str and line_count >= 80 and not for_report:
        return RemediationRecommendation(
            kind="docs",
            target_path_hint="the repo planning/status surface",
            reason="The current-memory note is growing beyond re-orientation support and likely reflects planner or workflow spillover.",
            confidence="low",
            memory_action="shrink",
        )
    return None


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
    if kind == "test" and "memory/mistakes/" in relative_str and not has_failure_entries:
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
    lines = text.splitlines()
    line_count = len(lines)
    imperative_lines = sum(1 for line in lines if re.match(r"^\s*(?:-|\*|\d+\.)\s+", line) or line.strip().startswith("`"))
    has_failure_entries = _has_concrete_failure_entries(text)

    if note is not None:
        manifest_hint = _manifest_improvement_hint(note, has_failure_entries=has_failure_entries)
        if manifest_hint:
            hints.append(manifest_hint)

    if "memory/mistakes/" in relative_str and has_failure_entries:
        hints.append("a regression test, validation, or lint rule if the recurring failure remains active")
    if "memory/runbooks/" in relative_str and line_count >= 35 and imperative_lines >= 6:
        hints.append("a checked-in skill first, then a repo-owned script or command if the workflow stays mechanical")
    if "memory/domains/" in relative_str and line_count >= 140:
        hints.append(("clearer canonical docs or refactor review if this note keeps compensating for a high-discovery-cost subsystem"))
    if relative_str.endswith("memory/index.md") and line_count >= 120:
        hints.append(("clearer repo boundaries or note consolidation if routing keeps expanding to explain one awkward area"))
    if "memory/current/" in relative_str and line_count >= 80 and not for_report:
        hints.append(("shrinking planning/status spillover or unresolved structure friction before growing current-memory notes further"))

    recommendation = _build_remediation_recommendation(note, note_path, text, for_report=for_report)
    if recommendation:
        hints.append(f"{recommendation.kind} at {recommendation.target_path_hint}")

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
    if "memory/mistakes/" in note.path.as_posix() and not has_failure_entries:
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
        for hint in _collect_improvement_hints(note, note_path, text, for_report=False):
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
    return f"memory/skills/{stem}/SKILL.md"


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
    }
    return {word for word in words if word not in stop_words}


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
) -> list[tuple[str, str, str]]:
    if manifest is None:
        return []

    suggestions: list[tuple[str, str, str]] = []
    for note in manifest.notes:
        reasons: list[str] = []
        if surfaces and any(surface in surfaces for surface in note.surfaces):
            matched = ", ".join(sorted({surface for surface in note.surfaces if surface in surfaces}))
            reasons.append(f"manifest surface match ({matched})")

        globs = note.stale_when if use_staleness else note.routes_from
        if files and globs:
            matched_globs = sorted({pattern for pattern in globs if any(_path_matches_pattern(path, pattern) for path in files)})
            if matched_globs:
                reasons.append(f"manifest path match ({', '.join(matched_globs)})")

        if reasons:
            reason = "; ".join(reasons)
            if _routes_to_canonical_doc(note):
                suggestions.append(
                    (
                        "required",
                        note.canonical_home.as_posix(),
                        f"{reason}; canonical doc takes precedence over memory",
                    )
                )
                suggestions.append(
                    (
                        "recommended",
                        note.path.as_posix(),
                        f"{reason}; memory note is fallback context only",
                    )
                )
                continue

            recommendation = "required" if note.task_relevance == "required" else "recommended"
            suggestions.append((recommendation, note.path.as_posix(), reason))
    return suggestions


def _path_matches_pattern(raw_path: str, pattern: str) -> bool:
    normalised_path = raw_path.replace("\\", "/").strip("./")
    normalised_pattern = pattern.replace("\\", "/").strip()
    if not normalised_path or not normalised_pattern:
        return False
    path = Path(normalised_path)
    patterns = [normalised_pattern]
    if "/**/" in normalised_pattern:
        patterns.append(normalised_pattern.replace("/**/", "/"))
    return any(path.match(candidate) for candidate in patterns)


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
