"""Effect facts and directly usable continuations share the Rust public boundary."""

import hashlib
import json

import pytest
from tests.test_native_operating_carriage import proposal
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("surface", ["native", "native-yaml", "json", "python", "typescript"])
@pytest.mark.parametrize("projection", ["full", "compact", "carried"])
def test_invoke_returns_current_projection_without_another_entry(tmp_path, shared_core_binary, native_cli, surface, projection):
    from tests.native_instruction_support import _admit, _write

    guidance = "Review the configuration source after it changes."
    source = _write(
        tmp_path,
        "configuration",
        "---\npaths: [.agentic-workspace/config.toml]\nchecks:\n  - run: echo configuration-reviewed\n---\n" + guidance,
    )
    delivery = {}
    if surface == "json" and projection == "full":
        delivery["available_sources"] = [
            {
                "reference": source.relative_to(tmp_path).as_posix(),
                "revision": "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest(),
                "extent": "whole-source",
            }
        ]
    _admit(tmp_path)
    context = proposal(surface, shared_core_binary, native_cli, tmp_path)
    offered = consume(surface, shared_core_binary, native_cli, context | {"projection": "carried"})
    assert guidance not in json.dumps(offered["view"]["decision_packet"].get("material", {}))
    selected = consume(
        surface,
        shared_core_binary,
        native_cli,
        {
            "request": offered["carriage"],
            "reference": offered["view"]["decision_packet"]["decision_request"]["reference"],
            "answer": "authorize-write",
            "projection": "carried",
        },
    )
    result = consume(
        surface,
        shared_core_binary,
        native_cli,
        {
            "invocation": selected["carriage"],
            "reference": selected["view"]["decision_packet"]["primary_action"]["reference"],
            "projection": projection,
            **delivery,
        },
    )
    assert result["effect_outcome"]["status"] == "committed"
    continuation = result["continuation"]
    assert continuation["status"] == "current"
    assert continuation["retry_effect"] is False
    assert continuation["context"]["changed"] == [".agentic-workspace/config.toml"]
    # This fresh call is the correctness oracle, not a required operating call.
    fresh = consume(
        surface,
        shared_core_binary,
        native_cli,
        {
            **continuation["reentry"]["context"],
            "projection": projection,
            **delivery,
        },
    )
    assert continuation["result"] == fresh
    packet = fresh["view"]["decision_packet"] if projection == "carried" else fresh["decision_packet"]
    if delivery:
        instruction = packet["material"]["scoped-instructions"][0]
        assert instruction["delivery"]["status"] == "caller-held"
        assert "guidance" not in instruction
    else:
        assert guidance in json.dumps(packet["material"])
    assert "configuration-reviewed" in json.dumps(packet)
    assert packet["primary_action"] is None  # Return control; no invented next mutation.
    if projection == "carried":
        # The next exact optional detail remains usable with no reconstructed context.
        detailed = consume(
            surface,
            shared_core_binary,
            native_cli,
            {
                "request": fresh["carriage"],
                "reference": fresh["view"]["detail_refs"]["/configuration"],
            },
        )
        assert detailed["value"]["cli_invoke"] == "aw-local"
    assert ("next_decision" in result) == (projection == "full")
    if projection == "full":
        assert result["next_decision"] == packet
    if surface == "json" and projection == "carried":
        # Explicit fixture trace: baseline asks the model to copy its exact
        # authorized action and issue post-effect entry. The host version only
        # asks for the bounded authorization answer; no subsequent action loop.
        exact = next(e["envelope"] for e in selected["carriage"]["envelopes"] if e["selector"] == "/decision_packet/primary_action")
        question = next(e["envelope"] for e in offered["carriage"]["envelopes"] if e["selector"] == "/decision_packet/decision_request")
        baseline_answer = {**question["response_request"]}
        baseline_answer["arguments"] = {**baseline_answer["arguments"], "answer": "authorize-write"}

        def size(value):
            return len(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode())

        baseline_bytes = size(baseline_answer) + size(exact) + size(continuation["reentry"]["context"])
        carried_bytes = size(
            {"reference": offered["view"]["decision_packet"]["decision_request"]["reference"], "answer": "authorize-write"}
        )
        print(
            json.dumps(
                {
                    "journey": "authorized-config-write-through-current-continuation",
                    "baseline_public_calls": 4,
                    "carried_public_calls": 3,
                    "baseline_model_interactions": 3,
                    "carried_model_interactions": 1,
                    "baseline_model_protocol_bytes": baseline_bytes,
                    "carried_model_protocol_bytes": carried_bytes,
                    "post_invoke_start_calls": [1, 0],
                    "required_detail_calls": [0, 0],
                    "judgments": [1, 1],
                    "provider_tokens": "not-measured",
                }
            )
        )
        assert carried_bytes < baseline_bytes


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_unknown_invocation_is_rejected_before_effect_with_exact_reentry(tmp_path, shared_core_binary, native_cli, surface):
    context = {"target": str(tmp_path), "task": "Exact work", "changed": ["owned.txt"]}
    result = consume(
        surface, shared_core_binary, native_cli, context | {"invocation": {"operation_id": "forged.write"}}, allow_failure=True
    )
    assert result["status"] == "rejected"
    assert result["effect_outcome"]["status"] == "rejected-before-effect"
    assert result["continuation"]["reentry"]["context"] == context
    assert not list(tmp_path.iterdir())
