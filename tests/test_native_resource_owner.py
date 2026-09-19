"""Generic exact owner references retain the direct resource primitive's bounds."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


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
    request = reference["value"]
    request["arguments"]["request"] = {"operation": "scratch-create"}
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
