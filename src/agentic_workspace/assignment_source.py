"""Fixed local-config source adapter for one current replacement answer.

Configuration is the established human-owned authority surface. Operation
arguments remain intention; they never supply this adapter's source facts.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tomllib
from pathlib import Path
from typing import Any

from agentic_workspace.config import DelegationTargetProfile, load_workspace_config
from agentic_workspace.decision import replace_assignment

SOURCE = ".agentic-workspace/config.local.toml"


def current_route_configurations(
    root: Path, profiles: list[dict[str, Any]], policy: Any, work: dict[str, Any], selection: dict[str, str] | None = None
) -> dict[str, Any]:
    """Host facts for existing process/manual routes, without probing providers.

    Executable presence proves only the generic argv transport. It never proves
    a remote model, vendor parameter, or native continuation is available.
    """
    from agentic_workspace.decision import execution_configurations

    candidates: list[dict[str, Any]] = []
    for profile in profiles:
        name = profile["name"]
        current = bool(policy.current_target) and policy.current_target in {name, profile.get("target_id"), *profile.get("aliases", [])}
        transports = list(profile.get("transports", []))
        if current:
            transports = [{"method": "internal", "kind": "current-host"}]
        elif policy.manual_transport_policy != "disabled" and not any(t.get("method") == "manual" for t in transports):
            # The established manual owner can export any bounded target packet.
            transports.append({"method": "manual", "kind": "manual"})
        for transport in transports:
            method = transport["method"]
            if transport.get("kind") == "native":
                # A hard-ineligible route cannot benefit from remote discovery.
                if (
                    policy.transport_authority != "automatic"
                    or policy.safe_to_auto_run_commands is not True
                    or profile.get("capability_mismatch")
                    or profile.get("required_action") == "escalate-before-execution"
                    or "off" in profile.get("human_control_modes", [])
                    or "required-proof-missing" in profile.get("proof_requirements", [])
                ):
                    continue
                from agentic_workspace.native_transport import configuration_offers

                candidates.extend(configuration_offers(root, profile, transport, policy, work))
                continue
            command = transport.get("command", [])
            executable = shutil.which(command[0]) if command else None
            if command and not executable:
                local = root / command[0]
                executable = str(local.resolve()) if local.is_file() else None
            manual = method == "manual"
            constructible = current or manual or bool(executable and method in {"cli", "api"})
            executable_stat = Path(executable).stat() if executable else None
            facts = {
                "transport": transport,
                "executable": executable,
                "executable_fingerprint": [executable_stat.st_size, executable_stat.st_mtime_ns] if executable_stat else None,
                "target_revision": profile.get("target_revision"),
            }
            candidates.append(
                {
                    "id": f"{name}:{method}",
                    "target": name,
                    "transport": method,
                    "capability_revision": revision(facts),
                    "current": True,
                    "authorized": current
                    or (policy.manual_transport_policy != "disabled" if manual else policy.transport_authority == "automatic"),
                    "safe": current or manual or policy.safe_to_auto_run_commands is True,
                    "constructible": constructible,
                    "result_classes": ["read-only", "unapplied-patch"],
                    "proof_classes": [],
                    "independent_context": False,
                    "concurrency_available": True,
                    "execution": {"adapter": transport, "context_strategy": "bounded", "continuity": {"mode": "adapter-owned-unknown"}},
                }
            )
    for candidate in candidates:
        candidate["execution"]["authority_revision"] = configuration_authority_revision(root, candidate["target"])
    return execution_configurations(
        {
            "work": work,
            "required_result_classes": [],
            "required_proof_classes": [],
            "independent_context": False,
            "candidates": candidates,
            "selection": selection,
        }
    )


def revision(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def configuration_authority_revision(root: Path, target: str) -> str:
    """Bind relevant human-owned source facts, excluding unrelated local settings."""
    path = root / SOURCE
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("configuration-source-outside-owner-root")
    raw = tomllib.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    return revision(
        {"delegation": raw.get("delegation", {}), "safety": raw.get("safety", {}), "target": raw.get("delegation_targets", {}).get(target)}
    )


def validate_current_configuration(root: Path, configuration: dict[str, Any]) -> None:
    execution = configuration.get("execution", {})
    expected = execution.get("authority_revision")
    # Legacy/imported assignments have their established admission contract.
    # Every newly source-resolved configuration carries the explicit binding.
    if expected is None:
        return
    target = configuration["target"]
    if expected != configuration_authority_revision(root, target):
        raise ValueError("assignment-configuration-source-stale")
    adapter = execution.get("adapter", {})
    if adapter.get("kind") == "process":
        command = adapter.get("command", [])
        executable = shutil.which(command[0]) if command else None
        if command and not executable:
            local = root / command[0]
            executable = str(local.resolve()) if local.is_file() else None
        stat = Path(executable).stat() if executable else None
        config = load_workspace_config(target_root=root)
        profile = next((p for p in config.local_override.delegation_targets if p.name == target), None)
        facts = {
            "transport": adapter,
            "executable": executable,
            "executable_fingerprint": [stat.st_size, stat.st_mtime_ns] if stat else None,
            "target_revision": profile.target_revision if profile else None,
        }
        if revision(facts) != configuration.get("capability_revision"):
            raise ValueError("assignment-configuration-capability-stale")


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
        fields = {"kind", "command", "output_mode", "timeout_seconds"}
        if isinstance(item, dict) and item.get("kind") == "native":
            fields = {"kind", "adapter", "parameters", "timeout_seconds"}
        if not isinstance(item, dict) or set(item) - fields:
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
