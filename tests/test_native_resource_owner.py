"""Generic exact owner references retain the direct resource primitive's bounds."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("projection", ["compact", "carried", "full"])
@pytest.mark.parametrize("kind", ["scratch", "worktree", "worktree-default"])
def test_created_resource_result_drives_existing_lifecycle(tmp_path, shared_core_binary, native_cli, projection, kind):
    from tests.test_native_resources import repository

    root = tmp_path / "repo"
    root.mkdir()
    default_path = kind == "worktree-default"
    kind = "worktree" if default_path else kind
    if kind == "worktree":
        repository(root)
    context = {"target": str(root), "task": "Create and retire exact task resource"}

    def call(data):
        return consume("json", shared_core_binary, native_cli, data)

    request = call(context)["resources"]["requests"][0]
    args = {"operation": f"{kind}-create"}
    if kind == "worktree":
        args |= {"need": "destructive-validation", "reason": "Isolate destructive validation"}
        if not default_path:
            args["path"] = str(tmp_path / "isolated")
        request["arguments"]["request"] = args
        policy = call(context | {"request": request})["resources"]["proposal"]["policy_revision"]
        args |= {"policy_revision": policy, "policy_answer": "permits-isolation"}
    request["arguments"]["request"] = args
    ready = call(context | {"request": request})
    created = call(context | {"invocation": ready["decision_packet"]["primary_action"], "projection": projection})
    assert created["effect_outcome"]["status"] == "committed"
    assert created["continuation"]["status"] == "current"
    value = created["value"]
    path = Path(value["path"])
    assert path.is_dir() and path.is_absolute()
    assert value["resource"]["status"] == "present"
    assert value["resource"]["custody"]["task"] == context["task"]
    assert "snapshot" not in value and "operation_result" not in value
    step = value["next_step"]
    # Answer the returned current step, without extracting a raw public request
    # or reconstructing resource identity from the preceding proposal.
    answer = step["answer_shape"]
    if kind == "scratch":
        answer["request"]["reason"] = "Keep the requested draft until checked"
        retained = call(step["reentry"] | {"reference": step["reference"], "answer": answer})
        held = call(step["reentry"] | {"invocation": retained["decision_packet"]["primary_action"]})
        assert held["effect_outcome"]["status"] == "committed"
        assert json.loads((path / ".aw-scratch.json").read_text())["retain"] is True
        selected = call(context | {"reference": "owner:request:workspace-resources:resources/propose/v1"})
        release = call(
            selected["reentry"]
            | {
                "reference": selected["next_step"]["reference"],
                "answer": {"request": answer["request"] | {"operation": "scratch-release", "reason": "Draft checked"}},
            }
        )
        assert call(context | {"invocation": release["decision_packet"]["primary_action"]})["effect_outcome"]["status"] == "committed"
    else:
        # A created path conveys no permission to discard newly authored work.
        (path / "needed.txt").write_text("Preserve authored material")
        blocked = call(step["reentry"] | {"reference": step["reference"], "answer": answer})
        assert not blocked["resources"]["proposal"].get("action")
        assert (path / "needed.txt").read_text() == "Preserve authored material"
        (path / "needed.txt").unlink()
    answer["request"]["operation"] = f"{kind}-remove"
    answer["request"].pop("reason", None)
    removal = call(step["reentry"] | {"reference": step["reference"], "answer": answer})
    assert call(context | {"invocation": removal["decision_packet"]["primary_action"]})["effect_outcome"]["status"] == "committed"
    assert not path.exists()


def test_resource_action_carries_selected_planning_answer(tmp_path, shared_core_binary, native_cli):
    from tests.test_native_planning_create import material

    context = {"target": str(tmp_path), "task": "Prepare and retire bounded task scratch"}

    def call(**extra):
        return consume("json", shared_core_binary, native_cli, context | extra)

    creation = call()["planning"]["creation_requests"][0]
    creation["arguments"] = {"material": material()}
    created = call(invocation=call(request=creation)["decision_packet"]["primary_action"])
    context = created["continuation"]["context"]

    current = call()
    planning = current["planning"]["requests"][0]
    planning["arguments"] = {"answer": "continue-selected"}
    create = current["resources"]["requests"][0]
    create["arguments"]["request"] = {"operation": "scratch-create"}
    ready = call(request=[planning, create])
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "workspace.resources.scratch-create"
    assert planning in action["source_requests"]
    path = Path(ready["resources"]["proposal"]["path"])
    assert call(invocation=action)["effect_outcome"]["status"] == "committed"
    assert path.is_dir()

    current = call()
    planning = current["planning"]["requests"][0]
    planning["arguments"] = {"answer": "continue-selected"}
    remove = current["resources"]["requests"][0]
    remove["arguments"]["request"] = {"operation": "scratch-remove", "path": ready["resources"]["proposal"]["action"]["request"]["path"]}
    action = call(request=[planning, remove])["decision_packet"]["primary_action"]
    assert action["operation_id"] == "workspace.resources.scratch-remove"
    assert planning in action["source_requests"]
    assert remove in action["source_requests"]
    assert call(invocation=action)["effect_outcome"]["status"] == "committed"
    assert not path.exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_resource_reference_proposal_effect_and_stale_reentry(tmp_path, shared_core_binary, native_cli, surface):
    context = {"target": str(tmp_path), "task": "Use bounded task scratch"}

    def call(**extra):
        allow_failure = extra.pop("allow_failure", False)
        return consume(surface, shared_core_binary, native_cli, context | extra, allow_failure=allow_failure)

    selected = call(reference="owner:request:workspace-resources:resources/propose/v1")
    # Stable identity selects an exact current template; selecting executes nothing.
    reference = selected
    assert reference["status"] == "current"
    step = reference["next_step"]
    schema = step["answer_schema"]["properties"]["request"]
    assert schema["required"] == ["operation"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["path"]["type"] == ["string", "null"]
    assert schema["properties"]["disposable_outputs"]["items"] == {"type": "string"}
    carried = consume(
        surface,
        shared_core_binary,
        native_cli,
        reference["reentry"]
        | {"reference": step["reference"], "answer": {"request": {"operation": "scratch-create"}}, "projection": "carried"},
    )
    request = carried["carriage"]["context"]["request"]
    if isinstance(request, list):
        request = next(r for r in request if r["owner"] == "workspace-resources")
    proposed = call(request=request)
    proposal = proposed["resources"]["proposal"]
    path = Path(proposal["path"])
    assert not path.exists()

    action_ref = call(request=request, reference="owner:action:workspace-resources:workspace.resources.scratch-create")
    assert action_ref["status"] == "current"
    assert action_ref["value"]["arguments"] == proposal["action"]
    assert not path.exists()
    injected = copy.deepcopy(request)
    injected["arguments"]["request"] = proposal["action"]["request"]
    with pytest.raises(AssertionError, match="proposal cannot execute"):
        call(request=injected)
    executed = call(invocation=action_ref["value"])
    assert executed["effect_outcome"]["status"] == "committed"
    assert path.is_dir()
    # A new snapshot does not permit replay of the pre-create exact action.
    stale = call(invocation=action_ref["value"], allow_failure=True)
    assert stale["effect_outcome"]["status"] == "rejected-before-effect"
    remove = call()["resources"]["requests"][0]
    remove["arguments"]["request"] = {"operation": "scratch-remove", "path": proposal["action"]["request"]["path"]}
    ready = call(request=remove)
    removed = call(invocation=ready["decision_packet"]["primary_action"])
    assert removed["effect_outcome"]["status"] == "committed"
    assert not path.exists()


def test_resource_reference_keeps_protection_and_policy_drift(tmp_path, shared_core_binary, native_cli):
    context = {"target": str(tmp_path), "task": "Prepare bounded scratch"}

    def call(**extra):
        failure = extra.pop("allow_failure", False)
        return consume("json", shared_core_binary, native_cli, context | extra, allow_failure=failure)

    request = call()["resources"]["requests"][0]
    request["arguments"]["request"] = {"operation": "scratch-create"}
    proposed = call(request=request)
    action = proposed["decision_packet"]["primary_action"]
    path = Path(proposed["resources"]["proposal"]["path"])
    source = tmp_path / ".agentic-workspace/instructions/resources.md"
    source.parent.mkdir(parents=True)
    source.write_text("---\nprotect: [.agentic-workspace/local/scratch/**]\n---\nPreserve resource material.\n")
    blocked = call(request=call()["resources"]["requests"][0] | {"arguments": request["arguments"]})
    assert not blocked["resources"]["proposal"].get("action")
    assert not path.exists()
    rejected = call(invocation=action, allow_failure=True)
    assert rejected["effect_outcome"]["status"] == "rejected-before-effect"
    assert not path.exists()


def test_resource_reference_preserves_explicit_route_dependency(tmp_path, shared_core_binary, native_cli):
    import json

    context = {"target": str(tmp_path), "task": "Prepare temporary material"}
    registry = tmp_path / "tools/skills/REGISTRY.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"skills": [{"id": "sample", "semantic_routes": ["sample/protected"]}]}))
    source = tmp_path / ".agentic-workspace/instructions/resource.md"
    source.parent.mkdir(parents=True)
    source.write_text("---\nroutes: [sample/protected]\nprotect: [.agentic-workspace/local/scratch/**]\n---\nPreserve resource material.\n")

    def call(**extra):
        failure = extra.pop("allow_failure", False)
        return consume("json", shared_core_binary, native_cli, context | extra, allow_failure=failure)

    request = call()["resources"]["requests"][0]
    request["arguments"]["request"] = {"operation": "scratch-create"}
    unresolved = call(request=request)
    assert not unresolved["resources"]["proposal"].get("action")
    route = next(r for r in unresolved["resources"]["proposal"]["route_requests"] if r["request_kind"] == "semantic-routes/select/v1")
    route["arguments"] = {"posture": "none", "routes": []}
    request["arguments"]["request"]["route_request"] = route
    ready = call(request=request)
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "workspace.resources.scratch-create"
    assert call(invocation=action)["effect_outcome"]["status"] == "committed"
