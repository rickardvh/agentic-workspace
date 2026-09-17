"""Codex protocol I/O only; no Assignment policy, packet admission or repository semantics."""

from __future__ import annotations

import hashlib
import json
import os
import queue
import shutil
import signal
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
            start_new_session=os.name != "nt",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
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
            if os.name == "nt":
                # The installed CLI may be a cmd/node launcher. Terminating
                # only that wrapper does not prove its worker has stopped.
                killed = subprocess.run(
                    ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                    capture_output=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    check=False,
                )
                if killed.returncode != 0:
                    raise ProviderError("native-process-tree-release-unconfirmed")
                self.process.wait(timeout=5)
            else:
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.process.wait(timeout=5)


def discover(
    root: Path, *, executable: str = "codex", refresh: bool = False, now: float | None = None, persist: bool = True
) -> dict[str, Any]:
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
    if persist:
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
    deadline = None
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
            if "ephemeral" in selection["parameters"] and thread.get("ephemeral") is not ephemeral:
                raise ProviderError("provider-history-guarantee-unconfirmed")
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
            reason = str(error) if isinstance(error, ProviderError) else "native-return-or-control-failed"
            if reason == "provider-response-timeout" and deadline is not None and time.monotonic() >= deadline:
                reason = "provider-turn-timeout"
            raise ProviderError(reason, metrics=metrics) from error
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
