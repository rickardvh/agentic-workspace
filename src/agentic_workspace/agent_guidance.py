from __future__ import annotations

from pathlib import Path
from typing import Any

from agentic_workspace.config import (
    WORKSPACE_LOCAL_CONFIG_PATH,
    WORKSPACE_LOCAL_CORRECTION_EVENTS_DEFAULT_PATH,
    WORKSPACE_LOCAL_TARGET_GUIDANCE_OVERLAY_DEFAULT_PATH,
    DelegationTargetProfile,
    MixedAgentLocalOverride,
)


def _target_identity_subject(profile: DelegationTargetProfile) -> dict[str, Any]:
    return {
        "profile_name": profile.name,
        "stable_target_id": profile.target_id,
        "target_revision": profile.target_revision,
        "aliases": list(profile.aliases),
        "identity_status": profile.identity_status,
        "revision_policy": profile.revision_policy,
        "provider": profile.provider,
        "model_family": profile.model_family,
        "role_identity": profile.name,
        "continuity_rule": (
            "preserve guidance"
            if profile.revision_policy == "preserve"
            else "revalidate guidance before reuse"
            if profile.revision_policy == "revalidate"
            else "migrate guidance with explicit provenance"
            if profile.revision_policy == "migrate"
            else "retire guidance unless a newer target explicitly supersedes it"
        ),
    }


def target_identity_posture(*, local_override: MixedAgentLocalOverride, target_root: Path | None) -> dict[str, Any]:
    subjects = [_target_identity_subject(profile) for profile in local_override.delegation_targets]
    current_name = local_override.current_target or ""
    exact = [subject for subject in subjects if subject["profile_name"] == current_name]
    alias = [subject for subject in subjects if current_name and current_name in subject["aliases"]]
    matches = exact or alias
    if not current_name:
        current_status = "unknown"
        recovery = "set delegation.current_target to a configured delegation_targets entry before target guidance can route"
    elif len(matches) > 1:
        current_status = "ambiguous"
        recovery = "replace the alias with one exact delegation target profile name or stable target_id"
    elif not matches:
        current_status = "unavailable"
        recovery = "configure delegation_targets.<current_target> or clear delegation.current_target"
    else:
        lifecycle = str(matches[0].get("identity_status") or "active")
        current_status = "known" if lifecycle == "active" and matches[0].get("stable_target_id") else lifecycle
        if lifecycle == "active" and not matches[0].get("stable_target_id"):
            current_status = "unknown"
            recovery = "set delegation_targets.<target>.target_id before using user-local target guidance"
        elif lifecycle in {"retired", "superseded", "ambiguous", "unavailable"}:
            recovery = "revalidate or migrate target guidance before reuse"
        else:
            recovery = "not-needed"
    current_subject = matches[0] if len(matches) == 1 else None
    user_root = local_override.user_guidance_root
    overlay_path = local_override.target_guidance_overlay_path or WORKSPACE_LOCAL_TARGET_GUIDANCE_OVERLAY_DEFAULT_PATH
    correction_path = local_override.correction_events_path or WORKSPACE_LOCAL_CORRECTION_EVENTS_DEFAULT_PATH
    overlay_exists = (target_root / overlay_path).exists() if target_root is not None else False
    correction_exists = (target_root / correction_path).exists() if target_root is not None else False
    enabled = bool(local_override.target_guidance_enabled)
    storage_status = "disabled" if not enabled else "missing-user-root" if not user_root else "available"
    return {
        "kind": "agentic-workspace/target-identity-posture/v1",
        "status": "configured" if subjects else "no-target-profiles",
        "current_target": current_name or None,
        "current_target_identity": {
            "status": current_status,
            "subject": current_subject,
            "provenance": {
                "source": local_override.field_sources.get("delegation.current_target", "unset") if current_name else "unset",
                "binding": "delegation.current_target",
                "raw_runtime_identity_stored": False,
            },
            "recovery": recovery,
            "fail_closed": current_status not in {"known"},
        },
        "subjects": subjects,
        "storage": {
            "status": storage_status,
            "user_local_target_guidance": {
                "enabled": enabled,
                "root": user_root,
                "source": local_override.field_sources.get("local_memory.user_guidance_root", "unset") if user_root else "unset",
                "checked_in": False,
                "portable_by_user_backup_only": True,
            },
            "repo_local_overlay": {
                "path": overlay_path.as_posix(),
                "exists": overlay_exists,
                "checked_in": False,
                "git_ignored": True,
                "safe_to_delete": True,
            },
            "correction_events": {
                "path": correction_path.as_posix(),
                "exists": correction_exists,
                "checked_in": False,
                "bounded_local_retention": True,
                "raw_transcripts_stored": False,
            },
        },
        "precedence": [
            "explicit current user instruction",
            "checked-in repo authority, safety, proof, and policy",
            "checked-in shared Memory for agent-independent repository knowledge",
            "repo-local target overlay under .agentic-workspace/local/",
            "user-local target guidance for this stable target id",
            "agent self-observation",
        ],
        "continuity_rules": {
            "preserve": "guidance survives target revision only when profile revision_policy=preserve",
            "revalidate": "guidance is visible but must be rechecked before use",
            "migrate": "guidance may move to a replacement target with explicit provenance",
            "retire": "guidance is not routed to new work",
        },
        "rule": "Target guidance routes only through a known stable target identity; display names and aliases alone are not sufficient.",
    }


def correction_feedback_contract(*, identity_posture: dict[str, Any]) -> dict[str, Any]:
    current_identity = identity_posture.get("current_target_identity", {})
    current_known = isinstance(current_identity, dict) and current_identity.get("status") == "known"
    storage = identity_posture.get("storage", {}) if isinstance(identity_posture.get("storage"), dict) else {}
    correction_storage = storage.get("correction_events", {}) if isinstance(storage.get("correction_events"), dict) else {}
    return {
        "kind": "agentic-workspace/correction-feedback-contract/v1",
        "status": "ready" if current_known else "fail-closed",
        "target_identity_required": True,
        "failure_recovery": current_identity.get("recovery", "resolve target identity before admitting correction events")
        if isinstance(current_identity, dict)
        else "resolve target identity before admitting correction events",
        "event_schema": {
            "required": [
                "target_identity_ref",
                "desired_behavior",
                "replaced_behavior",
                "applicability",
                "source",
                "authority",
                "provenance",
                "admission_state",
                "normalized_correction_key",
            ],
            "source_types": [
                "explicit-user-correction",
                "remember-instruction",
                "pr-review",
                "orchestrator-review",
                "evaluator-finding",
                "agent-self-observation",
                "external-adapter",
            ],
            "admission_states": [
                "accepted-candidate",
                "duplicate-replay",
                "recurrence",
                "contradicted",
                "disputed",
                "superseded",
                "withdrawn",
                "rejected-ambiguous-target",
                "rejected-secret-bearing",
            ],
        },
        "routing": {
            "agent_guidance": "candidate only; promotion threshold is out of scope for raw events",
            "target_suitability": "allowed when applicability and outcome evidence are scoped",
            "shared_memory": "only for agent-independent repository knowledge",
            "no_retention": "required for malformed, secret-bearing, or unauthorised submissions",
        },
        "storage": {
            "path": correction_storage.get("path", WORKSPACE_LOCAL_CORRECTION_EVENTS_DEFAULT_PATH.as_posix()),
            "checked_in": False,
            "raw_transcripts_stored": False,
            "controlled_by": WORKSPACE_LOCAL_CONFIG_PATH.as_posix(),
        },
        "rule": "Correction feedback is a structured local event stream, not a transcript archive and not direct workflow policy.",
    }
