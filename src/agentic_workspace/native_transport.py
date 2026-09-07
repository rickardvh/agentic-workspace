"""Codex native transport adapter, without AW sessions or transcript retention.

Provider protocol and knobs live here. The portable assignment owner sees only
current execution configurations, opaque references and measured counters.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Callable, Iterator

_discovery_scope: ContextVar[dict[tuple[str, str], dict[str, Any]] | None] = ContextVar("native-discovery-scope", default=None)


@contextmanager
def discovery_scope() -> Iterator[None]:
    """Share one current snapshot within a bounded source-owner evaluation."""
    token = _discovery_scope.set({})
    try:
        yield
    finally:
        _discovery_scope.reset(token)


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
    root: Path, profile: dict[str, Any], transport: dict[str, Any], policy: Any, work: dict[str, Any]
) -> list[dict[str, Any]]:
    """Offer this adapter beside argv/manual peers; no portable vendor taxonomy."""
    if transport.get("adapter") != "codex-app-server/v1":
        return []
    try:
        snapshot = discover(root)
        source_revision = _source_revision(root, profile["name"])
        parameters = dict(transport["parameters"])
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
    # Publishing new candidates during admission would invalidate the originating
    # decision. Reuse becomes routable after that existing attempt is terminal.
    origin = lineage.get("origin_run_id", "")
    terminal = False
    if isinstance(origin, str) and origin and all(c.isalnum() or c in "-_" for c in origin):
        try:
            state = json.loads((root / ".agentic-workspace/local/assignment-runs" / origin / "state.json").read_text(encoding="utf-8"))
            terminal = state.get("current_state") in {"closed", "archived", "rejected"}
        except (OSError, ValueError):
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
        if selection.get("mode") != "fresh":
            try:
                lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                raise ProviderError("native-lineage-not-current") from error
            if digest(lineage) != selection.get("lineage_revision"):
                raise ProviderError("native-lineage-not-current")
            selection = {**selection, "reference": lineage["reference"]}
        properties = {key: {"type": "string", "const": value} for key, value in packet["return_contract"]["required_identity"].items()}
        properties.update(
            {
                "changed_paths": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
                "stop_conditions_hit": {"type": "array", "items": {"type": "string"}},
                "patch": {"type": "string"},
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
            _write(
                lineage_path,
                {
                    "reference": result["continuation"]["reference"],
                    "capability_revision": snapshot["revision"],
                    "target_revision": execution.get("target_revision"),
                    "semantic_scope": execution["semantic_scope"],
                    "semantic_revision": execution["semantic_revision"],
                    "adapter_identity": snapshot["identity"],
                    "origin_run_id": packet["run_id"],
                    "live": False,
                    "exclusive": True,
                },
            )
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


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


class ProviderError(ValueError):
    def __init__(self, message: str, *, metrics: dict[str, Any] | None = None):
        super().__init__(message)
        self.metrics = metrics or {}


class CodexConnection:
    """One provider process. Only the provider owns conversation persistence."""

    def __init__(self, executable: str, *, timeout: float = 30, environment: dict[str, str] | None = None):
        self.timeout = timeout
        self.process = subprocess.Popen(
            [executable, "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            env={**os.environ, **environment} if environment is not None else None,
        )
        self.messages: queue.Queue[dict[str, Any]] = queue.Queue()
        self.number = 0
        self.events: list[dict[str, Any]] = []
        threading.Thread(target=self._read, daemon=True).start()
        try:
            self.call("initialize", {"clientInfo": {"name": "aw-native-transport", "version": "1"}})
            self.send({"method": "initialized"})
        except Exception:
            self.close()
            raise

    def _read(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            # Drop reasoning, deltas, commands and history at the adapter ingress.
            if "id" in value or value.get("method") in {"item/completed", "turn/completed", "thread/tokenUsage/updated", "error"}:
                if value.get("method") == "item/completed" and value.get("params", {}).get("item", {}).get("type") != "agentMessage":
                    continue
                self.messages.put(value)
        self.messages.put({"adapter_closed": True})

    def send(self, payload: dict[str, Any]) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(payload) + "\n")
        self.process.stdin.flush()

    def next(self, timeout: float | None = None) -> dict[str, Any]:
        try:
            item = self.messages.get(timeout=self.timeout if timeout is None else timeout)
        except queue.Empty as error:
            raise ProviderError("provider-response-timeout") from error
        if item.get("adapter_closed"):
            raise ProviderError("provider-process-closed")
        # This adapter does not admit interactive approvals or tool execution
        # outside its fixed read-only sandbox. Deny provider requests explicitly.
        if "id" in item and "method" in item:
            self.send({"id": item["id"], "error": {"code": -32601, "message": "Unsupported by bounded read-only adapter"}})
            return self.next(timeout)
        return item

    def call(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self.number += 1
        number = self.number
        self.send({"id": number, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            message = self.next(max(0.01, deadline - time.monotonic()))
            if message.get("id") == number:
                if "error" in message:
                    if (
                        method == "thread/archive"
                        and message["error"].get("message") == f"no rollout found for thread id {params.get('threadId')}"
                    ):
                        raise ProviderError("native-active-thread-unavailable")
                    if (
                        method in {"thread/resume", "thread/fork"}
                        and message["error"].get("message") == f"no rollout found for thread id {params.get('threadId')}"
                    ):
                        raise ProviderError("native-continuation-unavailable")
                    # No prompt or provider payload is retained in an error.
                    raise ProviderError(f"provider-operation-rejected:{method}:{message['error'].get('code')}")
                return message["result"]
            self.events.append(message)
        raise ProviderError("provider-response-timeout")

    def close(self) -> None:
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)


def discover(root: Path, *, executable: str = "codex", refresh: bool = False, now: float | None = None) -> dict[str, Any]:
    """Local version signal plus bounded remote/account capability refresh."""
    clock = time.time() if now is None else now
    scope = _discovery_scope.get()
    key = (str(root.resolve()), executable)
    scoped = scope.get(key, {}) if scope is not None else {}
    if not refresh and clock < scoped.get("expires_at", 0) and not scoped.get("invalidated"):
        return scoped
    resolved = shutil.which(executable)
    if not resolved:
        raise ProviderError("native-adapter-executable-unavailable")
    version = subprocess.run([resolved, "--version"], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    adapter_revision = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    identity = digest({"adapter": "codex-app-server/v1", "implementation": adapter_revision, "executable": resolved, "version": version})
    path = root / ".agentic-workspace/local/transport-capabilities" / f"{identity[7:]}.json"
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cached = {}
    if not refresh and cached.get("identity") == identity and clock < cached.get("expires_at", 0) and not cached.get("invalidated"):
        if scope is not None:
            scope[key] = cached
        return cached
    # Discover actual installed protocol properties. In particular excludeTurns
    # is required: AW never requests the provider's persisted conversation.
    with tempfile.TemporaryDirectory(prefix="aw-provider-schema-") as directory:
        subprocess.run([resolved, "app-server", "generate-json-schema", "--out", directory], capture_output=True, timeout=20, check=True)
        schemas = {}
        for name in (
            "ThreadStartParams",
            "ThreadResumeParams",
            "ThreadForkParams",
            "TurnStartParams",
            "ThreadArchiveParams",
            "ConfigReadParams",
        ):
            schema_path = Path(directory) / "v2" / f"{name}.json"
            if schema_path.is_file():
                schemas[name] = json.loads(schema_path.read_text())["properties"]
    turn_supported = {"threadId", "input", "outputSchema", "model", "approvalPolicy"} <= schemas.get("TurnStartParams", {}).keys()
    thread_fields = {"cwd", "model", "sandbox", "approvalPolicy"}
    modes = ["fresh"] if turn_supported and thread_fields <= schemas.get("ThreadStartParams", {}).keys() else []
    for mode, name in (("resume", "ThreadResumeParams"), ("fork", "ThreadForkParams")):
        if turn_supported and (thread_fields | {"excludeTurns", "threadId"}) <= schemas.get(name, {}).keys():
            modes.append(mode)
    if "resume" in modes:
        modes.append("restart")
    connection = CodexConnection(resolved)
    try:
        result = connection.call("model/list", {"limit": 100})
        effective_effort = None
        effective_settings_known = {"cwd", "includeLayers"} <= schemas.get("ConfigReadParams", {}).keys()
        if effective_settings_known:
            effective = connection.call("config/read", {"includeLayers": False, "cwd": str(root)})
            effective_effort = effective.get("config", {}).get("model_reasoning_effort")
    finally:
        connection.close()
    if result.get("nextCursor"):
        raise ProviderError("provider-catalog-exceeds-bounded-discovery")
    catalog = [
        {
            "model": m["model"],
            "reasoning_efforts": [item["reasoningEffort"] for item in m.get("supportedReasoningEfforts", [])],
            "default_reasoning_effort": m.get("defaultReasoningEffort"),
        }
        for m in result["data"]
        if not m.get("hidden")
    ]
    facts = {
        "adapter": "codex-app-server/v1",
        "implementation_revision": adapter_revision,
        "executable": resolved,
        "version": version,
        "modes": modes,
        "models": catalog,
        "effective_reasoning_effort": effective_effort,
        "effective_settings_known": effective_settings_known,
        "protocol_revision": digest(schemas),
        "parameters": ["model", "timeout_seconds"]
        + (["reasoning_effort"] if "effort" in schemas.get("TurnStartParams", {}) else [])
        + (["ephemeral"] if "ephemeral" in schemas.get("ThreadStartParams", {}) else []),
        "ephemeral_modes": [
            mode
            for mode, name in (("fresh", "ThreadStartParams"), ("fork", "ThreadForkParams"))
            if mode in modes and "ephemeral" in schemas.get(name, {})
        ],
        "archive_supported": "threadId" in schemas.get("ThreadArchiveParams", {}),
    }
    snapshot = {
        **facts,
        "identity": identity,
        "revision": digest(facts),
        "observed_at": clock,
        "expires_at": clock + 900,
        "live_worker_continuity": False,
        "exclusive_writer": True,
        "process_lifetime": "one-dispatch",
        "conversation_lifetime": "provider-owned",
        "source": "installed-protocol-and-model-list",
    }
    _write(path, snapshot)
    if scope is not None:
        scope[key] = snapshot
    return snapshot


def validate_selection(snapshot: dict[str, Any], selection: dict[str, Any], *, now: float | None = None) -> None:
    clock = time.time() if now is None else now
    if snapshot.get("invalidated") or clock >= snapshot["expires_at"] or selection.get("capability_revision") != snapshot["revision"]:
        raise ProviderError("native-capability-not-current")
    if set(selection) - {"capability_revision", "mode", "reference", "parameters", "semantic_scope", "lineage_revision"}:
        raise ProviderError("unsupported-native-selection-field")
    mode = selection.get("mode")
    if mode not in snapshot["modes"]:
        raise ProviderError("native-continuity-unavailable")
    if mode != "fresh" and not selection.get("reference"):
        raise ProviderError("native-continuation-reference-required")
    if mode == "fresh" and selection.get("reference"):
        raise ProviderError("fresh-cannot-inherit-reference")
    validate_parameters(snapshot, mode, selection.get("parameters", {}))


def validate_parameters(snapshot: dict[str, Any], mode: str, parameters: dict[str, Any]) -> None:
    if set(parameters) - set(snapshot.get("parameters", ["model"])):
        raise ProviderError("native-parameter-unsupported")
    if "ephemeral" in parameters and not isinstance(parameters["ephemeral"], bool):
        raise ProviderError("native-parameter-unsupported")
    if parameters.get("ephemeral") and mode not in snapshot.get("ephemeral_modes", []):
        raise ProviderError("native-ephemeral-continuity-unavailable")
    model = next((m for m in snapshot["models"] if m["model"] == parameters.get("model")), None)
    if model is None:
        raise ProviderError("native-model-unavailable")
    if "reasoning_effort" in parameters and parameters["reasoning_effort"] not in model["reasoning_efforts"]:
        raise ProviderError("native-parameter-unsupported")
    if "timeout_seconds" in parameters:
        timeout = parameters["timeout_seconds"]
        if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 1800:
            raise ProviderError("native-parameter-unsupported")


@contextmanager
def exclusive_lineage(reference: str) -> Iterator[None]:
    """Cross-worktree OS lock; released on process death, never guessed from TTL."""
    directory = Path(tempfile.gettempdir()) / "agentic-workspace-provider-locks"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (hashlib.sha256(("codex:" + reference).encode()).hexdigest() + ".lock")
    with path.open("a+b") as lock:
        try:
            if path.stat().st_size == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ProviderError("native-lineage-exclusive-writer-busy") from error
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def execute(
    root: Path,
    snapshot: dict[str, Any],
    selection: dict[str, Any],
    prompt: str,
    schema: dict[str, Any],
    *,
    timeout: int = 1800,
    on_thread: Callable[[str], None] | None = None,
    worker_environment: dict[str, str] | None = None,
    on_closed: Callable[[], None] | None = None,
    on_history: Callable[[bool], None] | None = None,
) -> dict[str, Any]:
    """Run an exact native topology; missing provider state never becomes fresh."""
    validate_selection(snapshot, selection)
    reference = selection.get("reference")
    mode = selection["mode"]
    started = time.monotonic()
    metrics: dict[str, Any] = {"kind": "agentic-workspace/assignment-transport-metrics/v1"}
    usage_current = True
    with exclusive_lineage(reference or "fresh:" + os.urandom(16).hex()):
        connection = (
            CodexConnection(snapshot["executable"], environment=worker_environment)
            if worker_environment is not None
            else CodexConnection(snapshot["executable"])
        )
        try:
            method = {"fresh": "thread/start", "resume": "thread/resume", "restart": "thread/resume", "fork": "thread/fork"}[mode]
            params = {"cwd": str(root), "model": selection["parameters"]["model"], "sandbox": "read-only", "approvalPolicy": "never"}
            ephemeral = selection["parameters"].get("ephemeral", False)
            if mode in {"fresh", "fork"} and "ephemeral" in selection["parameters"]:
                params["ephemeral"] = ephemeral
            if reference:
                params.update({"threadId": reference, "excludeTurns": True})
            result = connection.call(method, params)
            thread = result["thread"]
            actual = thread["id"]
            if mode in {"resume", "restart"} and actual != reference:
                raise ProviderError("provider-continuation-identity-mismatch")
            if mode == "fork" and actual == reference:
                raise ProviderError("provider-fork-lineage-not-independent")
            if on_thread is not None:
                on_thread(actual)
            if on_history is not None and isinstance(thread.get("ephemeral"), bool):
                on_history(thread["ephemeral"])
            if ephemeral and thread.get("ephemeral") is not True:
                raise ProviderError("provider-ephemeral-guarantee-not-enforced")
            if not ephemeral and thread.get("ephemeral") is True:
                raise ProviderError("provider-persistence-guarantee-not-enforced")
            turn_params = {
                "threadId": actual,
                "input": [{"type": "text", "text": prompt}],
                "outputSchema": schema,
                "model": selection["parameters"]["model"],
                "approvalPolicy": "never",
            }
            if selection["parameters"].get("reasoning_effort"):
                turn_params["effort"] = selection["parameters"]["reasoning_effort"]
            turn = connection.call("turn/start", turn_params)["turn"]["id"]
            output = ""
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                event = connection.events.pop(0) if connection.events else connection.next(max(0.01, deadline - time.monotonic()))
                payload = event.get("params", {})
                if payload.get("threadId") != actual:
                    continue
                if event.get("method") == "thread/tokenUsage/updated" and payload.get("turnId") == turn and mode == "fresh":
                    # `last` covers one model response, not the entire tool loop.
                    # Fresh has a known zero lineage baseline. Reused contexts
                    # lack a proven pre-turn baseline, so their total is unknown.
                    usage = payload.get("tokenUsage", {}).get("total", {})
                    observed: dict[str, int] = {}
                    for source, target in (
                        ("inputTokens", "effective_input_tokens"),
                        ("cachedInputTokens", "cached_input_tokens"),
                        ("outputTokens", "output_tokens"),
                    ):
                        value = usage.get(source)
                        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                            observed[target] = value
                    fields = ("effective_input_tokens", "cached_input_tokens", "output_tokens")
                    if (
                        len(observed) != len(fields)
                        or any(observed.get(field, -1) < metrics.get(field, 0) for field in fields)
                        or observed.get("cached_input_tokens", 0) > observed.get("effective_input_tokens", 0)
                    ):
                        usage_current = False
                    if usage_current:
                        metrics.update(observed)
                    else:
                        # A provider counter reset/estimate is not a cheaper run.
                        for field in fields:
                            metrics.pop(field, None)
                if payload.get("turnId") == turn and event.get("method") == "item/completed":
                    output = payload["item"].get("text", "")
                if event.get("method") == "turn/completed" and payload.get("turn", {}).get("id") == turn:
                    if payload["turn"].get("status") != "completed":
                        raise ProviderError("provider-turn-failed")
                    return {
                        "returned_work": json.loads(output),
                        "metrics": metrics,
                        "elapsed_ms": round((time.monotonic() - started) * 1000),
                        "continuation": {
                            "reference": actual,
                            "mode": mode,
                            "capability_revision": snapshot["revision"],
                            "parameters": selection["parameters"],
                            "live": False,
                            "exclusive": True,
                            "ephemeral": ephemeral,
                        },
                        "raw_transcript_stored": False,
                    }
            raise ProviderError("provider-turn-timeout")
        except (ProviderError, ValueError, OSError) as error:
            raise ProviderError(
                str(error) if isinstance(error, ProviderError) else "native-return-or-control-failed", metrics=metrics
            ) from error
        finally:
            connection.close()
            if on_closed is not None:
                on_closed()


def archive_reference(snapshot: dict[str, Any], reference: str) -> str:
    """Reversible cleanup of a caller-owned terminal worker; never delete state."""
    if not snapshot.get("archive_supported"):
        raise ProviderError("native-archive-unavailable")
    connection = CodexConnection(snapshot["executable"])
    try:
        try:
            connection.call("thread/archive", {"threadId": reference})
        except ProviderError as error:
            if str(error) != "native-active-thread-unavailable":
                raise
            return "already-absent"
        return "archived"
    finally:
        connection.close()
