"""Current Planning judgment outranks hints only within its admitted custody."""

import json
from pathlib import Path

import pytest
from repo_planning_bootstrap import installer as planning

from agentic_workspace import workspace_runtime_core as runtime
from agentic_workspace.config import load_workspace_config


@pytest.mark.parametrize("relation", ["current", "unrelated", "reentry", "stale-reentry"])
def test_assignment_consumes_only_current_owner_task_judgment(tmp_path: Path, monkeypatch, relation: str) -> None:
    root = tmp_path / ".agentic-workspace"
    root.mkdir()
    (root / "config.local.toml").write_text(
        "schema_version = 1\n[delegation_targets.worker]\n"
        'target_id = "host:worker"\ntarget_revision = "1"\nstrength = "weak"\n'
        'location = "external"\ntransports = [{kind="manual"}]\n'
    )
    task = "Check the bounded policy document links."
    record = planning._build_execplan_record_from_todo_item(
        title=task, item_id="links", status="in-progress", why_now=task, next_action=task, done_when="links checked"
    )
    record["capability_posture"] = {
        "execution class": "mechanical-follow-through",
        "recommended strength": "weak",
        "preferred location": "either",
        "delegation friendly": "yes",
        "strong external reasoning": "avoid",
        "why": "Exact link existence inspection is bounded.",
    }
    plan_ref = ".agentic-workspace/planning/execplans/links.plan.json"
    path = tmp_path / plan_ref
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(record))
    (root / "planning/state.toml").write_text(
        f'[todo]\nactive_items = [{{id="links", status="in-progress", surface="{plan_ref}"}}]\nqueued_items = []\n'
    )
    captured = {}

    class ResolutionReached(Exception):
        pass

    def capture(*, config, capability_posture):
        captured.update(capability_posture)
        raise ResolutionReached

    monkeypatch.setattr(runtime, "_runtime_resolution_payload", capture)
    identity = None
    if relation.endswith("reentry"):
        binding = runtime._live_assignment_plan_binding(target_root=tmp_path, task_text=task, changed_paths=["docs/policy.md"])
        identity = {
            "task_class": "reasoning-heavy",
            "scope_class": "bounded",
            "slice_id": "links",
            "plan_ref": plan_ref,
            "plan_revision": binding["plan_revision"] if relation == "reentry" else "stale",
        }
    with pytest.raises(ResolutionReached):
        runtime._current_assignment_selection(
            config=load_workspace_config(target_root=tmp_path),
            changed_paths=["docs/policy.md"],
            task_text=task if relation != "unrelated" else "Inspect the separate runtime contract.",
            work_identity=identity,
        )
    assert (
        captured["execution class"]
        == {
            "current": "mechanical-follow-through",
            "unrelated": "boundary-shaping",
            "reentry": "reasoning-heavy",
            "stale-reentry": "reasoning-heavy",
        }[relation]
    )
    assert captured["recommended strength"] == ("strong" if relation in {"unrelated", "stale-reentry"} else "weak")
