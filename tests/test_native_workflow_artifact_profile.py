"""Artifact methods use current Planning custody without recreating record forests."""

from pathlib import Path

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_repo_owned_profile_preserves_real_planning_custody(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    reference = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / reference
    plan.parent.mkdir(parents=True)
    original = (ROOT / reference).read_bytes()
    plan.write_bytes(original)
    (plan.parent.parent / "state.toml").write_text(
        f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{reference.as_posix()}"\nstatus="active"\n'
    )
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text('schema_version=1\n[workspace]\nworkflow_artifact_profile="repo-owned"\n')
    context = {"target": str(tmp_path), "task": "Continue the bounded current owner"}
    current = consume(surface, shared_core_binary, native_cli, context)
    profile = current["workflow_artifact_profile"]
    assert profile["canonical_owner"] == "planning"
    assert profile["current_owner"]["status"] == current["planning"]["status"]
    assert current["decision_packet"]["decision_request"]
    assert not any(r["field"] == "workspace.workflow_artifact_profile" for r in current["configuration"]["residuals"])
    request = current["decision_packet"]["decision_request"]["response_request"]
    request["arguments"]["answer"] = "continue-selected"
    action = consume(surface, shared_core_binary, native_cli, {**context, "request": request})["decision_packet"]["primary_action"]
    config.write_text(config.read_text().replace('"repo-owned"', '"gemini"'))
    with pytest.raises(AssertionError, match="stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": request})
    with pytest.raises(AssertionError, match="stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "invocation": action})
    gemini = consume(surface, shared_core_binary, native_cli, context)
    gemini_request = gemini["decision_packet"]["decision_request"]["response_request"]
    gemini_request["arguments"]["answer"] = "continue-selected"
    gemini_action = consume(surface, shared_core_binary, native_cli, {**context, "request": gemini_request})["decision_packet"][
        "primary_action"
    ]
    (tmp_path / "walkthrough.md").write_text("New unadmitted runtime facts")
    with pytest.raises(AssertionError, match="stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "request": gemini_request})
    with pytest.raises(AssertionError, match="stale"):
        consume(surface, shared_core_binary, native_cli, {**context, "invocation": gemini_action})
    config.write_text(config.read_text().replace('"gemini"', '"repo-owned"'))
    assert consume(surface, shared_core_binary, native_cli, {**context, "invocation": action})["status"] == "applied"
    fresh = consume(surface, shared_core_binary, native_cli, context)
    assert fresh["planning"]["current_owner"]["current"] is True
    assert fresh["workflow_artifact_profile"]["current_owner"]["current"] is True
    assert plan.read_bytes() == original
    assert not (tmp_path / ".agentic-workspace/planning/decompositions").exists()
    config.write_text(config.read_text() + "\n[modules]\nenabled=[]\n")
    disabled = consume(surface, shared_core_binary, native_cli, context)
    assert disabled["planning"]["status"] == "disabled"
    assert disabled["planning"]["sources"]
    assert disabled["decision_packet"]["blockers"]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_optional_scratchpads_preserve_only_affected_transfer_gap(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir()
    config.write_text('schema_version=1\n[workspace]\nworkflow_artifact_profile="gemini"\n')
    context = {"target": str(tmp_path), "task": "Inspect an unrelated source"}
    absent = consume(surface, shared_core_binary, native_cli, context)
    assert absent["decision_packet"]["status"] == "direct"
    assert absent["workflow_artifact_profile"]["transfer_status"] == "not-required"
    source = tmp_path / "task.md"
    source.write_text("Unadmitted scratchpad facts")
    original = source.read_bytes()
    result = consume(surface, shared_core_binary, native_cli, context)
    profile = result["workflow_artifact_profile"]
    assert profile["sources"][0]["reference"] == "task.md"
    assert profile["transfer_status"] == "unresolved-owner-update"
    assert profile["blockers"][0]["affects"] == ["effect:delegation", "claim:complete", "claim:pr-complete"]
    assert not any("task" in b["affects"] for b in result["decision_packet"]["blockers"])
    assert source.read_bytes() == original
    assert not (tmp_path / ".agentic-workspace/local").exists()
    config.write_text(config.read_text().replace('"gemini"', '"repo-owned"'))
    assert consume(surface, shared_core_binary, native_cli, context)["workflow_artifact_profile"]["sources"] == []
