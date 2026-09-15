"""Current advisory controls retain meaning without acquiring task authority."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

ROOT = Path(__file__).resolve().parents[1]


def workspace_blockers(packet: dict) -> list:
    return [row for row in packet["decision_packet"]["blockers"] if row["owner"] == "workspace"]


def test_unsupported_config_is_rejected_before_state_without_fallback(tmp_path, shared_core_binary, native_cli):
    from agentic_workspace.config import WorkspaceUsageError, load_workspace_config

    context = {"target": str(tmp_path), "task": "Inspect a link", "changed": []}
    quiet = consume("json", shared_core_binary, native_cli, context)
    assert quiet["decision_packet"]["status"] == "direct"
    source = tmp_path / ".agentic-workspace/config.toml"
    source.parent.mkdir()
    for text in [
        "schema_version=1\n",
        "schema_version=2\n",
        "[cli_compatibility]\nminimum_reader_epoch=1\n",
        "[workflow_obligations.old]\nsummary='Old policy'\n",
    ]:
        source.write_text(text)
        result = consume("json", shared_core_binary, native_cli, context)
        assert result["status"] == "blocked"
        assert result["managed_state_interpreted"] is False
        assert "decision_packet" not in result
        assert source.read_text() == text
        assert not (tmp_path / ".agentic-workspace/local").exists()
        with pytest.raises(WorkspaceUsageError, match="Invalid configuration"):
            load_workspace_config(target_root=tmp_path)
        rejected = consume(
            "json", shared_core_binary, native_cli, {**context, "invocation": {"operation_id": "planning.reconcile"}}, allow_failure=True
        )
        assert rejected["effect_outcome"]["status"] == "rejected-before-effect"
    source.unlink()
    # An unselected filename is neither a fallback source nor a migration scan.
    (tmp_path / "agentic-workspace.local.toml").write_text("invalid prerelease input")
    current = consume("json", shared_core_binary, native_cli, context)
    assert current["decision_packet"]["status"] == "direct"
    assert not current["configuration"]["sources"]


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
    local.write_text("[safety]\nsafe_to_auto_run_commands=false\nrequires_human_verification_on_pr=true\n", encoding="utf-8")
    before = source.read_bytes(), local.read_bytes()
    result = consume(
        surface, shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Inspect a documentation link", "changed": ["README.md"]}
    )
    config = result["configuration"]
    # P0 moved these repository instructions to their source owners. The
    # current config must not resurrect removed compatibility controls.
    blockers = workspace_blockers(result)
    assert config["improvement_latitude"] == "proactive"
    assert any(
        blocker["code"] == "local-command-safety-ceiling" and blocker["affects"] == ["effect:execute-command"] for blocker in blockers
    )
    assert any(blocker["code"] == "local-human-review-required" and blocker["affects"] == ["claim:pr-complete"] for blocker in blockers)
    assert any(blocker["code"] == "native-payload-target-unproven" and blocker["affects"] == ["task"] for blocker in blockers)
    assert any(b["code"] == "strict-closeout-judgment-required" for b in result["decision_packet"]["blockers"])
    assert (source.read_bytes(), local.read_bytes()) == before
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("source_name", ["config.toml", "config.local.toml"])
def test_exact_configuration_write_preserves_source_authority_and_rejects_drift(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, source_name: str
) -> None:
    import copy

    context = {"target": str(tmp_path), "task": "Correct the configured native invocation", "changed": []}
    continuation = None

    def call(**extra):
        nonlocal continuation
        if continuation is not None and not extra:
            continuation = consume(surface, shared_core_binary, native_cli, context)["planning"]["requests"][0]
            continuation["arguments"]["answer"] = "continue-selected"
        if continuation is not None and "invocation" not in extra:
            extra["request"] = [continuation, *([extra["request"]] if "request" in extra else [])]
        return consume(surface, shared_core_binary, native_cli, {**context, **extra})

    assert call()["configuration_write"]["requests"] == []
    source = tmp_path / ".agentic-workspace" / source_name
    source.parent.mkdir()
    original = b"# Human-owned policy\r\n[workspace] # preserve table comment\r\ncli_invoke = 'old-command' # preserve inline comment\r\nenabled=true\r\n"
    source.write_bytes(original)
    if source_name == "config.local.toml":
        plan_ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
        plan = tmp_path / plan_ref
        plan.parent.mkdir(parents=True)
        plan.write_bytes((Path(__file__).resolve().parents[1] / plan_ref).read_bytes())
        (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
            f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{plan_ref.as_posix()}"\nstatus="active"\n'
        )
        continuation = call()["decision_packet"]["decision_request"]["response_request"]
        continuation["arguments"]["answer"] = "continue-selected"
        call(invocation=call()["decision_packet"]["primary_action"])
        continuation = None
        continuation = call()["planning"]["requests"][0]
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_bytes(b"in-progress unrelated work")
    request = call()["configuration_write"]["requests"][0]
    # Same-value work is a deterministic no-op, without a human prompt or write.
    assert call(request=request)["configuration_write"]["status"] == "unchanged"
    assert not list((source.parent / "local/effects").glob("configuration-*"))
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
    if continuation is not None:
        assert continuation in action["source_requests"]
        plan_bytes = plan.read_bytes()
        plan.write_bytes(plan_bytes + b"\n")
        with pytest.raises(AssertionError, match="changed|stale|current"):
            call(invocation=action)
        assert source.read_bytes() == original
        plan.write_bytes(plan_bytes)
    # A change to the other source also invalidates the exact write.
    local = source.with_name("config.local.toml" if source_name == "config.toml" else "config.toml")
    local.write_text('[workspace]\ncli_invoke="conflicting-command"\n')
    with pytest.raises(AssertionError):
        call(invocation=action)
    assert source.read_bytes() == original
    fresh = next(
        r
        for r in call()["configuration_write"]["requests"]
        if r["arguments"]["source"].endswith(source_name) and r["arguments"]["key"] == "workspace.cli_invoke"
    )
    fresh["arguments"]["value"] = "another-override"
    override = call(request=fresh)["configuration_write"]
    assert override["status"] == "human-decision-required"
    assert "another-override" in override["proposal"]["postimage"]
    assert source.read_bytes() == original
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
    for original in [b"# human source\n", b"[workspace] # policy\nenabled=true # retain\n"]:
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
        assert original in written
        assert b'cli_invoke = "configured-native"' in written
        assert call()["configuration"]["cli_invoke"] == "configured-native"
        with pytest.raises(AssertionError):
            call(invocation=action)

    source.write_bytes(b"workspace={enabled=true}\n")
    request = call()["configuration_write"]["requests"][0]
    with pytest.raises(AssertionError, match="ordinary workspace table"):
        call(request=request)
    assert source.read_bytes() == b"workspace={enabled=true}\n"


@pytest.mark.parametrize("linked", ["source", "parent", "effects"])
def test_configuration_writer_preserves_linked_sources(tmp_path: Path, shared_core_binary: Path, native_cli: Path, linked: str) -> None:
    import os
    import subprocess

    target = tmp_path / "target"
    target.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    body = b'[workspace]\ncli_invoke="original"\n'
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
