"""One proof publisher for current native and interoperability owner actions."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from tests.test_native_proof_producer import fixture
from tests.test_native_public_cli import consume
from tests.test_native_public_cli import native_cli as native_cli


@pytest.mark.parametrize("surface", ["native", "json", "python", "typescript"])
def test_current_manual_observation_does_not_gain_proof(tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str) -> None:
    context = fixture(tmp_path)

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    claim = call(context)["verification"]["requests"][0]
    subject = call({**context, "request": claim})["verification"]["judgment_request"]
    request = call(context)["verification"]["record_requests"][0]
    request["arguments"]["result"] = "passed"
    request["arguments"]["reported_observation"] = {
        "authority": "aw-proof",
        "execution_kind": "native-aw-proof",
        "claim_sufficiency": "sufficient",
        "task_claim_judgment": {
            "work_ref": subject["work_ref"],
            "work_revision": subject["work_revision"],
            "task_identity": subject["task_claim_identity"],
            "claim_class": "slice_complete",
            "status": "sufficient",
        },
    }
    selected = call({**context, "request": request})
    invocation = selected["decision_packet"]["primary_action"]
    assert invocation["arguments"]["record_receipt"] is True
    result = call({**context, "invocation": invocation})
    assert result["value"]["publication"]["status"] == "published"
    assert result["value"]["producer_admission"] == "unproven-interoperability-observation"
    assert not (tmp_path / "count.txt").exists()
    claim = call(context)["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [result["value"]["publication"]["reference"]]
    checked = call({**context, "request": claim})
    assert checked["verification"]["evidence"][0]["evidence_freshness"] != "reusable"
    assert checked["verification"]["judgment_request"]["admitted_automated_evidence"] == []
    assert checked["verification"]["evidence"][0]["task_judgment"]["current_judgment_count"] == 0
    assert checked["verification"]["evidence"][0]["task_judgment"]["matched_judgment_count"] == 0
    publication_id = result["value"]["publication"]["reference"].rsplit("/", 1)[1]
    receipt = json.loads((tmp_path / ".agentic-workspace/proof/receipts" / f"{publication_id}.json").read_text())
    assert "task_claim_judgment" not in receipt
    assert receipt["execution"]["reported_observation"]["reported_observation"] == request["arguments"]["reported_observation"]
    (tmp_path / "a.txt").write_text("new material")
    next_request = call(context)["verification"]["record_requests"][0]
    next_request["arguments"]["result"] = "passed"
    next_invocation = call({**context, "request": next_request})["decision_packet"]["primary_action"]
    second = call({**context, "invocation": next_invocation})
    assert second["value"]["publication"]["reference"] != result["value"]["publication"]["reference"]
    index = json.loads((tmp_path / ".agentic-workspace/proof/receipts/index.json").read_text())
    assert len(index["receipts"]) == 2


@pytest.mark.parametrize("surface", ["native", "python", "typescript", "json"])
def test_planning_claim_cannot_use_published_manual_result(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, surface: str
) -> None:
    context = fixture(tmp_path)
    root = Path(__file__).resolve().parents[1]
    ref = Path(".agentic-workspace/planning/execplans/delegation-lane-sweep.plan.json")
    plan = tmp_path / ref
    plan.parent.mkdir(parents=True)
    plan.write_bytes((root / ref).read_bytes())
    (tmp_path / ".agentic-workspace/planning/state.toml").write_text(
        f'[[active.execplans]]\nid="delegation-lane-sweep"\npath="{ref.as_posix()}"\nstatus="active"\n'
    )

    def call(value):
        return consume(surface, shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    initial = call(context)
    continuation = initial["decision_packet"]["decision_request"]["response_request"]
    continuation["arguments"]["answer"] = "continue-selected"
    selected = call({**context, "request": continuation})
    planning_action = selected["decision_packet"]["primary_action"]
    assert planning_action["operation_id"] == "planning.reconcile"
    call({**context, "invocation": planning_action})
    request = call(context)["verification"]["record_requests"][0]
    request["arguments"]["result"] = "passed"
    request["arguments"]["reported_observation"] = {
        "claim_sufficiency": "sufficient",
        "manual_verification": "passed",
        "authority": "independent-reviewer",
    }
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    published = call({**context, "invocation": action})
    claim = call(context)["verification"]["requests"][0]
    claim["arguments"]["evidence_refs"] = [published["value"]["publication"]["reference"]]
    checked = call({**context, "request": claim})
    assert checked["verification"]["judgment_request"]["planning_subject"] is not None
    assert checked["verification"]["judgment_request"]["admitted_automated_evidence"] == []
    assert checked["verification"]["evidence"][0]["task_judgment"]["current_judgment_count"] == 0


def test_subsequent_native_execution_appends_without_replaying_prior_shell(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path
) -> None:
    context = fixture(tmp_path)

    def call(value):
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    references = []
    for content in ("first material", "second material"):
        (tmp_path / "a.txt").write_text(content)
        request = call(context)["verification"]["execution_requests"][0]
        action = call({**context, "request": request})["decision_packet"]["primary_action"]
        result = call({**context, "invocation": action})
        references.append(result["value"]["publication"]["reference"])
        assert call({**context, "invocation": action})["value"] == result["value"]
    assert len(set(references)) == 2
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed", "executed"]
    assert len(json.loads((tmp_path / ".agentic-workspace/proof/receipts/index.json").read_text())["receipts"]) == 2


def test_prior_native_run_custody_survives_receipt_format_transition(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    context = fixture(tmp_path)

    def call(value):
        return consume("native", shared_core_binary, native_cli, value, host_path=os.environ["PATH"])

    request = call(context)["verification"]["execution_requests"][0]
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    first = call({**context, "invocation": action})
    receipt_path = tmp_path / ".agentic-workspace/proof/receipts" / (first["value"]["publication"]["reference"].rsplit("/", 1)[1] + ".json")
    receipt = json.loads(receipt_path.read_text())
    # Earlier native receipts retain run/completed custody, not this newly added carrier.
    receipt.pop("publication_custody")
    receipt_path.write_text(json.dumps(receipt))
    prior_bytes = receipt_path.read_bytes()
    (tmp_path / "a.txt").write_text("new source material")
    request = call(context)["verification"]["execution_requests"][0]
    action = call({**context, "request": request})["decision_packet"]["primary_action"]
    second = call({**context, "invocation": action})
    assert second["value"]["publication"]["status"] == "published"
    assert receipt_path.read_bytes() == prior_bytes
    assert len(json.loads(receipt_path.with_name("index.json").read_text())["receipts"]) == 2
