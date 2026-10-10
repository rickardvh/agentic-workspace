"""Current comparative judgments never grant capabilities or erase manual intent."""

from __future__ import annotations

import copy
import os

import pytest
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli

BASE = '[delegation]\nassignment_policy="required-best-fit"\ncurrent_target="local"\ntransport_authority="manual"\n[delegation_targets.local]\ntransports=[{kind="internal"}]\n'


@pytest.mark.parametrize("policy", ["best-fit-advisory", "required-best-fit"])
def test_compact_policy_posture_preserves_assignment_scope(tmp_path, shared_core_binary, native_cli, policy):
    """An unresolved recommendation is not a binding implementation gate."""
    import hashlib

    from tests.test_native_execution_configurations import fixture

    source, _, context = fixture(tmp_path)
    source.write_text(
        source.read_text()
        .replace("required-best-fit", policy)
        .replace("[delegation_targets.worker]\n", '[delegation_targets.worker]\nforbidden_task_classes=["mixed"]\n')
    )
    (tmp_path / ".agentic-workspace/config.toml").write_text("[assurance]\nstrict_closeout=true\n")
    binding = policy == "required-best-fit"

    def call(value):
        return consume("native", shared_core_binary, native_cli, {**value, "projection": "compact"})

    def answer(view, fields):
        return call({**view["reentry"], "reference": view["assignment_context"]["next_step"]["reference"], "answer": fields})

    initial = call(context)
    assert set(initial["assignment_context"]["next_step"]["answer_shape"]["target_scope"]["worker"]) == {"status", "reason"}
    scope = {"worker": {"status": "not-applicable", "reason": "This fixture asks for a bounded source inspection, not mixed work."}}
    offered = answer(initial, {"required_result_classes": ["unapplied-patch"], "target_scope": scope})
    unavailable = answer(
        initial, {"required_result_classes": ["unapplied-patch"], "required_proof_classes": ["independent-evidence"], "target_scope": scope}
    )
    for view in [initial, offered, unavailable]:
        posture = view["assignment_context"]
        assert posture["policy_mode"] == policy and posture["binding"] is binding
        assert posture["local_continuation_allowed"] is (not binding)
        assert posture["status"] == ("assessment-required" if binding else "not-required")
        assert ("effect:implementation" in posture["affects"]) is binding
        assert posture["policy_source"]["revision"]
        assert posture["policy_source"]["sources"] == [
            {
                "reference": ".agentic-workspace/config.local.toml",
                "revision": "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest(),
                "status": "current",
            }
        ]
        assert posture["next_step"]["reference"]
        blockers = view["decision_packet"]["blockers"]
        assert any(b["owner"] == "assignment" and "effect:implementation" in b["affects"] for b in blockers) is binding
        assert any(b["owner"] == "verification" and "claim:complete" in b["affects"] for b in blockers)
    assert unavailable["assignment_context"]["ineligible_configurations"]
    assert not (tmp_path / "marker.txt").exists()


def test_verification_transitions_keep_execution_judgment_and_recover_changed_obligation(tmp_path, shared_core_binary, native_cli):
    """Closeout choices do not invalidate unrelated executor capabilities."""
    from tests.test_native_execution_configurations import fixture

    source, _, context = fixture(tmp_path)
    config = tmp_path / ".agentic-workspace/config.toml"
    config.write_text('[assurance]\ndefault_level="medium"\n')
    manifest = tmp_path / ".agentic-workspace/verification/manifest.toml"
    manifest.parent.mkdir()
    manifest.write_text(
        'schema_version="agentic-workspace/verification-manifest/v1"\n'
        '[assurance.requirements.semantic]\nforce="required-before-closeout"\nlevel="medium"\n'
        'proof_profile="required"\napplies_to_task_markers=["different purpose"]\n'
        '[assurance.proof_profiles.required]\nrequired_commands=["echo current"]\n'
        '[protocols.semantic]\npurpose="Independent bounded evidence"\ncommands=[]\n'
        'applies_to_task_markers=["different purpose"]\nreview_owner="independent-maintainer"\n'
    )

    def call(value):
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    def answer(view, reference, value):
        return call({"request": view["carriage"], "reference": reference, "answer": value, "projection": "carried"})

    def owner(view, kind):
        return call({"request": view["carriage"], "reference": f"owner:request:verification:{kind}"})["reference"]

    initial = call({**context, "projection": "carried"})
    offered = answer(initial, initial["view"]["assignment_context"]["next_step"]["reference"], {"required_result_classes": ["read-only"]})
    current = answer(
        offered,
        offered["view"]["assignment_context"]["next_step"]["reference"],
        {"alternative": "local:internal", "reason": "Local meets the bounded read; a worker handoff adds no required capability."},
    )
    assignment_answers = [r for r in current["carriage"]["context"]["request"] if r["owner"] == "assignment"]
    assert current["view"]["assignment_context"]["local_continuation_allowed"] is True
    scope = {"semantic": "not-applicable", "protocol:semantic": "not-applicable"}
    for kind, value in (
        ("verification/assurance-applicability/v1", {"decisions": scope}),
        ("verification/strategy/v1", {"level": "medium", "profile_ids": ["required"], "reason": "Cover the selected bounded source."}),
    ):
        current = answer(current, owner(current, kind), value)
        assert current["view"]["assignment_context"]["local_continuation_allowed"] is True
        assert [r for r in current["carriage"]["context"]["request"] if r["owner"] == "assignment"] == assignment_answers

    # Newly applicable obligation declarations are a legitimate dependency change.
    # The submitted stale Assignment envelopes remain unusable; the answered
    # Verification request reaches a current, exact Assignment question instead.
    recovered = answer(
        current, owner(current, "verification/assurance-applicability/v1"), {"decisions": {**scope, "protocol:semantic": "applicable"}}
    )
    assignment = recovered["view"]["assignment_context"]
    assert assignment["local_continuation_allowed"] is False
    assert assignment["recovery"]["status"] == "stale-assignment-rejected"
    assert assignment["recovery"]["affected_judgment"] == "assignment/judge-task-requirements/v1"
    assert assignment["next_step"]["reference"]
    assert all(r["owner"] != "assignment" for r in recovered["carriage"]["context"]["request"])
    assert any("effect:implementation" in b["affects"] for b in recovered["view"]["decision_packet"]["blockers"])
    with pytest.raises(AssertionError, match="changed|stale"):
        call({**recovered["carriage"]["context"], "request": [*recovered["carriage"]["context"]["request"], *assignment_answers]})

    # A genuine proof capability requirement cannot be smuggled through the
    # preserved comparison. The ordinary fresh answer retains its honest gap.
    changed_requirements = copy.deepcopy(current["carriage"]["context"])
    next(r for r in changed_requirements["request"] if r["request_kind"] == "assignment/judge-task-requirements/v1")["arguments"][
        "required_proof_classes"
    ] = ["independent-evidence"]
    with pytest.raises(AssertionError, match="source changed|stale"):
        call(changed_requirements)
    fresh = call({**context, "projection": "carried"})
    denied = answer(
        fresh,
        fresh["view"]["assignment_context"]["next_step"]["reference"],
        {"required_result_classes": ["unapplied-patch"], "required_proof_classes": ["independent-evidence"]},
    )
    assert denied["view"]["assignment_context"]["local_continuation_allowed"] is False
    assert denied["view"]["assignment_context"]["ineligible_configurations"]
    for changed_context in ({"task": "Different work"}, {"changed": []}):
        with pytest.raises(AssertionError, match="changed|stale"):
            call({**current["carriage"]["context"], **changed_context})
    source.write_text(source.read_text() + 'forbidden_task_classes=["boundary-shaping"]\n')
    with pytest.raises(AssertionError, match="changed|stale"):
        call(current["carriage"]["context"])


def test_compact_assignment_answers_preserve_owner_context(tmp_path, shared_core_binary, native_cli):
    """The ordinary caller answers questions, without reading request bundles."""
    from tests.test_native_execution_configurations import fixture

    source, _, context = fixture(tmp_path)
    # Relative targets and omitted optional fields must round-trip exactly;
    # the returned work context must not introduce invalid material=null.
    context["target"] = os.path.relpath(tmp_path)

    def call(value):
        return consume("native", shared_core_binary, native_cli, {**value, "projection": "compact"})

    def answer(view, material):
        step = view["assignment_context"]["next_step"]
        return call({**view["reentry"], "reference": step["reference"], "answer": material})

    initial = call(context)
    assert initial["assignment_context"]["local_continuation_allowed"] is False
    unavailable = answer(initial, {"required_result_classes": ["unapplied-patch"], "required_proof_classes": ["independent-evidence"]})
    assert unavailable["assignment_context"]["local_continuation_allowed"] is False
    assert unavailable["assignment_context"]["ineligible_configurations"]
    recovered = answer(unavailable, {"required_proof_classes": []})
    assert recovered["assignment_context"]["alternatives"]
    offered = answer(initial, {"required_result_classes": ["read-only"]})
    comparison = offered["assignment_context"]
    assert {a["id"] for a in comparison["alternatives"]} == {"local:internal", "worker:cli"}
    current = answer(
        offered,
        {
            "alternative": "local:internal",
            "reason": "The local executor meets this bounded read; a worker handoff adds preparation without a needed capability.",
        },
    )
    assert current["assignment_context"]["local_continuation_allowed"] is True
    assert "next_step" not in current["assignment_context"]
    assert "task_requirements" not in current
    assert not (tmp_path / ".agentic-workspace/local").exists()
    nonlocal_result = answer(offered, {"alternative": "worker:cli", "reason": "Use the eligible worker for this independent read."})
    assert nonlocal_result["assignment_context"]["local_continuation_allowed"] is False
    assert any("effect:implementation" in b["affects"] for b in nonlocal_result["decision_packet"]["blockers"])

    # A direct task has no source-shaped defaults. Capture changes the issued
    # input source; an older answer still appears in comparison prerequisites.
    # The compact next step must name the current capture, without inspecting
    # or rewriting immutable request identities.
    def prepare(view, fields):
        step = view["assignment_context"]["handoff_preparation"]["next_step"]
        return call({**view["reentry"], "reference": step["reference"], "answer": fields})

    # Prepare before explicit comparison: changing preparation correctly
    # invalidates an older comparative judgment.
    captured = prepare(offered, {"input_refs": ["a.txt"], "complete": False, "reason": "Observe the exact bounded inspection source."})
    prepared = prepare(captured, {"complete": True, "reason": "The observed source fully describes this independent read."})
    assert prepared["assignment_context"]["handoff_preparation"]["status"] == "ready"
    delegated = answer(
        prepared, {"alternative": "worker:cli", "reason": "The prepared bounded read reuses captured context with this eligible worker."}
    )
    assert delegated["assignment_context"]["handoff_preparation"]["sealed_handoff_status"] == "export-ready"
    assert not (tmp_path / "marker.txt").exists()
    (tmp_path / "a.txt").write_text("Changed after capture")
    with pytest.raises(AssertionError, match="changed|stale"):
        prepare(captured, {"complete": True, "reason": "An old observation cannot authorize changed input."})
    (tmp_path / "a.txt").write_text("current")
    with pytest.raises(AssertionError, match="stale|changed|unknown"):
        call(
            {
                **offered["reentry"],
                "task": "Different work",
                "reference": comparison["next_step"]["reference"],
                "answer": {"alternative": "local:internal", "reason": "Old choice"},
            }
        )

    # A sole eligible local executor settles in two calls, with no essay.
    source.write_text(BASE)
    settled = answer(call(context), {"required_result_classes": ["read-only"]})
    assert settled["assignment_context"]["determination"] == "sole-eligible-configuration"
    assert settled["assignment_context"]["local_continuation_allowed"] is True
    assert "next_step" not in settled["assignment_context"]
    # Source prohibitions are visible in the first question, without transport
    # discovery; unknown applicability cannot silently admit the local target.
    source.write_text(BASE + 'forbidden_task_classes=["boundary-shaping"]\n')
    first = call(context)
    assert first["assignment_context"]["target_scope_questions"][0]["target"] == "local"
    denied = answer(
        first,
        {
            "required_result_classes": ["read-only"],
            "target_scope": {"local": {"status": "applies", "reason": "This task changes a boundary."}},
        },
    )
    assert denied["assignment_context"]["local_continuation_allowed"] is False


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
    assert first["task_requirements"]["implementation_admission"]["status"] == "assessment-required"
    compact = call(projection="compact")
    recovery = next(row for row in compact["consequence_recovery"] if row["owner"] == "assignment")
    restricted = {row["consequence_id"] for row in compact["decision_packet"]["blockers"] if "effect:implementation" in row["affects"]}
    assert restricted <= {row["consequence_id"] for row in recovery["consequences"]}
    route = next(row for row in recovery["routes"] if row["selector"] == "/task_requirements")
    task = call(reference=route["reference"])["value"]["requests"][0]
    task["arguments"]["required_result_classes"] = ["read-only"]
    offered = call(task)["task_requirements"]["assignment"]
    assert offered["result"]["status"] == "assigned-current-target"
    assert offered["result"]["determination"] == "sole-eligible-configuration"
    assert offered["result"]["judgment"] is None
    request = offered["requests"][0]
    request[-1]["arguments"]["alternative"] = "local:internal"
    request[-1]["arguments"]["reason"] = "This bounded read requires no external capability; the current local configuration is sufficient."
    current = call(request)
    assert current["task_requirements"]["assignment"]["result"]["status"] == "assigned-current-target"
    assert current["task_requirements"]["implementation_admission"]["status"] == "admitted-local"
    assert current["task_requirements"]["implementation_admission"]["historical_compliance"] == "not-established"
    assert not any(b["code"] == "current-binding-assignment-required" for b in current["decision_packet"]["blockers"])
    assert not any("effect:implementation" in b["affects"] for b in current["decision_packet"]["blockers"])
    assert not current.get("consequence_recovery")
    assert current["decision_packet"].get("primary_action") is None
    assert not (tmp_path / ".agentic-workspace/local").exists()
    with pytest.raises(AssertionError, match="stale|changed"):
        call(request, task="Implement a different change")
    forged = copy.deepcopy(request)
    forged[-1]["arguments"]["alternative"] = "unlisted"
    with pytest.raises(AssertionError, match="admitted"):
        call(forged)
    source.write_text(BASE + '\n[delegation_targets.expert]\ntransports=[{kind="manual"}]\n')
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
    assert current["task_requirements"]["implementation_admission"]["status"] == "admitted-nonlocal"
    assert current["task_requirements"]["implementation_admission"]["local_continuation_allowed"] is False
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
    source.write_text('[delegation]\nassignment_policy="required-best-fit"\n')
    blocked = call()
    assert any(b["code"] == "binding-policy-current-target-unresolved" for b in blocked["decision_packet"]["blockers"])


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_unobserved_provider_cannot_be_dismissed_by_local_assessment(tmp_path, shared_core_binary, native_cli, surface):
    source = tmp_path / ".agentic-workspace/config.local.toml"
    source.parent.mkdir()
    source.write_text(
        BASE
        + '[delegation_targets.native]\ntransports=[{kind="native",adapter="provider-owned",parameters={},command=["unavailable-worker"]}]\n'
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
    original = BASE + '[delegation_targets.bounded]\nforbidden_task_classes=["boundary-shaping"]\ntransports=[{kind="manual"}]\n'
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
    source.write_text(original)
    assert source.read_text() == original
    assert not (tmp_path / ".agentic-workspace/local").exists()
