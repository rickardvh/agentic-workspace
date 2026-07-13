from __future__ import annotations

import json
import re
import shlex
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence

STACK_CACHE_PATH = Path(".agentic-workspace") / "local" / "cache" / "pr-comment-stack.json"


def _string_list(value: Any) -> list[str]:
    values = value if isinstance(value, list) else [value] if value not in (None, "") else []
    return [str(item).strip().replace("\\", "/") for item in values if str(item).strip()]


def _dedupe(values: Sequence[str]) -> list[str]:
    ordered: list[str] = []
    for value in values:
        if value and value not in ordered:
            ordered.append(value)
    return ordered


def _safe_slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-._")
    return normalized or "review-stack-transition"


def _load_stack(target_root: Path) -> dict[str, Any]:
    try:
        payload = json.loads((target_root / STACK_CACHE_PATH).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _member_paths(member: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    delta = member.get("delta")
    member_cache: dict[str, Any] = delta if isinstance(delta, dict) else member
    for source in (member, member_cache):
        for key in ("changed_effect_paths", "changed_paths", "files_changed", "changed_files"):
            paths.extend(_string_list(source.get(key)))
        files = source.get("files")
        if isinstance(files, list):
            for item in files:
                if isinstance(item, dict):
                    paths.extend(_string_list(item.get("path") or item.get("filename")))
                else:
                    paths.extend(_string_list(item))
    return _dedupe(paths)


def _stack_current_pr(stack: dict[str, Any]) -> str:
    raw_discovery = stack.get("stack_discovery")
    discovery: dict[str, Any] = raw_discovery if isinstance(raw_discovery, dict) else {}
    value = str(discovery.get("current_branch_pr_number") or stack.get("current_pr_number") or "").strip()
    if value:
        return value
    members = [item for item in stack.get("stack_members", []) if isinstance(item, dict)]
    return str(members[-1].get("pr_number") or "").strip() if members else ""


def _select_member(stack: dict[str, Any], *, pr_number: str, changed_paths: list[str]) -> dict[str, Any]:
    members = [item for item in stack.get("stack_members", []) if isinstance(item, dict)]
    normalized = set(_dedupe(changed_paths))
    if normalized:
        for member in members:
            member_paths = set(_member_paths(member))
            if normalized.issubset(member_paths) or member_paths.intersection(normalized):
                return member
    if pr_number:
        match = next((member for member in members if str(member.get("pr_number") or "").strip() == pr_number), None)
        if match is not None:
            return match
    current = _stack_current_pr(stack)
    if current:
        match = next((member for member in members if str(member.get("pr_number") or "").strip() == current), None)
        if match is not None:
            return match
    return members[-1] if members else {}


def _review_record_path(target_root: Path, slug: str) -> Path:
    reviews_root = target_root / ".agentic-workspace" / "planning" / "reviews"
    today_prefix = date.today().isoformat()
    expected = reviews_root / f"{today_prefix}-{slug}.review.json"
    matches = sorted(reviews_root.glob(f"*-{slug}.review.json")) if reviews_root.is_dir() else []
    return matches[-1] if matches else expected


def _default_review_record(*, title: str, classification: str, lifecycle_payload: dict[str, Any], command: str) -> dict[str, Any]:
    scope_text = json.dumps(lifecycle_payload, separators=(",", ":"), sort_keys=True)
    return {
        "kind": "planning-review/v1",
        "title": title,
        "date": date.today().isoformat(),
        "scope": [scope_text],
        "classification": classification,
        "goal": ["Record a bounded review-stack workflow transition from an ordinary command."],
        "non_goals": ["Do not use this transition record as proof that all review work is complete."],
        "review_mode": {
            "mode": classification,
            "review question": "Which review-stack phase changed, and what command or receipt proves the transition?",
            "default finding cap": "bounded",
            "inputs inspected first": "ordinary command result and current PR stack cache",
        },
        "review_method": {
            "commands used": command,
            "evidence sources": "ordinary command results; PR stack cache; proof receipt when present",
        },
        "references": [],
        "findings": [],
        "recommendation": {
            "promote": "pending",
            "defer": "pending",
            "dismiss": "pending",
        },
        "retention": {
            "closeout shape": "shrink",
            "trigger": "review stack phase superseded or parent PR merged",
            "proof surface": "review_stack_continuity.workflow_trace",
        },
        "prose_templates": {},
        "validation_commands": [command],
        "drift_log": [f"{date.today().isoformat()}: Review-stack lifecycle recorded by ordinary command."],
    }


def record_review_stack_transition(
    *,
    target_root: Path,
    phase: str,
    phase_after: str,
    command: str,
    outcome: str,
    next_action_id: str,
    changed_paths: Sequence[str] = (),
    pr_number: str = "",
    command_exit_code: int | None = None,
    proof_receipt_path: str = "",
    proof_receipt_result: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    stack = _load_stack(target_root)
    members = [item for item in stack.get("stack_members", []) if isinstance(item, dict)]
    if not members:
        return {"status": "skipped", "reason": "review stack cache unavailable"}
    normalized_paths = _dedupe(_string_list(list(changed_paths)))
    selected_member = _select_member(stack, pr_number=pr_number, changed_paths=normalized_paths)
    selected_pr = str(pr_number or selected_member.get("pr_number") or _stack_current_pr(stack)).strip()
    if not selected_pr:
        return {"status": "skipped", "reason": "review stack PR unavailable"}
    member_paths = _member_paths(selected_member)
    if (
        normalized_paths
        and member_paths
        and not (set(normalized_paths).issubset(set(member_paths)) or set(member_paths).intersection(normalized_paths))
    ):
        return {"status": "skipped", "reason": "changed paths do not match review stack member", "pr_number": selected_pr}
    transition_payload = {
        "pr_number": selected_pr,
        "phase": phase,
        "phase_after": phase_after,
        "command": command,
        "outcome": outcome,
        "next_action_id": next_action_id,
        "changed_paths": normalized_paths or member_paths,
        "command_exit_code": command_exit_code,
        "proof_receipt_path": proof_receipt_path,
        "proof_receipt_result": proof_receipt_result,
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source": "ordinary-command",
    }
    slug = _safe_slug(f"review-stack-{selected_pr}-lifecycle")
    record_path = _review_record_path(target_root, slug)
    title = f"Review Stack {selected_pr} Lifecycle".replace("-", " ").title()
    lifecycle_payload: dict[str, Any] = {
        "record_kind": "review-stack-lifecycle",
        "pr_number": selected_pr,
        "current_phase": phase_after,
        "next_action_id": next_action_id,
        "changed_paths": normalized_paths or member_paths,
        "updated_at": transition_payload["recorded_at"],
        "source": "ordinary-command",
        "transitions": [transition_payload],
    }
    if dry_run:
        return {
            "status": "dry-run",
            "path": record_path.relative_to(target_root).as_posix(),
            "scope": lifecycle_payload,
        }
    record_path.parent.mkdir(parents=True, exist_ok=True)
    if record_path.exists():
        try:
            record = json.loads(record_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            record = {}
        if not isinstance(record, dict):
            record = {}
        if not record:
            record = _default_review_record(
                title=title,
                classification="review-stack-transition",
                lifecycle_payload=lifecycle_payload,
                command=command,
            )
        else:
            existing_lifecycle: dict[str, Any] = {}
            for raw_scope in _string_list(record.get("scope")):
                try:
                    parsed = json.loads(raw_scope)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    existing_lifecycle = parsed
                    break
            existing_transitions = [item for item in existing_lifecycle.get("transitions", []) if isinstance(item, dict)]
            transitions_by_phase = {str(item.get("phase_after") or item.get("phase") or ""): item for item in existing_transitions}
            transitions_by_phase[phase_after or phase] = transition_payload
            lifecycle_payload["transitions"] = list(transitions_by_phase.values())
            record["title"] = title
            record["classification"] = "review-stack-transition"
            record["scope"] = [json.dumps(lifecycle_payload, separators=(",", ":"), sort_keys=True)]
            record.setdefault("validation_commands", [])
            if isinstance(record["validation_commands"], list) and command not in record["validation_commands"]:
                record["validation_commands"].append(command)
            record.setdefault("drift_log", [])
            if isinstance(record["drift_log"], list):
                record["drift_log"].append(f"{date.today().isoformat()}: Review-stack lifecycle updated by ordinary command.")
        status = "updated"
    else:
        record = _default_review_record(
            title=title,
            classification="review-stack-transition",
            lifecycle_payload=lifecycle_payload,
            command=command,
        )
        status = "written"
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": status,
        "path": record_path.relative_to(target_root).as_posix(),
        "pr_number": selected_pr,
        "phase": phase,
        "phase_after": phase_after,
        "outcome": outcome,
        "proof_receipt_path": proof_receipt_path,
        "command_exit_code": command_exit_code,
    }


def command_text(program: str, argv: Sequence[str]) -> str:
    return " ".join([program, *[shlex.quote(str(item)) for item in argv]])
