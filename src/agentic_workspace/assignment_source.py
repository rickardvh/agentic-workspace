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


def configuration_requirements(
    policy: Any,
    *,
    task_identity: dict[str, Any],
    work: dict[str, Any],
    judgment: dict[str, Any] | None,
    target_root: Path | None = None,
    task: str = "",
    changed_paths: list[str] | None = None,
) -> dict[str, Any]:
    """Current owner projection; absent task judgment never means no constraints."""
    from agentic_workspace.decision import task_requirements, verification_requirements

    current_judgment = dict(judgment) if judgment is not None else None
    request = current_judgment.pop("verification_request", None) if current_judgment is not None else None
    verification_owner = None
    verification = None
    if target_root is not None and current_judgment is not None and (current_judgment.get("role") == "evaluator" or request is not None):
        verification_owner = verification_requirements(
            {
                "target": str(target_root),
                "task": task,
                "changed_paths": changed_paths or [],
                "current_work": work,
                "role": current_judgment["role"],
                "request": request,
            }
        )
        verification = verification_owner["verification"]
        # The exact submitted owner request already binds this judgment's
        # source. Derive its identity from the owner, never from caller facts.
        if verification is not None and current_judgment.get("verification_identity") is None:
            current_judgment["verification_identity"] = {"id": verification["id"], "revision": verification["revision"]}

    result = task_requirements(
        {
            "kind": "agentic-workspace/task-requirements-input/v1",
            "task_identity": task_identity,
            "current_work": work,
            "judgment": current_judgment,
            "verification": verification,
            "required_execution_guarantees": list(getattr(policy, "required_execution_guarantees", ())),
        }
    )
    schema = json.loads((Path(__file__).parent / "contracts/schemas/source_decision_input.schema.json").read_text(encoding="utf-8"))
    result["judgment_request"] = {
        "argument_name": "task_judgment_json",
        "encoding": "json",
        "arguments": {
            "task_identity": task_identity,
            "current_work": work,
            "role": "executor",
            "required_result_classes": [],
            "required_proof_classes": [],
            "verification_identity": None,
        },
        "input_schema": {
            "$schema": schema["$schema"],
            "$defs": {key: schema["$defs"][key] for key in ("task_requirements_identity", "task_requirements_judgment")},
            "$ref": "#/$defs/task_requirements_judgment",
        },
        "rule": "Supply only current task judgment through assignment preview/export/dispatch; this does not grant policy, proof or transport authority.",
    }
    if verification_owner is not None and current_judgment is not None:
        result["verification_requirements"] = verification_owner
        result["judgment_request"]["arguments"]["role"] = current_judgment["role"]
        result["judgment_request"]["arguments"]["verification_request"] = verification_owner["request"]
    return result


def current_route_configurations(
    root: Path,
    profiles: list[dict[str, Any]],
    policy: Any,
    work: dict[str, Any],
    selection: dict[str, str] | None = None,
    *,
    completed_packet: dict[str, Any] | None = None,
    requirements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One bounded capability evaluation across eligible transport peers."""
    from agentic_workspace.native_transport import discovery_scope

    with discovery_scope():
        return _current_route_configurations(
            root, profiles, policy, work, selection, completed_packet=completed_packet, requirements=requirements
        )


def _current_route_configurations(
    root: Path,
    profiles: list[dict[str, Any]],
    policy: Any,
    work: dict[str, Any],
    selection: dict[str, str] | None = None,
    *,
    completed_packet: dict[str, Any] | None = None,
    requirements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Host facts for process/manual routes and discovered native peers.

    Executable presence proves only the generic argv transport. It never proves
    a remote model, vendor parameter, or native continuation is available.
    """
    from agentic_workspace.decision import execution_configurations

    if requirements is None:
        raise ValueError("current-task-requirements-required")
    candidates: list[dict[str, Any]] = []
    for profile in profiles:
        name = profile["name"]
        current = bool(policy.current_target) and policy.current_target in {name, profile.get("target_id"), *profile.get("aliases", [])}
        transports = list(profile.get("transports", []))
        if current:
            transports = [{"method": "internal", "kind": "current-host"}] + [
                item for item in transports if item.get("kind") not in {"internal", "current-host"}
            ]
        elif policy.manual_transport_policy != "disabled" and not any(t.get("method") == "manual" for t in transports):
            # The established manual owner can export any bounded target packet.
            transports.append({"method": "manual", "kind": "manual"})
        native_allowed = (
            policy.transport_authority == "automatic"
            and policy.safe_to_auto_run_commands is True
            and not profile.get("capability_mismatch")
            and profile.get("required_action") != "escalate-before-execution"
            and "off" not in profile.get("human_control_modes", [])
            and "required-proof-missing" not in profile.get("proof_requirements", [])
        )
        if native_allowed:
            from agentic_workspace.native_transport import discovered_transports

            transports.extend(discovered_transports(root, profile))
        for transport in transports:
            method = transport["method"]
            retained = current and transport.get("kind") == "current-host"
            if transport.get("kind") == "native":
                # A hard-ineligible route cannot benefit from remote discovery.
                if not native_allowed:
                    continue
                from agentic_workspace.native_transport import configuration_offers

                candidates.extend(configuration_offers(root, profile, transport, policy, work, completed_packet=completed_packet))
                continue
            command = transport.get("command", [])
            executable = shutil.which(command[0]) if command else None
            if command and not executable:
                local = root / command[0]
                executable = str(local.resolve()) if local.is_file() else None
            manual = method == "manual"
            constructible = retained or manual or bool(executable and method in {"cli", "api"})
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
                    "authorized": retained
                    or (policy.manual_transport_policy != "disabled" if manual else policy.transport_authority == "automatic"),
                    "safe": retained or manual or policy.safe_to_auto_run_commands is True,
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
            **requirements,
            "candidates": candidates,
            "selection": selection,
        }
    )


def revision(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def parameterize_configuration(root: Path, configuration: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    """Delegate parameter constructibility to the selected transport owner."""
    if configuration.get("execution", {}).get("adapter", {}).get("kind") == "native":
        from agentic_workspace import native_transport

        return native_transport.parameterize_configuration(root, configuration, parameters)
    raise ValueError("configuration-parameterization-unavailable")


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
    effective_policy = load_workspace_config(target_root=root).local_override.human_override_policy or "explicit-only"
    if not isinstance(answer, dict) or effective_policy not in {"explicit-only", "allowed-with-recorded-reason"}:
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
        "revision": revision(
            {
                "answer": answer,
                "execution": execution,
                "policy": delegation,
                "effective_human_override_policy": effective_policy,
                "safety": raw.get("safety", {}),
            }
        ),
        "human_override_policy": effective_policy,
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
    if admission["source"].get("human_override_policy") == "allowed-with-recorded-reason":
        reason = request.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("assignment-override-reason-required")
        # Reason is recorded provenance only. The independently resolved exact
        # source answer above remains the sole replacement authorization.
        source = {**admission["source"], "recorded_reason": reason.strip()}
        source["revision"] = revision(source)
        admission = {**admission, "source": source}
    identity = packet.get("assignment_identity", {})
    if str(work.get("revision") or "").startswith(("planning-owner:", "direct-task:")):
        from agentic_workspace.workspace_runtime_core import _live_assignment_plan_binding

        current = _live_assignment_plan_binding(
            target_root=root,
            task_text=identity.get("human_intent", ""),
            changed_paths=identity.get("allowed_paths", []),
        )
        if current.get("plan_ref") != identity.get("plan_ref") or current.get("plan_revision") != work.get("revision"):
            raise ValueError("assignment-override-stale-work")
    else:
        # Compatibility for already sealed pre-owner-projection assignments.
        # New ordinary assignments always take the source-current path above.
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
        task_judgment=identity.get("task_judgment"),
    )
    if decision.get("task_requirements", {}).get("status") != "resolved":
        raise ValueError("current-task-requirements-unresolved")
    eligibility = replacement_eligibility(decision=decision, work=work, execution=execution, packet_integrity=packet["packet_integrity"])
    return replace_assignment(
        {
            "current": packet,
            "work": work,
            "source": admission["source"],
            "admission": admission,
            "execution": execution,
            "request": {key: value for key, value in request.items() if key != "reason"},
            "eligibility": eligibility,
        }
    )


def replace_after_repair(
    root: Path, packet: dict[str, Any], choice: dict[str, Any] | None, *, completed_packet: dict[str, Any] | None = None
) -> dict[str, Any]:
    """The assignment owner admits a new eligible attempt, never new semantics."""
    from agentic_workspace.target_evidence import replacement_eligibility
    from agentic_workspace.workspace_runtime_core import _current_assignment_selection, _live_assignment_plan_binding

    identity = packet["assignment_identity"]
    work = {"id": identity["slice_id"], "revision": identity["plan_revision"]}
    current = _live_assignment_plan_binding(target_root=root, task_text=identity["human_intent"], changed_paths=identity["allowed_paths"])
    if current.get("plan_ref") != identity.get("plan_ref") or current.get("plan_revision") != work["revision"]:
        raise ValueError("assignment-repair-semantic-source-stale")
    run_id = packet["run_id"]
    if not isinstance(run_id, str) or not run_id or any(not (c.isalnum() or c in "-_") for c in run_id):
        raise ValueError("assignment-repair-run-invalid")
    run_root = root / ".agentic-workspace/local/assignment-runs" / run_id
    state = json.loads((run_root / "state.json").read_text(encoding="utf-8"))
    receipt_ref = state.get("repair_admission_ref", "")
    receipt_path = root / receipt_ref
    if not receipt_ref or not receipt_path.resolve().is_relative_to(run_root.resolve()) or receipt_path.is_symlink():
        raise ValueError("assignment-repair-admission-unavailable")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected = {key: packet[key] for key in ("assignment_id", "assignment_revision", "run_id", "packet_integrity")}
    if receipt.get("repair_binding") != expected or receipt.get("status") != "repair-requested":
        raise ValueError("assignment-repair-admission-stale")
    if state.get("current_state") != ("superseded" if completed_packet else "repair-requested"):
        raise ValueError("assignment-repair-run-not-current")
    native = identity.get("dispatch_adapter", {}).get("execution_configuration", {}).get("execution", {}).get("adapter", {})
    if native.get("kind") == "native":
        from agentic_workspace.native_transport import assignment_worker_released

        if not assignment_worker_released(root, packet):
            raise ValueError("assignment-repair-worker-release-unconfirmed")
    config = load_workspace_config(target_root=root)
    answer = config.local_override.assignment_replacement
    if (
        answer
        and answer.get("assignment_id") == packet["assignment_id"]
        and answer.get("assignment_revision") == packet["assignment_revision"]
    ):
        raise ValueError("assignment-repair-explicit-source-answer-pending")
    *_, decision = _current_assignment_selection(
        config=config,
        changed_paths=identity["allowed_paths"],
        task_text=identity["human_intent"],
        execution_choice=choice,
        task_judgment=identity.get("task_judgment"),
        completed_packet=completed_packet,
    )
    if decision.get("task_requirements", {}).get("status") != "resolved":
        raise ValueError("current-task-requirements-unresolved")
    if choice is None:
        return {"status": "repair-choice-required", "execution_configurations": decision["execution_configurations"], "work": work}
    selected = decision["selected_execution_configuration"]
    target = next(p for p in config.local_override.delegation_targets if p.name == selected["target"])
    adapter = selected["execution"]["adapter"]
    execution = {
        "target": target.name,
        "target_identity_ref": target.target_id,
        "target_revision": target.target_revision,
        "transport": selected["transport"],
        "adapter": {
            "kind": adapter["kind"],
            "execution_configuration": selected,
            "execution_methods": [selected["transport"]],
            "transports": [adapter],
            "model": target.model_family,
        },
    }
    source = {
        "kind": "assignment-repair-source/v1",
        "reference": receipt_ref,
        "revision": revision({"repair": receipt, "choice": choice, "authority": configuration_authority_revision(root, target.name)}),
        "execution_choice": choice,
    }
    admission = {**expected, "work": work, "source": source, "execution": execution}
    eligibility = replacement_eligibility(decision=decision, work=work, execution=execution, packet_integrity=packet["packet_integrity"])
    return replace_assignment(
        {
            "current": packet,
            "work": work,
            "source": source,
            "admission": admission,
            "execution": execution,
            "request": {"assignment_revision": packet["assignment_revision"], "target": target.name, "transport": selected["transport"]},
            "eligibility": eligibility,
        }
    )


def current_replacement(root: Path, packet: dict[str, Any], work: dict[str, Any]) -> dict[str, Any]:
    from agentic_workspace.decision import admit_assignment_packet

    previous_run = packet.get("replacement", {}).get("previous_run_id", "")
    if not previous_run or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in previous_run):
        raise ValueError("invalid previous assignment run")
    old_path = root / ".agentic-workspace/local/assignment-runs" / previous_run / "export/packet.json"
    if old_path.is_symlink() or not old_path.resolve().is_relative_to(root.resolve()):
        raise ValueError("unowned previous packet path")
    old = json.loads(old_path.read_text(encoding="utf-8-sig"))
    if packet.get("replacement", {}).get("source", {}).get("kind") == "assignment-repair-source/v1":
        if work != packet["replacement"].get("work"):
            raise ValueError("assignment-repair-semantic-source-stale")
        expected = replace_after_repair(root, old, packet["replacement"]["source"]["execution_choice"], completed_packet=packet)
        if expected.get("packet") != packet:
            raise ValueError("assignment-repair-source-stale")
        return {"status": "current"}
    admission, execution = source_facts(root)
    expected = replace_from_source(
        root,
        old,
        work,
        {
            "assignment_revision": admission["assignment_revision"],
            "target": execution["target"],
            "transport": execution["transport"],
            "reason": packet["replacement"]["source"].get("recorded_reason"),
        },
    )
    if expected["status"] != "replaced":
        raise ValueError(expected["reason_code"])
    result = admit_assignment_packet(
        {
            "packet": packet,
            "canonical": expected["packet"],
            "source": expected["packet"]["replacement"]["source"],
            "execution": execution,
            "work": work,
        }
    )
    if result["status"] != "current":
        raise ValueError(result["reason_code"])
    return result
