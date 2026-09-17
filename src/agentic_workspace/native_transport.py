"""Codex native transport adapter, without AW sessions or transcript retention.

Provider protocol and knobs live here. The portable assignment owner sees only
current execution configurations, opaque references and measured counters.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from agentic_workspace.codex_provider import (
    CodexConnection as CodexConnection,
)
from agentic_workspace.codex_provider import (
    ProviderError as ProviderError,
)
from agentic_workspace.codex_provider import (
    _write as _write,
)
from agentic_workspace.codex_provider import (
    archive_reference as archive_reference,
)
from agentic_workspace.codex_provider import (
    digest as digest,
)
from agentic_workspace.codex_provider import (
    discover as discover,
)
from agentic_workspace.codex_provider import (
    discovery_scope as discovery_scope,
)
from agentic_workspace.codex_provider import (
    exclusive_lineage as exclusive_lineage,
)
from agentic_workspace.codex_provider import (
    execute as execute,
)
from agentic_workspace.codex_provider import (
    validate_parameters as validate_parameters,
)
from agentic_workspace.codex_provider import (
    validate_selection as validate_selection,
)


def _lineage_path(root: Path, profile: dict[str, Any], transport: dict[str, Any]) -> Path:
    key = digest(
        {
            "target": profile.get("target_id") or profile["name"],
            "adapter": transport.get("adapter"),
            "parameters": transport.get("parameters"),
        }
    )
    return root / ".agentic-workspace/local/transport-continuations" / f"{key[7:]}.json"


def _source_revision(root: Path, target: str = "") -> str:
    from agentic_workspace.assignment_source import configuration_authority_revision

    return configuration_authority_revision(root, target)


def discovered_transports(root: Path, profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Adapter-owned peer discovery; the source host still admits authority/safety."""
    if profile.get("provider") != "openai" or not profile.get("model_family"):
        return []
    if any(item.get("adapter") == "codex-app-server/v1" for item in profile.get("transports", [])):
        return []
    try:
        snapshot = discover(root)
        parameters = {"model": profile["model_family"]}
        validate_selection(snapshot, {"mode": "fresh", "parameters": parameters, "capability_revision": snapshot["revision"]})
    except (ProviderError, OSError, subprocess.SubprocessError, ValueError, KeyError):
        return []
    transports = [{"kind": "native", "method": "cli", "adapter": "codex-app-server/v1", "parameters": parameters}]
    if "fresh" in snapshot.get("ephemeral_modes", []):
        transports.append({**transports[0], "parameters": {**parameters, "ephemeral": True}})
    return transports


def configuration_offers(
    root: Path,
    profile: dict[str, Any],
    transport: dict[str, Any],
    policy: Any,
    work: dict[str, Any],
    *,
    completed_packet: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Offer this adapter beside argv/manual peers; no portable vendor taxonomy."""
    if transport.get("adapter") != "codex-app-server/v1":
        return []
    try:
        snapshot = discover(root)
        source_revision = _source_revision(root, profile["name"])
        parameters = dict(transport["parameters"])
        if "ephemeral" in snapshot["parameters"]:
            parameters.setdefault("ephemeral", False)
        model = next((row for row in snapshot["models"] if row["model"] == parameters.get("model")), {})
        if "reasoning_effort" in snapshot["parameters"] and "reasoning_effort" not in parameters:
            if not snapshot.get("effective_settings_known"):
                raise ProviderError("native-default-parameter-unavailable")
            effort = snapshot.get("effective_reasoning_effort") or model.get("default_reasoning_effort")
            if not effort:
                raise ProviderError("native-default-parameter-unavailable")
            parameters["reasoning_effort"] = effort
        fresh: dict[str, Any] = {"mode": "fresh", "parameters": parameters, "capability_revision": snapshot["revision"]}
        validate_selection(snapshot, fresh)
    except (ProviderError, OSError, subprocess.SubprocessError, ValueError, KeyError):
        return []
    selections: list[dict[str, Any]] = [fresh]
    try:
        lineage = json.loads(_lineage_path(root, profile, transport).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        lineage = {}
    lineage = _completed_attempt_input_lineage(root, lineage, profile, transport, completed_packet)
    # Publishing new candidates during admission would invalidate the originating
    # decision. Reuse becomes routable after that existing attempt is terminal.
    origin = lineage.get("origin_run_id", "")
    terminal = False
    if isinstance(origin, str) and origin and all(c.isalnum() or c in "-_" for c in origin):
        try:
            state = json.loads((root / ".agentic-workspace/local/assignment-runs" / origin / "state.json").read_text(encoding="utf-8"))
            terminal = state.get("current_state") in {"closed", "archived", "rejected"}
            if state.get("current_state") in {"repair-requested", "superseded"}:
                packet = state.get("assignment", {})
                receipt_path = root / state.get("repair_admission_ref", "")
                run_root = _custody_path(root, origin).parent
                if receipt_path.resolve().is_relative_to(run_root) and not receipt_path.is_symlink():
                    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                    binding = {key: packet.get(key) for key in ("assignment_id", "assignment_revision", "run_id", "packet_integrity")}
                    prepared = prepare_repair_continuation(root, packet)
                    terminal = (
                        receipt.get("repair_binding") == binding
                        and receipt.get("status") == "repair-requested"
                        and prepared is not None
                        and prepared[1] == lineage
                    )
        except (OSError, ValueError, KeyError, TypeError, AttributeError, ProviderError):
            pass
    if (
        lineage.get("semantic_scope") == work.get("id")
        and lineage.get("semantic_revision") == work.get("revision")
        and lineage.get("target_revision") == profile.get("target_revision")
        and lineage.get("capability_revision") == snapshot["revision"]
        and lineage.get("reference")
        and terminal
    ):
        for mode in snapshot["modes"]:
            if mode != "fresh":
                selections.append(
                    {
                        **fresh,
                        "mode": mode,
                        "reference": lineage["reference"],
                        "semantic_scope": work["id"],
                        "lineage_revision": digest(lineage),
                    }
                )
    offers = []
    for selection in selections:
        try:
            validate_selection(snapshot, selection)
        except ProviderError:
            continue
        available = True
        if selection.get("reference"):
            try:
                with exclusive_lineage(selection["reference"]):
                    pass
            except ProviderError:
                available = False
        offers.append(
            {
                "id": f"{profile['name']}:native:{digest(selection)[7:23]}",
                "target": profile["name"],
                "transport": transport["method"],
                "capability_revision": snapshot["revision"],
                "current": True,
                "authorized": policy.transport_authority == "automatic",
                "safe": policy.safe_to_auto_run_commands is True,
                "constructible": True,
                "result_classes": ["read-only", "unapplied-patch"],
                "proof_classes": [],
                "independent_context": selection["mode"] == "fresh",
                "concurrency_available": available,
                "execution_guarantees": [
                    "history.non-persisted" if selection["parameters"].get("ephemeral") else "history.provider-persisted",
                ]
                if "ephemeral" in selection["parameters"]
                else [],
                "execution": {
                    "source_revision": source_revision,
                    "adapter": transport,
                    "context_strategy": "bounded",
                    "parameter_options": {
                        **(
                            {"reasoning_effort": {"enum": model.get("reasoning_efforts", [])}}
                            if "reasoning_effort" in snapshot["parameters"]
                            else {}
                        ),
                        "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": min(1800, transport.get("timeout_seconds", 1800))},
                    },
                    "history": {
                        "persistence": "ephemeral" if selection["parameters"].get("ephemeral") else "provider-owned",
                        "active_list_visibility": "not-stored" if selection["parameters"].get("ephemeral") else "provider-default",
                        "cleanup_capability": "archive" if snapshot.get("archive_supported") else "unavailable",
                    },
                    # The canonical Planning assignment may be checked in. It
                    # carries only a digest binding to adapter-local residue.
                    "continuity": {key: value for key, value in selection.items() if key != "reference"},
                    "target_identity": profile.get("target_id") or profile["name"],
                    "target_revision": profile.get("target_revision"),
                    "semantic_scope": work["id"],
                    "semantic_revision": work["revision"],
                },
            }
        )
    return offers


def _completed_attempt_input_lineage(
    root: Path, lineage: dict[str, Any], profile: dict[str, Any], transport: dict[str, Any], packet: dict[str, Any] | None
) -> dict[str, Any]:
    """Revalidate a consumed offer against its own exact completed publication.

    This is only an admission view. Ordinary selection still sees the new
    lineage, which remains unavailable while its return awaits acceptance.
    """
    if not packet:
        return lineage
    from agentic_workspace.contracts.python_primitive_support import _assignment_packet_integrity

    try:
        configuration = packet["assignment_identity"]["dispatch_adapter"]["execution_configuration"]
        if (
            packet.get("packet_integrity") != _assignment_packet_integrity(packet)
            or configuration["target"] != profile["name"]
            or configuration["execution"]["adapter"] != transport
            or lineage.get("origin_run_id") != packet["run_id"]
        ):
            return lineage
        path = _custody_path(root, packet["run_id"])
        custody = json.loads(path.read_text(encoding="utf-8"))
        state = json.loads(path.with_name("state.json").read_text(encoding="utf-8"))
        if (
            custody.get("run_id") != packet["run_id"]
            or custody.get("packet_integrity") != packet["packet_integrity"]
            or custody.get("live") is not False
            or custody.get("published_lineage_revision") != digest(lineage)
            or state.get("assignment", {}).get("packet_integrity") != packet["packet_integrity"]
            or state.get("current_state") not in {"awaiting-admission", "admitted", "integrated", "proof-recorded"}
            or not isinstance(custody.get("input_lineage"), dict)
        ):
            return lineage
        return custody["input_lineage"]
    except (KeyError, OSError, ValueError, TypeError, AttributeError, ProviderError):
        return lineage


def parameterize_configuration(root: Path, configuration: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
    """Validate an actor's bounded knob choice; never accept new source facts."""
    snapshot = discover(root)
    result = copy.deepcopy(configuration)
    execution = result["execution"]
    if execution.get("adapter", {}).get("adapter") != "codex-app-server/v1":
        raise ProviderError("native-parameterization-unavailable")
    selection = execution["continuity"]
    if configuration["capability_revision"] != snapshot["revision"]:
        raise ProviderError("native-capability-not-current")
    # History/topology and model remain choices of an existing eligible offer.
    # This adapter exposes only controls it can enforce on that selected route.
    if set(parameters) - {"reasoning_effort", "timeout_seconds"}:
        raise ProviderError("native-parameter-unsupported")
    selection["parameters"] = {**selection["parameters"], **parameters}
    validate_parameters(snapshot, selection["mode"], selection["parameters"])
    if selection["parameters"].get("timeout_seconds", 1) > execution["parameter_options"]["timeout_seconds"]["maximum"]:
        raise ProviderError("native-parameter-exceeds-configured-bound")
    result["id"] = f"{result['target']}:native:{digest(selection)[7:23]}"
    return result


def dispatch_packet(root: Path, packet: Any, prompt: str) -> dict[str, Any]:
    """Transport only: the ordinary assignment owner still admits the result."""
    from agentic_workspace.contracts.python_primitive_support import _assignment_context_cost, _assignment_packet_integrity

    started = time.monotonic()
    custody: dict[str, Any] = {}
    receipt: dict[str, Any] = {
        "kind": "agentic-workspace/assignment-dispatch-receipt/v1",
        "status": "blocked",
        "transport": packet.get("transport"),
        "adapter_kind": "native",
        "run_id": packet.get("run_id"),
        "packet_integrity": packet.get("packet_integrity"),
        "worker_launch_attempted": False,
        "claim_boundary": "transport-only; return requires assignment admission, integration, proof and closeout",
    }
    try:
        if not packet.get("packet_integrity") or packet["packet_integrity"] != _assignment_packet_integrity(packet):
            raise ProviderError("native-packet-unsealed")
        configuration = packet["assignment_identity"]["dispatch_adapter"]["execution_configuration"]
        execution = configuration["execution"]
        if execution.get("source_revision") != _source_revision(root, configuration["target"]):
            raise ProviderError("native-source-not-current")
        adapter = execution["adapter"]
        if (
            adapter.get("adapter") != "codex-app-server/v1"
            or configuration["transport"] != packet["transport"]
            or configuration["target"] != packet["target"]
        ):
            raise ProviderError("native-execution-configuration-mismatch")
        if not all(configuration.get(key) is True for key in ("authorized", "safe", "constructible", "current", "concurrency_available")):
            raise ProviderError("native-execution-ineligible")
        snapshot = discover(root)
        selection = execution["continuity"]
        profile = {
            "name": configuration["target"],
            "target_id": execution["target_identity"],
            "target_revision": execution.get("target_revision"),
        }
        lineage_path = _lineage_path(root, profile, adapter)
        try:
            lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            lineage = {}
        if selection.get("mode") != "fresh":
            if digest(lineage) != selection.get("lineage_revision"):
                raise ProviderError("native-lineage-not-current")
            selection = {**selection, "reference": lineage["reference"]}
        properties = {key: {"type": "string", "const": value} for key, value in packet["return_contract"]["required_identity"].items()}
        properties.update(
            {
                "changed_paths": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
                "stop_conditions_hit": {"type": "array", "items": {"type": "string"}},
                "patch": {
                    "type": "string",
                    "description": 'Return "" when changed_paths is empty, including read-only, no-change, or stopped work. Otherwise return a complete git-compatible unified diff; never invent a diff.',
                },
                "result_delivery": {
                    "type": "object",
                    "properties": {"mode": {"type": "string", "const": "unapplied-patch"}, "mutation_baseline": {"type": "string"}},
                    "required": ["mode", "mutation_baseline"],
                    "additionalProperties": False,
                },
            }
        )
        schema = {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}
        validate_selection(snapshot, selection)
        from agentic_workspace.native_core import core_binary

        try:
            worker_core = core_binary()
        except RuntimeError as error:
            raise ProviderError("native-worker-core-unavailable") from error
        custody_path = _custody_path(root, packet["run_id"])
        custody_path.parent.mkdir(parents=True, exist_ok=True)
        initial = {
            "kind": "agentic-workspace/native-transport-custody/v1",
            "run_id": packet["run_id"],
            "packet_integrity": packet["packet_integrity"],
            "adapter": "codex-app-server/v1",
            "reference": None,
            "live": True,
            "ephemeral": None,
            "input_lineage": {
                key: value
                for key, value in lineage.items()
                if key
                in {
                    "reference",
                    "capability_revision",
                    "target_revision",
                    "semantic_scope",
                    "semantic_revision",
                    "adapter_identity",
                    "origin_run_id",
                    "live",
                    "exclusive",
                    "unavailable",
                }
            },
        }
        try:
            with custody_path.open("x", encoding="utf-8") as handle:
                json.dump(initial, handle)
        except FileExistsError as error:
            raise ProviderError("native-run-already-attempted") from error
        custody = initial

        def capture_thread(reference: str) -> None:
            custody["reference"] = reference
            _write(custody_path, custody)

        def process_closed() -> None:
            custody["live"] = False
            _write(custody_path, custody)

        def history_observed(ephemeral: bool) -> None:
            custody["ephemeral"] = ephemeral
            if ephemeral:
                custody["reference"] = None
            _write(custody_path, custody)

        worker_kernel = {"assignment": {key: packet[key] for key in ("assignment_id", "assignment_revision", "run_id", "target")}}
        receipt["worker_launch_attempted"] = True
        result = execute(
            root,
            snapshot,
            selection,
            prompt,
            schema,
            timeout=selection["parameters"].get("timeout_seconds", adapter.get("timeout_seconds", 1800)),
            worker_environment={
                "AGENTIC_WORKSPACE_DELEGATED_WORKER_KERNEL": json.dumps(worker_kernel),
                "AGENTIC_WORKSPACE_CORE_BINARY": str(worker_core),
            },
            on_thread=capture_thread,
            on_closed=process_closed,
            on_history=history_observed,
        )
        custody["ephemeral"] = result["continuation"].get("ephemeral") is True
        if custody["ephemeral"]:
            custody["reference"] = None
        _write(custody_path, custody)
        if not result["continuation"].get("ephemeral"):
            published_lineage = {
                "reference": result["continuation"]["reference"],
                "capability_revision": snapshot["revision"],
                "target_revision": execution.get("target_revision"),
                "semantic_scope": execution["semantic_scope"],
                "semantic_revision": execution["semantic_revision"],
                "adapter_identity": snapshot["identity"],
                "origin_run_id": packet["run_id"],
                "live": False,
                "exclusive": True,
            }
            _write(lineage_path, published_lineage)
            custody["published_lineage_revision"] = digest(published_lineage)
            _write(custody_path, custody)
        receipt.update(
            {
                "status": "returned",
                "reason": "worker-returned-untrusted-evidence",
                "returned_work": result["returned_work"],
                "adapter_revision": snapshot["revision"],
                "continuation": result["continuation"],
                "context_cost": _assignment_context_cost(
                    packet=packet,
                    prompt=prompt,
                    transport=packet["transport"],
                    adapter_revision=snapshot["revision"],
                    elapsed_ms=round((time.monotonic() - started) * 1000),
                    observed=result["metrics"],
                ),
            }
        )
    except (ProviderError, OSError, subprocess.SubprocessError, ValueError, KeyError) as error:
        if isinstance(error, ProviderError) and str(error) == "native-continuation-unavailable":
            # Revoke just this adapter reference. Planning and assignment state
            # survive; the caller must resolve a new eligible route explicitly.
            _write(lineage_path, {**lineage, "reference": "", "unavailable": True})
        receipt["reason"] = str(error) if isinstance(error, ProviderError) else "native-transport-contract-unavailable"
        if custody:
            receipt["context_cost"] = _assignment_context_cost(
                packet=packet,
                prompt=prompt,
                transport=packet["transport"],
                adapter_revision=snapshot["revision"],
                elapsed_ms=round((time.monotonic() - started) * 1000),
                observed=getattr(error, "metrics", {}),
            )
    if custody:
        receipt["custody_ref"] = custody_path.relative_to(root.resolve()).as_posix()
    return receipt


def prepare_repair_continuation(root: Path, packet: dict[str, Any]) -> tuple[Path, dict[str, Any]] | None:
    """Prepare only bounded persistent custody for an owner-admitted repair."""
    try:
        configuration = packet["assignment_identity"]["dispatch_adapter"]["execution_configuration"]
        execution = configuration["execution"]
        if execution["adapter"].get("kind") != "native":
            return None
        custody = json.loads(_custody_path(root, packet["run_id"]).read_text(encoding="utf-8"))
        if (
            custody.get("packet_integrity") != packet["packet_integrity"]
            or custody.get("live") is not False
            or custody.get("ephemeral") is not False
            or not isinstance(custody.get("reference"), str)
            or not custody["reference"]
        ):
            return None
        profile = {"name": configuration["target"], "target_id": execution["target_identity"]}
        return _lineage_path(root, profile, execution["adapter"]), {
            "reference": custody["reference"],
            "capability_revision": configuration["capability_revision"],
            "target_revision": execution["target_revision"],
            "semantic_scope": execution["semantic_scope"],
            "semantic_revision": execution["semantic_revision"],
            "origin_run_id": packet["run_id"],
            "live": False,
            "exclusive": True,
        }
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ProviderError):
        return None


def assignment_worker_released(root: Path, packet: dict[str, Any]) -> bool:
    """Only exact adapter custody can prove release before another attempt."""
    try:
        custody = json.loads(_custody_path(root, packet["run_id"]).read_text(encoding="utf-8"))
        return custody.get("packet_integrity") == packet["packet_integrity"] and custody.get("live") is False
    except FileNotFoundError:
        try:
            receipt = json.loads((_custody_path(root, packet["run_id"]).parent / "dispatch/receipt.json").read_text(encoding="utf-8"))
            return (
                receipt.get("kind") == "agentic-workspace/assignment-dispatch-receipt/v1"
                and receipt.get("adapter_kind") == "native"
                and receipt.get("run_id") == packet["run_id"]
                and receipt.get("packet_integrity") == packet["packet_integrity"]
                and receipt.get("worker_launch_attempted") is False
            )
        except (OSError, ValueError, KeyError, TypeError, AttributeError, ProviderError):
            return False
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ProviderError):
        return False


def _custody_path(root: Path, run_id: str) -> Path:
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
        raise ProviderError("native-run-identity-invalid")
    path = (root / ".agentic-workspace/local/assignment-runs" / run_id / "transport-custody.json").resolve()
    if not path.is_relative_to(root.resolve()):
        raise ProviderError("native-custody-not-local")
    return path


def require_unattempted_run(root: Path, run_id: str) -> None:
    if _custody_path(root, run_id).exists():
        raise ProviderError("native-run-already-attempted")


def cleanup_owned_run(root: Path, run_id: str) -> dict[str, Any]:
    """Archive only an exact terminal attempt with confirmed process release."""
    started = time.monotonic()
    try:
        path = _custody_path(root, run_id)
        custody = json.loads(path.read_text(encoding="utf-8"))
        state = json.loads(path.with_name("state.json").read_text(encoding="utf-8"))
        assignment = state.get("assignment") if isinstance(state, dict) else None
        if (
            not isinstance(custody, dict)
            or not isinstance(assignment, dict)
            or custody.get("kind") != "agentic-workspace/native-transport-custody/v1"
            or custody.get("adapter") != "codex-app-server/v1"
            or custody.get("run_id") != run_id
            or state.get("run_id") != run_id
            or custody.get("live") is not False
            or state.get("current_state") not in {"closed", "archived", "rejected", "dispatch-failed"}
            or not custody.get("packet_integrity")
            or assignment.get("packet_integrity") != custody["packet_integrity"]
        ):
            raise ProviderError("native-cleanup-custody-not-terminal")
        previous = custody.get("cleanup_status")
        if previous in {"archived", "already-absent", "not-stored"}:
            return {"status": previous, "reused": True, "elapsed_ms": 0, "provider_state_deleted": False}
        if custody.get("ephemeral") is True:
            status = "not-stored"
        elif isinstance(custody.get("reference"), str) and custody["reference"]:
            with exclusive_lineage(custody["reference"]):
                # The process lock protects live writers. Existing run custody
                # also protects a released sibling still awaiting admission or
                # review. Bound inspection rather than inventing a session DB.
                for index, sibling in enumerate(path.parent.parent.glob("*/transport-custody.json")):
                    if index >= 256:
                        raise ProviderError("native-cleanup-custody-scan-limit")
                    if sibling.resolve() == path:
                        continue
                    if not sibling.resolve().is_relative_to(root.resolve()):
                        raise ProviderError("native-custody-not-local")
                    other = json.loads(sibling.read_text(encoding="utf-8"))
                    if not isinstance(other, dict):
                        raise ProviderError("native-cleanup-custody-unavailable")
                    if other.get("reference") == custody["reference"]:
                        other_state = json.loads(sibling.with_name("state.json").read_text(encoding="utf-8"))
                        if (
                            other.get("live") is not False
                            or not isinstance(other_state, dict)
                            or other_state.get("current_state") not in {"closed", "archived", "rejected", "dispatch-failed"}
                        ):
                            raise ProviderError("native-cleanup-conversation-still-needed")
                lineages = []
                for index, lineage_path in enumerate((root / ".agentic-workspace/local/transport-continuations").glob("*.json")):
                    if index >= 256 or not lineage_path.resolve().is_relative_to(root.resolve()):
                        raise ProviderError("native-cleanup-custody-scan-limit")
                    lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
                    if not isinstance(lineage, dict):
                        raise ProviderError("native-cleanup-custody-unavailable")
                    if lineage.get("reference") == custody["reference"]:
                        lineages.append((lineage_path, lineage))
                status = archive_reference(discover(root), custody["reference"])
                for lineage_path, lineage in lineages:
                    _write(lineage_path, {**lineage, "reference": "", "unavailable": "archived"})
        else:
            raise ProviderError("native-cleanup-reference-unavailable")
        _write(path, {**custody, "cleanup_status": status})
        return {"status": status, "elapsed_ms": round((time.monotonic() - started) * 1000), "provider_state_deleted": False}
    except (ProviderError, OSError, ValueError, KeyError) as error:
        return {"status": "deferred", "reason": str(error) if isinstance(error, ProviderError) else "native-cleanup-custody-unavailable"}
