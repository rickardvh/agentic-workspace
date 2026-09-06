"""Fixed local-config source adapter for one current replacement answer.

Configuration is the established human-owned authority surface. Operation
arguments remain intention; they never supply this adapter's source facts.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

from agentic_workspace.config import DelegationTargetProfile, load_workspace_config
from agentic_workspace.decision import replace_assignment

SOURCE = ".agentic-workspace/config.local.toml"


def revision(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def source_facts(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read only the established local source; no caller-selectable source path."""
    path = root / SOURCE
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("replacement authority cannot use a symlink source")
    raw = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    delegation = raw.get("delegation", {})
    answer = delegation.get("replacement")
    if not isinstance(answer, dict) or delegation.get("human_override_policy") != "explicit-only":
        raise ValueError("assignment-override-authority-unavailable")
    required = {
        "assignment_id",
        "assignment_revision",
        "work_id",
        "work_revision",
        "target",
        "transport",
        "execution_revision",
        "packet_integrity",
    }
    if set(answer) != required or any(not isinstance(v, str) or not v for v in answer.values()):
        raise ValueError("invalid revision-bound replacement answer")
    execution = execution_configuration(root, answer["target"], answer["transport"])
    if answer["execution_revision"] != revision(execution):
        raise ValueError("replacement-configuration-stale")
    source = {
        "reference": SOURCE,
        "revision": revision({"answer": answer, "execution": execution, "policy": delegation, "safety": raw.get("safety", {})}),
    }
    admission = {
        "packet_integrity": answer["packet_integrity"],
        "assignment_id": answer["assignment_id"],
        "assignment_revision": answer["assignment_revision"],
        "work": {"id": answer["work_id"], "revision": answer["work_revision"]},
        "source": source,
        "execution": execution,
    }
    return admission, execution


def execution_configuration(root: Path, target_name: str, transport: str) -> dict[str, Any]:
    """Describe only parameters constructible by this host; this grants nothing."""
    path = root / SOURCE
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("replacement-source-outside-owner-root")
    raw = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    delegation = raw.get("delegation", {})
    config = load_workspace_config(target_root=root)
    target = next((p for p in config.local_override.delegation_targets if p.name == target_name), None)
    if target is None or not target.target_id or not target.target_revision:
        raise ValueError("replacement-target-unavailable")
    raw_profile = raw.get("delegation_targets", {}).get(target_name, {})
    unsupported = set(raw_profile) - set(DelegationTargetProfile.__dataclass_fields__)
    if unsupported:
        raise ValueError("unsupported-replacement-parameters:" + ",".join(sorted(unsupported)))
    for item in raw_profile.get("transports", []):
        if not isinstance(item, dict) or set(item) - {"kind", "command", "output_mode", "timeout_seconds"}:
            raise ValueError("unsupported-replacement-transport-parameters")
    if transport not in target.execution_methods:
        raise ValueError("replacement-transport-unavailable")
    # This command-line host can construct manual exports and configured argv
    # transports. Host-native launch needs a real host capability input, not a
    # configuration assertion that an internal tool is available.
    if transport == "internal":
        raise ValueError("replacement-host-capability-unavailable")
    if transport == "manual":
        if delegation.get("manual_transport_policy", "allowed") == "disabled":
            raise ValueError("replacement-manual-transport-forbidden")
        adapter = {"kind": "manual", "execution_methods": ["manual"], "transports": [{"kind": "manual", "method": "manual"}]}
    else:
        if delegation.get("transport_authority") != "automatic" or raw.get("safety", {}).get("safe_to_auto_run_commands") is not True:
            raise ValueError("replacement-automatic-transport-forbidden")
        selected = next((dict(t) for t in target.transports if t.get("method") == transport), None)
        if not selected or not selected.get("command"):
            raise ValueError("replacement-transport-unconstructible")
        adapter = {"kind": "process", "execution_methods": [transport], "transports": [selected]}
        if any("{model}" in str(part) for part in selected["command"]):
            if not target.model_family:
                raise ValueError("replacement-model-parameter-unavailable")
            adapter["model"] = target.model_family
    execution = {
        "target": target.name,
        "target_identity_ref": target.target_id,
        "target_revision": target.target_revision,
        "transport": transport,
        "adapter": adapter,
    }
    return execution


def replacement_offer(root: Path, packet: dict[str, Any], target_name: str, transport: str) -> dict[str, Any]:
    execution = execution_configuration(root, target_name, transport)
    return {
        "status": "unadmitted-proposal",
        "source_owner": SOURCE,
        "schema_ref": "workspace_local_override.schema.json#/properties/delegation/properties/replacement",
        "answer": {
            "assignment_id": packet["assignment_id"],
            "assignment_revision": packet["assignment_revision"],
            "work_id": packet["assignment_identity"]["slice_id"],
            "work_revision": packet["assignment_identity"]["plan_revision"],
            "target": target_name,
            "transport": transport,
            "execution_revision": revision(execution),
            "packet_integrity": packet["packet_integrity"],
        },
        "execution_configuration": execution,
        "rule": "Only the human-owned configuration source can admit this exact answer; returning or resubmitting this proposal is not authority.",
    }


def replace_from_source(root: Path, packet: dict[str, Any], work: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    admission, execution = source_facts(root)
    identity = packet.get("assignment_identity", {})
    plan_ref = identity.get("plan_ref", "")
    plan_path = (root / plan_ref).resolve()
    if not plan_ref or not plan_path.is_relative_to(root.resolve()) or (root / plan_ref).is_symlink():
        raise ValueError("replacement-work-source-unavailable")
    current_plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    if not isinstance(current_plan, dict) or current_plan.get("revision") != work.get("revision"):
        raise ValueError("assignment-override-stale-work")
    from agentic_workspace.target_evidence import replacement_eligibility
    from agentic_workspace.workspace_runtime_core import _current_assignment_selection

    *_, decision = _current_assignment_selection(
        config=load_workspace_config(target_root=root),
        changed_paths=identity["allowed_paths"],
        task_text=identity["human_intent"],
        work_identity=identity,
    )
    eligibility = replacement_eligibility(decision=decision, work=work, execution=execution, packet_integrity=packet["packet_integrity"])
    return replace_assignment(
        {
            "current": packet,
            "work": work,
            "source": admission["source"],
            "admission": admission,
            "execution": execution,
            "request": request,
            "eligibility": eligibility,
        }
    )


def current_replacement(root: Path, packet: dict[str, Any], work: dict[str, Any]) -> dict[str, Any]:
    from agentic_workspace.decision import admit_assignment_packet

    admission, execution = source_facts(root)
    previous_run = packet.get("replacement", {}).get("previous_run_id", "")
    if not previous_run or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in previous_run):
        raise ValueError("invalid previous assignment run")
    old_path = root / ".agentic-workspace/local/assignment-runs" / previous_run / "export/packet.json"
    if old_path.is_symlink() or not old_path.resolve().is_relative_to(root.resolve()):
        raise ValueError("unowned previous packet path")
    old = json.loads(old_path.read_text(encoding="utf-8-sig"))
    expected = replace_from_source(
        root,
        old,
        work,
        {"assignment_revision": admission["assignment_revision"], "target": execution["target"], "transport": execution["transport"]},
    )
    if expected["status"] != "replaced":
        raise ValueError(expected["reason_code"])
    result = admit_assignment_packet(
        {"packet": packet, "canonical": expected["packet"], "source": admission["source"], "execution": execution, "work": work}
    )
    if result["status"] != "current":
        raise ValueError(result["reason_code"])
    return result
