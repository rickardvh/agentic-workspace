"""The Python owner consumes the shared direct subject without identity drift."""

import json
from pathlib import Path

from agentic_workspace.decision import direct_task_subject
from agentic_workspace.workspace_runtime_core import _assignment_plan_binding_matches, _live_assignment_plan_binding


def test_python_bridge_preserves_established_unicode_identity_vectors() -> None:
    vectors = json.loads((Path(__file__).parent / "fixtures/direct_task_identity.json").read_text(encoding="utf-8"))
    for vector in vectors:
        actual = direct_task_subject(vector["input"]["task"], vector["input"]["paths"])
        assert actual == {"id": vector["expected"], "revision": vector["expected"]}


def test_current_and_legacy_assignment_consumers_share_direct_subject(tmp_path: Path) -> None:
    task = "Check\u00a0current\x1cfiles"
    paths = ["b.txt", "a.txt"]
    expected = direct_task_subject(task, paths)["revision"]
    current = _live_assignment_plan_binding(target_root=tmp_path, task_text=task, changed_paths=paths)
    assert current["plan_ref"] == current["plan_revision"] == expected
    legacy = {"assignment_gate": {"allowed_paths": paths, "human_intent": task}}
    assert _assignment_plan_binding_matches(assignment=legacy, live_binding=current)
    legacy["assignment_gate"]["human_intent"] = "A different task"
    assert not _assignment_plan_binding_matches(assignment=legacy, live_binding=current)
