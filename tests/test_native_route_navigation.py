"""Read-only navigation cannot replace current work applicability."""

from __future__ import annotations

import json

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_selection_survives_navigation_with_memory_and_assignment(tmp_path, shared_core_binary, native_cli, surface):
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"id": "work", "semantic_routes": ["custom/design", "custom/edit", "other/check"]}]}))
    workspace = tmp_path / ".agentic-workspace"
    workspace.mkdir()
    (workspace / "config.toml").write_text('[execution_posture."custom/design"]\npreferred_execution_guarantees=["cost.bounded"]\n')
    (workspace / "config.local.toml").write_text(
        '[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\n[delegation_targets.local]\ntransports=[{kind="internal"}]\n'
    )
    note_ref = ".agentic-workspace/memory/repo/domains/design.md"
    note = tmp_path / note_ref
    note.parent.mkdir(parents=True)
    note.write_text("Use the existing bounded completion contract.")
    (note.parent.parent / "manifest.toml").write_text(
        f'version=1\n[notes."{note_ref}"]\nsemantic_routes=["custom/design"]\nsummary="Current design advice"\n'
    )
    context = {"target": str(tmp_path), "task": "Inspect the current design", "changed": [], "projection": "carried"}

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value)

    def select(view, kind, fields):
        request = call({"request": view["carriage"], "reference": f"owner:request:semantic-routes:semantic-routes/{kind}/v1"})
        return call({"request": view["carriage"], "reference": request["reference"], "answer": fields, "projection": "carried"})

    initial = call(context)
    chosen = select(initial, "select", {"posture": "selected", "routes": ["custom/design"]})
    prepared = call(
        {
            "request": chosen["carriage"],
            "reference": chosen["view"]["assignment_context"]["next_step"]["reference"],
            "answer": {"required_result_classes": ["read-only"]},
            "projection": "carried",
        }
    )
    navigated = select(prepared, "discover", {"parent": "other"})
    before = call({**prepared["carriage"]["context"], "projection": "full"})
    after = call({**navigated["carriage"]["context"], "projection": "full"})
    assert before["decision_packet"]["semantic_task_routes"] == after["decision_packet"]["semantic_task_routes"]
    assert after["semantic_routes"]["discovery"]["parent"] == "other"
    assert after["memory"]["selected_notes"] == before["memory"]["selected_notes"]
    assert after["memory"]["selected_notes"][0]["source"]["reference"] == note_ref
    assert after["task_requirements"]["result"] == before["task_requirements"]["result"]
    assert after["task_requirements"]["result"]["execution_posture"]["preferred_execution_guarantees"] == ["cost.bounded"]
    assert after["decision_packet"]["blockers"] == before["decision_packet"]["blockers"]
    assert not (workspace / "local").exists()
    # Genuine reselection changes applicability; navigation itself never does.
    clean = select(chosen, "discover", {"parent": "other"})
    replaced = select(clean, "select", {"posture": "selected", "routes": ["custom/edit"]})
    assert replaced["view"]["decision_packet"]["semantic_task_routes"]["routes"] == ["custom/edit"]
    assert select(initial, "discover", {"parent": "other"})["view"]["decision_packet"]["semantic_task_routes"]["routes"] == []
    duplicate = dict(clean["carriage"]["context"])
    duplicate["request"] = [*duplicate["request"], duplicate["request"][0]]
    with pytest.raises(AssertionError):
        call(duplicate)
    with pytest.raises(AssertionError, match="stale|changed|identity"):
        call({**navigated["carriage"]["context"], "task": "Different work"})
    registry.write_text(registry.read_text().replace("custom/design", "custom/changed"))
    stale = call({**clean["carriage"]["context"], "projection": "full"})
    assert stale["decision_packet"]["semantic_task_routes"]["status"] != "current"
    assert stale["memory"]["selected_notes"] == []
    assert "execution_posture" not in stale["task_requirements"]["result"]
