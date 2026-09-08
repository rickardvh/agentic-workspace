"""Public creation uses one Rust owner, preserving selection and provenance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from tests.test_native_public_cli import ROOT, consume
from tests.test_native_public_cli import native_cli as native_cli


def material() -> dict:
    original = json.loads((ROOT / ".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json").read_text())
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
    return value


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_public_pending_update_current_same_owner_reentry(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    context = {"target": str(tmp_path), "task": "Revise this bounded native Planning owner"}

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value)

    creation = call(context)["planning"]["creation_requests"][0]
    creation["arguments"] = {"material": material()}
    action = call({**context, "request": creation})["decision_packet"]["primary_action"]
    created = call({**context, "invocation": action})
    select = call({**context, "request": created["value"]["selection_request"]})["decision_packet"]["primary_action"]
    call({**context, "invocation": select})
    update = call(context)["planning"]["update_requests"][0]
    update["arguments"]["material"] = {**material(), "lifecycle": "live", "phase": "implementation"}
    old = call({**context, "request": update})["decision_packet"]["primary_action"]
    result = call({**context, "invocation": old})
    path = tmp_path / created["value"]["owner_path"]
    before = path.read_bytes()
    # Exact genuine producer postimage with its result withheld is a deterministic
    # interrupted-publication fixture; the Rust process test kills the real writer.
    (tmp_path / result["custody"]["committed"]["path"]).unlink()
    current = {**context, "task": "Continue the same bounded owner revision after restart"}
    fresh = call(current)
    continuation = fresh["planning"]["requests"][0]
    recovery = fresh["planning"]["update_recovery_requests"][0]
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
    ready = call({**current, "request": [continuation, recovery]})
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.update-recover"
    with pytest.raises(AssertionError):
        call({**current, "task": "Unrelated new work", "invocation": action})
    finalized = call({**current, "invocation": action})
    assert finalized["status"] == "applied" and finalized["value"]["material_written"] is False
    assert finalized["value"]["original_outcome"]["status"] == "applied"
    assert finalized["custody"] != finalized["value"]["original_custody"]
    assert path.read_bytes() == before
    after = call(current)
    assert after["planning"]["pending_update"] is None
    assert after["decision_packet"]["status"] != "terminal"


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_public_creation_then_separate_selection(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    context = {"target": str(tmp_path), "task": "Create current bounded Planning custody"}

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value)

    initial = call(context)
    assert not (tmp_path / ".agentic-workspace").exists()
    request = initial["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    ready = call({**context, "request": request})
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.create", ready
    result = call({**context, "invocation": action})
    assert result["status"] == "applied", result
    path = tmp_path / result["value"]["owner_path"]
    body = json.loads(path.read_bytes())
    assert body["lifecycle"] == "planned" and body["phase"] == "shaping"
    assert body["canonical_core"] == material()["canonical_core"]
    selection = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    assert not selection.exists()
    replay = call({**context, "invocation": action})
    assert replay["value"] == result["value"]
    # Fresh process discovers exact producer-backed creation without the parent result.
    fresh_creation = call(context)["planning"]["created_owner"]
    assert fresh_creation["path"] == result["value"]["owner_path"]
    select = call({**context, "request": fresh_creation["selection_request"]})
    assert select["decision_packet"]["primary_action"]["operation_id"] == "planning.reconcile", select
    call({**context, "invocation": select["decision_packet"]["primary_action"]})
    fresh = call(context)
    assert fresh["planning"]["current_owner"]["current"] is True
    assert fresh["decision_packet"]["status"] != "terminal"


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
        stale = consume("native", shared_core_binary, native_cli, {**context, "request": result["value"]["selection_request"]})
        assert stale["planning"]["status"] == "stale"
    else:
        with pytest.raises(AssertionError):
            consume("native", shared_core_binary, native_cli, {**context, "request": result["value"]["selection_request"]})
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_creation_preserves_existing_selected_owner(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    reference = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / reference
    plan.parent.mkdir(parents=True)
    plan.write_bytes((ROOT / reference).read_bytes())
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
    continuation = initial["decision_packet"]["decision_request"]["response_request"]
    continuation["arguments"]["answer"] = "unrelated-direct"
    creation = initial["planning"]["creation_requests"][0]
    creation["arguments"] = {"material": material()}
    ready = consume("native", shared_core_binary, native_cli, {**context, "request": [continuation, creation]})
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
    choice = first["value"]["selection_request"]
    call({**context, "invocation": call({**context, "request": choice})["decision_packet"]["primary_action"]})
    selector = tmp_path / ".agentic-workspace/local/planning/owner-selection.json"
    before = selector.read_bytes()
    first_path = tmp_path / first["value"]["owner_path"]
    first_bytes = first_path.read_bytes()
    context["task"] = "Create a distinct bounded owner"
    current = call(context)
    unrelated = current["decision_packet"]["decision_request"]["response_request"]
    unrelated["arguments"]["answer"] = "unrelated-direct"
    request = current["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    action = call({**context, "request": [unrelated, request]})["decision_packet"]["primary_action"]
    second = call({**context, "invocation": action})
    assert selector.read_bytes() == before
    choice = second["value"]["selection_request"]
    selected = call({**context, "request": choice})
    action = selected["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.reconcile"
    assert action["arguments"]["selection_transition"]["prior_custody"]["committed"]
    assert selector.read_bytes() == before
    forged = json.loads(json.dumps(action))
    forged["arguments"]["selection_transition"]["prior_sha256"] = "sha256:" + "0" * 64
    with pytest.raises(AssertionError):
        call({**context, "invocation": forged})
    assert selector.read_bytes() == before
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
    config.write_text("schema_version=1\n[modules]\nenabled=[]\n")
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
    choice = call(context)["planning"]["created_owner"]["selection_request"]
    reconcile = call({**context, "request": choice})["decision_packet"]["primary_action"]
    call({**context, "invocation": reconcile})
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
    with pytest.raises(AssertionError, match="snapshot is stale"):
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
    select = created["value"]["selection_request"]
    action = call({**context, "request": select})["decision_packet"]["primary_action"]
    call({**context, "invocation": action})
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
    explicit = quiet["planning"]["requests"][0]
    assert call({**other, "request": explicit})["planning"]["status"] == "reentry-required"
    assert before == {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    # New owner creation remains separate, and a native-owned closed selector
    # can move only via its exact returned current reconciliation invocation.
    request = quiet["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    action = call({**other, "request": request})["decision_packet"]["primary_action"]
    created_other = call({**other, "invocation": action})
    action = call({**other, "request": created_other["value"]["selection_request"]})["decision_packet"]["primary_action"]
    call({**other, "invocation": action})
    assert call(other)["planning"]["selected_owner"]["ref"] == created_other["value"]["owner_path"]
    assert path.read_bytes() == before[path]


@pytest.mark.parametrize("state", ["closed", "closeout", "unknown"])
def test_quiescent_disposition_never_acquires_historical_selector(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, state: str
) -> None:
    body = json.loads((ROOT / ".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json").read_text())
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

    if state == "unknown":
        with pytest.raises(AssertionError, match="not live"):
            call(context)
    else:
        view = call(context)
        assert view["planning"]["status"] == ("direct" if state == "closed" else "unresolved")
        continued = call({**context, "request": view["planning"]["requests"][0]})
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
    request["arguments"] = {"material": material()}
    created = call({**context, "invocation": call({**context, "request": request})["decision_packet"]["primary_action"]})
    selected = call({**context, "request": created["value"]["selection_request"]})
    call({**context, "invocation": selected["decision_packet"]["primary_action"]})
    old = call(context)
    proof_request = old["verification"]["execution_requests"][0]
    proof_action = call({**context, "request": proof_request})["decision_packet"]["primary_action"]
    proof_result = call({**context, "invocation": proof_action})
    proof_ref = proof_result["value"]["publication"]["reference"]
    claim = call(context)["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [proof_ref]
    assert call({**context, "request": claim})["verification"]["evidence"][0]["evidence_freshness"] == "reusable"
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
    assert updated["scope"] == changed_material["scope"]
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


@pytest.mark.parametrize("attempt", ["mutation", "typescript-overwrite", "rollback-existing", "rollback-arrival"])
def test_retained_planning_adapter_preserves_native_plan(tmp_path: Path, shared_core_binary: Path, native_cli: Path, attempt: str) -> None:
    from repo_planning_bootstrap import installer

    context = {"target": str(tmp_path), "task": "Create one native owner for retained-adapter boundaries"}

    def call(value: dict) -> dict:
        return consume("native", shared_core_binary, native_cli, value)

    request = call(context)["planning"]["creation_requests"][0]
    request["arguments"] = {"material": material()}
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    path = tmp_path / action["arguments"]["owner_path"]
    if attempt == "rollback-arrival":

        def legacy_operation() -> None:
            call({**context, "invocation": action})
            raise RuntimeError("legacy operation interrupted after native arrival")

        with pytest.raises(ValueError, match="Native Planning owner preserved"):
            installer._apply_planning_writes_atomically([path], legacy_operation)
        assert call(context)["planning"]["created_owner"]["path"] == action["arguments"]["owner_path"]
        return
    created = call({**context, "invocation": action})
    before = path.read_bytes()
    if attempt == "typescript-overwrite":
        import shutil
        import subprocess

        process = subprocess.run(
            [
                shutil.which("node"),
                str(ROOT / "generated/planning/typescript/src/cli.mjs"),
                "new-plan",
                "--id",
                json.loads(before)["id"],
                "--title",
                "Legacy overwrite",
                "--target",
                str(tmp_path),
                "--overwrite",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert process.returncode != 0
        assert "Native Planning owner preserved" in process.stderr + process.stdout
    elif attempt == "mutation":
        refused = installer.targeted_execplan_write(target=tmp_path, plan=str(path), patch={"next_action": "legacy overwrite"}, apply=True)
        assert refused["status"] == "native-owner-required", refused
        with pytest.raises(ValueError, match="Native Planning owner preserved"):
            installer._write_execplan_record(record_path=path, record=json.loads(before))
    else:

        def legacy_operation() -> None:
            pytest.fail("existing native custody must refuse before the old writer runs")

        with pytest.raises(ValueError, match="Native Planning owner preserved"):
            installer._apply_planning_writes_atomically([path], legacy_operation)
    assert path.read_bytes() == before
    assert call(context)["planning"]["created_owner"]["path"] == created["value"]["owner_path"]
