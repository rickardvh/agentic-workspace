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
