"""Planning lifetime changes use the public owner, never direct plan rewrites."""

from __future__ import annotations

import copy
import json
import os
import subprocess
from pathlib import Path

import pytest
from tests.test_native_planning_create import material
from tests.test_native_proof_producer import fixture as proof_fixture
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


def test_classified_proof_observations_preserve_work_and_reusable_evidence(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path
) -> None:
    """One native journey covers the shared lifetime/proof boundary, not adapters."""
    context = proof_fixture(tmp_path)

    def call(value: dict) -> dict:
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    value = material()
    value["material_lifetimes"]["proof_observed"] = "observation"
    value["relationships"]["external_posture"] = {"head": "old", "review": "pending"}
    value["proof"] = {"observed": "Check queued at old head", "remaining": "Current input must satisfy the check"}
    value["continuation"] = {
        "accepted_progress": "Source boundary implemented; current evidence establishes the bounded leaf",
        "residual": "Containing lane still requires the separate integration outcome",
    }
    create = call(context)["planning"]["creation_requests"][0]
    create["arguments"] = {"material": value}
    ready = call({**context, "request": create})
    created = call({**context, "invocation": ready["decision_packet"]["primary_action"]})
    context = created["value"]["selection_context"]
    selected = call({**context, "request": created["value"]["selection_request"]})
    call({**context, "invocation": selected["decision_packet"]["primary_action"]})
    plan = tmp_path / created["value"]["owner_path"]
    before = plan.read_bytes()
    assert "observed" not in json.loads(before)["proof"]
    current = call(context)
    subject = current["planning"]["current_owner"]["reconciliation"]["subject"]
    execute = current["verification"]["execution_requests"][0]
    action = call({**context, "request": execute})["decision_packet"]["primary_action"]
    result = call({**context, "invocation": action})
    reference = result["value"]["publication"]["reference"]
    assert result["value"]["process"]["status"] == "passed"
    receipts = tmp_path / ".agentic-workspace/proof/receipts"
    published = {p.name: p.read_bytes() for p in receipts.glob("*.json")}

    def evidence() -> dict:
        claim = call(context)["verification"]["requests"][0]
        claim["arguments"]["evidence_refs"] = [reference]
        checked = call({**context, "request": claim})
        assert checked["decision_packet"]["status"] != "terminal"
        return checked["verification"]["evidence"][0]

    update = {**value, "lifecycle": "planned", "phase": "shaping"}
    for observation in ("Check passed at new head; leaf merged", "Provider unavailable; historical result unchanged"):
        update["proof"]["observed"] = observation
        update["relationships"]["external_posture"] = {"head": observation, "review": "changed"}
        request = call(context)["planning"]["update_requests"][0]
        request["arguments"]["material"] = update
        resolved = call({**context, "request": request})
        assert resolved["planning"]["update_material_status"] == "unchanged"
        assert resolved["decision_packet"]["primary_action"] is None
        assert plan.read_bytes() == before
        fresh = call(context)["planning"]["current_owner"]["reconciliation"]["subject"]
        assert fresh == subject
        assert fresh["state"]["proof"]["declared"]["remaining"] == value["proof"]["remaining"]
        assert fresh["state"]["residual"]["continuation"] == value["continuation"]
        assert evidence()["evidence_freshness"] == "reusable"
        assert {p.name: p.read_bytes() for p in receipts.glob("*.json")} == published
        assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]

    # Real proof inputs and obligations remain material; no rerun is hidden in resolution.
    original = (tmp_path / "a.txt").read_bytes()
    (tmp_path / "a.txt").write_text("changed input")
    assert evidence()["evidence_freshness"] == "stale"
    (tmp_path / "a.txt").write_bytes(original)
    assert evidence()["evidence_freshness"] == "reusable"
    update["proof"]["remaining"] = "Also establish the changed compatibility requirement"
    request = call(context)["planning"]["update_requests"][0]
    request["arguments"]["material"] = update
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.update"
    call({**context, "invocation": action})
    assert plan.read_bytes() != before
    assert call(context)["planning"]["current_owner"]["reconciliation"]["subject"]["revision"] != subject["revision"]
    assert evidence()["evidence_freshness"] == "stale"
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]
    with pytest.raises(AssertionError, match="stale"):
        call({**context, "request": request})


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_observation_movement_has_no_postimage_but_semantic_change_does(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = {"target": str(tmp_path), "task": "Implement the upper feature's durable outcome"}

    def call(value: dict) -> dict:
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    def git(*args: str) -> str:
        result = subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True, text=True)
        return result.stdout.strip()

    git("init", "-b", "master")
    git("config", "user.name", "Planning fixture")
    git("config", "user.email", "planning@example.invalid")
    git("config", "core.autocrlf", "false")
    git("commit", "--allow-empty", "-m", "Initial target")
    git("switch", "-c", "feature/upper")

    value = material()
    value["material_lifetimes"] = {
        "next_action": "observation",
        "external_posture": "observation",
        "continuation_frontier": "observation",
    }
    value["next_action"] = "Wait for lower PR review"
    value["relationships"]["external_posture"] = {"head": "lower-a", "review": "pending"}
    value["continuation"] = {
        "frontier": "Lower PR is unmerged",
        "accepted_progress": "The upper feature has its new source-delivery boundary",
        "residual": "Prove the upper feature's currentness negatives",
    }
    value["integration_proposal"] = {
        "target_ref": "refs/heads/master",
        "requested_transition": "close-owner",
        "proof_refs": [],
        "remaining_obligations": "Integration alone cannot close the owner; prove currentness negatives",
    }
    create = call(context)["planning"]["creation_requests"][0]
    create["arguments"] = {"material": value}
    unclassified = copy.deepcopy(create)
    del unclassified["arguments"]["material"]["material_lifetimes"]
    with pytest.raises(AssertionError):
        call({**context, "request": unclassified})
    ready = call({**context, "request": create})
    created = call({**context, "invocation": ready["decision_packet"]["primary_action"]})
    context = created["value"]["selection_context"]
    selection = call({**context, "request": created["value"]["selection_request"]})
    call({**context, "invocation": selection["decision_packet"]["primary_action"]})
    path = tmp_path / created["value"]["owner_path"]
    before = path.read_bytes()
    git("add", "--", created["value"]["owner_path"])
    git("commit", "-m", "Upper feature semantic owner")
    feature_head = git("rev-parse", "HEAD")
    assert call(context)["planning"]["integration"]["status"] == "awaiting-target"
    retained = json.loads(before)
    assert retained["next_action"] == ""
    assert "external_posture" not in retained["relationships"]
    assert "frontier" not in retained["continuation"]
    assert retained["continuation"]["accepted_progress"] == value["continuation"]["accepted_progress"]

    update_value = {**value, "lifecycle": "planned", "phase": "shaping"}
    for observation in (
        {"head": "lower-b", "review": "approved", "ci": "running", "merged": False},
        {"head": "lower-c", "review": "approved", "ci": "passed", "merged": True},
        {"issue": "closed", "provider": "unavailable", "quota": "exhausted"},
    ):
        update_value["relationships"]["external_posture"] = observation
        update_value["next_action"] = f"Reobserve: {observation}"
        update_value["continuation"]["frontier"] = f"Current stack: {observation}"
        request = call(context)["planning"]["update_requests"][0]
        request["arguments"]["material"] = update_value
        current = call({**context, "request": request})
        assert current["planning"]["update_material_status"] == "unchanged"
        assert current["decision_packet"]["primary_action"] is None
        assert path.read_bytes() == before

    # Each consumer call is a fresh native process; no parent chat or carried
    # external observations are needed to recover accepted progress and residual.
    fresh = call(context)
    state = fresh["planning"]["current_owner"]["reconciliation"]["subject"]["state"]
    assert state["residual"]["continuation"]["accepted_progress"] == retained["continuation"]["accepted_progress"]
    assert state["residual"]["continuation"]["residual"] == retained["continuation"]["residual"]
    assert state["dependencies"]["external_posture"] is None

    # The target performs lazy observation of exact committed inclusion. Neither
    # the feature branch nor the target needs an AW bookkeeping commit.
    git("switch", "master")
    git("merge", "--no-ff", "feature/upper", "-m", "Integrate upper feature")
    integrated = call(context)["planning"]["integration"]
    assert integrated["status"] == "integration-observed"
    assert integrated["observed_head"] == git("rev-parse", "HEAD")
    assert integrated["completion_authority"] is False
    assert integrated["proof_authority"] is False
    assert path.read_bytes() == before
    git("commit", "--allow-empty", "-m", "Independent lower work advances target")
    advanced = call(context)["planning"]["integration"]
    assert advanced["status"] == "integration-observed"
    assert advanced["observed_head"] != integrated["observed_head"]
    assert path.read_bytes() == before
    terminal = copy.deepcopy(update_value)
    terminal["lifecycle"] = "closed"
    terminal["phase"] = "complete"
    terminal_request = call(context)["planning"]["update_requests"][0]
    terminal_request["arguments"]["material"] = terminal
    widened = copy.deepcopy(terminal_request)
    widened["arguments"]["material"]["continuation"]["residual"] = "Different work was not integrated"
    with pytest.raises(AssertionError, match="target reconciliation"):
        call({**context, "request": widened})
    replaced_proposal = copy.deepcopy(terminal_request)
    replaced_proposal["arguments"]["material"]["integration_proposal"]["requested_transition"] = "keep-open"
    with pytest.raises(AssertionError, match="target reconciliation"):
        call({**context, "request": replaced_proposal})
    terminal_action = call({**context, "request": terminal_request})["decision_packet"]["primary_action"]
    assert terminal_action["arguments"]["integration_observation"]["observed_head"] == advanced["observed_head"]
    git("commit", "--allow-empty", "-m", "Target moves after action selection")
    with pytest.raises(AssertionError):
        call({**context, "invocation": terminal_action})
    assert path.read_bytes() == before

    # A stale or foreign committed owner cannot inherit inclusion merely from
    # the target branch name. The live owner remains its exact admitted bytes.
    path.write_bytes(before + b"\n")
    git("add", "--", created["value"]["owner_path"])
    git("commit", "-m", "Different committed owner bytes")
    path.write_bytes(before)
    assert call(context)["planning"]["integration"]["status"] == "owner-not-integrated"
    path.write_bytes(before + b"\n")
    git("revert", "--no-edit", "HEAD")
    git("switch", "feature/upper")
    assert git("rev-parse", "HEAD") == feature_head
    assert path.read_bytes() == before
    git("switch", "--detach")
    assert call(context)["planning"]["integration"]["status"] == "detached-target-unproven"
    git("switch", "feature/upper")
    terminal_request = call(context)["planning"]["update_requests"][0]
    terminal_request["arguments"]["material"] = terminal
    with pytest.raises(AssertionError, match="target reconciliation"):
        call({**context, "request": terminal_request})
    if surface == "native":
        unavailable = consume(surface, shared_core_binary, native_cli, context, host_path="")
        assert unavailable["planning"]["integration"]["status"] == "unavailable"
        assert path.read_bytes() == before

    changed = copy.deepcopy(update_value)
    changed["continuation"]["residual"] = "Also prove failure after source replacement"
    request = fresh["planning"]["update_requests"][0]
    request["arguments"]["material"] = changed
    ready = call({**context, "request": request})
    action = ready["decision_packet"]["primary_action"]
    assert action["operation_id"] == "planning.update"
    assert path.read_bytes() == before
    call({**context, "invocation": action})
    after = json.loads(path.read_bytes())
    assert after["revision"] == retained["revision"] + 1
    assert after["continuation"]["residual"] == changed["continuation"]["residual"]
    assert "external_posture" not in after["relationships"]
    with pytest.raises(AssertionError):
        call({**context, "request": request})
    git("add", "--", created["value"]["owner_path"])
    git("commit", "-m", "Durable semantic change")
    git("switch", "master")
    git("merge", "--no-ff", "feature/upper", "-m", "Integrate durable semantic change")
    fresh = call(context)
    continuation = fresh["planning"]["requests"][0]
    reentry = call({**context, "request": continuation})
    call({**context, "invocation": reentry["decision_packet"]["primary_action"]})
    current = call(context)
    assert current["planning"]["integration"]["status"] == "integration-observed"
    terminal_request = current["planning"]["update_requests"][0]
    terminal_request["arguments"]["material"] = {**changed, "lifecycle": "closed", "phase": "complete"}
    action = call({**context, "request": terminal_request})["decision_packet"]["primary_action"]
    applied = call({**context, "invocation": action})
    assert applied["status"] == "applied"
    assert json.loads(path.read_bytes())["lifecycle"] == "closed"
    assert json.loads(path.read_bytes())["continuation"]["residual"] == changed["continuation"]["residual"]
    assert call(context)["decision_packet"]["status"] != "terminal"
    # Effect replay observes the committed owner result; it does not reapply or
    # infer current task completion from the owner lifecycle disposition.
    assert call({**context, "invocation": action})["value"] == applied["value"]
