from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from agentic_workspace.review_stack_topology import (
    TOPOLOGY_OBSERVATION_KIND,
    TopologyAdmissionError,
    current_provider_pr_identity,
    current_review_owner_identity,
    validate_admitted_pr_topology,
)

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


def _current_branch(target_root: Path) -> str:
    completed = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=target_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _select_member(stack: dict[str, Any], *, pr_number: str, branch: str, changed_paths: list[str]) -> dict[str, Any]:
    members = [item for item in stack.get("stack_members", []) if isinstance(item, dict)]
    if pr_number:
        match = next((member for member in members if str(member.get("pr_number") or "").strip() == pr_number), None)
        if match is not None:
            return match
    if branch:
        match = next(
            (
                member
                for member in members
                if branch
                in {
                    str(member.get("branch") or "").strip(),
                    str(member.get("head_ref") or "").strip(),
                    str(member.get("head_branch") or "").strip(),
                }
            ),
            None,
        )
        if match is not None:
            return match
    normalized = set(_dedupe(changed_paths))
    if normalized:
        for member in members:
            member_paths = set(_member_paths(member))
            if normalized.issubset(member_paths) or member_paths.intersection(normalized):
                return member
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
    branch = _current_branch(target_root)
    observation = stack.get("topology_observation")
    if not isinstance(observation, dict) or observation.get("kind") != TOPOLOGY_OBSERVATION_KIND:
        return {
            "status": "skipped",
            "reason": "admitted review topology required before lifecycle mutation",
            "recovery": "refresh-current-pr-topology",
        }
    repository = str(stack.get("repository") or observation.get("repository") or "").strip()
    if not repository or not branch:
        return {
            "status": "skipped",
            "reason": "review topology repository or branch unavailable",
            "recovery": "refresh-current-pr-topology",
        }
    topology_current, topology_reason, admitted = validate_admitted_pr_topology(
        target_root=target_root,
        cache=stack,
        expected_repository=repository,
        expected_branch=branch,
    )
    if not topology_current:
        return {
            "status": "skipped",
            "reason": topology_reason,
            "recovery": "refresh-current-pr-topology",
            "topology_status": "diagnostic-only",
        }
    selected_pr = str(admitted.get("current_pr_number") or "").strip()
    selected_head = str(admitted.get("current_head_sha") or "").strip()
    selected_state = str(admitted.get("current_pr_state") or "").strip().lower()
    if selected_state != "open":
        return {
            "status": "skipped",
            "reason": "current PR is not open",
            "pr_number": selected_pr,
            "pr_state": selected_state or "unknown",
            "recovery": "refresh-current-pr-topology",
        }
    if pr_number and str(pr_number).strip() != selected_pr:
        return {
            "status": "skipped",
            "reason": "requested PR does not match the admitted current branch PR",
            "pr_number": selected_pr,
            "recovery": "refresh-current-pr-topology",
        }
    selected_member = next(
        (
            member
            for member in members
            if str(member.get("pr_number") or "").strip() == selected_pr
            and str(member.get("branch") or "").strip() == branch
            and str(member.get("head_sha") or "").strip() == selected_head
        ),
        {},
    )
    if not selected_member:
        return {"status": "skipped", "reason": "admitted current PR member unavailable", "recovery": "refresh-current-pr-topology"}
    try:
        live_pr = current_provider_pr_identity(repository=repository, pr_number=selected_pr)
    except TopologyAdmissionError as exc:
        return {"status": "skipped", "reason": str(exc), "recovery": "refresh-current-pr-topology"}
    expected_live = {
        "pr_number": selected_pr,
        "pr_state": selected_state,
        "branch": branch,
        "head_sha": selected_head,
    }
    live_mismatches = [field for field, expected in expected_live.items() if live_pr.get(field) != expected]
    if live_mismatches:
        return {
            "status": "skipped",
            "reason": "live PR identity mismatch",
            "mismatched_fields": live_mismatches,
            "recovery": "refresh-current-pr-topology",
        }
    admitted_owner = admitted.get("review_owner_identity")
    live_owner = current_review_owner_identity(target_root)
    if not isinstance(admitted_owner, dict) or not live_owner:
        return {
            "status": "skipped",
            "reason": "current source-owned review owner unavailable",
            "recovery": "create-or-refresh-current-review-owner",
        }
    owner_mismatches = [
        field for field in ("owner_ref", "owner_revision") if str(admitted_owner.get(field) or "").strip() != live_owner[field]
    ]
    if owner_mismatches:
        return {
            "status": "skipped",
            "reason": "review owner revision mismatch",
            "mismatched_fields": owner_mismatches,
            "recovery": "create-or-refresh-current-review-owner",
        }
    member_paths = _member_paths(selected_member)
    if (
        normalized_paths
        and member_paths
        and not (set(normalized_paths).issubset(set(member_paths)) or set(member_paths).intersection(normalized_paths))
    ):
        return {"status": "skipped", "reason": "changed paths do not match review stack member", "pr_number": selected_pr}
    identity = {
        "repository": repository,
        "branch": branch,
        "pr_number": selected_pr,
        "pr_state": selected_state,
        "head_sha": selected_head,
        "topology_observation_digest": str(admitted.get("observation_digest") or ""),
        "review_owner_ref": live_owner["owner_ref"],
        "review_owner_revision": live_owner["owner_revision"],
    }
    slug = _safe_slug(f"review-stack-{selected_pr}-lifecycle")
    record_path = _review_record_path(target_root, slug)
    record: dict[str, Any] = {}
    existing_lifecycle: dict[str, Any] = {}
    if record_path.exists():
        try:
            loaded = json.loads(record_path.read_text(encoding="utf-8-sig"))
            record = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return {
                "status": "skipped",
                "reason": "review lifecycle record is unreadable",
                "path": record_path.relative_to(target_root).as_posix(),
            }
        for raw_scope in _string_list(record.get("scope")):
            try:
                parsed = json.loads(raw_scope)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                existing_lifecycle = parsed
                break
        existing_identity = existing_lifecycle.get("review_owner_identity")
        if isinstance(existing_identity, dict):
            mismatched = [
                field
                for field in (
                    "repository",
                    "branch",
                    "pr_number",
                    "pr_state",
                    "head_sha",
                    "topology_observation_digest",
                    "review_owner_ref",
                    "review_owner_revision",
                )
                if str(existing_identity.get(field) or "").strip() != identity[field]
            ]
            if mismatched:
                return {
                    "status": "skipped",
                    "reason": "review lifecycle owner identity mismatch",
                    "mismatched_fields": mismatched,
                    "path": record_path.relative_to(target_root).as_posix(),
                    "recovery": "create-or-refresh-current-review-owner",
                }
    owner_revision_before = (
        "sha256:" + hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest() if record else "new"
    )
    idempotency_basis = {
        "identity": identity,
        "phase": phase,
        "phase_after": phase_after,
        "command": command,
        "outcome": outcome,
        "next_action_id": next_action_id,
        "changed_paths": normalized_paths or member_paths,
        "command_exit_code": command_exit_code,
        "proof_receipt_path": proof_receipt_path,
        "proof_receipt_result": proof_receipt_result,
    }
    idempotency_key = "sha256:" + hashlib.sha256(json.dumps(idempotency_basis, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    existing_transitions = [item for item in existing_lifecycle.get("transitions", []) if isinstance(item, dict)]
    if any(str(item.get("idempotency_key") or "") == idempotency_key for item in existing_transitions):
        return {
            "status": "already-recorded",
            "path": record_path.relative_to(target_root).as_posix(),
            "pr_number": selected_pr,
            "head_sha": selected_head,
            "owner_revision": live_owner["owner_revision"],
            "lifecycle_revision": str(existing_lifecycle.get("lifecycle_revision") or owner_revision_before),
            "idempotency_key": idempotency_key,
        }
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
        "identity": identity,
        "owner_revision_before": owner_revision_before,
        "idempotency_key": idempotency_key,
    }
    title = f"Review Stack {selected_pr} Lifecycle".replace("-", " ").title()
    updated_transitions = [*existing_transitions, transition_payload]
    lifecycle_revision = (
        "sha256:"
        + hashlib.sha256(
            json.dumps({"identity": identity, "transitions": updated_transitions}, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )
    lifecycle_payload: dict[str, Any] = {
        "record_kind": "review-stack-lifecycle",
        "pr_number": selected_pr,
        "current_phase": phase_after,
        "next_action_id": next_action_id,
        "changed_paths": normalized_paths or member_paths,
        "updated_at": transition_payload["recorded_at"],
        "source": "ordinary-command",
        "review_owner_identity": identity,
        "review_owner_revision": live_owner["owner_revision"],
        "lifecycle_revision": lifecycle_revision,
        "transitions": updated_transitions,
    }
    if dry_run:
        return {
            "status": "dry-run",
            "path": record_path.relative_to(target_root).as_posix(),
            "scope": lifecycle_payload,
        }
    record_path.parent.mkdir(parents=True, exist_ok=True)
    if record:
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
    temporary_path = record_path.with_name(record_path.name + ".tmp")
    temporary_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary_path.replace(record_path)
    return {
        "status": status,
        "path": record_path.relative_to(target_root).as_posix(),
        "pr_number": selected_pr,
        "head_sha": selected_head,
        "owner_revision": live_owner["owner_revision"],
        "lifecycle_revision": lifecycle_revision,
        "idempotency_key": idempotency_key,
        "phase": phase,
        "phase_after": phase_after,
        "outcome": outcome,
        "proof_receipt_path": proof_receipt_path,
        "command_exit_code": command_exit_code,
    }


def command_text(program: str, argv: Sequence[str]) -> str:
    return " ".join([program, *[shlex.quote(str(item)) for item in argv]])
