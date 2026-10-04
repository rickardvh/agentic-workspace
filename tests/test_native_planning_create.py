"""Public creation uses one Rust owner, preserving selection and provenance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from tests.native_planning_fixtures import fixture_source
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize(
    "schema_path",
    [
        ".agentic-workspace/planning/schemas/planning-execplan.schema.json",
        "src/core/src/modules/planning/contracts/planning-execplan.schema.json",
    ],
)
def test_native_update_observation_schema(schema_path: str) -> None:
    schema = json.loads((ROOT / schema_path).read_text())
    validator = Draft202012Validator(schema)
    body = json.loads(fixture_source(".agentic-workspace/planning/execplans/v1-contraction-2983-2990.plan.json").read_text())
    validator.validate(body)
    for version in ["v1", "v2"]:
        body["update_provenance"]["kind"] = f"agentic-planning/update-provenance/{version}"
        validator.validate(body)
    body["update_provenance"]["kind"] = "agentic-planning/update-provenance/v3"
    assert list(validator.iter_errors(body))
    body["update_provenance"]["kind"] = "agentic-planning/update-provenance/v2"
    body["update_provenance"]["outcome"] = "not-an-outcome"
    assert list(validator.iter_errors(body))
    del body["update_provenance"]["outcome"]
    assert list(validator.iter_errors(body))


def material() -> dict:
    original = json.loads(fixture_source(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json").read_text())
    fields = [
        "title",
        "owner_level",
        "intent",
        "parent",
        "scope",
        "relationships",
        "next_action",
        "proof",
        "continuation",
        "canonical_core",
        "references",
        "blockers",
    ]
    value = {key: original[key] for key in fields}
    value["relationships"] = {"dependencies": {"refs": []}}
    value["material_lifetimes"] = {
        "next_action": "durable",
        "external_posture": "observation",
        "continuation_frontier": "durable",
    }
    return value


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("selector_mode", ["shared", "legacy-local"])
def test_real_former_owner_can_evolve_after_native_custody(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, selector_mode: str
) -> None:
    ref = Path(".agentic-workspace/planning/execplans/v1-contraction-2983-2990.plan.json")
    path = tmp_path / ref
    path.parent.mkdir(parents=True)
    path.write_bytes(fixture_source(ref).read_bytes())
    original = json.loads(path.read_bytes())
    state = tmp_path / ".agentic-workspace/planning/state.toml"
    state.write_text(f'[[active.execplans]]\nid="{original["id"]}"\npath="{ref.as_posix()}"\nstatus="active"\n')
    selector = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    legacy = {
        "kind": "agentic-planning/owner-selection/v1",
        "mode": "local",
        "current_work_id": "default",
        "selected_owner": {"id": original["id"], "ref": ref.as_posix()},
        "planning_revision": "former-producer-revision",
        "reason": "Selected owner through the established former Planning producer",
    }
    if selector_mode == "legacy-local":
        selector.parent.mkdir(parents=True)
        selector.write_text(json.dumps(legacy, indent=2) + "\n")
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("Preserve this concurrent work")
    context = {"target": str(tmp_path), "task": "Maintain the current reconstruction frontier"}

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value)

    def resume(value):
        quiet = call(value)
        request = quiet["planning"]["selection_requests"][0]
        request["arguments"] = {"owner_ref": ref.as_posix()}
        return call({**value, "request": request})

    first = resume(context)
    assert first["planning"]["update_requests"] == [], "source recognition is not mutation custody"
    continuation = first["planning"]["requests"][0]
    selected = call({**context, "request": continuation})
    if selector_mode == "legacy-local":
        assert selected["planning"]["status"] == "custody-required"
        before_selector = selector.read_bytes()
        question = selected["decision_packet"]["decision_request"]
        assert question["resolution"] == "bounded-domain-answer"
        assert not any(b["code"] == "planning-selection-custody-required" for b in selected["decision_packet"]["blockers"])
        assert selected["decision_packet"]["primary_action"] is None
        assert "human_context" not in question
        transfer = question["response_request"]
        assert "answer" not in transfer["arguments"], "the owner requires an exact domain answer"
        with pytest.raises(AssertionError):
            call({**context, "request": transfer})
        transfer["arguments"]["answer"] = "authorize-selector-transfer"
        # Even semantically identical selector bytes require a new decision.
        selector.write_bytes(before_selector + b" ")
        with pytest.raises(AssertionError):
            call({**context, "request": transfer})
        assert selector.read_bytes() == before_selector + b" "
        selector.write_bytes(before_selector)
        selected = call({**context, "request": transfer})
    action = selected["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.reconcile"
    if selector_mode == "legacy-local":
        policy = tmp_path / ".agentic-workspace/config.local.toml"
        policy.write_text("[workspace]\nenabled=false\n")
        call(context)
        current_answer = transfer.copy()
        current_answer["arguments"]["answer"] = "authorize-selector-transfer"
        with pytest.raises(AssertionError, match="workspace.enabled=false"):
            call({**context, "request": current_answer})
        with pytest.raises(AssertionError):
            call({**context, "invocation": action})
        assert selector.read_bytes() == before_selector
        assert path.read_bytes() == fixture_source(ref).read_bytes()
        policy.unlink()
    acquired = call({**context, "invocation": action})
    assert path.read_bytes() == fixture_source(ref).read_bytes(), "custody transfer cannot rewrite Planning material"
    if selector_mode == "legacy-local":
        transferred = json.loads(selector.read_bytes())
        assert {k: v for k, v in transferred.items() if k != "reconciliation"} == legacy
        retained = transferred["reconciliation"]
        assert retained["invocation"]["arguments"]["selection_transition"]["domain_authorization"] == transfer
        assert retained["custody"]["committed"]
        assert call({**context, "invocation": action})["value"] == acquired["value"]
        assert selector.read_bytes() == json.dumps(transferred, indent=2).encode()
        with pytest.raises(AssertionError):
            call({**context, "request": transfer})
    before = resume(context)
    subject = before["planning"]["current_owner"]["reconciliation"]["subject"]
    update = before["planning"]["update_requests"][0]
    value = {key: original[key] for key in [*material(), "lifecycle", "phase"] if key in original}
    # The current owner explicitly preserves the legacy work/frontier meaning
    # while classifying external posture as a nonauthoritative observation.
    value["material_lifetimes"] = material()["material_lifetimes"]
    value["next_action"] = "Finish the current P0/P1 owner audit before #2909 and exact #2990 admission"
    value["goal"] = ["Complete the current P0/P1 reconstruction owners before release admission"]
    value["intent_continuity"] = {
        **original["intent_continuity"],
        "this slice completes the larger intended outcome": "no",
        "continuation surface": "#2983 / #2909 / #2990",
    }
    update["arguments"]["material"] = value
    action = call({**context, "request": update})["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.update"
    forged = json.loads(json.dumps(action))
    forged["arguments"]["document"]["id"] = "replacement-identity"
    with pytest.raises(AssertionError):
        call({**context, "invocation": forged})
    assert path.read_bytes() == fixture_source(ref).read_bytes()
    applied = call({**context, "invocation": action})
    updated = json.loads(path.read_bytes())
    assert updated["id"] == original["id"]
    assert "creation_provenance" not in updated
    assert updated["update_provenance"]["kind"] == "agentic-planning/update-provenance/v2"
    assert str(tmp_path) not in path.read_text()
    assert all(ref["target"] == "." for ref in updated["update_provenance"]["custody"].values())
    # A fresh checkout retains source identity/frontier, but must acquire its
    # own native custody. Shared observations cannot impersonate a local writer.
    clone = tmp_path / "fresh-checkout"
    clone_path = clone / ref
    clone_path.parent.mkdir(parents=True)
    clone_path.write_bytes(path.read_bytes())
    clone_state = clone / state.relative_to(tmp_path)
    clone_state.write_bytes(state.read_bytes())
    clone_context = {**context, "target": str(clone)}
    observed = resume(clone_context)
    assert observed["planning"]["update_requests"] == []
    changed = {**updated, "next_action": "Unadmitted observation drift"}
    clone_path.write_text(json.dumps(changed))
    with pytest.raises(AssertionError, match="portable Planning"):
        changed_view = resume(clone_context)
        call({**clone_context, "request": changed_view["planning"]["requests"][0]})
    clone_path.write_bytes(path.read_bytes())
    malformed = json.loads(path.read_bytes())
    malformed["update_provenance"]["outcome"] = "not-an-outcome"
    clone_path.write_text(json.dumps(malformed))
    with pytest.raises(AssertionError, match="invalid portable Planning"):
        malformed_view = resume(clone_context)
        call({**clone_context, "request": malformed_view["planning"]["requests"][0]})
    clone_path.write_bytes(path.read_bytes())
    evidence = clone / updated["update_provenance"]["custody"]["attempt"]["path"]
    evidence.parent.mkdir(parents=True)
    evidence.write_text("{}")
    with pytest.raises(AssertionError):
        call({**clone_context, "request": observed["planning"]["requests"][0]})
    evidence.unlink()
    clone_action = call({**clone_context, "request": observed["planning"]["requests"][0]})["decision_packet"]["primary_action"]
    assert clone_action["operation_id"] == "planning.reconcile"
    call({**clone_context, "invocation": clone_action})
    admitted_clone = resume(clone_context)
    assert admitted_clone["planning"]["update_requests"]
    assert admitted_clone["planning"]["selected_owner"]["id"] == original["id"]
    assert admitted_clone["planning"]["current_owner"]["reconciliation"]["subject"]["id"] != subject["id"], (
        "custody subject remains target-bound"
    )
    assert value["next_action"] in str(admitted_clone)
    assert admitted_clone["decision_packet"]["status"] != "terminal"
    assert clone_path.read_bytes() == path.read_bytes()
    if surface == "native" and selector_mode == "shared":
        original_reentry = call(context)["planning"]["requests"][0]
        original_portable = call({**context, "request": original_reentry})["planning"]["portable_continuation"]
        assert admitted_clone["planning"]["portable_continuation"]["semantic_subject"] == original_portable["semantic_subject"]
    expected_relationships = dict(original["relationships"])
    expected_relationships.pop("external_posture", None)
    assert updated["relationships"] == expected_relationships
    for key in original:
        if key not in {"revision", "next_action", "goal", "intent_continuity", "update_provenance", "relationships"}:
            assert updated[key] == original[key], key
    assert call({**context, "invocation": action})["value"] == applied["value"]
    with pytest.raises(AssertionError):
        call({**context, "request": update})
    # The real former source follows the same exact uncertain-publication route.
    # Withhold only the producer's commit, never hand-author a successful result.
    (tmp_path / applied["custody"]["committed"]["path"]).unlink()
    context = {**context, "task": "Resume the same reconstruction owner after interruption"}
    pending = call(context)
    continuation = pending["planning"]["selection_requests"][0]
    assert not pending["planning"]["update_requests"]
    assert not pending["planning"]["update_recovery_requests"]
    admitted = call({**context, "request": continuation})
    recovery = admitted["planning"]["update_recovery_requests"][0]
    with pytest.raises(AssertionError):
        call({**context, "request": recovery})
    ready = admitted
    assert (
        ready["decision_packet"]["primary_action"]
        == call({**context, "request": [continuation, recovery]})["decision_packet"]["primary_action"]
    )
    recovered = call({**context, "invocation": ready["decision_packet"]["primary_action"]})
    assert recovered["value"]["material_written"] is False
    assert json.loads(path.read_bytes()) == updated
    fresh = resume(context)
    reentry = call({**context, "request": fresh["planning"]["requests"][0]})
    call({**context, "invocation": reentry["decision_packet"]["primary_action"]})
    current = call(context)
    reconciled = current["planning"]["current_owner"]["reconciliation"]
    assert reconciled["subject"]["id"] == subject["id"]
    assert reconciled["subject"]["revision"] != subject["revision"]
    assert value["next_action"] in str(reconciled)
    assert current["decision_packet"]["status"] != "terminal"
    assert unrelated.read_text() == "Preserve this concurrent work"
    # A same-material owner update no longer rewrites tracked source custody.
    unchanged_bytes = path.read_bytes()
    same = current["planning"]["update_requests"][0]
    same["arguments"]["material"] = value
    unchanged = call({**context, "request": same})
    assert unchanged["decision_packet"]["primary_action"] is None
    assert unchanged["planning"]["update_material_status"] == "unchanged"
    assert path.read_bytes() == unchanged_bytes
    assert call(context)["planning"]["current_owner"]["reconciliation"]["subject"] == reconciled["subject"]
    # Fresh unrelated task can stay direct without reactivating historical work.
    other = {**context, "task": "Explain this unrelated function"}
    quiet = call(other)
    assert quiet["planning"]["status"] == "direct"
    assert quiet["planning"]["incumbent_owner"] is None
    if surface == "native" and selector_mode == "legacy-local":
        # The acquired former selector can later select a new native owner.
        # Historical annotations stay in prior custody, not the successor shape.
        next_context = {**context, "task": "Create a separate follow-through owner"}
        current = call(next_context)
        create = current["planning"]["creation_requests"][0]
        create["arguments"] = {"material": {**material(), "title": "Separate follow-through owner"}}
        ready = call({**next_context, "request": create})
        created = call({**next_context, "invocation": ready["decision_packet"]["primary_action"]})
        next_context = created["continuation"]["context"]
        transitioned = created
        assert transitioned["effect_outcome"]["status"] == "committed"
        successor = json.loads(selector.read_bytes())
        assert "reason" not in successor and "planning_revision" not in successor
        assert successor["selected_owner"]["ref"] == created["value"]["owner_path"]


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_public_pending_update_current_same_owner_reentry(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    context = {"target": str(tmp_path), "task": "Revise this bounded native Planning owner"}

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value)

    creation = call(context)["planning"]["creation_requests"][0]
    creation["arguments"] = {"material": material()}
    action = call({**context, "request": creation})["decision_packet"]["primary_action"]
    created = call({**context, "invocation": action})
    context = created["continuation"]["context"]
    update = call(context)["planning"]["update_requests"][0]
    invalid = {**update, "arguments": {**update["arguments"], "material": {"title": None}}}
    with pytest.raises(AssertionError):
        call({**context, "request": invalid})
    update["arguments"]["material"] = {
        "next_action": "Resume the committed sparse update",
        "continuation": {"owner": None, "accepted": "The bounded update was agreed"},
    }
    ordinary = call({**context, "projection": "compact"})
    assert ordinary["planning_context"]["owner_ref"] == created["value"]["owner_path"]
    old = call(
        {
            **ordinary["reentry"],
            "reference": ordinary["planning_context"]["next_step"]["reference"],
            "answer": {"material": update["arguments"]["material"]},
        }
    )["decision_packet"]["primary_action"]
    result = call({**context, "invocation": old})
    path = tmp_path / created["value"]["owner_path"]
    before = path.read_bytes()
    updated = json.loads(before)
    assert updated["lifecycle"] == "planned" and updated["phase"] == "shaping"
    assert updated["intent"] == material()["intent"]
    assert updated["relationships"] == material()["relationships"]
    assert updated["continuation"] == {
        **{k: v for k, v in material()["continuation"].items() if k != "owner"},
        "accepted": "The bounded update was agreed",
    }
    # Exact genuine producer postimage with its result withheld is a deterministic
    # interrupted-publication fixture; the Rust process test kills the real writer.
    (tmp_path / result["custody"]["committed"]["path"]).unlink()
    current = {**context, "task": "Continue the same bounded owner revision after restart"}
    fresh = call(current)
    continuation = fresh["planning"]["selection_requests"][0] if not fresh["planning"]["requests"] else fresh["planning"]["requests"][0]
    assert not fresh["planning"]["update_requests"]
    assert not fresh["planning"]["update_recovery_requests"]
    admitted = call({**current, "request": continuation})
    recovery = admitted["planning"]["update_recovery_requests"][0]
    with pytest.raises(AssertionError):
        call({**current, "invocation": old})
    with pytest.raises(AssertionError):
        call({**current, "request": recovery})
    unrelated = {**continuation, "arguments": {"answer": "unrelated-direct"}}
    with pytest.raises(AssertionError):
        call({**current, "request": [unrelated, recovery]})
    stale_continuation = {**continuation, "source_revision": "sha256:" + "0" * 64}
    with pytest.raises(AssertionError):
        call({**current, "request": [stale_continuation, recovery]})
    ready = admitted
    assert (
        ready["decision_packet"]["primary_action"]
        == call({**current, "request": [continuation, recovery]})["decision_packet"]["primary_action"]
    )
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.update-recover"
    with pytest.raises(AssertionError):
        call({**current, "task": "Unrelated new work", "invocation": action})
    finalized = call({**current, "invocation": action})
    assert finalized["status"] == "applied" and finalized["value"]["material_written"] is False
    assert finalized["continuation"]["status"] == "current"
    assert created["value"]["owner_path"] in finalized["continuation"]["context"]["changed"]
    assert finalized["value"]["original_outcome"]["status"] == "applied"
    assert finalized["custody"] != finalized["value"]["original_custody"]
    assert path.read_bytes() == before
    after = call(current)
    assert after["planning"]["pending_update"] is None
    assert after["decision_packet"]["status"] != "terminal"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_public_creation_continues_with_current_owner(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    context = {"target": str(tmp_path), "task": "Create current bounded Planning custody"}

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value)

    initial = call(context)
    assert not (tmp_path / ".agentic-workspace").exists()
    request = initial["planning"]["creation_requests"][0]
    value = material()
    if surface == "native":
        value["references"] = [*value["references"], ".agentic-workspace/local/evidence/worker.json"]
        evidence = tmp_path / ".agentic-workspace/local/evidence/worker.json"
        evidence.parent.mkdir(parents=True)
        evidence.write_text("A local observation, not portable proof")
    request["arguments"] = {"material": value}
    ready = call({**context, "request": request})
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.create", ready
    operation = next(
        row
        for owner in ready["capability_contract"]["owners"]
        if owner["owner"] == "planning"
        for row in owner["operations"]
        if row["id"] == "planning.create"
    )
    assert operation["semantic_revision"] == "planning-create-current-owner-v2"
    assert action["arguments"]["establish_current_owner"] is True
    Draft202012Validator(operation["input_schema"]).validate(action["arguments"])
    create_only = json.loads(json.dumps(action))
    del create_only["arguments"]["establish_current_owner"]
    with pytest.raises(AssertionError):
        call({**context, "invocation": create_only})
    assert not (tmp_path / action["arguments"]["owner_path"]).exists()
    assert not (tmp_path / ".agentic-workspace/local/planning/owner-selection.json").exists()
    result = call({**context, "invocation": action})
    assert result["status"] == "applied", result
    path = tmp_path / result["value"]["owner_path"]
    body = json.loads(path.read_bytes())
    assert body["lifecycle"] == "planned" and body["phase"] == "shaping"
    assert body["canonical_core"] == material()["canonical_core"]
    selection = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    assert selection.exists()
    assert result["value"]["selection"]["effect_outcome"]["status"] == "committed"
    assert result["continuation"]["result"]["planning"]["current_owner"]["current"] is True
    assert "selection_request" not in result["value"]
    replay = call({**context, "invocation": action})
    assert replay["value"]["owner_path"] == result["value"]["owner_path"]
    assert path.read_bytes() == json.dumps(body, indent=2).encode()
    # Fresh process discovers exact producer-backed creation without the parent result.
    fresh_creation = call(context)["planning"]["created_owner"]
    assert fresh_creation["path"] == result["value"]["owner_path"]
    assert call(context)["planning"]["current_owner"]["current"] is True
    fresh = call(context)
    assert fresh["planning"]["current_owner"]["current"] is True
    assert fresh["decision_packet"]["status"] != "terminal"

    if surface == "native":
        # One cross-environment journey; adapter parameterization above proves
        # transport only. Copy repo meaning, never local effects or selector.
        clone = tmp_path / "fresh-consumer"
        relative = result["value"]["owner_path"]
        clone_path = clone / relative
        clone_path.parent.mkdir(parents=True)
        clone_path.write_bytes(path.read_bytes())
        (clone / ".agentic-workspace/planning/state.toml").write_text(
            f'[[active.execplans]]\nid="{body["id"]}"\npath="{relative}"\nstatus="active"\n'
        )
        new_context = {"target": str(clone), "task": "Continue the repository-owned outcome with no parent chat"}
        discovered = call(new_context)
        assert discovered["planning"]["update_requests"] == []
        choice = discovered["planning"]["selection_requests"][0]
        selected = call({**new_context, "request": choice})
        portable = selected["planning"]["portable_continuation"]
        assert portable["semantic_subject"] == fresh["planning"]["portable_continuation"]["semantic_subject"]
        assert portable["local_custody"]["current"] is False
        assert portable["local_references"] == [
            {"path": ".agentic-workspace/local/evidence/worker.json", "status": "unavailable-local-reference", "authority": False}
        ]
        assert fresh["planning"]["portable_continuation"]["local_references"][0]["status"] == "present-unvalidated"
        assert (
            selected["planning"]["current_owner"]["reconciliation"]["subject"]["state"]
            == fresh["planning"]["current_owner"]["reconciliation"]["subject"]["state"]
        )
        assert str(tmp_path) not in path.read_text(encoding="utf-8")
        # Partial loss is an uncertain effect, never a source-only switch.
        local_attempt = clone / body["creation_provenance"]["custody"]["attempt"]["path"]
        local_attempt.parent.mkdir(parents=True)
        local_attempt.write_text("{}")
        with pytest.raises(AssertionError, match="uncertain"):
            call({**new_context, "request": choice})
        local_attempt.unlink()
        call({**new_context, "invocation": selected["decision_packet"]["primary_action"]})
        recovered = call(new_context)
        assert recovered["planning"]["update_requests"]
        assert clone_path.read_bytes() == path.read_bytes()
        assert recovered["planning"]["portable_continuation"]["semantic_subject"] == portable["semantic_subject"]
        assert (
            recovered["planning"]["portable_continuation"]["local_custody"]["subject"]
            != fresh["planning"]["portable_continuation"]["local_custody"]["subject"]
        )
        assert recovered["decision_packet"]["status"] != "terminal"

        # Abrupt loss of all local custody still exposes source meaning. Exact
        # partial custody above stays uncertain; a remembered create cannot run.
        retained = json.loads(selection.read_bytes())["reconciliation"]["custody"]
        for custody in [retained, result["custody"]]:
            for field in ["attempt", "committed"]:
                (tmp_path / custody[field]["path"]).unlink()
        selection.unlink()
        orphaned = call(context)
        assert orphaned["planning"]["created_owner"]["status"] == "source-observation-local-outcome-unknown"
        with pytest.raises(AssertionError, match="unknown|custody|current"):
            call({**context, "invocation": action})
        resume = orphaned["planning"]["created_owner"]["selection_request"]
        reacquire = call({**context, "request": resume})
        assert reacquire["planning"]["portable_continuation"]["semantic_subject"] == portable["semantic_subject"]
        assert reacquire["decision_packet"]["primary_action"]["operation_id"] == "planning.reconcile"
        call({**context, "invocation": reacquire["decision_packet"]["primary_action"]})
        assert call(context)["planning"]["current_owner"]["current"] is True
        assert json.loads(path.read_bytes()) == body


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
@pytest.mark.parametrize("drift", ["occupied", "work", "arguments"])
def test_creation_rejects_stale_or_substituted_action(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str, drift: str
) -> None:
    context = {"target": str(tmp_path), "task": "Create a bounded owner"}
    initial = consume(surface, shared_core_binary, native_cli, context)
    request = initial["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    action = consume(surface, shared_core_binary, native_cli, {**context, "request": request})["decision_packet"]["primary_action"]
    path = tmp_path / action["arguments"]["owner_path"]
    if drift == "occupied":
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(action["arguments"]["document"]))
    elif drift == "work":
        context["task"] = "Another current task"
    else:
        action["arguments"]["document"]["canonical_core"]["hard_constraints"] = "Caller substituted semantics"
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(AssertionError):
        consume(surface, shared_core_binary, native_cli, {**context, "invocation": action})
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize("damage", ["material", "provenance", "missing-commit"])
def test_creation_retention_never_adopts_changed_or_uncertain_source(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, damage: str
) -> None:
    context = {"target": str(tmp_path), "task": "Create a bounded owner"}
    initial = consume("native", shared_core_binary, native_cli, context)
    request = initial["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    action = consume("native", shared_core_binary, native_cli, {**context, "request": request})["decision_packet"]["primary_action"]
    result = consume("native", shared_core_binary, native_cli, {**context, "invocation": action})
    path = tmp_path / result["value"]["owner_path"]
    body = json.loads(path.read_bytes())
    saved_context = result["continuation"]["context"]
    saved_request = result["continuation"]["result"]["planning"]["requests"][0]
    if damage == "material":
        body["canonical_core"]["hard_constraints"] = "Materially revised scope"
        path.write_text(json.dumps(body))
    elif damage == "provenance":
        body["creation_provenance"]["invocation_revision"] = "forged-owner"
        path.write_text(json.dumps(body))
    else:
        (tmp_path / result["custody"]["committed"]["path"]).unlink()
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(AssertionError):
        consume("native", shared_core_binary, native_cli, {**context, "invocation": action})
    if damage == "material":
        stale = consume(
            "native",
            shared_core_binary,
            native_cli,
            {**saved_context, "request": saved_request},
        )
        assert stale["planning"]["status"] == "stale"
    else:
        with pytest.raises(AssertionError):
            consume(
                "native",
                shared_core_binary,
                native_cli,
                {**saved_context, "request": saved_request},
            )
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_creation_preserves_existing_selected_owner(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    reference = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / reference
    plan.parent.mkdir(parents=True)
    plan.write_bytes(fixture_source(reference).read_bytes())
    selection = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    selection.parent.mkdir(parents=True)
    selection.write_text(
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "default",
                "selected_owner": {"id": "delegation-lane-sweep", "ref": reference.as_posix()},
            }
        )
    )
    context = {"target": str(tmp_path), "task": "Create another unselected bounded owner"}
    initial = consume("native", shared_core_binary, native_cli, context)
    assert initial["planning"]["status"] == "direct"
    creation = initial["planning"]["creation_requests"][0]
    creation["arguments"] = {"material": material()}
    ready = consume("native", shared_core_binary, native_cli, {**context, "request": creation})
    # A separate owner may be created, but no current selection is transferable.
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.create", ready
    before = {selection: selection.read_bytes(), plan: plan.read_bytes()}
    result = consume("native", shared_core_binary, native_cli, {**context, "invocation": action})
    assert result["status"] == "applied", result
    assert before == {p: p.read_bytes() for p in before}
    assert "selection_request" not in result["value"]
    assert "transfer" in result["value"]["selection_gap"]


@pytest.mark.parametrize("field", ["proof", "canonical_core", "lifecycle"])
def test_creation_does_not_fabricate_missing_judgment_or_terminal_state(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, field: str
) -> None:
    context = {"target": str(tmp_path), "task": "Create bounded Planning work"}
    request = consume("native", shared_core_binary, native_cli, context)["planning"]["creation_requests"][0]
    value = material()
    if field == "lifecycle":
        value[field] = "closed"
    else:
        del value[field]
    request["arguments"] = {"material": value}
    with pytest.raises(AssertionError):
        consume("native", shared_core_binary, native_cli, {**context, "request": request})
    assert not (tmp_path / ".agentic-workspace").exists()


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_owned_selection_switches_only_by_current_explicit_request(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = {"target": str(tmp_path), "task": "Continue the first bounded owner"}

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value)

    request = call(context)["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    first = call({**context, "invocation": call({**context, "request": request})["decision_packet"]["primary_action"]})
    context = first["continuation"]["context"]
    selector = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    before = selector.read_bytes()
    first_path = tmp_path / first["value"]["owner_path"]
    first_bytes = first_path.read_bytes()
    context["task"] = "Create a distinct bounded owner"
    current = call(context)
    assert current["planning"]["selected_owner"] is None
    assert current["planning"]["incumbent_owner"] is None
    assert current["planning"]["status"] == "direct"
    assert current["decision_packet"]["decision_request"] is None
    if surface == "native":
        import copy

        selection = current["planning"]["selection_requests"][0]
        for field in ("source_revision", "capability_revision", "owner_revision", "task_identity"):
            forged = copy.deepcopy(selection)
            forged[field] = {"kind": "current-work", "id": "wrong"} if field == "task_identity" else "stale"
            with pytest.raises(AssertionError):
                call({**context, "request": forged})
        for changed_context in ({"task": "Other task"}, {"changed": ["different.rs"]}, {"target": str(tmp_path.parent)}):
            with pytest.raises(AssertionError):
                call({**context, **changed_context, "request": selection})
        assert selector.read_bytes() == before
        assert first_path.read_bytes() == first_bytes
    request = current["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    planned = call({**context, "request": request})
    assert planned["planning"]["selected_owner"] is None
    action = planned["decision_packet"]["primary_action"]
    second = call({**context, "invocation": action})
    assert selector.read_bytes() != before
    context = second["continuation"]["context"]
    action = json.loads(selector.read_bytes())["reconciliation"]["invocation"]
    assert action["operation_id"] == "planning.reconcile"
    assert action["arguments"]["selection_transition"]["prior_custody"]["committed"]
    selected_bytes = selector.read_bytes()
    forged = json.loads(json.dumps(action))
    forged["arguments"]["selection_transition"]["prior_sha256"] = "sha256:" + "0" * 64
    with pytest.raises(AssertionError):
        call({**context, "invocation": forged})
    assert selector.read_bytes() == selected_bytes
    call({**context, "invocation": action})
    fresh = call(context)
    assert fresh["planning"]["current_owner"]["current"] is True
    assert fresh["planning"]["selected_owner"]["ref"] == second["value"]["owner_path"]
    assert first_path.read_bytes() == first_bytes
    call({**context, "invocation": action})
    assert fresh["decision_packet"]["status"] != "terminal"
    if surface == "native":
        destination = tmp_path / second["value"]["owner_path"]
        body = json.loads(destination.read_bytes())
        subject = fresh["planning"]["current_owner"]["reconciliation"]["subject"]
        for change in ["attempt", "material"]:
            if change == "attempt":
                body["relationships"]["assignment"] = {"attempt": 2, "status": "retrying"}
            else:
                body["canonical_core"]["hard_constraints"] = "New owner-authored material limit"
            destination.write_text(json.dumps(body))
            with pytest.raises(AssertionError):
                call({**context, "invocation": action})
            current = call(context)
            answer = current["decision_packet"]["decision_request"]["response_request"]
            answer["arguments"]["answer"] = "continue-selected"
            continuation = call({**context, "request": answer})
            pending = continuation["decision_packet"]["primary_action"]
            assert "selection_transition" not in pending["arguments"]
            call({**context, "invocation": pending})
            resumed = call(context)["planning"]["current_owner"]
            assert resumed["current"] is True
            assert (resumed["reconciliation"]["subject"]["revision"] == subject["revision"]) is (change == "attempt")


def test_creation_intersects_current_instruction_write_scope(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    import shutil

    from tests.test_native_public_cli import pin_instructions

    instruction = tmp_path / ".agentic-workspace/instructions/owner.md"
    instruction.parent.mkdir(parents=True)
    instruction.write_text(
        "---\npaths: [.agentic-workspace/**]\nprotect: [.agentic-workspace/planning/execplans/**]\n---\nPreserve Planning sources.\n"
    )
    pin_instructions(tmp_path)
    host_path = str(Path(shutil.which("git")).parent)
    context = {"target": str(tmp_path), "task": "Create bounded Planning work"}
    request = consume("native", shared_core_binary, native_cli, context, host_path=host_path)["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    before = {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace").rglob("*") if p.is_file()}
    result = consume("native", shared_core_binary, native_cli, {**context, "request": request}, host_path=host_path)
    assert not result["decision_packet"]["ready_actions"]
    assert any("protected" in str(blocker) for blocker in result["decision_packet"]["blockers"]), result
    assert before == {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace").rglob("*") if p.is_file()}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_disabled_planning_does_not_read_or_execute_creation(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = {"target": str(tmp_path), "task": "Create bounded Planning work"}
    request = consume(surface, shared_core_binary, native_cli, context)["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    action = consume(surface, shared_core_binary, native_cli, {**context, "request": request})["decision_packet"]["primary_action"]
    config = tmp_path / ".agentic-workspace/config.toml"
    config.parent.mkdir(parents=True)
    config.write_text("[modules]\nenabled=[]\n")
    occupied = tmp_path / action["arguments"]["owner_path"]
    occupied.parent.mkdir(parents=True)
    occupied.write_text("Not Planning-owned JSON")
    direct = consume(surface, shared_core_binary, native_cli, context)
    assert direct["planning"]["creation_requests"] == []
    before = {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace").rglob("*") if p.is_file()}
    with pytest.raises(AssertionError):
        consume(surface, shared_core_binary, native_cli, {**context, "invocation": action})
    assert before == {p: p.read_bytes() for p in (tmp_path / ".agentic-workspace").rglob("*") if p.is_file()}


@pytest.mark.parametrize("change", ["attempt", "material"])
def test_created_owner_revision_outlives_creation_provenance(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, change: str
) -> None:
    context = {"target": str(tmp_path), "task": "Continue bounded Planning work"}

    def call(value: dict) -> dict:
        return consume("native", shared_core_binary, native_cli, value)

    request = call(context)["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    creation = call({**context, "request": request})["decision_packet"]["primary_action"]
    created = call({**context, "invocation": creation})
    context = created["continuation"]["context"]
    first = call(context)["planning"]["current_owner"]["reconciliation"]["subject"]
    path = tmp_path / created["value"]["owner_path"]
    body = json.loads(path.read_bytes())
    if change == "attempt":
        body["relationships"]["assignment"] = {"attempt_id": "retry-2", "status": "retrying"}
    else:
        body["canonical_core"]["hard_constraints"] = "New material source-owned scope constraint"
    path.write_text(json.dumps(body))
    pending = call(context)
    request = pending["decision_packet"]["decision_request"]["response_request"]
    request["arguments"]["answer"] = "continue-selected"
    current = call({**context, "request": request})
    subject = current["planning"]["current_owner"]["reconciliation"]["subject"]
    assert subject["id"] == first["id"]
    assert (subject["revision"] == first["revision"]) is (change == "attempt")
    call({**context, "invocation": current["decision_packet"]["primary_action"]})
    assert call(context)["planning"]["current_owner"]["current"] is True
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "invocation": creation})


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_quiescent_selected_owner_preserves_task_and_allows_unrelated_work(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value)

    context = {"target": str(tmp_path), "task": "Implement bounded current owner"}
    request = call(context)["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    created = call({**context, "invocation": action})
    context = created["continuation"]["context"]
    live = call(context)
    old_subject = live["planning"]["current_owner"]["reconciliation"]["subject"]
    path = tmp_path / created["value"]["owner_path"]
    body = json.loads(path.read_bytes())
    body["lifecycle"] = "closed"
    body["phase"] = "closed"
    path.write_text(json.dumps(body))
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    same = call(context)
    assert same["planning"]["status"] == "reentry-required", same
    subject = same["planning"]["current_owner"]["reconciliation"]["subject"]
    assert (subject["id"], subject["revision"]) == (old_subject["id"], old_subject["revision"])
    assert (
        same["planning"]["current_owner"]["reconciliation"]["subject"]["state"]["scope"]
        == live["planning"]["current_owner"]["reconciliation"]["subject"]["state"]["scope"]
    )
    assert same["decision_packet"]["status"] != "terminal"
    other = {**context, "task": "Inspect an unrelated bounded source"}
    quiet = call(other)
    assert quiet["planning"]["status"] == "direct"
    assert quiet["decision_packet"]["status"] != "terminal"
    explicit = quiet["planning"]["selection_requests"][0]
    assert call({**other, "request": explicit})["planning"]["status"] == "reentry-required"
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    # New owner creation remains separate, and a native-owned closed selector
    # can move only via its exact returned current reconciliation invocation.
    request = quiet["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    action = call({**other, "request": request})["decision_packet"]["primary_action"]
    created_other = call({**other, "invocation": action})
    other = created_other["continuation"]["context"]
    assert call(other)["planning"]["selected_owner"]["ref"] == created_other["value"]["owner_path"]
    assert path.read_bytes() == before[path]


@pytest.mark.parametrize("state", ["closed", "closeout", "unknown"])
def test_quiescent_disposition_never_acquires_historical_selector(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, state: str
) -> None:
    body = json.loads(fixture_source(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json").read_text())
    body["lifecycle"] = "closed" if state == "closed" else "live" if state == "closeout" else "unknown"
    body["phase"] = state
    reference = ".agentic-workspace/planning/execplans/historical.plan.json"
    path = tmp_path / reference
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(body))
    selector = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    selector.parent.mkdir(parents=True)
    selector.write_text(
        json.dumps(
            {
                "kind": "agentic-planning/owner-selection/v1",
                "mode": "local",
                "current_work_id": "default",
                "selected_owner": {"id": body["id"], "ref": reference},
            }
        )
    )
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    context = {"target": str(tmp_path), "task": "Read an unrelated bounded source"}

    def call(value: dict) -> dict:
        return consume("native", shared_core_binary, native_cli, value)

    view = call(context)
    assert view["planning"]["status"] == "direct"
    request = view["planning"]["selection_requests"][0]
    if state == "unknown":
        with pytest.raises(AssertionError, match="not live"):
            call({**context, "request": request})
    else:
        continued = call({**context, "request": request})
        assert continued["planning"]["status"] == ("reentry-required" if state == "closed" else "custody-required")
        assert continued["decision_packet"]["status"] != "terminal"
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_native_created_owner_typed_material_update(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    import os

    from tests.test_native_proof_producer import fixture

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    context = fixture(tmp_path)
    request = call(context)["planning"]["creation_requests"][0]
    authored = {**material(), "adaptive_assurance": {"proof_profiles": []}, "risk_registry_refs": ["risk:original"], "invariant_refs": []}
    request["arguments"] = {"material": authored}
    created = call({**context, "invocation": call({**context, "request": request})["decision_packet"]["primary_action"]})
    context = created["continuation"]["context"]
    old = call(context)
    proof_request = old["verification"]["execution_requests"][0]
    proof_action = call({**context, "request": proof_request})["decision_packet"]["primary_action"]
    proof_result = call({**context, "invocation": proof_action})
    proof_ref = proof_result["value"]["publication"]["reference"]
    claim = call(context)["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [proof_ref]
    assert call({**context, "request": claim})["verification"]["evidence"][0]["evidence_freshness"] == "reusable"
    # Only a typed risk reference changes: unchanged scope/frontier cannot hide
    # this material revision, and Planning cannot turn the declaration into proof.
    old_subject = old["planning"]["current_owner"]["reconciliation"]["subject"]
    # A remembered native owner is advisory until this task admits continuation.
    unrelated = {**context, "task": "Explain an unrelated helper"}
    unresolved = call(unrelated)
    assert unresolved["planning"]["task_relation"] == "no-incumbent"
    assert unresolved["planning"]["selected_owner"] is None
    assert unresolved["planning"]["incumbent_owner"] is None
    assert not unresolved["planning"]["update_requests"]
    assert not unresolved["planning"]["update_recovery_requests"]
    assert not unresolved["planning"]["adoption_requests"]
    owner_path = tmp_path / created["value"]["owner_path"]
    selector_path = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    preserved = owner_path.read_bytes(), selector_path.read_bytes()
    forged = json.loads(json.dumps(old["planning"]["update_requests"][0]))
    forged["task_identity"] = unresolved["current_work"]
    forged["arguments"]["material"] = {**authored, "lifecycle": "live", "phase": "implementation"}
    with pytest.raises(AssertionError, match="admitted current-owner continuation"):
        call({**unrelated, "request": forged})
    assert (owner_path.read_bytes(), selector_path.read_bytes()) == preserved
    risk_update = old["planning"]["update_requests"][0]
    risk_update["arguments"]["material"] = {**authored, "lifecycle": "planned", "phase": "shaping", "risk_registry_refs": ["risk:revised"]}
    risk_action = call({**context, "request": risk_update})["decision_packet"]["primary_action"]
    call({**context, "invocation": risk_action})
    old = call(context)
    risk_reentry = call({**context, "request": old["planning"]["requests"][0]})["decision_packet"]["primary_action"]
    call({**context, "invocation": risk_reentry})
    old = call(context)
    assert old["planning"]["current_owner"]["reconciliation"]["subject"]["revision"] != old_subject["revision"]
    new_claim = old["verification"]["requests"][0]
    new_claim["arguments"]["evidence_refs"] = [proof_ref]
    assert call({**context, "request": new_claim})["verification"]["evidence"][0]["evidence_freshness"] == "stale"
    selector = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    selector_bytes = selector.read_bytes()
    path = tmp_path / created["value"]["owner_path"]
    body = json.loads(path.read_bytes())
    request = old["planning"]["update_requests"][0]
    changed_material = material()
    changed_material.update({"lifecycle": "live", "phase": "implementation"})
    changed_material["scope"] = {"allowed": "One exact revised component"}
    request["arguments"]["material"] = changed_material
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.update"
    result = call({**context, "invocation": action})
    assert result["status"] == "applied", result
    updated = json.loads(path.read_bytes())
    assert updated["scope"] == {**body["scope"], **changed_material["scope"]}
    assert updated["risk_registry_refs"] == ["risk:revised"], "omitted optional update fields retain their current owner value"
    assert updated["id"] == body["id"] and updated["creation_provenance"] == body["creation_provenance"]
    assert selector.read_bytes() == selector_bytes
    assert call({**context, "invocation": action})["value"] == result["value"]
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "request": request})
    current = call(context)
    continuation = current["planning"]["requests"][0]
    reconciled = call({**context, "request": continuation})
    action = reconciled["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.reconcile", reconciled
    call({**context, "invocation": action})
    fresh = call(context)
    previous_subject = old["planning"]["current_owner"]["reconciliation"]["subject"]
    subject = fresh["planning"]["current_owner"]["reconciliation"]["subject"]
    assert subject["id"] == previous_subject["id"]
    assert subject["revision"] != previous_subject["revision"]
    assert fresh["decision_packet"]["status"] != "terminal"
    claim = fresh["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [proof_ref]
    evidence = call({**context, "request": claim})["verification"]["evidence"][0]
    assert evidence["publication_admission"]["status"] == "admitted"
    assert evidence["evidence_freshness"] == "stale"
    assert evidence["task_judgment"]["current_judgment_count"] == 0
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]
    # Frontier-only closure/reentry remains the same material work. The caller
    # supplies reopening judgment; closed status itself grants no proof.
    for lifecycle, phase in [("closed", "complete"), ("blocked", "validation"), ("live", "validation")]:
        update_request = call(context)["planning"]["update_requests"][0]
        changed_material.update({"lifecycle": lifecycle, "phase": phase})
        update_request["arguments"]["material"] = changed_material
        update_action = call({**context, "request": update_request})["decision_packet"]["primary_action"]
        assert update_action["operation_id"] == "planning.update"
        call({**context, "invocation": update_action})
        current = call(context)
        if lifecycle in {"closed", "blocked"}:
            assert current["planning"]["status"] == "reentry-required"
        else:
            continuation = current["planning"]["requests"][0]
            action = call({**context, "request": continuation})["decision_packet"]["primary_action"]
            call({**context, "invocation": action})
            current = call(context)
        assert current["planning"]["current_owner"]["reconciliation"]["subject"]["revision"] == subject["revision"]
        assert current["decision_packet"]["status"] != "terminal"
        assert "update_provenance" not in json.loads(path.read_bytes())["update_provenance"]


@pytest.mark.parametrize("unsupported", [False, True])
def test_legacy_aggregate_migrates_to_owner_and_retires_exactly(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, unsupported: bool
) -> None:
    context = {"target": str(tmp_path), "task": "Upgrade legacy Planning"}

    def call(value):
        return consume("native", shared_core_binary, native_cli, value)

    owners = []
    for title in ["Current frontier"] if unsupported else ["Current frontier", "Related continuing work"]:
        context["task"] = title
        create = call(context)["planning"]["creation_requests"][0]
        create["arguments"] = {"material": {**material(), "title": title}}
        ready = call({**context, "request": create})
        made = call({**context, "invocation": ready["decision_packet"]["primary_action"]})
        owners.append(made["value"])
    # Construct the former aggregate-only entry, without today's native cursor.
    (tmp_path / ".agentic-workspace/local/planning/owner-selection.json").unlink()
    state = tmp_path / ".agentic-workspace/planning/state.toml"
    state.write_text(
        "kind='planning-state/v1'\n"
        + "".join(
            f"[[active.execplans]]\nid='{owner['owner_id']}'\nsurface='{owner['owner_path']}'\nrevision='stale-aggregate'\nstatus='active'\n"
            for owner in owners
        )
        + ("[roadmap]\nintent='preserve unfamiliar useful intent'\n" if unsupported else "")
    )
    held = state.read_bytes()
    selection = call(context)["planning"]["selection_requests"][0]
    ambiguous = call({**context, "request": selection})["planning"]
    assert ambiguous["selected_owner"] is None
    assert ambiguous["status"] == "legacy-choice-required"
    assert ambiguous["task_relation"] == "unresolved"
    assert ambiguous["legacy_aggregate"]["current_authority"] is False
    assert len(ambiguous["legacy_aggregate"]["selection_requests"]) == len(owners)
    assert call(context)["planning"]["status"] == "direct"
    assert state.read_bytes() == held
    request = ambiguous["legacy_aggregate"]["selection_requests"][0]
    ready = call({**context, "request": request})
    call({**context, "invocation": ready["decision_packet"]["primary_action"]})
    before = call(context)
    owner_body = (tmp_path / owners[0]["owner_path"]).read_bytes()
    before = call({**context, "request": before["planning"]["terminal_retention"]["discovery_request"]})
    if unsupported:
        # Cold unknown material preserves safe discovery, but never authorizes
        # retiring unknown bytes after selecting the useful canonical owner.
        assert before["planning"]["selected_owner"]["id"] == owners[0]["owner_id"]
        assert before["planning"]["terminal_retention"]["requests"] == []
        assert state.read_bytes() == held
        assert (tmp_path / owners[0]["owner_path"]).read_bytes() == owner_body
        cold = tmp_path / "unfamiliar-only"
        cold_state = cold / ".agentic-workspace/planning/state.toml"
        cold_state.parent.mkdir(parents=True)
        cold_state.write_text("[unfamiliar]\nintent='preserve'\n")
        cold_bytes = cold_state.read_bytes()
        preserved = call({"target": str(cold), "task": "Independent read"})
        assert preserved["planning"]["status"] == "direct"
        assert preserved["planning"]["terminal_retention"]["status"] == "quiet"
        assert cold_state.read_bytes() == cold_bytes
        return
    retire = before["planning"]["terminal_retention"]["requests"][0]
    retire["arguments"].update(
        sources=[state.relative_to(tmp_path).as_posix()],
        terminal=True,
        no_unresolved_intent=True,
        no_continuing_value=True,
        reason="Canonical owners retain all useful intent; stale aggregate has no continuing value.",
    )
    ready = call({**context, "request": retire})
    action = ready["decision_packet"]["primary_action"]
    state.write_bytes(held + b"\n")
    with pytest.raises(AssertionError):
        call({**context, "invocation": action})
    assert state.exists()
    state.write_bytes(held)
    call({**context, "invocation": action})
    after = call(context)
    assert not state.exists()
    assert after["planning"]["legacy_aggregate"]["status"] == "absent"
    assert after["planning"]["selected_owner"]["id"] == before["planning"]["selected_owner"]["id"]
    assert after["planning"]["selected_owner"]["source"] == before["planning"]["selected_owner"]["source"]
    assert (tmp_path / owners[0]["owner_path"]).read_bytes() == owner_body
    assert (tmp_path / owners[1]["owner_path"]).exists()
    state.write_text("[unfamiliar]\nintent='preserve'\n")
    current = call(context)
    observed = call({**context, "request": current["planning"]["terminal_retention"]["discovery_request"]})
    assert observed["planning"]["terminal_retention"]["status"] == "legacy-migration-required"
    assert state.exists()
