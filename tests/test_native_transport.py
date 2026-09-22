"""Native transport boundary tests; synthetic protocol fixtures are not host evidence."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from agentic_workspace import codex_provider as provider


@pytest.mark.skipif(os.name != "nt", reason="Windows launcher-tree contract; POSIX uses an owned process group")
def test_forced_native_close_stops_owned_launcher_and_child():
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    connection = object.__new__(provider.CodexConnection)
    connection.process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import subprocess,sys,time; child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); print(child.pid,flush=True); time.sleep(60)",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    child = None
    try:
        child_pid = int(connection.process.stdout.readline())
        child = kernel.OpenProcess(0x00100001, False, child_pid)  # synchronize + terminate, exact owned handle
        assert child
        connection.close()
        assert connection.process.returncode is not None
        assert kernel.WaitForSingleObject(child, 1000) == 0
    finally:
        if child:
            if kernel.WaitForSingleObject(child, 0) != 0:
                kernel.TerminateProcess(child, 1)
            kernel.CloseHandle(child)
        if connection.process.poll() is None:
            connection.process.kill()
            connection.process.wait(timeout=5)


def test_active_turn_deadline_is_not_reported_as_initial_control_failure(tmp_path, monkeypatch, snapshot):
    clock = [0.0]
    monkeypatch.setattr(provider, "time", SimpleNamespace(time=time.time, monotonic=lambda: clock[0]))

    class Connection:
        def __init__(self, executable):
            self.events = []

        def call(self, method, params):
            return {"turn": {"id": "turn"}} if method == "turn/start" else {"thread": {"id": "fresh"}}

        def next(self, timeout):
            clock[0] = 2.0
            raise provider.ProviderError("provider-response-timeout")

        def close(self):
            pass

    monkeypatch.setattr(provider, "CodexConnection", Connection)
    with pytest.raises(provider.ProviderError, match="provider-turn-timeout"):
        provider.execute(tmp_path, snapshot, selection(snapshot), "unused", {}, timeout=1)


@pytest.fixture
def snapshot():
    return {
        "revision": "cap-v1",
        "identity": "adapter-v1",
        "effective_settings_known": True,
        "executable": "fixture",
        "expires_at": time.time() + 900,
        "modes": ["fresh", "resume", "fork", "restart"],
        "parameters": ["model", "reasoning_effort", "timeout_seconds"],
        "models": [{"model": "fixture-model", "reasoning_efforts": ["low"], "default_reasoning_effort": "low"}],
    }


@pytest.mark.parametrize("phase", ["start", "completed"])
@pytest.mark.parametrize("invalid_schema", [False, True])
def test_provider_schema_rejection_is_actionable_and_does_not_echo_payload(tmp_path, monkeypatch, snapshot, phase, invalid_schema):
    error = {
        "code": -32600,
        "message": ("Invalid schema for response_format 'codex_output_schema': " if invalid_schema else "failure: ")
        + "secret-prompt-credential",
    }

    class Connection:
        call = provider.CodexConnection.call

        def __init__(self, executable):
            self.events = []
            self.number = 0
            self.timeout = 1

        def send(self, request):
            self.request = request

        def next(self, timeout):
            if self.request["method"] == "thread/start":
                assert self.request["params"]["sandbox"] == "read-only"
                assert self.request["params"]["approvalPolicy"] == "never"
                return {"id": self.number, "result": {"thread": {"id": "fresh"}}}
            if phase == "start":
                return {"id": self.number, "error": error}
            self.events.append(
                {"method": "turn/completed", "params": {"threadId": "fresh", "turn": {"id": "turn", "status": "failed", "error": error}}}
            )
            return {"id": self.number, "result": {"turn": {"id": "turn"}}}

        def close(self):
            pass

    monkeypatch.setattr(provider, "CodexConnection", Connection)
    with pytest.raises(provider.ProviderError) as failure:
        provider.execute(tmp_path, snapshot, selection(snapshot), "private prompt", {}, timeout=1)
    expected = (
        "provider-output-schema-invalid:check-adapter-output-schema"
        if invalid_schema
        else ("provider-operation-rejected:turn/start:-32600" if phase == "start" else "provider-turn-failed")
    )
    assert str(failure.value) == expected


def selection(snapshot, **changes):
    return {
        "capability_revision": snapshot["revision"],
        "mode": "fresh",
        "parameters": {"model": "fixture-model", "reasoning_effort": "low"},
        **changes,
    }


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"mode": "steer", "reference": "opaque"}, "continuity-unavailable"),
        ({"mode": "resume"}, "reference-required"),
        ({"reference": "opaque"}, "fresh-cannot-inherit"),
        ({"capability_revision": "old"}, "not-current"),
        ({"parameters": {"model": "retired"}}, "model-unavailable"),
        ({"parameters": {"model": "fixture-model", "reasoning_effort": "ultra"}}, "parameter-unsupported"),
        ({"parameters": {"model": "fixture-model", "unsafe_flag": True}}, "parameter-unsupported"),
        ({"parameters": {"model": "fixture-model", "reasoning_effort": ""}}, "parameter-unsupported"),
        ({"parameters": {"model": "fixture-model", "timeout_seconds": True}}, "parameter-unsupported"),
        ({"parameters": {"model": "fixture-model", "timeout_seconds": 0}}, "parameter-unsupported"),
        ({"parameters": {"model": "fixture-model", "timeout_seconds": 1801}}, "parameter-unsupported"),
    ],
)
def test_selection_fails_closed(snapshot, changes, reason):
    with pytest.raises(provider.ProviderError, match=reason):
        provider.validate_selection(snapshot, selection(snapshot, **changes))


def test_unchanged_version_does_not_make_expired_catalog_current(snapshot):
    with pytest.raises(provider.ProviderError, match="not-current"):
        provider.validate_selection(snapshot, selection(snapshot), now=snapshot["expires_at"])


def test_ephemeral_is_mode_specific_and_not_restartable(snapshot):
    snapshot["parameters"].append("ephemeral")
    snapshot["ephemeral_modes"] = ["fresh", "fork"]
    fresh = selection(snapshot, parameters={"model": "fixture-model", "ephemeral": True})
    provider.validate_selection(snapshot, fresh)
    with pytest.raises(provider.ProviderError, match="ephemeral-continuity-unavailable"):
        provider.validate_selection(snapshot, {**fresh, "mode": "resume", "reference": "opaque"})
    with pytest.raises(provider.ProviderError, match="parameter-unsupported"):
        provider.validate_selection(snapshot, {**fresh, "parameters": {"model": "fixture-model", "ephemeral": "true"}})


def test_partial_startup_captures_cleanup_custody_before_turn_failure(tmp_path, monkeypatch, snapshot):
    closed = []
    history = []

    class Connection:
        def __init__(self, executable):
            pass

        def call(self, method, params):
            if method == "thread/start":
                return {"thread": {"id": "owned-probe", "ephemeral": False}}
            raise provider.ProviderError("fixture-turn-rejected")

        def close(self):
            closed.append(True)

    monkeypatch.setattr(provider, "CodexConnection", Connection)
    owned = set()
    with pytest.raises(provider.ProviderError, match="fixture-turn-rejected"):
        provider.execute(tmp_path, snapshot, selection(snapshot), "unused", {}, on_thread=owned.add, on_history=history.append)
    assert owned == {"owned-probe"}
    assert closed == [True]
    assert history == [False]


def test_archive_failure_does_not_delete_or_claim_success(monkeypatch, snapshot):
    calls = []

    class Connection:
        def __init__(self, executable):
            pass

        def call(self, method, params):
            calls.append(method)
            raise provider.ProviderError("provider-active-writer")

        def close(self):
            calls.append("closed")

    monkeypatch.setattr(provider, "CodexConnection", Connection)
    with pytest.raises(provider.ProviderError, match="archive-unavailable"):
        provider.archive_reference(snapshot, "owned")
    assert calls == []
    snapshot["archive_supported"] = True
    with pytest.raises(provider.ProviderError, match="provider-active-writer"):
        provider.archive_reference(snapshot, "owned")
    assert calls == ["thread/archive", "closed"]


def test_exclusive_lineage_is_not_a_ttl_lease():
    with provider.exclusive_lineage("fixture-exclusive-test"):
        with pytest.raises(provider.ProviderError, match="exclusive-writer-busy"):
            with provider.exclusive_lineage("fixture-exclusive-test"):
                pytest.fail("a parallel writer was admitted")
    with provider.exclusive_lineage("fixture-exclusive-test"):
        pass


@pytest.mark.parametrize(
    "mode,method,new_id",
    [
        ("fresh", "thread/start", "new"),
        ("resume", "thread/resume", "opaque"),
        ("restart", "thread/resume", "opaque"),
        ("fork", "thread/fork", "new"),
    ],
)
@pytest.mark.parametrize("counter_reset", [False, True])
def test_native_topology_uses_metadata_only_and_returns_counters(tmp_path, monkeypatch, snapshot, mode, method, new_id, counter_reset):
    calls = []
    environments = []

    class Connection:
        def __init__(self, executable, *, environment=None):
            environments.append(environment)
            self.events = [
                {
                    "method": "thread/tokenUsage/updated",
                    "params": {
                        "threadId": new_id,
                        "turnId": "turn",
                        "tokenUsage": {
                            "last": {"inputTokens": 120, "cachedInputTokens": 80, "outputTokens": 9},
                            "total": {"inputTokens": 300, "cachedInputTokens": 160, "outputTokens": 25},
                        },
                    },
                },
                {"method": "item/completed", "params": {"threadId": new_id, "turnId": "turn", "item": {"text": '{"ok":true}'}}},
                {"method": "turn/completed", "params": {"threadId": new_id, "turn": {"id": "turn", "status": "completed"}}},
            ]
            self.events.insert(1, copy.deepcopy(self.events[0]))
            foreign = copy.deepcopy(self.events[0])
            foreign["params"]["turnId"] = "foreign-turn"
            foreign["params"]["tokenUsage"]["total"]["inputTokens"] = 999
            self.events.insert(2, foreign)
            if counter_reset:
                reset = copy.deepcopy(self.events[0])
                reset["params"]["tokenUsage"]["total"] = {"inputTokens": 0, "cachedInputTokens": 0, "outputTokens": 0}
                self.events.insert(3, reset)
                self.events.insert(4, copy.deepcopy(self.events[0]))

        def call(self, name, params):
            calls.append((name, params))
            return {"turn": {"id": "turn"}} if name == "turn/start" else {"thread": {"id": new_id}}

        def close(self):
            calls.append(("closed", {}))

    monkeypatch.setattr(provider, "CodexConnection", Connection)
    choice = selection(snapshot, mode=mode, **({"reference": "opaque"} if mode != "fresh" else {}))
    worker_environment = {"AGENTIC_WORKSPACE_DELEGATED_WORKER_KERNEL": '{"assignment":{"assignment_id":"worker"}}'}
    result = provider.execute(tmp_path, snapshot, choice, "bounded input", {"type": "object"}, worker_environment=worker_environment)
    assert environments == [worker_environment]
    assert calls[0][0] == method
    assert calls[0][1].get("excludeTurns") is (True if mode != "fresh" else None)
    assert calls[0][1]["sandbox"] == "read-only"
    assert result["metrics"].get("cached_input_tokens") == (160 if mode == "fresh" and not counter_reset else None)
    assert result["metrics"].get("effective_input_tokens") == (300 if mode == "fresh" and not counter_reset else None)
    assert result["metrics"].get("output_tokens") == (25 if mode == "fresh" and not counter_reset else None)
    assert "retry_count" not in result["metrics"]
    assert result["raw_transcript_stored"] is False
    assert calls[-1][0] == "closed"
    assert not list(tmp_path.rglob("*.json"))


def test_reader_drops_transcript_events():
    import io
    import queue

    connection = object.__new__(provider.CodexConnection)
    connection.process = SimpleNamespace(
        stdout=io.StringIO(
            "\n".join(
                json.dumps(x)
                for x in [
                    {"method": "item/reasoning/textDelta", "params": {"delta": "private"}},
                    {"method": "item/completed", "params": {"item": {"type": "reasoning", "text": "private"}}},
                    {"method": "item/completed", "params": {"item": {"type": "agentMessage", "text": "result"}}},
                ]
            )
        )
    )
    connection.messages = queue.Queue()
    connection._read()
    assert connection.messages.get_nowait()["params"]["item"]["text"] == "result"
    assert connection.messages.get_nowait() == {"adapter_closed": True}
    assert connection.messages.empty()


@pytest.mark.skipif(not os.environ.get("AW_NATIVE_TRANSPORT_HOST_MODEL"), reason="explicit installed-provider probe model required")
def test_installed_native_host_continuity(tmp_path):
    """Opt-in live transport proof; this is not independent task Verification."""
    snapshot = provider.discover(tmp_path, refresh=True)
    if not snapshot.get("archive_supported"):
        pytest.skip("persisted probe requires constructible terminal cleanup")
    parameters = {"model": os.environ["AW_NATIVE_TRANSPORT_HOST_MODEL"]}
    if os.environ.get("AW_NATIVE_TRANSPORT_HOST_EFFORT"):
        parameters["reasoning_effort"] = os.environ["AW_NATIVE_TRANSPORT_HOST_EFFORT"]
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False}
    base = {"capability_revision": snapshot["revision"], "parameters": parameters}
    observed = []
    original = ""
    owned = set()
    try:
        modes = os.environ.get("AW_NATIVE_TRANSPORT_HOST_MODES", "fresh,resume,fork,restart").split(",")
        assert modes[0] == "fresh" and set(modes) <= {"fresh", "resume", "fork", "restart"}
        for mode in modes:
            if mode not in snapshot["modes"]:
                continue
            choice = {**base, "mode": mode, **({"reference": original} if mode != "fresh" else {})}
            result = provider.execute(
                tmp_path, snapshot, choice, "Return JSON with ok true. Do not use tools or read files.", schema, on_thread=owned.add
            )
            reference = result["continuation"]["reference"]
            assert result["returned_work"] == {"ok": True}
            if mode in {"resume", "restart"}:
                assert reference == original
            elif mode == "fork":
                assert reference != original
            else:
                original = reference
            observed.append(
                {"mode": mode, "identity_contract_passed": True, "metrics": result["metrics"], "elapsed_ms": result["elapsed_ms"]}
            )
        with pytest.raises(provider.ProviderError, match="native-continuation-unavailable"):
            provider.execute(
                tmp_path,
                snapshot,
                {**base, "mode": "resume", "reference": "00000000-0000-4000-8000-000000000001"},
                "must not launch",
                schema,
            )
    finally:
        failures = []
        pending = []
        for reference in owned:
            try:
                provider.archive_reference(snapshot, reference)
            except Exception as error:
                failures.append(error)
                pending.append(reference)
        if failures:
            provider._write(tmp_path / ".agentic-workspace/local/provider-test-cleanup.json", {"references": pending, "status": "pending"})
            raise ExceptionGroup("owned provider test cleanup failed", failures)
    connection = provider.CodexConnection(snapshot["executable"])
    try:
        listing = connection.call("thread/list", {"cwd": str(tmp_path), "archived": False, "limit": 100})
        assert not ({row["id"] for row in listing["data"]} & owned)
    finally:
        connection.close()
    print(
        json.dumps(
            {
                "version": snapshot["version"],
                "capability_revision": snapshot["revision"],
                "observations": observed,
                "missing_reference_failed_closed": True,
                "live_steer_available": snapshot["live_worker_continuity"],
                "owned_threads_archived": len(owned),
                "active_list_residue": 0,
            }
        )
    )
