"""Current semantic scope reaches exact proof choices without granting proof."""

from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest
from tests.test_native_proof_procedure import install, procedure
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_named_scope_journey_and_stale_controls(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    source = tmp_path / ".agentic-workspace/verification/manifest.toml"
    source.parent.mkdir(parents=True)
    source.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n'
        '[protocols.semantic]\napplies_to_task_markers=["semantic task"]\n'
        'applies_to_paths=["exact.txt"]\ncommands=["echo protocol"]\n[proof_routes]\n'
        '[assurance.domain_proof_lanes.semantic]\npurpose="A named semantic lane"\n'
        'applies_to_task_markers=["domain task"]\ncommands=["echo domain"]\n'
    )
    (tmp_path / "a.txt").write_text("subject")
    context = {"target": str(tmp_path), "task": "semantic task domain task", "changed": ["a.txt"]}
    install(tmp_path)

    def call(value):
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    initial = call(context)["verification"]
    assert initial["execution_requests"] == []  # Words in the task are not selectors.
    scope = initial["assurance_request"]
    assert scope["arguments"]["decisions"] == {"domain:semantic": "unresolved", "protocol:semantic": "unresolved"}
    scope["arguments"]["decisions"] = {key: "applicable" for key in scope["arguments"]["decisions"]}
    selected = call({**context, "request": scope})["verification"]
    assert selected["assurance_owner_gaps"] == []  # Proof scope is not an evidence requirement.
    assert "semantic" in selected["strategy"]["protocols"]
    exact = next(r for r in selected["execution_requests"] if r[-1]["arguments"]["route_id"] == "domain:semantic")
    action = call({**context, "request": exact})["decision_packet"]["primary_action"]
    result = call({**context, "invocation": action})
    assert result["value"]["process"]["status"] == "passed"
    assert result["value"]["claim_boundary"]["completion_claim_allowed"] is False
    assert call({**context, "invocation": action})["value"] == result["value"]
    composed = procedure(shared_core_binary, context, "execute", request=exact)
    assert composed["proof"]["evidence"][0]["checked_scope"]["claim"] == "selected-command-passed"
    assert composed["effect"]["value"] == result["value"]
    rejected = copy.deepcopy(scope)
    rejected["arguments"]["decisions"] = {key: "not-applicable" for key in scope["arguments"]["decisions"]}
    negative = call({**context, "request": rejected})["verification"]
    assert negative["execution_requests"] == [] and negative["assurance_request"] is None
    stale = call({**context, "task": "Another outcome", "request": scope})["verification"]
    assert stale["execution_requests"] == [] and stale["assurance_request"] is not None
    unknown = copy.deepcopy(scope)
    unknown["arguments"]["decisions"]["domain:invented"] = "applicable"
    with pytest.raises(AssertionError, match="unknown requirement"):
        call({**context, "request": unknown})
    expanded = copy.deepcopy(scope)
    expanded["arguments"]["paths"] = ["**"]
    with pytest.raises(AssertionError):
        call({**context, "request": expanded})
    (tmp_path / "exact.txt").write_text("positive path")
    direct = {**context, "changed": ["exact.txt"]}
    path_scope = call(direct)["verification"]["assurance_request"]
    path_scope["arguments"]["decisions"] = {"protocol:semantic": "not-applicable", "domain:semantic": "not-applicable"}
    positive = call({**direct, "request": path_scope})["verification"]
    assert "semantic" in positive["strategy"]["protocols"]
    source.write_text(source.read_text().replace("echo domain", "echo changed"))
    expired = call({**context, "request": scope})["verification"]
    assert expired["execution_requests"] == [] and expired["assurance_request"] is not None
    source.write_text('schema_version="agentic-workspace/verification-manifest/v1"\n[protocols]\n[proof_routes]\n')
    quiet = call(context)["verification"]
    assert quiet["assurance_request"] is None and quiet["execution_requests"] == []
