"""Remembered plans stay inert until exact current work selects or resumes one."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.test_native_planning_create import material
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_remembered_plans_are_inert_until_explicit_binding(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    def call(context):
        return consume(surface, shared_core_binary, native_cli, context)

    def create(task):
        context = {"target": str(tmp_path), "task": task}
        request = call(context)["planning"]["creation_requests"][0]
        request["arguments"] = {"material": {**material(), "title": task}}
        action = call({**context, "request": request})["decision_packet"]["primary_action"]
        result = call({**context, "invocation": action})
        made = result["value"]
        context = result["continuation"]["context"]
        return context, tmp_path / made["owner_path"]

    first_context, first = create("First unfinished objective")
    first_bytes = first.read_bytes()
    _, second = create("Distinct unfinished objective")
    assert first.read_bytes() == first_bytes
    second_bytes = second.read_bytes()
    assert json.loads(first_bytes)["lifecycle"] == json.loads(second_bytes)["lifecycle"] == "planned"
    selector = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    remembered = selector.read_bytes()
    context = {"target": str(tmp_path), "task": "Unrelated direct work"}
    for absent in (False, True):
        if absent:
            second.unlink()  # Test-owned branch/source-absence fixture.
        before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        quiet = call(context)
        assert quiet["planning"]["status"] == "direct"
        assert quiet["planning"]["status_scope"] == "current-owner-obligations"
        assert quiet["planning"]["incumbent_owner"] is None
        assert quiet["planning"]["selected_owner"] is None
        assert quiet["planning"]["current_owner"] is None
        assert quiet["planning"]["terminal_retention"]["status"] == "quiet"
        assert not any(d["owner"] == "planning" for d in quiet["decision_packet"]["pending_consequences"]["decisions"])
        assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        resume = quiet["planning"]["selection_requests"][0]
        if absent:
            with pytest.raises(AssertionError, match="selected owner missing.*source checkout"):
                call({**context, "request": resume})
        else:
            selected = call({**context, "request": resume})
            assert selected["planning"]["selected_owner"]["ref"] == second.relative_to(tmp_path).as_posix()
            assert selected["planning"]["current_owner"]["current"] is True
    assert selector.read_bytes() == remembered
    # Selecting another owner does not depend on the old hint's missing source.
    resume = call(first_context)["planning"]["selection_requests"][0]
    resume["arguments"] = {"owner_ref": first.relative_to(tmp_path).as_posix()}
    ready = call({**first_context, "request": resume})
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.reconcile"
    call({**first_context, "invocation": action})
    assert call(first_context)["planning"]["selected_owner"]["ref"] == first.relative_to(tmp_path).as_posix()
    assert first.read_bytes() == first_bytes
    second.write_bytes(second_bytes)
    # Forged current binding identities remain fail-closed; quiet discovery is no authority.
    forged = call(context)["planning"]["selection_requests"][0]
    forged["task_identity"]["id"] = "another-task"
    with pytest.raises(AssertionError):
        call({**context, "request": forged})
    # Advisory work metadata cannot forge a new producer binding.
    record = json.loads(selector.read_text())
    record["reconciliation"]["current_work"] = call(context)["planning"]["selection_requests"][0]["task_identity"]
    selector.write_text(json.dumps(record))
    with pytest.raises(AssertionError, match="current work differs from its retained Planning producer"):
        call(context)
    # Malformed remembered custody is inert for unrelated work, strict on resume.
    selector.write_text("{malformed")
    quiet = call(context)
    assert quiet["planning"]["status"] == "direct"
    with pytest.raises(AssertionError):
        call({**context, "request": quiet["planning"]["selection_requests"][0]})
    assert selector.read_text() == "{malformed"
