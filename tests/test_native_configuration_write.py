"""Durable configuration choices use one exact source-owned human answer."""

from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize(
    "key,value,source_name",
    [
        ("modules.enabled", [], "config.toml"),
        ("safety.safe_to_auto_run_commands", False, "config.local.toml"),
        ("safety.requires_human_verification_on_pr", True, "config.local.toml"),
        ("workspace.agent_instructions_file", "GUIDE.md", "config.toml"),
    ],
)
def test_durable_choices_are_exact_and_do_not_admit_operational_state(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, key: str, value: object, source_name: str
) -> None:
    source = tmp_path / ".agentic-workspace" / source_name
    source.parent.mkdir()
    before = b"# Human-owned configuration\r\nschema_version=1\r\n"
    source.write_bytes(before)
    (tmp_path / "GUIDE.md").write_text("Fixture instructions, retained as a source.\n")
    context = {"target": str(tmp_path), "task": "Apply a deliberate fixture configuration choice", "changed": []}

    def call(**extra: object) -> dict:
        return consume(surface, shared_core_binary, native_cli, {**context, **extra})

    current = call()
    request = next(r for r in current["configuration_write"]["requests"] if r["arguments"]["key"] == key)
    request["arguments"]["value"] = value
    for forbidden in [
        "delegation.human_override_policy",
        "delegation.current_target",
        "assurance.instruction_revision",
        "runtime.learned_confidence",
    ]:
        wrong = copy.deepcopy(request)
        wrong["arguments"]["key"] = forbidden
        with pytest.raises(AssertionError):
            call(request=wrong)
    proposed = call(request=request)
    proposal = proposed["configuration_write"]["proposal"]
    assert proposal["postimage"].encode().startswith(before)
    assert source.read_bytes() == before
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    deferred = copy.deepcopy(answer)
    deferred["arguments"]["answer"] = "defer"
    assert call(request=deferred)["configuration_write"]["status"] == "deferred"
    answer["arguments"]["answer"] = "authorize-write"
    action = call(request=answer)["decision_packet"]["primary_action"]
    other = source.with_name("config.toml" if source_name == "config.local.toml" else "config.local.toml")
    other.write_text("schema_version=1\n")
    with pytest.raises(AssertionError):
        call(invocation=action)
    assert source.read_bytes() == before
    other.unlink()
    applied = call(invocation=action)
    assert applied["value"]["continuing_custody"] is False
    assert source.read_bytes() == proposal["postimage"].encode()
    fresh = call()
    if key == "modules.enabled":
        assert fresh["configuration"]["modules"] == []
    elif key.startswith("safety."):
        assert fresh["configuration"]["safety"][key.split(".")[1]] == value
        assert fresh["configuration"]["safety"]["automatic_execution_permitted"] is False
    else:
        assert fresh["configuration"]["agent_instructions_file"] == "GUIDE.md"
    with pytest.raises(AssertionError):
        call(invocation=action)


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_optional_configuration_creation_is_bound_to_absence(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = {"target": str(tmp_path), "task": "Set a deliberate local safety ceiling", "changed": []}

    def call(**extra: object) -> dict:
        return consume(surface, shared_core_binary, native_cli, {**context, **extra})

    initial = call()
    assert initial["decision_packet"]["status"] == "direct"
    assert initial["configuration_write"]["requests"] == []
    assert not (tmp_path / ".agentic-workspace").exists()
    assert initial["configuration_write"]["creation_requests"] == []
    discovery = initial["configuration_write"]["creation_discovery_request"]
    delivered = call(request=discovery)
    assert delivered["configuration_write"]["status"] == "creation-choices-delivered"
    assert delivered["decision_packet"]["primary_action"] is None
    assert not (tmp_path / ".agentic-workspace").exists()
    request = next(
        r for r in delivered["configuration_write"]["creation_requests"] if r["arguments"]["key"] == "safety.safe_to_auto_run_commands"
    )
    request["arguments"]["value"] = False
    proposed = call(request=request)
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    action = call(request=answer)["decision_packet"]["primary_action"]
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    raced = b"schema_version=1\n# Another author arrived first\n"
    source.write_bytes(raced)
    with pytest.raises(AssertionError, match="stale|changed"):
        call(request=discovery)
    with pytest.raises(AssertionError):
        call(invocation=action)
    assert source.read_bytes() == raced
    source.unlink()
    call(invocation=action)
    assert source.read_bytes() == proposed["configuration_write"]["proposal"]["postimage"].encode()
    assert call()["configuration"]["safety"]["safe_to_auto_run_commands"] is False


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_configuration_postimage_cannot_exceed_its_reader(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    context = {"target": str(tmp_path), "task": "Fixture bounded configuration", "changed": []}

    def call(**extra: object) -> dict:
        return consume(surface, shared_core_binary, native_cli, {**context, **extra})

    oversized = next(
        r
        for r in call(request=call()["configuration_write"]["creation_discovery_request"])["configuration_write"]["creation_requests"]
        if r["arguments"]["key"] == "system_intent.sources"
    )
    oversized["arguments"]["value"] = ["x" * 4097]
    with pytest.raises(AssertionError):
        call(request=oversized)
    assert not (tmp_path / ".agentic-workspace").exists()
    source = tmp_path / ".agentic-workspace/config.toml"
    source.parent.mkdir()
    prefix = b"schema_version=1\n[workspace]\ncli_invoke='a'\n#"
    # Publication and recovery use the narrower confined source reader.
    original = prefix + b"x" * (262_144 - len(prefix))
    source.write_bytes(original)
    request = call()["configuration_write"]["requests"][0]
    request["arguments"]["value"] = "longer-invocation"
    with pytest.raises(AssertionError, match="postimage exceeds"):
        call(request=request)
    assert source.read_bytes() == original
    assert not (tmp_path / ".agentic-workspace/local").exists()


def test_config_explicit_policy_choice_does_not_self_grant(tmp_path, shared_core_binary, native_cli):
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text(
        'schema_version=1\n[assurance]\ndecision_delegations=[{owner="configuration",scope=["path:.agentic-workspace/config.local.toml"]}]\n'
    )
    context = {"target": str(tmp_path), "task": "Apply authorized local safety choice", "changed": []}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    request = next(
        r
        for r in call(request=call()["configuration_write"]["creation_discovery_request"])["configuration_write"]["creation_requests"]
        if r["arguments"]["key"] == "safety.safe_to_auto_run_commands"
    )
    request["arguments"]["value"] = False
    ready = call(request=request)
    assert ready["configuration_write"]["authority_basis"]["kind"] == "exact-policy-delegated-decision"
    action = ready["decision_packet"]["primary_action"]
    call(invocation=action)
    assert call()["configuration"]["safety"]["automatic_execution_permitted"] is False


def test_configuration_defer_resumes_outside_human_policy(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Decide local command policy", "changed": []}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, {**context, **extra}, host_path=os.environ["PATH"])

    request = next(
        r
        for r in call(request=call()["configuration_write"]["creation_discovery_request"])["configuration_write"]["creation_requests"]
        if r["arguments"]["key"] == "safety.safe_to_auto_run_commands"
    )
    request["arguments"]["value"] = False
    proposed = call(request=request)
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "defer"
    action = call(request=answer)["decision_packet"]["primary_action"]
    assert action["operation_id"] == "configuration.defer-choice"
    call(invocation=action)
    assert not (tmp_path / ".agentic-workspace/config.local.toml").exists()
    context["task"] = "Resume local command policy in a fresh session"
    fresh = call()
    assert fresh["decision_packet"]["status"] == "direct"
    pending = fresh["configuration_write"]["deferred_choices"][0]
    proposed = call(request=pending["resume_request"])
    answer = proposed["decision_packet"]["decision_request"]["response_request"]
    answer["arguments"]["answer"] = "authorize-write"
    call(invocation=call(request=answer)["decision_packet"]["primary_action"])
    assert call()["configuration_write"]["deferred_choices"] == []
    assert (
        tmp_path / ".agentic-workspace/config.local.toml"
    ).read_text() == "schema_version=1\n\n[safety]\nsafe_to_auto_run_commands = false\n"
