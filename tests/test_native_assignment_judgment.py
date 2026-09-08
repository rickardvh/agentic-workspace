"""Current comparative judgments never grant capabilities or erase manual intent."""

from __future__ import annotations

import copy

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

BASE = 'schema_version=1\n[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\ntransport_authority="manual"\n[delegation_targets.local]\nstrength="weak"\ntransports=[{kind="internal"}]\n'


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_current_comparison_and_stale_work_preserve_binding(tmp_path, shared_core_binary, native_cli, surface):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(BASE)
    context = {"target": str(tmp_path), "task": "Inspect current source", "changed": []}

    def call(request=None, **updates):
        return consume(
            surface, shared_core_binary, native_cli, {**context, **updates, **({"request": request} if request is not None else {})}
        )

    first = call()
    assert any(b["code"] == "current-binding-assignment-required" for b in first["decision_packet"]["blockers"])
    task = first["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    offered = call(task)["task_requirements"]["assignment"]
    request = offered["requests"][0]
    request[-1]["arguments"]["alternative"] = "local:internal"
    request[-1]["arguments"]["reason"] = "This bounded read requires no external capability; the current local configuration is sufficient."
    current = call(request)
    assert current["task_requirements"]["assignment"]["result"]["status"] == "assigned-current-target"
    assert not any(b["code"] == "current-binding-assignment-required" for b in current["decision_packet"]["blockers"])
    assert current["decision_packet"].get("primary_action") is None
    assert not (tmp_path / ".agentic-workspace/local").exists()
    with pytest.raises(AssertionError, match="stale|changed"):
        call(request, task="Implement a different change")
    forged = copy.deepcopy(request)
    forged[-1]["arguments"]["alternative"] = "unlisted"
    with pytest.raises(AssertionError, match="admitted"):
        call(forged)
    source.write_text(BASE + '\n[delegation_targets.expert]\nstrength="strong"\ntransports=[{kind="manual"}]\n')
    with pytest.raises(AssertionError, match="stale|changed"):
        call(request)
    fresh = call()
    newtask = fresh["task_requirements"]["requests"][0]
    newtask["arguments"]["required_result_classes"] = ["read-only"]
    alternatives = call(newtask)["task_requirements"]["assignment"]
    manual = copy.deepcopy(alternatives["requests"][0])
    manual[-1]["arguments"]["alternative"] = "unresolved-target:expert"
    manual[-1]["arguments"]["reason"] = "Domain evaluation belongs with the configured expert; retain unresolved handoff."
    pending = call(manual)
    assert pending["task_requirements"]["assignment"]["result"]["status"] == "unresolved-assessment"
    assert pending["task_requirements"]["assignment"]["result"]["assignment_identity"] is None
    assert any(b["code"] == "current-binding-assignment-required" for b in pending["decision_packet"]["blockers"])
    local = copy.deepcopy(alternatives["requests"][0])
    local[-1]["arguments"]["alternative"] = "local:internal"
    local[-1]["arguments"]["reason"] = "Local appears sufficient but cannot dismiss unknown expert feasibility."
    assert call(local)["task_requirements"]["assignment"]["result"]["local_assignment_satisfied"] is False
    assert source.read_text().endswith('transports=[{kind="manual"}]\n')


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_nonlocal_assignment_keeps_exact_handoff_gap_and_uncertainty(tmp_path, shared_core_binary, native_cli, surface):
    from tests.test_native_execution_configurations import fixture

    source, executable, context = fixture(tmp_path)
    source.write_text(source.read_text().replace("[delegation]\n", '[delegation]\nassignment_policy="required-best-fit"\n'))

    def call(request=None):
        return consume(surface, shared_core_binary, native_cli, {**context, **({"request": request} if request else {})})

    first = call()
    task = first["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    offered = call(task)["task_requirements"]["assignment"]
    request = offered["requests"][0]
    request[-1]["arguments"]["alternative"] = "worker:cli"
    request[-1]["arguments"]["reason"] = "The current worker configuration is the preferred bounded execution route."
    current = call(request)
    result = current["task_requirements"]["assignment"]["result"]
    assert result["status"] == "assigned-nonlocal-handoff-required"
    assert result["assignment_identity"]["selected"]["configuration"]["execution"]
    local = copy.deepcopy(request)
    local[-1]["arguments"]["alternative"] = "local:internal"
    local[-1]["arguments"]["reason"] = "The current local configuration is sufficient for this bounded comparison."
    local_result = call(local)["task_requirements"]["assignment"]["result"]
    assert local_result["status"] == "assigned-current-target"
    assert (
        local_result["assignment_identity"]["assignment_decision_revision"] != result["assignment_identity"]["assignment_decision_revision"]
    )

    assert any(b["code"] == "current-nonlocal-assignment-handoff-required" for b in current["decision_packet"]["blockers"])
    assert current["decision_packet"].get("primary_action") is None
    uncertain = copy.deepcopy(request)
    uncertain[-1]["arguments"]["uncertainties"] = ["Current evaluator comparison remains unresolved."]
    assert call(uncertain)["task_requirements"]["assignment"]["result"]["assignment_identity"] is None
    executable.write_text("changed executable")
    with pytest.raises(AssertionError, match="stale|changed"):
        call(request)
    assert not (tmp_path / "marker.txt").exists()
    assert not (tmp_path / ".agentic-workspace/local").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_binding_without_targets_remains_owned_and_empty_checkout_quiet(tmp_path, shared_core_binary, native_cli, surface):
    context = {"target": str(tmp_path), "task": "Read a document", "changed": []}

    def call():
        return consume(surface, shared_core_binary, native_cli, context)

    quiet = call()
    assert quiet["task_requirements"]["assignment"]["status"] == "not-applicable"
    assert not any(b.get("owner") == "assignment" for b in quiet["decision_packet"]["blockers"])
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text('schema_version=1\n[delegation]\nassignment_policy="required-best-fit"\n')
    blocked = call()
    assert any(b["code"] == "binding-policy-current-target-unresolved" for b in blocked["decision_packet"]["blockers"])


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_unobserved_provider_cannot_be_dismissed_by_local_assessment(tmp_path, shared_core_binary, native_cli, surface):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(
        BASE + '[delegation_targets.native]\nstrength="strong"\ntransports=[{kind="native",adapter="provider-owned",parameters={}}]\n'
    )
    context = {"target": str(tmp_path), "task": "Inspect current source", "changed": []}

    def call(request=None):
        return consume(surface, shared_core_binary, native_cli, {**context, **({"request": request} if request else {})})

    task = call()["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    offered = call(task)["task_requirements"]["assignment"]
    assert len(offered["requests"]) == 1
    request = offered["requests"][0]
    request[-1]["arguments"].update(
        alternative="local:internal", reason="Local appears sufficient, but provider capability is still unknown."
    )
    result = call(request)
    assert result["task_requirements"]["assignment"]["result"]["status"] == "unresolved-assessment"
    assert any(b["code"] == "current-binding-assignment-required" for b in result["decision_packet"]["blockers"])
    assert not (tmp_path / ".agentic-workspace/local").exists()
