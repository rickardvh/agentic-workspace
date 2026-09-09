"""Current advisory controls retain meaning without acquiring task authority."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]


def workspace_blockers(packet: dict) -> list:
    return [row for row in packet["decision_packet"]["blockers"] if row["owner"] == "workspace"]


def write_config(target: Path, obligation: dict) -> Path:
    source = target / ".agentic-workspace/config.toml"
    source.parent.mkdir(exist_ok=True)
    lines = ["schema_version=1", "[workflow_obligations.commit_after_proof]"]
    lines.extend(f"{key}={json.dumps(value)}" for key, value in obligation.items())
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return source


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_actual_recommended_source_preserved_without_task_veto(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    actual = tomllib.loads((ROOT / ".agentic-workspace/config.toml").read_text(encoding="utf-8"))
    obligation = actual["workflow_obligations"]["commit_after_proof"]
    context = {"target": str(tmp_path), "task": "Inspect a documentation link", "changed": ["README.md"]}
    quiet = consume(surface, shared_core_binary, native_cli, context)
    assert quiet["configuration"]["residuals"] == []
    source = write_config(tmp_path, obligation)
    original = source.read_bytes()
    result = consume(surface, shared_core_binary, native_cli, context)
    config = result["configuration"]
    assert workspace_blockers(result) == []
    assert result["decision_packet"]["status"] == "direct"
    fields = {item["field"]: item for item in config["residuals"]}
    assert fields["workflow_obligations.commit_after_proof"]["value"] == obligation
    for item in fields.values():
        assert item["source"] == ".agentic-workspace/config.toml"
        assert item["affects"] == []
        assert item["authority"] == "advisory"
        assert item["satisfaction"] == "not-evidence"
    assert source.read_bytes() == original
    obligation = {**obligation, "summary": "A revised recommended method"}
    write_config(tmp_path, obligation)
    changed = consume(surface, shared_core_binary, native_cli, context)
    assert changed["configuration"]["revision"] != config["revision"]
    assert workspace_blockers(changed) == []
    for force in ["blocking", "required-before-closeout"]:
        write_config(tmp_path, {**obligation, "force": force})
        hard = consume(surface, shared_core_binary, native_cli, context)
        blockers = workspace_blockers(hard)
        assert len(blockers) == 1
        assert blockers[0]["affects"] == ["task"]
        assert "workflow_obligations.commit_after_proof" in blockers[0]["code"]
    write_config(tmp_path, {**obligation, "unknown_future_constraint": "must remain unresolved"})
    unknown = consume(surface, shared_core_binary, native_cli, context)
    assert len(workspace_blockers(unknown)) == 1
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_current_shared_controls_keep_hard_and_unresolved_owner_boundaries(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    source = tmp_path / ".agentic-workspace/config.toml"
    source.parent.mkdir()
    # Repository admission pins name its own sources, not this temporary target.
    # Preserve all policy values while leaving those unrelated pins unconfigured.
    lines = (ROOT / ".agentic-workspace/config.toml").read_text(encoding="utf-8").splitlines()
    source.write_text(
        "\n".join(
            line
            for line in lines
            if not line.startswith(("decision_record_target =", "decision_record_revision =", "instruction_revision ="))
        )
        + "\n",
        encoding="utf-8",
    )
    local = source.with_name("config.local.toml")
    local.write_text(
        "schema_version=1\n[safety]\nsafe_to_auto_run_commands=false\nrequires_human_verification_on_pr=true\n", encoding="utf-8"
    )
    before = source.read_bytes(), local.read_bytes()
    result = consume(
        surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Inspect a documentation link", "changed": ["README.md"]}
    )
    config = result["configuration"]
    advisory = {item["field"] for item in config["residuals"] if item["affects"] == []}
    assert advisory == {
        "workflow_obligations.commit_after_proof",
        "workflow_obligations.system_intent_refresh",
        "cli_compatibility.enforcement",
        "cli_compatibility.source_classes",
        "cli_compatibility.target_relations",
        "cli_compatibility.required_resources",
        "cli_compatibility.resolution_policy",
    }
    blockers = workspace_blockers(result)
    for field in [
        "workspace.improvement_latitude",
        "workflow_obligations.adapter_surface_refresh",
        "workflow_obligations.dogfooding_lane_closeout",
    ]:
        assert any(blocker["code"].endswith(":" + field) for blocker in blockers)
    assert any(
        blocker["code"] == "local-command-safety-ceiling" and blocker["affects"] == ["effect:execute-command"] for blocker in blockers
    )
    assert any(blocker["code"] == "local-human-review-required" and blocker["affects"] == ["claim:pr-complete"] for blocker in blockers)
    assert any(blocker["code"] == "native-payload-target-unproven" and blocker["affects"] == ["task"] for blocker in blockers)
    assert any(
        blocker["code"].endswith(":workspace.improvement_latitude") and blocker["affects"] == ["effect:initiative"] for blocker in blockers
    )
    for field in ("adapter_surface_refresh", "dogfooding_lane_closeout"):
        boundary = next(blocker for blocker in blockers if blocker["code"].endswith(":" + "workflow_obligations." + field))
        assert "task" not in boundary["affects"] and "claim:complete" in boundary["affects"]
    assert len(blockers) == len(config["residuals"]) - len(advisory) + 3
    assert (source.read_bytes(), local.read_bytes()) == before
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("source_name", ["config.toml", "config.local.toml"])
def test_exact_configuration_write_preserves_source_authority_and_rejects_drift(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, source_name: str
) -> None:
    import copy

    context = {"target": str(tmp_path), "task": "Correct the configured native invocation", "changed": []}

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra})

    assert call()["configuration_write"]["requests"] == []
    source = tmp_path / ".agentic-workspace" / source_name
    source.parent.mkdir()
    original = b"# Human-owned policy\r\nschema_version=1\r\n[workspace] # preserve table comment\r\ncli_invoke = 'old-command' # preserve inline comment\r\nenabled=true\r\n"
    source.write_bytes(original)
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_bytes(b"in-progress unrelated work")
    request = call()["configuration_write"]["requests"][0]
    # Same-value work is a deterministic no-op, without a human prompt or write.
    assert call(request=request)["configuration_write"]["status"] == "unchanged"
    assert not (source.parent / "local").exists()
    request["arguments"]["value"] = "agentic-workspace"
    proposal = call(request=request)["decision_packet"]
    assert proposal["status"] == "decision"
    answer = proposal["decision_request"]["response_request"]
    deferred = copy.deepcopy(answer)
    deferred["arguments"]["answer"] = "defer"
    assert call(request=deferred)["configuration_write"]["status"] == "deferred"
    answer["arguments"]["answer"] = "authorize-write"  # faithful bounded human answer
    tampered = copy.deepcopy(answer)
    tampered["arguments"]["value"] = "different-command"
    with pytest.raises(AssertionError):
        call(request=tampered)
    unsupported = copy.deepcopy(answer)
    unsupported["arguments"]["key"] = "modules.enabled"
    with pytest.raises(AssertionError):
        call(request=unsupported)
    ready = call(request=answer)
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "configuration.write"
    # A change to the other source also invalidates the exact write.
    local = source.with_name("config.local.toml" if source_name == "config.toml" else "config.toml")
    local.write_text('schema_version=1\n[workspace]\ncli_invoke="conflicting-command"\n')
    with pytest.raises(AssertionError):
        call(invocation=action)
    assert source.read_bytes() == original
    fresh = call()["configuration_write"]["requests"][1]
    fresh["arguments"]["value"] = "another-override"
    with pytest.raises(AssertionError, match="conflict"):
        call(request=fresh)
    local.unlink()
    source.write_bytes(original + b"# changed since authorization\r\n")
    with pytest.raises(AssertionError):
        call(invocation=action)
    source.write_bytes(original)
    forged = copy.deepcopy(action)
    forged["arguments"]["post_revision"] = "sha256:forged"
    with pytest.raises(AssertionError):
        call(invocation=forged)
    applied = call(invocation=action)
    assert applied["status"] == "applied"
    assert applied["value"]["continuing_custody"] is False
    assert applied["value"]["completion_authority"] is False
    expected = original.replace(b"'old-command'", b'"agentic-workspace"')
    assert source.read_bytes() == expected
    assert unrelated.read_bytes() == b"in-progress unrelated work"
    current = call()
    assert current["configuration"]["cli_invoke"] == "agentic-workspace"
    assert current["configuration_write"]["recovery_requests"] == []
    with pytest.raises(AssertionError):
        call(invocation=action)
    assert source.read_bytes() == expected
    # Returning to identical preimage bytes cannot revive a consumed authorization.
    source.write_bytes(original)
    with pytest.raises(AssertionError, match="already consumed"):
        call(invocation=action)
    assert source.read_bytes() == original
    source.write_bytes(expected)
    # Historical evidence does not authorize a new edit.
    next_request = current["configuration_write"]["requests"][0]
    next_request["arguments"]["value"] = "yet-another-command"
    assert call(request=next_request)["configuration_write"]["status"] == "human-decision-required"
    # Malformed current bytes are preserved and never interpreted as a repair grant.
    source.write_bytes(b"[broken")
    rejected = call(request=answer)
    assert rejected["status"] == "blocked"
    assert source.read_bytes() == b"[broken"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_configuration_insertion_preserves_existing_source_and_exact_authorization(tmp_path, shared_core_binary, native_cli, surface):
    context = {"target": str(tmp_path), "task": "Configure invocation in the existing human source", "changed": []}

    def call(**extra):
        return consume(surface, shared_core_binary, native_cli, {**context, **extra})

    source = tmp_path / ".agentic-workspace/config.toml"
    source.parent.mkdir()
    for original in [b"# human source\nschema_version=1\n", b"schema_version=1\n[workspace] # policy\nenabled=true # retain\n"]:
        source.write_bytes(original)
        before_files = sorted(source.parent.rglob("*"))
        request = call()["configuration_write"]["requests"][0]
        request["arguments"]["value"] = "configured-native"
        proposal = call(request=request)
        assert proposal["configuration_write"]["proposal"]["before"] is None
        assert source.read_bytes() == original and sorted(source.parent.rglob("*")) == before_files
        answer = proposal["decision_packet"]["decision_request"]["response_request"]
        answer["arguments"]["answer"] = "authorize-write"
        action = call(request=answer)["decision_packet"]["primary_action"]
        source.write_bytes(original + b"# human drift\n")
        with pytest.raises(AssertionError, match="stale|changed"):
            call(invocation=action)
        assert source.read_bytes() == original + b"# human drift\n"
        source.write_bytes(original)
        result = call(invocation=action)
        assert result["value"]["continuing_custody"] is False
        written = source.read_bytes()
        assert written.startswith(original)
        assert b'cli_invoke = "configured-native"' in written
        assert call()["configuration"]["cli_invoke"] == "configured-native"
        with pytest.raises(AssertionError):
            call(invocation=action)

    source.write_bytes(b"schema_version=1\nworkspace={enabled=true}\n")
    request = call()["configuration_write"]["requests"][0]
    with pytest.raises(AssertionError, match="ordinary workspace table"):
        call(request=request)
    assert source.read_bytes() == b"schema_version=1\nworkspace={enabled=true}\n"


@pytest.mark.parametrize("linked", ["source", "parent", "effects"])
def test_configuration_writer_preserves_linked_sources(tmp_path: Path, shared_core_binary: Path, native_cli: Path, linked: str) -> None:
    import os
    import subprocess

    target = tmp_path / "target"
    target.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    body = b'schema_version=1\n[workspace]\ncli_invoke="original"\n'
    (outside / "config.toml").write_bytes(body)
    workspace = target / ".agentic-workspace"
    context = {"target": str(target), "task": "Inspect linked configuration", "changed": []}
    if linked == "effects":
        workspace.mkdir()
        (workspace / "config.toml").write_bytes(body)
        initial = consume("native", shared_core_binary, native_cli, context)
        request = initial["configuration_write"]["requests"][0]
        request["arguments"]["value"] = "changed"
        proposal = consume("native", shared_core_binary, native_cli, {**context, "request": request})
        answer = proposal["decision_packet"]["decision_request"]["response_request"]
        answer["arguments"]["answer"] = "authorize-write"
        ready = consume("native", shared_core_binary, native_cli, {**context, "request": answer})
        action = ready["decision_packet"]["primary_action"]
        (workspace / "local").mkdir()
        link = workspace / "local/effects"
        if os.name == "nt":
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True)
            assert result.returncode == 0, result.stderr
        else:
            link.symlink_to(outside, target_is_directory=True)
        with pytest.raises(AssertionError, match="link|reparse|confined"):
            consume("native", shared_core_binary, native_cli, {**context, "invocation": action})
        assert (workspace / "config.toml").read_bytes() == body
        assert sorted(p.name for p in outside.iterdir()) == ["config.toml"]
        return
    if linked == "parent" and os.name == "nt":
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(workspace), str(outside)], capture_output=True)
        assert result.returncode == 0, result.stderr
    else:
        try:
            if linked == "parent":
                workspace.symlink_to(outside, target_is_directory=True)
            else:
                workspace.mkdir()
                (workspace / "config.toml").symlink_to(outside / "config.toml")
        except OSError:
            pytest.skip("Host does not permit file symlink creation; directory junction covered separately")
    result = consume("native", shared_core_binary, native_cli, context)
    assert result.get("status", result.get("decision_packet", {}).get("status")) == "blocked"
    assert (outside / "config.toml").read_bytes() == body
    assert not (outside / "local").exists()
