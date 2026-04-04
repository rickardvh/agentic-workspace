from __future__ import annotations

import json
import re
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable

from repo_memory_bootstrap._installer_shared import (
    AGENT_ROOT_MARKERS,
    CURRENT_MEMORY_BASELINE,
    CURRENT_CONTEXT_CHRONOLOGY_RE,
    CURRENT_CONTEXT_SUSPICIOUS_HEADINGS,
    CURRENT_CONTEXT_SUSPICIOUS_SECTION_RE,
    CURRENT_PROJECT_STATE_MAX_LINES,
    PROJECT_STATE_REQUIRED_SECTIONS,
    CURRENT_PROJECT_STATE_STALE_DAYS,
    CURRENT_TASK_MAX_LINES,
    TASK_CONTEXT_REQUIRED_SECTIONS,
    CURRENT_TASK_STALE_DAYS,
    DATE_RE,
    EMBEDDED_WORKFLOW_HEADINGS,
    LEGACY_BOOTSTRAP_AGENTS_PHRASES,
    LEGACY_UPGRADE_SOURCE_PATH,
    LEGACY_VERSION_PATH,
    LEGACY_WORKFLOW_PATH,
    PLACEHOLDER_RE,
    UPGRADE_SOURCE_PATH,
    VERSION_PATH,
    VERSION_RE,
    WORKFLOW_MARKER_END,
    WORKFLOW_MARKER_START,
    WORKFLOW_POINTER_BLOCK,
)

SECTION_HEADING_RE = re.compile(r"^\s{0,3}##\s+(.+?)\s*$")


def build_substitutions(
    *,
    target_root: Path,
    project_name: str | None,
    project_purpose: str | None = None,
    key_repo_docs: str | None = None,
    key_subsystems: str | None = None,
    primary_build_command: str | None = None,
    primary_test_command: str | None = None,
    other_key_commands: str | None = None,
) -> dict[str, str]:
    substitutions = {
        "<PROJECT_NAME>": project_name or target_root.name,
        "<LAST_CONFIRMED_DATE>": datetime.now(UTC).date().isoformat(),
    }
    optional_values = {
        "<PROJECT_PURPOSE>": project_purpose,
        "<KEY_REPO_DOCS>": key_repo_docs,
        "<KEY_SUBSYSTEMS>": key_subsystems,
        "<PRIMARY_BUILD_COMMAND>": primary_build_command,
        "<PRIMARY_TEST_COMMAND>": primary_test_command,
        "<OTHER_KEY_COMMANDS>": other_key_commands,
    }
    for placeholder, value in optional_values.items():
        if value:
            substitutions[placeholder] = value
    return substitutions


def detect_install_mode(target_root: Path) -> str:
    present_count = sum(1 for marker in AGENT_ROOT_MARKERS if (target_root / marker).exists())
    if present_count == 0:
        return "bootstrap"
    if present_count == len(AGENT_ROOT_MARKERS):
        return "full"
    return "augment"


def format_actions(actions: Iterable, target_root: Path) -> list[str]:
    lines: list[str] = []
    for action in actions:
        relative_path = action.path.relative_to(target_root) if action.path.is_relative_to(target_root) else action.path
        details: list[str] = []
        if action.detail:
            details.append(action.detail)
        if action.role:
            details.append(f"role={action.role}")
        if action.safety:
            details.append(f"safety={action.safety}")
        if action.category:
            details.append(f"category={action.category}")
        if action.remediation_kind:
            details.append(f"remediation={action.remediation_kind}")
        if action.remediation_target:
            details.append(f"target={action.remediation_target}")
        if action.remediation_confidence:
            details.append(f"confidence={action.remediation_confidence}")
        if action.memory_action:
            details.append(f"memory_action={action.memory_action}")
        if action.match_source:
            details.append(f"match_source={action.match_source}")
        detail = f" ({'; '.join(details)})" if details else ""
        lines.append(f"{action.kind}: {relative_path}{detail}")
    return lines


def format_result_json(result) -> str:
    return json.dumps(result.to_dict(), indent=2)


def _new_result(target_root: Path, *, dry_run: bool, message: str):
    from repo_memory_bootstrap._installer_shared import InstallResult

    result = InstallResult(target_root=target_root, dry_run=dry_run)
    result.mode = detect_install_mode(target_root)
    result.detected_version = _read_installed_version(_existing_version_path(target_root))
    result.message = message
    return result


def _existing_version_path(target_root: Path) -> Path:
    preferred = target_root / VERSION_PATH
    if preferred.exists():
        return preferred
    legacy = target_root / LEGACY_VERSION_PATH
    return legacy if legacy.exists() else preferred


def _read_installed_version(path: Path) -> int | None:
    if not path.exists():
        return None
    match = VERSION_RE.search(path.read_text(encoding="utf-8"))
    if not match:
        return None
    return int(match.group(1))


def _has_placeholders(text: str) -> bool:
    return bool(PLACEHOLDER_RE.search(text))


def _infer_action_category(*, kind: str, path: Path, detail: str, role: str, safety: str) -> str:
    detail_lower = detail.lower()
    path_str = path.as_posix()
    if kind == "customised":
        return "customisation-present"
    if "placeholder" in detail_lower:
        return "placeholder-review"
    if any(path_str.endswith(current_path.as_posix()) for current_path in CURRENT_MEMORY_BASELINE):
        if kind in {"missing", "manual review"}:
            return "current-memory-review"
    if role in {"payload-contract", "local-entrypoint"} or role.startswith("shared-"):
        if kind in {"manual review", "missing"}:
            return "contract-drift"
    if kind in {
        "would create",
        "would copy",
        "would replace",
        "created",
        "copied",
        "replaced",
        "current",
        "present",
        "optional",
        "required",
        "warning",
    }:
        return "safe-update"
    if kind in {"manual review", "consider"}:
        return "manual-review"
    if safety == "safe":
        return "safe-update"
    return ""


def _current_task_staleness_reason(text: str) -> str | None:
    lines = text.splitlines()
    if len(lines) > CURRENT_TASK_MAX_LINES:
        return (
            f"task-context note is oversized ({len(lines)} lines); "
            "compress it back to optional continuation-only context "
            "and remove planner, backlog, or execution-log spillover"
        )
    for idx, line in enumerate(lines):
        if line.strip().lower() == "## last confirmed":
            for follow in lines[idx + 1 :]:
                stripped = follow.strip()
                if not stripped:
                    continue
                date_match = DATE_RE.match(stripped)
                if date_match:
                    confirmed = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(tzinfo=UTC)
                    if confirmed < datetime.now(UTC) - timedelta(days=CURRENT_TASK_STALE_DAYS):
                        return (
                            f"task-context note has not been confirmed in over "
                            f"{CURRENT_TASK_STALE_DAYS} days; "
                            "check whether the active goal, touched surfaces, "
                            "assumptions, next validation, "
                            "or linked code and interfaces have drifted"
                        )
                break
    return None


def _current_task_structure_findings(text: str) -> list[str]:
    return _current_note_structure_findings(
        text=text,
        expected_sections=TASK_CONTEXT_REQUIRED_SECTIONS,
        note_name="task-context",
    )


def _project_state_staleness_reason(text: str) -> str | None:
    lines = text.splitlines()
    if len(lines) > CURRENT_PROJECT_STATE_MAX_LINES:
        return (
            f"project-state note is oversized ({len(lines)} lines); compress stale history, remove "
            "planner residue, and keep only current overview facts"
        )
    for idx, line in enumerate(lines):
        if line.strip().lower() == "## last confirmed":
            for follow in lines[idx + 1 :]:
                stripped = follow.strip()
                if not stripped:
                    continue
                date_match = DATE_RE.match(stripped)
                if date_match:
                    confirmed = datetime.strptime(date_match.group(1), "%Y-%m-%d").replace(tzinfo=UTC)
                    if confirmed < datetime.now(UTC) - timedelta(days=CURRENT_PROJECT_STATE_STALE_DAYS):
                        return (
                            f"project-state note has not been confirmed in over "
                            f"{CURRENT_PROJECT_STATE_STALE_DAYS} days; "
                            "check whether linked code, commands, or authority "
                            "boundaries have materially changed"
                        )
                break
    return None


def _project_state_structure_findings(text: str) -> list[str]:
    return _current_note_structure_findings(
        text=text,
        expected_sections=PROJECT_STATE_REQUIRED_SECTIONS,
        note_name="project-state",
    )


def _current_note_structure_findings(*, text: str, expected_sections: tuple[str, ...], note_name: str) -> list[str]:
    sections = [match.group(1).strip() for line in text.splitlines() if (match := SECTION_HEADING_RE.match(line))]
    findings: list[str] = []

    missing = [section for section in expected_sections if section not in sections]
    if missing:
        findings.append(
            f"{note_name} note is missing expected sections ({', '.join(missing)}); this looks like structure drift rather than compact continuation context"
        )

    suspicious_headings = [
        section
        for section in sections
        if section.strip().lower() in CURRENT_CONTEXT_SUSPICIOUS_HEADINGS
        or CURRENT_CONTEXT_SUSPICIOUS_SECTION_RE.match(f"## {section}")
    ]
    if suspicious_headings:
        findings.append(
            f"{note_name} note includes planner-like headings ({', '.join(sorted(set(suspicious_headings)))}); review for planner or log drift"
        )

    chronological_lines = sum(1 for line in text.splitlines() if CURRENT_CONTEXT_CHRONOLOGY_RE.match(line))
    if chronological_lines >= 3:
        findings.append(
            f"{note_name} note includes chronological task-log style bullets ({chronological_lines} entries); review for execution-log drift"
        )

    suspicious_sections = [
        section
        for section in sections
        if section.strip().lower() in {"todo", "to do", "done", "completed", "in progress", "history", "timeline"}
    ]
    if len(suspicious_sections) >= 2:
        findings.append(
            f"{note_name} note has multiple planner/log sections ({', '.join(suspicious_sections)}); keep current-memory notes brief and non-sequencing"
        )

    return findings


def _is_valid_upgrade_source_text(text: str) -> bool:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return False

    source_type = str(data.get("source_type", "")).strip()
    source_ref = str(data.get("source_ref", "")).strip()
    return source_type in {"git", "local"} and bool(source_ref)


def _validate_upgrade_source_record(path: Path, result) -> None:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        result.add(
            "manual review",
            path,
            "upgrade source metadata is not valid TOML",
            role="payload-contract",
            safety="manual",
            source=UPGRADE_SOURCE_PATH.as_posix(),
            category="contract-drift",
        )
        return

    source_type = str(data.get("source_type", "")).strip()
    source_ref = str(data.get("source_ref", "")).strip()
    if source_type not in {"git", "local"}:
        result.add(
            "manual review",
            path,
            "upgrade source metadata must declare source_type as git or local",
            role="payload-contract",
            safety="manual",
            source=UPGRADE_SOURCE_PATH.as_posix(),
            category="contract-drift",
        )
        return
    if not source_ref:
        result.add(
            "manual review",
            path,
            "upgrade source metadata is missing source_ref",
            role="payload-contract",
            safety="manual",
            source=UPGRADE_SOURCE_PATH.as_posix(),
            category="contract-drift",
        )


def resolve_upgrade_source(target: str | Path | None = None) -> dict[str, str]:
    target_root = Path(target or Path.cwd()).resolve()
    path = target_root / UPGRADE_SOURCE_PATH
    if not path.exists():
        legacy = target_root / LEGACY_UPGRADE_SOURCE_PATH
        if legacy.exists():
            path = legacy
    default = {
        "source_type": "git",
        "source_ref": "git+https://github.com/Tenfifty/agentic-memory",
    }
    if not target_root.exists() or not path.exists():
        return default

    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return default

    source_type = str(data.get("source_type", "")).strip()
    source_ref = str(data.get("source_ref", "")).strip()
    if source_type not in {"git", "local"} or not source_ref:
        return default
    return {"source_type": source_type, "source_ref": source_ref}


def _embeds_shared_workflow_rules(text: str) -> bool:
    matches = {heading for heading in EMBEDDED_WORKFLOW_HEADINGS if heading in text}
    return "## Task system boundary" in matches or len(matches) >= 2


def _patch_agents_workflow_block(existing: str) -> str:
    if WORKFLOW_MARKER_START in existing and WORKFLOW_MARKER_END in existing:
        pattern = re.compile(
            re.escape(WORKFLOW_MARKER_START) + r".*?" + re.escape(WORKFLOW_MARKER_END),
            re.DOTALL,
        )
        return pattern.sub(WORKFLOW_POINTER_BLOCK, existing, count=1)

    lines = existing.splitlines()
    if lines and lines[0].startswith("#"):
        rest_index = 1
        while rest_index < len(lines) and not lines[rest_index].strip():
            rest_index += 1
        rest = lines[rest_index:]
        body = "\n".join(rest).lstrip("\n")
        if body:
            return f"{lines[0]}\n\n{WORKFLOW_POINTER_BLOCK}\n\n{body.rstrip()}\n"
        return f"{lines[0]}\n\n{WORKFLOW_POINTER_BLOCK}\n"

    return f"{WORKFLOW_POINTER_BLOCK}\n\n{existing.lstrip()}"


def _has_legacy_bootstrap_agents_prose(text: str) -> bool:
    if WORKFLOW_MARKER_START in text and WORKFLOW_MARKER_END in text:
        pattern = re.compile(
            re.escape(WORKFLOW_MARKER_START) + r".*?" + re.escape(WORKFLOW_MARKER_END),
            re.DOTALL,
        )
        text = pattern.sub("", text, count=1)
    return any(phrase in text for phrase in LEGACY_BOOTSTRAP_AGENTS_PHRASES)


def _agents_has_current_workflow_pointer(text: str) -> bool:
    return WORKFLOW_POINTER_BLOCK in text


def _agents_has_legacy_workflow_reference(text: str) -> bool:
    return LEGACY_WORKFLOW_PATH.as_posix() in text
