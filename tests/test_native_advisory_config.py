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


def write_config(target: Path, bias: str, obligation: dict) -> Path:
    source = target / ".agentic-workspace/config.toml"
    source.parent.mkdir(exist_ok=True)
    lines = ["schema_version=1", "[workspace]", f"optimization_bias={json.dumps(bias)}", "[workflow_obligations.commit_after_proof]"]
    lines.extend(f"{key}={json.dumps(value)}" for key, value in obligation.items())
    source.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return source


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_actual_recommended_source_preserved_without_task_veto(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    actual = tomllib.loads((ROOT / ".agentic-workspace/config.toml").read_text(encoding="utf-8"))
    obligation = actual["workflow_obligations"]["commit_after_proof"]
    bias = actual["workspace"]["optimization_bias"]
    context = {"target": str(tmp_path), "task": "Inspect a documentation link", "changed": ["README.md"]}
    quiet = consume(surface, shared_core_binary, native_cli, context)
    assert quiet["configuration"]["residuals"] == []
    source = write_config(tmp_path, bias, obligation)
    original = source.read_bytes()
    result = consume(surface, shared_core_binary, native_cli, context)
    config = result["configuration"]
    assert workspace_blockers(result) == []
    assert result["decision_packet"]["status"] == "direct"
    fields = {item["field"]: item for item in config["residuals"]}
    assert fields["workspace.optimization_bias"]["value"] == bias
    assert fields["workflow_obligations.commit_after_proof"]["value"] == obligation
    for item in fields.values():
        assert item["source"] == ".agentic-workspace/config.toml"
        assert item["affects"] == []
        assert item["authority"] == "advisory"
        assert item["satisfaction"] == "not-evidence"
    assert source.read_bytes() == original
    obligation = {**obligation, "summary": "A revised recommended method"}
    write_config(tmp_path, bias, obligation)
    changed = consume(surface, shared_core_binary, native_cli, context)
    assert changed["configuration"]["revision"] != config["revision"]
    assert workspace_blockers(changed) == []
    for force in ["blocking", "required-before-closeout"]:
        write_config(tmp_path, bias, {**obligation, "force": force})
        hard = consume(surface, shared_core_binary, native_cli, context)
        blockers = workspace_blockers(hard)
        assert len(blockers) == 1
        assert blockers[0]["affects"] == ["task"]
        assert "workflow_obligations.commit_after_proof" in blockers[0]["code"]
    write_config(tmp_path, bias, {**obligation, "unknown_future_constraint": "must remain unresolved"})
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
        "workspace.optimization_bias",
        "workspace.advanced_features",
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
def test_optional_diagnostic_preferences_preserve_direct_work_and_human_latitude(tmp_path, shared_core_binary, native_cli, surface):
    context = {"target": str(tmp_path), "task": "Inspect a documentation link", "changed": ["README.md"]}
    source = tmp_path / ".agentic-workspace/config.toml"
    source.parent.mkdir()
    actual = tomllib.loads((ROOT / ".agentic-workspace/config.toml").read_text(encoding="utf-8"))
    features = actual["workspace"]["advanced_features"]
    text = "schema_version=1\n[workspace]\nadvanced_features=" + json.dumps(features) + "\n"
    source.write_text(text, encoding="utf-8")
    first = consume(surface, shared_core_binary, native_cli, context)
    assert first["decision_packet"]["status"] == "direct"
    preference = next(r for r in first["configuration"]["residuals"] if r["field"] == "workspace.advanced_features")
    assert preference["value"] == features
    assert preference["authority"] == "advisory" and preference["affects"] == []
    assert preference["satisfaction"] == "not-evidence"
    assert source.read_text(encoding="utf-8") == text
    source.write_text(text + 'improvement_latitude="proactive"\n', encoding="utf-8")
    initiative = consume(surface, shared_core_binary, native_cli, context)
    assert initiative["configuration"]["revision"] != first["configuration"]["revision"]
    assert any(b["code"].endswith(":workspace.improvement_latitude") for b in initiative["decision_packet"]["blockers"])
    assert not (tmp_path / ".agentic-workspace/local").exists()
