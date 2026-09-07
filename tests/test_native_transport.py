"""Native transport boundary tests; synthetic protocol fixtures are not host evidence."""

from __future__ import annotations

import copy
import json
import os
import time
from types import SimpleNamespace

import pytest

from agentic_workspace import native_transport as native
from agentic_workspace.contracts.python_primitive_support import _assignment_dispatch_configuration, _assignment_seal_host_native_packet


@pytest.fixture
def snapshot():
    return {
        "revision": "cap-v1",
        "identity": "adapter-v1",
        "executable": "fixture",
        "expires_at": time.time() + 900,
        "modes": ["fresh", "resume", "fork", "restart"],
        "parameters": ["model", "reasoning_effort"],
        "models": [{"model": "fixture-model", "reasoning_efforts": ["low"]}],
    }


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
    ],
)
def test_selection_fails_closed(snapshot, changes, reason):
    with pytest.raises(native.ProviderError, match=reason):
        native.validate_selection(snapshot, selection(snapshot, **changes))


def test_unchanged_version_does_not_make_expired_catalog_current(snapshot):
    with pytest.raises(native.ProviderError, match="not-current"):
        native.validate_selection(snapshot, selection(snapshot), now=snapshot["expires_at"])


def test_ephemeral_is_mode_specific_and_not_restartable(snapshot):
    snapshot["parameters"].append("ephemeral")
    snapshot["ephemeral_modes"] = ["fresh", "fork"]
    fresh = selection(snapshot, parameters={"model": "fixture-model", "ephemeral": True})
    native.validate_selection(snapshot, fresh)
    with pytest.raises(native.ProviderError, match="ephemeral-continuity-unavailable"):
        native.validate_selection(snapshot, {**fresh, "mode": "resume", "reference": "opaque"})
    with pytest.raises(native.ProviderError, match="parameter-unsupported"):
        native.validate_selection(snapshot, {**fresh, "parameters": {"model": "fixture-model", "ephemeral": "true"}})


def test_partial_startup_captures_cleanup_custody_before_turn_failure(tmp_path, monkeypatch, snapshot):
    closed = []

    class Connection:
        def __init__(self, executable):
            pass

        def call(self, method, params):
            if method == "thread/start":
                return {"thread": {"id": "owned-probe"}}
            raise native.ProviderError("fixture-turn-rejected")

        def close(self):
            closed.append(True)

    monkeypatch.setattr(native, "CodexConnection", Connection)
    owned = set()
    with pytest.raises(native.ProviderError, match="fixture-turn-rejected"):
        native.execute(tmp_path, snapshot, selection(snapshot), "unused", {}, on_thread=owned.add)
    assert owned == {"owned-probe"}
    assert closed == [True]


def test_archive_failure_does_not_delete_or_claim_success(monkeypatch, snapshot):
    calls = []

    class Connection:
        def __init__(self, executable):
            pass

        def call(self, method, params):
            calls.append(method)
            raise native.ProviderError("provider-active-writer")

        def close(self):
            calls.append("closed")

    monkeypatch.setattr(native, "CodexConnection", Connection)
    with pytest.raises(native.ProviderError, match="archive-unavailable"):
        native.archive_reference(snapshot, "owned")
    assert calls == []
    snapshot["archive_supported"] = True
    with pytest.raises(native.ProviderError, match="provider-active-writer"):
        native.archive_reference(snapshot, "owned")
    assert calls == ["thread/archive", "closed"]


def test_exclusive_lineage_is_not_a_ttl_lease():
    with native.exclusive_lineage("fixture-exclusive-test"):
        with pytest.raises(native.ProviderError, match="exclusive-writer-busy"):
            with native.exclusive_lineage("fixture-exclusive-test"):
                pytest.fail("a parallel writer was admitted")
    with native.exclusive_lineage("fixture-exclusive-test"):
        pass


def test_packet_chooses_exact_peer_adapter():
    process = {"kind": "process", "method": "cli", "command": ["fixture"]}
    control = {"kind": "native", "method": "cli", "adapter": "codex-app-server/v1"}
    identity = {
        "dispatch_adapter": {
            "execution_methods": ["cli"],
            "transports": [process, control],
            "execution_configuration": {"transport": "cli", "execution": {"adapter": control}},
        }
    }
    assert _assignment_dispatch_configuration(identity=identity, transport="cli")["kind"] == "native"
    identity["dispatch_adapter"]["execution_configuration"]["execution"]["adapter"] = process
    assert _assignment_dispatch_configuration(identity=identity, transport="cli")["command"] == ["fixture"]


def test_configured_process_and_native_remain_distinct_peer_options(tmp_path):
    from dataclasses import asdict

    from agentic_workspace.config import load_delegation_target_profiles
    from agentic_workspace.target_evidence import assignment_decision_from_policy

    profiles, _ = load_delegation_target_profiles(
        raw_targets={
            "worker": {
                "strength": "strong",
                "location": "external",
                "transports": [
                    {"kind": "process", "command": ["fixture"]},
                    {"kind": "native", "adapter": "codex-app-server/v1", "parameters": {"model": "fixture-model"}},
                ],
            }
        },
        config_path=tmp_path / "config.local.toml",
    )
    profile = asdict(profiles[0])
    assert profile["execution_methods"] == ("cli",)
    profile["execution_configurations"] = [
        {"eligible": True, "configuration": {"id": kind, "transport": "cli", "execution": {"adapter": transport}}}
        for kind, transport in zip(("process", "native"), profile["transports"], strict=True)
    ]
    decision = assignment_decision_from_policy(
        assignment_policy={}, runtime_resolution={"profile_recommendations": [profile]}, target_evidence={}
    )
    candidate = decision["candidate_scores"][0]
    assert [row["execution_configuration"]["id"] for row in candidate["transport_options"]] == ["process", "native"]
    assert candidate["selected_execution_configuration"]["id"] == "process"


def test_continuation_residue_cannot_invalidate_its_own_admission(tmp_path, monkeypatch, snapshot):
    monkeypatch.setattr(native, "discover", lambda root: snapshot)
    (tmp_path / ".agentic-workspace").mkdir()
    (tmp_path / ".agentic-workspace/config.local.toml").write_text("# synthetic configured authority\n")
    profile = {"name": "worker", "target_id": "worker-v1", "target_revision": "v1"}
    adapter = {"kind": "native", "method": "cli", "adapter": "codex-app-server/v1", "parameters": {"model": "fixture-model"}}
    policy = SimpleNamespace(transport_authority="automatic", safe_to_auto_run_commands=True)
    work = {"id": "slice", "revision": "r1"}
    native._write(
        native._lineage_path(tmp_path, profile, adapter),
        {
            "reference": "opaque",
            "target_revision": "v1",
            "semantic_scope": "slice",
            "semantic_revision": "r1",
            "capability_revision": snapshot["revision"],
            "origin_run_id": "run-1",
        },
    )
    assert len(native.configuration_offers(tmp_path, profile, adapter, policy, work)) == 1
    native._write(tmp_path / ".agentic-workspace/local/assignment-runs/run-1/state.json", {"current_state": "closed"})
    offers = native.configuration_offers(tmp_path, profile, adapter, policy, work)
    assert [row["execution"]["continuity"]["mode"] for row in offers] == ["fresh", "resume", "fork", "restart"]
    assert [row["independent_context"] for row in offers] == [True, False, False, False]
    assert "opaque" not in json.dumps(offers)


@pytest.mark.parametrize(
    "mode,method,new_id",
    [
        ("fresh", "thread/start", "new"),
        ("resume", "thread/resume", "opaque"),
        ("restart", "thread/resume", "opaque"),
        ("fork", "thread/fork", "new"),
    ],
)
def test_native_topology_uses_metadata_only_and_returns_counters(tmp_path, monkeypatch, snapshot, mode, method, new_id):
    calls = []

    class Connection:
        def __init__(self, executable):
            self.events = [
                {
                    "method": "thread/tokenUsage/updated",
                    "params": {
                        "threadId": new_id,
                        "tokenUsage": {"last": {"inputTokens": 120, "cachedInputTokens": 80, "outputTokens": 9}},
                    },
                },
                {"method": "item/completed", "params": {"threadId": new_id, "turnId": "turn", "item": {"text": '{"ok":true}'}}},
                {"method": "turn/completed", "params": {"threadId": new_id, "turn": {"id": "turn", "status": "completed"}}},
            ]

        def call(self, name, params):
            calls.append((name, params))
            return {"turn": {"id": "turn"}} if name == "turn/start" else {"thread": {"id": new_id}}

        def close(self):
            calls.append(("closed", {}))

    monkeypatch.setattr(native, "CodexConnection", Connection)
    choice = selection(snapshot, mode=mode, **({"reference": "opaque"} if mode != "fresh" else {}))
    result = native.execute(tmp_path, snapshot, choice, "bounded input", {"type": "object"})
    assert calls[0][0] == method
    assert calls[0][1].get("excludeTurns") is (True if mode != "fresh" else None)
    assert calls[0][1]["sandbox"] == "read-only"
    assert result["metrics"]["cached_input_tokens"] == 80
    assert "retry_count" not in result["metrics"]
    assert result["raw_transcript_stored"] is False
    assert calls[-1][0] == "closed"
    assert not list(tmp_path.rglob("*.json"))


def test_native_packet_tamper_blocks_before_provider_call(tmp_path, monkeypatch):
    monkeypatch.setattr(native, "discover", lambda root: pytest.fail("discovery before packet admission"))
    packet = _assignment_seal_host_native_packet(
        {
            "assignment_id": "a",
            "assignment_revision": "r",
            "run_id": "run",
            "target": "t",
            "transport": "cli",
            "assignment_identity": {},
            "return_contract": {},
        }
    )
    changed = copy.deepcopy(packet)
    changed["assignment_identity"]["dispatch_adapter"] = {"execution_configuration": {"mode": "resume"}}
    result = native.dispatch_packet(tmp_path, changed, "unused")
    assert result["status"] == "blocked"
    assert result["reason"] == "native-packet-unsealed"


def test_reader_drops_transcript_events():
    import io
    import queue

    connection = object.__new__(native.CodexConnection)
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
    snapshot = native.discover(tmp_path, refresh=True)
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
            result = native.execute(
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
        with pytest.raises(native.ProviderError, match="native-continuation-unavailable"):
            native.execute(
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
                native.archive_reference(snapshot, reference)
            except Exception as error:
                failures.append(error)
                pending.append(reference)
        if failures:
            native._write(tmp_path / ".agentic-workspace/local/provider-test-cleanup.json", {"references": pending, "status": "pending"})
            raise ExceptionGroup("owned provider test cleanup failed", failures)
    connection = native.CodexConnection(snapshot["executable"])
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
