"""Portable procedure receives fresh preferences; semantic judgment stays with agents."""

import json

from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_procedure_preferences_and_required_decisions_remain_owner_owned(tmp_path, shared_core_binary, native_cli):
    root = tmp_path / ".agentic-workspace"
    root.mkdir()
    local = root / "config.local.toml"
    shared = root / "config.toml"
    shared.write_text('[workspace]\ncli_invoke="uv run agentic-workspace"\n')

    def current():
        return consume("native", shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Clarify an ambiguous outcome"})

    for mode in ("ask-first", "suggest", "auto-continue"):
        local.write_text(f'[clarification]\nmode="{mode}"\n')
        result = current()
        assert result["configuration"]["clarification"]["mode"] == mode
        assert result["configuration_write"]["requests"]
        assert result["decision_packet"]["primary_action"] is None
        assert not (root / "local").exists()
    for latitude in ("none", "reporting", "conservative", "proactive"):
        shared.write_text(f'[workspace]\nimprovement_latitude="{latitude}"\ncli_invoke="npm exec agentic-workspace"\n')
        assert current()["configuration"]["improvement_latitude"] == latitude


def test_planning_preparation_exposes_current_policy_without_creating_work(tmp_path, shared_core_binary, native_cli):
    directory = tmp_path / ".agentic-workspace/instructions"
    directory.mkdir(parents=True)
    policy = directory / "planning.md"
    policy.write_text("Use durable Planning for accepted cross-session work.\n")

    def current():
        return consume("native", shared_core_binary, native_cli, {"target": str(tmp_path), "task": "Continue accepted work"})

    first = current()
    assert "accepted cross-session" in json.dumps(first["instructions"])
    policy.write_text("Keep this task direct; no durable continuity is needed.\n")
    second = current()
    assert "Keep this task direct" in json.dumps(second["instructions"])
    assert first["instructions"] != second["instructions"]
    assert not (tmp_path / ".agentic-workspace/planning").exists()
