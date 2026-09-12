"""#2986/#2987/#3059: exact carriage is disposable transport, not authority."""

from __future__ import annotations

import copy
import hashlib
import json
from time import perf_counter

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def proposal(surface, binary, native, root):
    context = {"target": str(root), "task": "Set the configured invocation"}
    initial = consume(surface, binary, native, context)
    initial = consume(surface, binary, native, {**context, "request": initial["configuration_write"]["creation_discovery_request"]})
    request = next(r for r in initial["configuration_write"]["creation_requests"] if r["arguments"]["key"] == "workspace.cli_invoke")
    request["arguments"] = {"source": ".agentic-workspace/config.toml", "key": "workspace.cli_invoke", "value": "aw-local"}
    context["request"] = request
    return context


def size(value):
    return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode())


def rehash(carrier, entry):
    value = {"kind": carrier["kind"], "context": carrier["context"], "selector": entry["selector"], "envelope": entry["envelope"]}
    entry["reference"] = (
        "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    )
    return entry["reference"]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_skill_consumer_uses_compact_reference_and_new_answer_only(tmp_path, shared_core_binary, native_cli, surface):
    context = proposal(surface, shared_core_binary, native_cli, tmp_path)
    compact = consume(surface, shared_core_binary, native_cli, {**context, "projection": "compact"})
    selected = compact["detail_refs"]["/decision_packet/decision_request"]
    # The skill/host retains the explicit work and substantive proposal. It
    # supplies only a reference and judgment, not immutable owner identity.
    answered = consume(
        surface,
        shared_core_binary,
        native_cli,
        {**context, "reference": selected, "answer": "authorize-write", "projection": "carried"},
        reference_helper=surface in {"python", "typescript"},
    )
    action = answered["view"]["decision_packet"]["primary_action"]
    result = consume(surface, shared_core_binary, native_cli, {"invocation": answered["carriage"], "reference": action["reference"]})
    assert result["effect_outcome"]["status"] == "committed"
    assert result["continuation"]["retry_effect"] is False
    # A lost disposable carrier recovers through fresh current owners.
    fresh = consume(surface, shared_core_binary, native_cli, result["continuation"]["reentry"]["context"])
    assert fresh["configuration"]["cli_invoke"] == "aw-local"
    before = (tmp_path / ".agentic-workspace/config.toml").read_bytes()
    replay = consume(
        surface, shared_core_binary, native_cli, {"invocation": answered["carriage"], "reference": action["reference"]}, allow_failure=True
    )
    assert replay["effect_outcome"]["status"] == "rejected-before-effect"
    assert replay["continuation"]["retry_effect"] is False
    assert (tmp_path / ".agentic-workspace/config.toml").read_bytes() == before


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_compact_detail_reference_rejects_forgery_and_changed_work(tmp_path, shared_core_binary, native_cli, surface):
    context = {"target": str(tmp_path), "task": "Inspect work"}
    compact = consume(surface, shared_core_binary, native_cli, {**context, "projection": "compact"})
    ref = compact["detail_refs"]["/current_work"]
    detail = consume(surface, shared_core_binary, native_cli, {**context, "reference": ref})
    full = consume(surface, shared_core_binary, native_cli, context)
    assert detail["value"] == full["current_work"]
    assert detail["authority"] == "detail-only"
    for altered in [{"task": "Different work"}, {"changed": ["different.rs"]}, {"reference": "sha256:" + "0" * 64}]:
        with pytest.raises(AssertionError, match="stale operating reference"):
            consume(surface, shared_core_binary, native_cli, {**context, "reference": ref, **altered})


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_exact_answer_and_action_carriage_preserve_full_effects(tmp_path, shared_core_binary, native_cli, surface):
    context = proposal(surface, shared_core_binary, native_cli, tmp_path)
    full = consume(surface, shared_core_binary, native_cli, context)
    carried = consume(surface, shared_core_binary, native_cli, {**context, "projection": "carried"})
    view = carried["view"]
    assert view["decision_packet"]["blockers"] == full["decision_packet"]["blockers"]
    assert view["decision_packet"]["claim_boundary"] == full["decision_packet"]["claim_boundary"]
    question = view["decision_packet"]["decision_request"]
    assert question["request_material"] == full["decision_packet"]["decision_request"]["response_request"]["arguments"]
    assert question["material"] == full["configuration_write"]["proposal"]
    assert "response_request" not in question
    assert size(view) < size(full)
    # Ordinary compact output without a host still includes the exact executable
    # request, rather than forcing a compensating detail call.
    compact = consume(surface, shared_core_binary, native_cli, {**context, "projection": "compact"})
    assert compact["decision_packet"]["decision_request"] == full["decision_packet"]["decision_request"]
    before = copy.deepcopy(carried)
    answered = consume(
        surface,
        shared_core_binary,
        native_cli,
        {
            "target": context["target"],
            "request": carried["carriage"],
            "reference": question["reference"],
            "answer": "authorize-write",
            "projection": "carried",
        },
    )
    assert carried == before
    conventional = copy.deepcopy(full["decision_packet"]["decision_request"]["response_request"])
    conventional["arguments"]["answer"] = "authorize-write"
    expected = consume(surface, shared_core_binary, native_cli, {**context, "request": conventional})
    compact_action = consume(surface, shared_core_binary, native_cli, {**context, "request": conventional, "projection": "compact"})
    assert compact_action["decision_packet"]["primary_action"] == expected["decision_packet"]["primary_action"]
    assert compact_action["decision_packet"]["claim_boundary"] == expected["decision_packet"]["claim_boundary"]
    action = answered["view"]["decision_packet"]["primary_action"]
    exact = next(e["envelope"] for e in answered["carriage"]["envelopes"] if e["reference"] == action["reference"])
    assert exact == expected["decision_packet"]["primary_action"]
    # This is one known, already authorized configuration write, not a general
    # primary_action loop. A host can connect this settled step without a model
    # turn to copy the returned envelope. All effect admission stays in Rust.
    result = consume(
        surface,
        shared_core_binary,
        native_cli,
        {
            "invocation": answered["carriage"],
            "reference": action["reference"],
        },
    )
    assert result["status"] == "applied"
    assert result["effects"] == exact["effects"]
    assert result["effect_outcome"]["status"] == "committed"
    assert result["continuation"]["status"] == "current"
    assert result["continuation"]["retry_effect"] is False
    assert 'cli_invoke = "aw-local"' in (tmp_path / ".agentic-workspace/config.toml").read_text()
    continuation_context = result["continuation"]["reentry"]["context"]
    assert continuation_context["changed"] == [".agentic-workspace/config.toml"]
    # Compare the same post-effect work, including the owner's newly changed
    # source; resolving the former scope is a different currentness oracle.
    fresh = consume(surface, shared_core_binary, native_cli, continuation_context)
    assert fresh["configuration"]["cli_invoke"] == "aw-local"
    assert result["continuation"]["result"] == fresh
    # No carrier or registry has been written into repository truth.
    assert not list(tmp_path.rglob("*carriage*"))


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_carriage_fails_closed_and_exact_detail_is_inspectable(tmp_path, shared_core_binary, native_cli, surface):
    context = proposal(surface, shared_core_binary, native_cli, tmp_path)
    carried = consume(surface, shared_core_binary, native_cli, {**context, "projection": "carried"})
    reference = carried["view"]["decision_packet"]["decision_request"]["reference"]
    call = {"request": carried["carriage"], "reference": reference, "answer": "authorize-write"}
    for mutation in [
        {"reference": "sha256:" + "0" * 64},
        {"task": "Different work"},
        {"changed": ["different.md"]},
        {"answer": {"answer": "authorize-write", "value": "forged"}},
    ]:
        with pytest.raises(AssertionError):
            consume(surface, shared_core_binary, native_cli, call | mutation)
    altered = copy.deepcopy(carried["carriage"])
    next(e for e in altered["envelopes"] if e["reference"] == reference)["envelope"]["response_request"]["arguments"]["value"] = "forged"
    with pytest.raises(AssertionError, match="altered carried envelope"):
        consume(surface, shared_core_binary, native_cli, call | {"request": altered})
    forged = next(e for e in altered["envelopes"] if e["reference"] == reference)
    forged_ref = rehash(altered, forged)
    with pytest.raises(AssertionError, match="not owner-issued"):
        consume(surface, shared_core_binary, native_cli, call | {"request": altered, "reference": forged_ref})
    detail_ref = carried["view"]["detail_refs"]["/capability_contract"]
    detail = consume(surface, shared_core_binary, native_cli, {"request": carried["carriage"], "reference": detail_ref})
    full = consume(surface, shared_core_binary, native_cli, context)
    assert detail["value"] == full["capability_contract"]
    assert detail["authority"] == "detail-only"
    assert not (tmp_path / ".agentic-workspace/config.toml").exists()
    source = tmp_path / ".agentic-workspace/config.toml"
    source.parent.mkdir(exist_ok=True)
    source.write_text('schema_version=1\n[workspace]\ncli_invoke="changed"\n')
    with pytest.raises(AssertionError):
        consume(surface, shared_core_binary, native_cli, call)
    assert "changed" in source.read_text()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_rehashed_forged_and_stale_action_carriage_cannot_write(tmp_path, shared_core_binary, native_cli, surface):
    context = proposal(surface, shared_core_binary, native_cli, tmp_path)
    first = consume(surface, shared_core_binary, native_cli, context | {"projection": "carried"})
    answered = consume(
        surface,
        shared_core_binary,
        native_cli,
        {
            "request": first["carriage"],
            "reference": first["view"]["decision_packet"]["decision_request"]["reference"],
            "answer": "authorize-write",
            "projection": "carried",
        },
    )
    original = answered["view"]["decision_packet"]["primary_action"]["reference"]
    for change in ("envelope", "context", "target"):
        carrier = copy.deepcopy(answered["carriage"])
        item = next(e for e in carrier["envelopes"] if e["reference"] == original)
        if change == "envelope":
            item["envelope"]["arguments"]["post_revision"] = "forged"
        elif change == "context":
            carrier["context"]["task"] = "A different task"
        else:
            other = tmp_path / "other"
            other.mkdir()
            carrier["context"]["target"] = str(other)
        ref = rehash(carrier, item)
        with pytest.raises(AssertionError):
            consume(surface, shared_core_binary, native_cli, {"invocation": carrier, "reference": ref})
    source = tmp_path / ".agentic-workspace/config.toml"
    assert not source.exists()
    source.parent.mkdir(exist_ok=True)
    source.write_text('schema_version=1\n[workspace]\ncli_invoke="preserve-current"\n')
    with pytest.raises(AssertionError):
        consume(surface, shared_core_binary, native_cli, {"invocation": answered["carriage"], "reference": original})
    assert "preserve-current" in source.read_text()


def test_operating_journey_measurement(tmp_path, shared_core_binary, native_cli):
    direct = {"target": str(tmp_path), "task": "Inspect this empty target"}
    direct_full = consume("json", shared_core_binary, native_cli, direct)
    direct_compact = consume("json", shared_core_binary, native_cli, direct | {"projection": "compact"})
    for field in ("status", "blockers", "claim_boundary", "primary_action", "decision_request"):
        assert direct_compact["decision_packet"][field] == direct_full["decision_packet"][field]
    assert size(direct_compact) < size(direct_full)
    context = proposal("json", shared_core_binary, native_cli, tmp_path)
    full = consume("json", shared_core_binary, native_cli, context)
    carried = consume("json", shared_core_binary, native_cli, context | {"projection": "carried"})
    question = carried["view"]["decision_packet"]["decision_request"]
    old_answer = copy.deepcopy(full["decision_packet"]["decision_request"]["response_request"])
    old_answer["arguments"]["answer"] = "authorize-write"
    began = perf_counter()
    action = consume("json", shared_core_binary, native_cli, context | {"request": old_answer})["decision_packet"]["primary_action"]
    full_answer_ms = (perf_counter() - began) * 1000
    began = perf_counter()
    consume(
        "json",
        shared_core_binary,
        native_cli,
        {
            "request": carried["carriage"],
            "reference": question["reference"],
            "answer": "authorize-write",
            "projection": "carried",
        },
    )
    carried_answer_ms = (perf_counter() - began) * 1000
    baseline = size({**context, "request": old_answer}) + size({"target": context["target"], "task": context["task"], "invocation": action})
    model_reply = {"reference": question["reference"], "answer": "authorize-write"}
    measurement = {
        "direct_full_bytes": size(direct_full),
        "direct_compact_bytes": size(direct_compact),
        "full_decision_bytes": size(full),
        "carried_view_bytes": size(carried["view"]),
        "adapter_local_carriage_bytes": size(carried["carriage"]),
        "baseline_model_protocol_bytes": baseline,
        "carried_model_protocol_bytes": size(model_reply),
        "baseline_model_turns_answer_then_copy_action": 2,
        "carried_model_turns_answer_then_known_host_write": 1,
        "required_detail_calls": 0,
        "baseline_public_calls_through_write": 3,
        "carried_public_calls_through_write": 3,
        "answer_internal_resolutions_full_then_carried": [1, 2],
        "answer_elapsed_ms_full_then_carried_single_sample": [round(full_answer_ms, 1), round(carried_answer_ms, 1)],
        "protocol_repairs": 0,
        "human_decisions_full_then_carried": [1, 1],
        "post_invoke_resolve_eliminated": False,
        "new_durable_registry_files": 0,
        "token_counts": "not measured",
        "host_effective_context": "not measured",
    }
    print(json.dumps(measurement, sort_keys=True))
    assert size(model_reply) < baseline
    assert size(carried["view"]) < size(full)


def test_carried_diagnostics_follow_explicit_work_target(tmp_path, shared_core_binary, native_cli, monkeypatch):
    from tests.test_native_maintainer_logging import configured, events

    configured(tmp_path)
    monkeypatch.setenv("AW_SESSION_LOGICAL_IDENTITY", "carriage-fixture")
    context = proposal("json", shared_core_binary, native_cli, tmp_path)
    offered = consume("json", shared_core_binary, native_cli, context | {"projection": "carried"})
    before = len(events(tmp_path))
    consume(
        "json",
        shared_core_binary,
        native_cli,
        {
            "request": offered["carriage"],
            "reference": offered["view"]["decision_packet"]["decision_request"]["reference"],
            "answer": "authorize-write",
        },
    )
    recorded = events(tmp_path)
    assert len(recorded) == before + 1
    assert recorded[-1]["payload"]["entry"]["target"] == "<target>"
    assert recorded[-1]["authoritative"] is False
