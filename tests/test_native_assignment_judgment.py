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
    uncertain[-1]["arguments"]["uncertainties"] = [
        "Comparative elapsed cost is sparsely observed; this bounded choice retains that uncertainty."
    ]
    observation = call(uncertain)["task_requirements"]["assignment"]["result"]
    assert observation["status"] == "assigned-nonlocal-handoff-required"
    assert observation["judgment"]["uncertainties"] == uncertain[-1]["arguments"]["uncertainties"]
    assert (
        observation["assignment_identity"]["assignment_decision_revision"] != result["assignment_identity"]["assignment_decision_revision"]
    )
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


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_current_target_scope_and_known_manual_result_mismatch(tmp_path, shared_core_binary, native_cli, surface):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    original = (
        BASE
        + '[delegation_targets.bounded]\nstrength="medium"\nforbidden_task_classes=["boundary-shaping"]\ntransports=[{kind="manual"}]\n'
    )
    original += "[runtime]\nsupports_internal_delegation=true\nstrong_planner_available=true\n"
    source.write_text(original)
    context = {"target": str(tmp_path), "task": "Repair an authority boundary", "changed": ["owner.rs"]}

    def call(request=None, **updates):
        return consume(
            surface, shared_core_binary, native_cli, {**context, **updates, **({"request": request} if request is not None else {})}
        )

    task = call()["task_requirements"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["unapplied-patch"]
    pending = call(task)["task_requirements"]
    assert pending["execution_configurations"]["target_scope_questions"][0]["restrictions"] == ["boundary-shaping"]
    assert pending["assignment"]["result"]["unresolved_alternatives"]
    task = pending["requests"][0]
    task["arguments"]["required_result_classes"] = ["unapplied-patch"]
    task["arguments"]["target_scope"]["bounded"] = {"status": "applies", "reason": "This task changes an authority boundary."}
    denied = call(task)["task_requirements"]
    assert all(
        not row["eligible"]
        for row in denied["execution_configurations"]["configurations"]["candidates"]
        if row["configuration"]["target"] == "bounded"
    )
    request = denied["assignment"]["requests"][0]
    request[-1]["arguments"].update(alternative="local:internal", reason="Current target is the eligible patch executor.")
    admitted = call(request)
    assert admitted["task_requirements"]["assignment"]["result"]["local_assignment_satisfied"] is True
    assert not any("effect:implementation" in b["affects"] for b in admitted["decision_packet"]["blockers"])
    assert any("effect:delegation" in b["affects"] for b in admitted["decision_packet"]["blockers"])
    assert source.read_text() == original

    # A non-applicable restriction is not a capability grant: manual remains read-only.
    task["arguments"]["target_scope"]["bounded"] = {
        "status": "not-applicable",
        "reason": "A bounded mechanical implementation of the already-decided boundary.",
    }
    observed = call(task)["task_requirements"]
    manual = observed["execution_configurations"]["manual_targets"][0]
    assert manual["required_result_classes_supported"] is False
    request = observed["assignment"]["requests"][0]
    request[-1]["arguments"].update(alternative="local:internal", reason="Only the current configuration can return the required patch.")
    assert call(request)["task_requirements"]["assignment"]["result"]["local_assignment_satisfied"] is True
    # The same manual alternative is viable for a read and must remain unresolved.
    task["arguments"]["required_result_classes"] = ["read-only"]
    assert call(task)["task_requirements"]["assignment"]["result"]["unresolved_alternatives"]
    with pytest.raises(AssertionError, match="stale|changed"):
        call(request, task="Different work")
    forged = copy.deepcopy(task)
    forged["arguments"]["target_scope"]["unknown"] = {"status": "not-applicable", "reason": "Unowned"}
    with pytest.raises(AssertionError, match="restriction"):
        call(forged)
    source.write_text(original.replace("boundary-shaping", "reasoning-heavy"))
    with pytest.raises(AssertionError, match="stale|changed"):
        call(request)
    source.write_text(original.replace("[runtime]", 'revision_policy="revalidate"\n[runtime]'))
    fresh_task = call()["task_requirements"]["requests"][0]
    fresh_task["arguments"].update(
        required_result_classes=["unapplied-patch"],
        target_scope={"bounded": {"status": "applies", "reason": "The boundary-shaping restriction applies."}},
    )
    fresh = call(fresh_task)["task_requirements"]["assignment"]["requests"][0]
    fresh[-1]["arguments"].update(alternative="local:internal", reason="Current executor remains eligible.")
    retained = call(fresh)
    assert retained["task_requirements"]["assignment"]["result"]["local_assignment_satisfied"] is True
    assert any(
        b["code"].endswith("delegation_targets.bounded") and "effect:implementation" in b["affects"]
        for b in retained["decision_packet"]["blockers"]
    ), "Unconsumed lifecycle policy is not cleared by Assignment"
    source.write_text(original)
    assert source.read_text() == original
    assert not (tmp_path / ".agentic-workspace/local").exists()
