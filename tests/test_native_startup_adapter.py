"""Current startup source delivery is distinct from source adoption and proof."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from tests.test_native_planning_create import material as planning_material
from tests.test_native_proof_producer import fixture as proof_fixture
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_configured_startup_text_is_exact_lazy_and_not_custody(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('schema_version=1\n[workspace]\nagent_instructions_file="AGENTS.md"\n')
    source = tmp_path / "AGENTS.md"
    source.write_bytes((ROOT / "AGENTS.md").read_bytes() + b"\nHuman-owned outside-fence instruction.\n")
    original = source.read_bytes()
    context = {"target": str(tmp_path), "task": "Inspect existing source", "changed": ["src/example.rs"]}
    result = consume(surface, shared_core_binary, native_cli, context)
    owner = result["startup_adapter"]
    assert owner["status"] == "source-context-required"
    assert "Human-owned" not in json.dumps(owner)
    assert len(json.dumps(owner)) < 6500
    assert not any(r["field"] == "workspace.agent_instructions_file" for r in result["configuration"]["residuals"])
    assert {"effect:implementation", "claim:complete"} <= set(owner["contribution"]["blockers"][0]["affects"])
    request = owner["requests"][0]
    read = consume(surface, shared_core_binary, native_cli, {**context, "request": request})["startup_adapter"]
    assert read["response"]["text"] == original.decode("utf-8")
    assert read["status"] == "source-context-delivered"
    assert read["contribution"]["blockers"] == []
    assert "no rule satisfaction, proof, acceptance or mutation custody" in read["response"]["authority_boundary"]
    assert source.read_bytes() == original
    assert not (tmp_path / ".agentic-workspace/local").exists()
    # Fresh clients must consume the current source themselves; no persisted read grant.
    assert consume(surface, shared_core_binary, native_cli, context)["startup_adapter"]["status"] == "source-context-required"
    for change in ({"task": "Different work"}, {"changed": ["different.rs"]}):
        with pytest.raises(AssertionError):
            consume(surface, shared_core_binary, native_cli, {**context, **change, "request": request})
    forged = json.loads(json.dumps(request))
    forged["arguments"]["reference"] = "elsewhere.md"
    with pytest.raises(AssertionError, match="outside current configured"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": forged})
    with pytest.raises(AssertionError, match="one current request"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": [request, request]})
    source.write_bytes(original + b"Changed authority\n")
    with pytest.raises(AssertionError, match="stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    source.write_bytes(original)
    config.write_text(config.read_text().replace('"AGENTS.md"', '"different.md"'))
    with pytest.raises(AssertionError, match="stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_missing_configured_source_is_scoped_and_absent_selection_quiet(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = {"target": str(tmp_path), "task": "Describe a direct task"}
    (tmp_path / "README.md").write_text("Unrelated source")
    quiet = consume(surface, shared_core_binary, native_cli, context)
    assert quiet["startup_adapter"]["status"] == "absent"
    assert quiet["decision_packet"]["status"] == "direct"
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('schema_version=1\n[workspace]\nagent_instructions_file="docs/agent.md"\n')
    missing = consume(surface, shared_core_binary, native_cli, context)["startup_adapter"]
    assert missing["source"]["status"] == "missing"
    assert missing["requests"] == []
    assert {"effect:implementation", "claim:complete", "effect:write:docs/agent.md"} <= set(
        missing["contribution"]["blockers"][0]["affects"]
    )
    assert not (tmp_path / "docs/agent.md").exists()
    config.write_text(config.read_text().replace("docs/agent.md", "../outside.md"))
    invalid = consume(surface, shared_core_binary, native_cli, context)["startup_adapter"]
    assert invalid["source"]["status"] == "unavailable"
    assert invalid["requests"] == []


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("operation", ["planning", "proof", "create", "switch"])
def test_startup_delivery_is_carried_into_fresh_effect_admission(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, operation: str
) -> None:
    switch_choice = None
    incumbent = None
    if operation == "switch":
        context = {"target": str(tmp_path), "task": "Establish current Planning custody"}

        def setup(value):
            return consume(surface, shared_core_binary, native_cli, value)

        for index in range(2):
            current = setup(context)
            request = current["planning"]["creation_requests"][0]
            request["arguments"] = {"material": planning_material()}
            requests = [request]
            if index:
                direct = current["decision_packet"]["decision_request"]["response_request"]
                direct["arguments"]["answer"] = "unrelated-direct"
                requests.insert(0, direct)
            created = setup({**context, "invocation": setup({**context, "request": requests})["decision_packet"]["primary_action"]})
            switch_choice = created["value"]["selection_request"]
            if not index:
                setup({**context, "invocation": setup({**context, "request": switch_choice})["decision_packet"]["primary_action"]})
                context["task"] = "Select a second bounded owner"
        incumbent = (tmp_path / ".agentic-workspace/local/planning/owner-selection.json").read_bytes()
    elif operation == "proof":
        context = proof_fixture(tmp_path)
    elif operation == "create":
        context = {"target": str(tmp_path), "task": "Create bounded current work"}
    else:
        reference = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
        plan = tmp_path / reference
        plan.parent.mkdir(parents=True)
        plan.write_bytes((ROOT / reference).read_bytes())
        (plan.parent.parent / "state.toml").write_text(
            f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{reference.as_posix()}"\nstatus="active"\n'
        )
        context = {"target": str(tmp_path), "task": "Continue bounded current work"}
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir(exist_ok=True)
    config.write_text('schema_version=1\n[workspace]\nagent_instructions_file="AGENTS.md"\n')
    source = tmp_path / "AGENTS.md"
    source.write_text("Read current source before executing. Keep independent proof separate.")

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    current = call(context)
    read_request = current["startup_adapter"]["requests"][0]
    if operation == "switch":
        # Refresh the exact request against the new startup source contract.
        owner_request = dict(switch_choice)
        owner_request["capability_revision"] = current["capability_contract"]["revision"]
    elif operation == "proof":
        owner_request = current["verification"]["execution_requests"][0]
    elif operation == "create":
        owner_request = current["planning"]["creation_requests"][0]
        owner_request["arguments"] = {"material": planning_material()}
    else:
        owner_request = current["decision_packet"]["decision_request"]["response_request"]
        owner_request["arguments"]["answer"] = "continue-selected"
    unread = call({**context, "request": owner_request})
    assert not unread["decision_packet"]["ready_actions"]
    delivered = call({**context, "request": [read_request, owner_request]})
    action = delivered["decision_packet"]["primary_action"]
    assert action["source_requests"] == [read_request]
    omitted = dict(action)
    omitted.pop("source_requests")
    with pytest.raises(AssertionError):
        call({**context, "invocation": omitted})
    forged = json.loads(json.dumps(action))
    forged["source_requests"][0]["arguments"]["revision"] = "sha256:" + "0" * 64
    with pytest.raises(AssertionError):
        call({**context, "invocation": forged})
    original = source.read_bytes()
    source.write_bytes(original + b"\nDifferent current instruction")
    with pytest.raises(AssertionError):
        call({**context, "invocation": action})
    source.unlink()
    missing = call(context)
    assert missing["startup_adapter"]["source"]["status"] == "missing"
    with pytest.raises(AssertionError):
        call({**context, "invocation": action})
    assert not (tmp_path / "count.txt").exists()
    selector = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    if operation == "switch":
        assert selector.read_bytes() == incumbent
    else:
        assert not selector.exists()
    if operation == "create":
        assert not (tmp_path / action["arguments"]["owner_path"]).exists()
    source.write_bytes(original)
    assert call({**context, "invocation": action})["status"] == "applied"
    assert call({**context, "invocation": action})["status"] == "applied"
    fresh = call(context)
    assert fresh["startup_adapter"]["status"] == "source-context-required"
    if operation in {"planning", "switch"}:
        assert fresh["planning"]["current_owner"]["current"] is True
