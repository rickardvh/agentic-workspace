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


def test_discovered_peer_preserves_policy_and_separates_current_host_safety(tmp_path, monkeypatch, snapshot):
    import sys

    from agentic_workspace.assignment_source import current_route_configurations

    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text("# synthetic authority\n")
    monkeypatch.setattr(native, "discover", lambda root: snapshot)
    profile = {
        "name": "worker",
        "provider": "openai",
        "model_family": "fixture-model",
        "transports": [{"kind": "internal", "method": "internal"}, {"kind": "process", "method": "cli", "command": [sys.executable]}],
    }
    policy = SimpleNamespace(
        current_target="worker", manual_transport_policy="allowed", transport_authority="automatic", safe_to_auto_run_commands=True
    )
    original_policy = vars(policy).copy()
    result = current_route_configurations(tmp_path, [profile], policy, {"id": "work", "revision": "1"})
    assert [row["configuration"]["execution"]["adapter"]["kind"] for row in result["candidates"]] == ["current-host", "process", "native"]
    assert all(row["eligible"] for row in result["candidates"])
    assert vars(policy) == original_policy
    policy.safe_to_auto_run_commands = False
    monkeypatch.setattr(native, "discover", lambda root: pytest.fail("unsafe peers must not probe"))
    result = current_route_configurations(tmp_path, [profile], policy, {"id": "work", "revision": "1"})
    assert [row["eligible"] for row in result["candidates"]] == [True, False]


def test_ephemeral_is_mode_specific_and_not_restartable(snapshot):
    snapshot["parameters"].append("ephemeral")
    snapshot["ephemeral_modes"] = ["fresh", "fork"]
    fresh = selection(snapshot, parameters={"model": "fixture-model", "ephemeral": True})
    native.validate_selection(snapshot, fresh)
    with pytest.raises(native.ProviderError, match="ephemeral-continuity-unavailable"):
        native.validate_selection(snapshot, {**fresh, "mode": "resume", "reference": "opaque"})
    with pytest.raises(native.ProviderError, match="parameter-unsupported"):
        native.validate_selection(snapshot, {**fresh, "parameters": {"model": "fixture-model", "ephemeral": "true"}})


def test_discovery_offers_disposable_and_persistent_peers(tmp_path, monkeypatch, snapshot):
    snapshot["parameters"].append("ephemeral")
    snapshot["ephemeral_modes"] = ["fresh", "fork"]
    monkeypatch.setattr(native, "discover", lambda root: snapshot)
    profile = {"provider": "openai", "model_family": "fixture-model"}
    offers = native.discovered_transports(tmp_path, profile)
    assert [row["parameters"].get("ephemeral") for row in offers] == [None, True]
    assert profile == {"provider": "openai", "model_family": "fixture-model"}


def test_native_source_binding_ignores_unrelated_local_preferences(tmp_path):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text('[delegation]\ntransport_authority = "automatic"\n')
    before = native._source_revision(tmp_path, "worker")
    source.write_text('[delegation]\ntransport_authority = "automatic"\n[editor]\ncolor = "blue"\n')
    assert native._source_revision(tmp_path, "worker") == before
    source.write_text('[delegation]\ntransport_authority = "manual"\n[editor]\ncolor = "blue"\n')
    assert native._source_revision(tmp_path, "worker") != before


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


@pytest.mark.parametrize("change", [{"live": True}, {"packet_integrity": "foreign"}, {"run_id": "other"}])
def test_cleanup_requires_exact_released_custody(tmp_path, monkeypatch, change):
    path = native._custody_path(tmp_path, "owned")
    custody = {
        "kind": "agentic-workspace/native-transport-custody/v1",
        "run_id": "owned",
        "adapter": "codex-app-server/v1",
        "packet_integrity": "sealed",
        "live": False,
        "reference": "opaque",
    }
    native._write(path, {**custody, **change})
    native._write(
        path.with_name("state.json"), {"run_id": "owned", "current_state": "closed", "assignment": {"packet_integrity": "sealed"}}
    )
    monkeypatch.setattr(native, "discover", lambda root: pytest.fail("unowned cleanup must not reach provider"))
    assert native.cleanup_owned_run(tmp_path, "owned")["status"] == "deferred"
    assert native.cleanup_owned_run(tmp_path, "../foreign")["status"] == "deferred"


def test_cleanup_archives_once_without_deleting_assignment(tmp_path, monkeypatch, snapshot):
    path = native._custody_path(tmp_path, "owned")
    native._write(
        path,
        {
            "kind": "agentic-workspace/native-transport-custody/v1",
            "run_id": "owned",
            "adapter": "codex-app-server/v1",
            "packet_integrity": "sealed",
            "live": False,
            "reference": "opaque",
        },
    )
    native._write(
        path.with_name("state.json"), {"run_id": "owned", "current_state": "dispatch-failed", "assignment": {"packet_integrity": "sealed"}}
    )
    before = path.with_name("state.json").read_bytes()
    lineage = tmp_path / ".agentic-workspace/local/transport-continuations/current.json"
    native._write(lineage, {"reference": "opaque", "semantic_scope": "slice"})
    calls = []
    monkeypatch.setattr(native, "discover", lambda root: snapshot)
    monkeypatch.setattr(native, "archive_reference", lambda facts, ref: calls.append(ref) or "archived")
    assert native.cleanup_owned_run(tmp_path, "owned")["status"] == "archived"
    assert native.cleanup_owned_run(tmp_path, "owned")["reused"] is True
    assert calls == ["opaque"]
    assert path.with_name("state.json").read_bytes() == before
    assert json.loads(lineage.read_text()) == {"reference": "", "semantic_scope": "slice", "unavailable": "archived"}


def test_cleanup_protects_released_sibling_awaiting_admission(tmp_path, monkeypatch):
    for run, state in (("owned", "closed"), ("sibling", "awaiting-admission")):
        path = native._custody_path(tmp_path, run)
        native._write(
            path,
            {
                "kind": "agentic-workspace/native-transport-custody/v1",
                "run_id": run,
                "adapter": "codex-app-server/v1",
                "packet_integrity": "sealed",
                "live": False,
                "reference": "shared",
            },
        )
        native._write(path.with_name("state.json"), {"run_id": run, "current_state": state, "assignment": {"packet_integrity": "sealed"}})
    monkeypatch.setattr(native, "discover", lambda root: pytest.fail("conversation still needed"))
    assert native.cleanup_owned_run(tmp_path, "owned")["reason"] == "native-cleanup-conversation-still-needed"


def test_dispatch_failure_retains_owned_reference_and_prevents_repeat(tmp_path, monkeypatch, snapshot):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text("# authority")
    monkeypatch.setattr(native, "discover", lambda root: snapshot)
    execution = {
        "source_revision": native._source_revision(tmp_path),
        "adapter": {"adapter": "codex-app-server/v1", "parameters": {"model": "fixture-model"}},
        "continuity": selection(snapshot),
        "target_identity": "worker",
        "semantic_scope": "slice",
        "semantic_revision": "r1",
    }
    configuration = {
        "execution": execution,
        "target": "worker",
        "transport": "cli",
        **dict.fromkeys(("authorized", "safe", "constructible", "current", "concurrency_available"), True),
    }
    packet = _assignment_seal_host_native_packet(
        {
            "assignment_id": "a",
            "assignment_revision": "r",
            "run_id": "owned",
            "target": "worker",
            "transport": "cli",
            "assignment_identity": {"dispatch_adapter": {"execution_configuration": configuration}},
            "return_contract": {"required_identity": {}},
        }
    )
    calls = []

    def fail(*args, **kwargs):
        calls.append(True)
        assert json.loads(kwargs["worker_environment"]["AGENTIC_WORKSPACE_DELEGATED_WORKER_KERNEL"])["assignment"]["assignment_id"] == "a"
        kwargs["on_thread"]("owned-provider-reference")
        kwargs["on_closed"]()
        raise native.ProviderError(
            "provider-turn-failed", metrics={"kind": "agentic-workspace/assignment-transport-metrics/v1", "effective_input_tokens": 13}
        )

    monkeypatch.setattr(native, "execute", fail)
    result = native.dispatch_packet(tmp_path, packet, "not retained")
    assert result["status"] == "blocked"
    assert result["context_cost"]["effective_input_tokens"] == 13
    custody = json.loads(native._custody_path(tmp_path, "owned").read_text())
    assert custody["reference"] == "owned-provider-reference" and custody["live"] is False
    assert "not retained" not in json.dumps(custody)
    assert native.dispatch_packet(tmp_path, packet, "not retained")["reason"] == "native-run-already-attempted"
    assert calls == [True]


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
        {"eligible": True, "configuration": {"id": kind, "target": "worker", "transport": "cli", "execution": {"adapter": transport}}}
        for kind, transport in zip(("process", "native"), profile["transports"], strict=True)
    ]
    decision = assignment_decision_from_policy(
        assignment_policy={}, runtime_resolution={"profile_recommendations": [profile]}, target_evidence={}
    )
    candidate = decision["candidate_scores"][0]
    assert [row["execution_configuration"]["id"] for row in candidate["transport_options"]] == ["process", "native"]
    assert candidate["selected_execution_configuration"]["id"] == "process"
    policy = {"assignment_policy": {"value": "required-best-fit"}, "binding": {"enforceable": True}}
    chosen = profile["execution_configurations"][1]["configuration"]
    selected = assignment_decision_from_policy(
        assignment_policy=policy,
        runtime_resolution={"profile_recommendations": [profile], "capability_context": {"task_class": "implementation"}},
        target_evidence={},
        execution_choice=chosen,
    )
    assert selected["selected_execution_configuration"] == chosen
    assert selected["assignment_decision_revision"] != decision["assignment_decision_revision"]
    profile["proof_requirements"] = ["required-proof-missing"]
    with pytest.raises(ValueError, match="owner-ineligible"):
        assignment_decision_from_policy(
            assignment_policy=policy, runtime_resolution={"profile_recommendations": [profile]}, target_evidence={}, execution_choice=chosen
        )


@pytest.mark.parametrize("prohibition", ["safety", "authority", "capability", "proof", "human-control"])
def test_hard_ineligible_native_route_does_not_probe_provider(tmp_path, monkeypatch, prohibition):
    from agentic_workspace.assignment_source import current_route_configurations

    def unexpected(*args, **kwargs):
        pytest.fail("hard-ineligible route must not invoke native discovery")

    monkeypatch.setattr(native, "configuration_offers", unexpected)
    policy = SimpleNamespace(
        current_target="local", manual_transport_policy="allowed", transport_authority="automatic", safe_to_auto_run_commands=True
    )
    profile = {"name": "worker", "transports": [{"kind": "native", "method": "cli"}]}
    if prohibition == "safety":
        policy.safe_to_auto_run_commands = False
    elif prohibition == "authority":
        policy.transport_authority = "manual-only"
    elif prohibition == "capability":
        profile["capability_mismatch"] = True
    elif prohibition == "proof":
        profile["proof_requirements"] = ["required-proof-missing"]
    else:
        profile["human_control_modes"] = ["off"]
    offers = current_route_configurations(tmp_path, [profile], policy, {"id": "work", "revision": "1"})
    assert [row["configuration"]["transport"] for row in offers["candidates"]] == ["manual"]


def test_configuration_authority_tracks_relevant_source_and_executable(tmp_path, monkeypatch):
    import sys
    from dataclasses import asdict

    from agentic_workspace.assignment_source import current_route_configurations, validate_current_configuration
    from agentic_workspace.config import load_workspace_config

    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    original = """schema_version = 1
[safety]
safe_to_auto_run_commands = true
[delegation]
transport_authority = "automatic"
assignment_policy = "required-best-fit"
[delegation_targets.worker]
target_id = "host:worker"
target_revision = "1"
strength = "strong"
location = "external"
transports = [{kind = "process", command = [EXE]}]
""".replace("EXE", json.dumps(sys.executable))
    source.write_text(original)
    config = load_workspace_config(target_root=tmp_path)
    profiles = [asdict(p) for p in config.local_override.delegation_targets]
    work = {"id": "work", "revision": "1"}
    offers = current_route_configurations(tmp_path, profiles, config.local_override, work)
    configuration = offers["candidates"][0]["configuration"]
    choice = {"revision": offers["revision"], "candidate": configuration["id"]}
    assert current_route_configurations(tmp_path, profiles, config.local_override, work, choice)["selected"] == configuration
    validate_current_configuration(tmp_path, configuration)
    source.write_text(original + '\n[workspace]\ncli_invoke = "unrelated-launcher"\n')
    validate_current_configuration(tmp_path, configuration)
    source.write_text(original.replace('target_revision = "1"', 'target_revision = "2"'))
    with pytest.raises(ValueError, match="source-stale"):
        validate_current_configuration(tmp_path, configuration)
    assert (
        current_route_configurations(tmp_path, profiles, config.local_override, work, choice)["reason_code"]
        == "assignment-configuration-choice-stale"
    )
    source.write_text(original)
    from agentic_workspace import workspace_runtime_core as runtime

    kwargs = {"config": config, "changed_paths": ["feature.py"], "task_text": "Repair the calculation."}
    baseline = runtime._current_assignment_selection(**kwargs)[4]
    offer = baseline["execution_configurations"]
    monkeypatch.setattr(
        runtime,
        "target_evidence_posture",
        lambda **_: {
            "suitability": [
                {
                    "target": "worker",
                    "context_key": baseline["context_key"],
                    "route_effect": "strong-review-required",
                    "record_count": 1,
                    "supporting_record_ids": ["admitted-contextual-observation"],
                }
            ]
        },
    )
    current = runtime._current_assignment_selection(**kwargs)[4]["execution_configurations"]
    assert current["feasibility_revision"] == offer["feasibility_revision"]
    assert current["revision"] != offer["revision"]
    with pytest.raises(ValueError, match="configuration-choice-stale"):
        runtime._current_assignment_selection(**kwargs, execution_choice={"revision": offer["revision"], "candidate": configuration["id"]})


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
    environments = []

    class Connection:
        def __init__(self, executable, *, environment=None):
            environments.append(environment)
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
    worker_environment = {"AGENTIC_WORKSPACE_DELEGATED_WORKER_KERNEL": '{"assignment":{"assignment_id":"worker"}}'}
    result = native.execute(tmp_path, snapshot, choice, "bounded input", {"type": "object"}, worker_environment=worker_environment)
    assert environments == [worker_environment]
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
