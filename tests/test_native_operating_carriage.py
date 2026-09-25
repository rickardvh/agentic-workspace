"""#2986/#2987/#3059: exact carriage is disposable transport, not authority."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
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


def test_shell_carriage_keeps_transport_outside_model_output(tmp_path, shared_core_binary, native_cli):
    """Execute the maintained shell recipe at the actual stdout boundary."""
    shell = shutil.which("pwsh")
    if shell is None:
        pytest.skip("PowerShell shell-consumer transport requires pwsh")
    context = proposal("native", shared_core_binary, native_cli, tmp_path)
    request = tmp_path / "proposal.json"
    request.write_text(json.dumps(context["request"]), encoding="utf-8")
    guide = (Path(__file__).resolve().parents[1] / ".agentic-workspace/skills/workspace-startup/references/owners.md").read_text()
    examples = [block.split("```", 1)[0] for block in guide.split("```powershell\n")[1:]]
    # The ordinary entry example has no proposal. This caller already holds one;
    # add only that existing request, retaining the exact documented transport.
    script = tmp_path / "consumer.ps1"
    script.write_text(
        "param($aw, $task, $carrier, $request)\n$changed = @()\n"
        + examples[0].replace("--projection carried", "--input $request --projection carried")
        + "\n$reference = $r.view.decision_packet.decision_request.reference\n"
        + "$answer = '\"authorize-write\"'\n"
        + examples[1],
        encoding="utf-8",
    )
    carrier = tmp_path / "carrier.json"
    result = subprocess.run(
        [shell, "-NoProfile", "-File", str(script), str(native_cli), context["task"], str(carrier), str(request)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    views = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert len(views) == 2
    assert all("carriage" not in view and "envelopes" not in view for view in views)
    saved = json.loads(carrier.read_text(encoding="utf-8-sig"))
    assert saved["envelopes"]
    assert views[-1]["decision_packet"]["primary_action"]["reference"]
    assert not (tmp_path / ".agentic-workspace/config.toml").exists()
    full = consume("native", shared_core_binary, native_cli, context)
    compact = consume("native", shared_core_binary, native_cli, {**context, "projection": "compact"})
    print(
        json.dumps(
            {
                "full_bytes": size(full),
                "compact_bytes": size(compact),
                "shell_visible_bytes": len(result.stdout.encode()),
                "carrier_bytes": carrier.stat().st_size,
                "shell_public_calls": 2,
                "detail_reads": 0,
                "immutable_fields_transcribed": 0,
            }
        )
    )
    # A failed command must stop before consuming output or replacing good data.
    before = carrier.read_bytes()
    failed = subprocess.run(
        [shell, "-NoProfile", "-File", str(script), str(native_cli), context["task"], str(carrier), str(tmp_path / "missing.json")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert failed.returncode != 0 and not failed.stdout.strip()
    assert carrier.read_bytes() == before


def test_public_owner_identity_uses_existing_question_and_effect_boundary(tmp_path, shared_core_binary, native_cli):
    context = proposal("native", shared_core_binary, native_cli, tmp_path)
    current = consume("native", shared_core_binary, native_cli, context)
    question = current["decision_packet"]["decision_request"]["response_request"]
    identity = f"owner:question:{question['owner']}:{question['id']}"
    selected = consume("native", shared_core_binary, native_cli, {**context, "reference": identity})
    assert selected["status"] == "current"
    assert not (tmp_path / ".agentic-workspace/config.local.toml").exists()
    answered = consume(
        "native",
        shared_core_binary,
        native_cli,
        {**context, "reference": selected["reference"], "answer": "authorize-write", "projection": "carried"},
    )
    action = answered["view"]["decision_packet"]["primary_action"]
    exact_context = answered["carriage"]["context"]
    stable = f"owner:action:{action['source_owner']}:{action['operation_id']}"
    resolved = consume("native", shared_core_binary, native_cli, {**exact_context, "reference": stable})
    for field in ("arguments", "effects", "authority"):
        assert resolved["value"][field] == action[field]
    result = consume("native", shared_core_binary, native_cli, {"invocation": answered["carriage"], "reference": resolved["reference"]})
    assert result["effect_outcome"]["status"] == "committed"
    assert result["continuation"]["retry_effect"] is False


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
    source.write_text('[workspace]\ncli_invoke="changed"\n')
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
    source.write_text('[workspace]\ncli_invoke="preserve-current"\n')
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
    assert offered["view"]["session_capture"] == {"status": "capturing", "authoritative": False}
    assert "session_capture" not in json.dumps(offered["carriage"])
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


def test_delivery_is_not_satisfaction_and_opaque_sources_redeliver(tmp_path, shared_core_binary, native_cli):
    (tmp_path / "AGENTS.md").write_text("Read current repository instructions.\n" * 45)
    directory = tmp_path / ".agentic-workspace/instructions"
    directory.mkdir(parents=True)
    source = directory / "policy.md"
    source.write_text("---\nreconcile: [guide.md]\n---\n" + "Preserve policy.\n" * 40)
    (tmp_path / ".agentic-workspace/config.toml").write_text('[workspace]\nagent_instructions_file="AGENTS.md"\n')
    (tmp_path / "guide.md").write_text("Canonical guide")
    context = {"target": str(tmp_path), "task": "Inspect current work", "projection": "compact"}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    first = call()
    startup = first["decision_packet"]["material"]["startup-adapter"]
    assert startup["source_material"]["extent"] == "whole-source"
    instruction = first["decision_packet"]["material"]["scoped-instructions"][0]
    assert instruction["source_material"]["extent"] == "exact-fragment"
    # Ordinary reads identify exact raw bytes without an AW-generated token.
    availability = [
        {
            "reference": str(p.relative_to(tmp_path)).replace("\\", "/"),
            "revision": "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest(),
            "extent": "whole-source",
        }
        for p in (tmp_path / "AGENTS.md", source)
    ]
    direct = call(available_sources=availability, projection="carried")
    assert "available_sources" not in direct["carriage"]["context"]
    material = direct["view"]["decision_packet"]["material"]
    assert material["startup-adapter"]["delivery"]["status"] == "caller-held"
    assert "text" not in material["startup-adapter"]
    assert "guidance" not in material["scoped-instructions"][0]
    for key in ("blockers", "claim_boundary", "primary_action", "status"):
        assert direct["view"]["decision_packet"][key] == first["decision_packet"][key]
    # Distinct CLI input-envelope forwarding risk, not another semantic matrix.
    input_file = tmp_path / "availability.json"
    input_file.write_text(json.dumps({**context, "available_sources": availability}), encoding="utf-8")
    shell = subprocess.run([str(native_cli), "start", "--input", str(input_file)], capture_output=True, text=True, check=True)
    assert json.loads(shell.stdout)["decision_packet"]["material"]["startup-adapter"]["delivery"]["status"] == "caller-held"
    input_file.unlink()
    # A fresh consumer does not inherit availability just because carriage survived.
    reset = call(**direct["carriage"]["context"])
    assert "text" in reset["decision_packet"]["material"]["startup-adapter"]
    refs = first["delivery_refs"]
    same = call(delivered=refs)
    assert len(json.dumps(same)) < len(json.dumps(first))
    print(f"delivery/json: fresh_bytes={len(json.dumps(first))} repeated_bytes={len(json.dumps(same))} extra_roundtrips=0")
    for key in ("blockers", "claim_boundary", "primary_action", "status"):
        assert same["decision_packet"][key] == first["decision_packet"][key]
    assert same["decision_packet"]["material"]["startup-adapter"]["delivery"]["status"] == "already-delivered"
    assert "text" not in same["decision_packet"]["material"]["startup-adapter"]
    source.write_text(source.read_text() + "A new applicable instruction.")
    drift = call(delivered=refs)
    assert drift["decision_packet"]["material"]["scoped-instructions"][0]["guidance"].endswith("A new applicable instruction.")
    assert "text" not in drift["decision_packet"]["material"]["startup-adapter"]
    drift = call(available_sources=availability)
    assert "text" not in drift["decision_packet"]["material"]["startup-adapter"]
    assert drift["decision_packet"]["material"]["scoped-instructions"][0]["guidance"].endswith("A new applicable instruction.")
    (directory / "new.md").write_text("---\nreconcile: [other.md]\n---\nNew source appeared while AW was absent.")
    opaque = call(delivered=refs)
    assert any("New source appeared" in r.get("guidance", "") for r in opaque["decision_packet"]["material"]["scoped-instructions"])
    assert "text" in call()["decision_packet"]["material"]["startup-adapter"]
    assert not (tmp_path / ".agentic-workspace/local").exists()
