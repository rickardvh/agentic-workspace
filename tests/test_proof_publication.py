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


def test_retained_python_writer_and_native_publication_share_index(tmp_path: Path, shared_core_binary: Path, native_cli: Path) -> None:
    import concurrent.futures
    import subprocess
    import sys

    context = fixture(tmp_path)
    initial = consume("native", shared_core_binary, native_cli, context, host_path=os.environ["PATH"])
    request = initial["verification"]["execution_requests"][0]
    invocation = consume("native", shared_core_binary, native_cli, {**context, "request": request}, host_path=os.environ["PATH"])[
        "decision_packet"
    ]["primary_action"]
    reported = {"command": request["arguments"]["command"], "result": "passed", "changed_paths": ["a.txt"]}
    script = "import json,sys; from pathlib import Path; from agentic_workspace.workspace_runtime_core import _write_trusted_producer_receipt; print(_write_trusted_producer_receipt(target_root=Path(sys.argv[1]),producer_class='aw-proof',receipt_id='ignored-caller-identity',receipt=json.loads(sys.argv[2]),source_ref='caller-report',task_text='Report the current observation'))"

    def python_publish():
        env = {**os.environ, "AGENTIC_WORKSPACE_CORE_BINARY": str(shared_core_binary)}
        result = subprocess.run(
            [sys.executable, "-c", script, str(tmp_path), json.dumps(reported)],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        python_result = pool.submit(python_publish)
        native_result = pool.submit(
            consume, "native", shared_core_binary, native_cli, {**context, "invocation": invocation}, host_path=os.environ["PATH"]
        )
        native_ref = native_result.result()["value"]["publication"]["reference"]
        python_ref = python_result.result()
    index = json.loads((tmp_path / ".agentic-workspace/proof/receipts/index.json").read_text())
    assert set(index["receipts"]) == {native_ref.rsplit("/", 1)[1], python_ref.rsplit("/", 1)[1]}
    assert (tmp_path / "count.txt").read_text().splitlines() == ["executed"]
    manual = json.loads((tmp_path / ".agentic-workspace/proof/receipts" / (python_ref.rsplit("/", 1)[1] + ".json")).read_text())
    assert manual["execution"]["producer_admission"] == "unproven"
    assert manual["execution"]["reported_observation"]["reported_observation"] == reported


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


def test_python_unknown_index_and_rollback_preserve_publication(
    tmp_path: Path, shared_core_binary: Path, native_cli: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from agentic_workspace import workspace_runtime_core as runtime
    from agentic_workspace.decision import DecisionContractError

    monkeypatch.setenv("AGENTIC_WORKSPACE_CORE_BINARY", str(shared_core_binary))
    context = fixture(tmp_path)
    request = consume("python", shared_core_binary, native_cli, context, host_path=os.environ["PATH"])["verification"]["record_requests"][0]
    reported = {"command": request["arguments"]["command"], "result": "passed", "changed_paths": ["a.txt"]}
    index = tmp_path / ".agentic-workspace/proof/receipts/index.json"
    index.parent.mkdir(parents=True)
    original = b'{"kind":"agentic-workspace/trusted-producer-receipt-index/v1","receipts":{}}'
    index.write_bytes(original)

    def publish():
        return runtime._write_trusted_producer_receipt(
            target_root=tmp_path,
            producer_class="aw-proof",
            receipt_id="untrusted-name",
            receipt=reported,
            source_ref="reported",
            task_text=context["task"],
        )

    with pytest.raises(DecisionContractError, match="custody-required"):
        publish()
    assert index.read_bytes() == original
    assert not (tmp_path / ".agentic-workspace/local/effects").exists()
    index.unlink()  # Test-owned collision fixture; never product recovery.
    with pytest.raises(RuntimeError, match="downstream failure"):
        with runtime._proof_receipt_publication_transaction(target_root=tmp_path, producer_receipt_id="untrusted-name"):
            reference = publish()
            published = index.read_bytes()
            raise RuntimeError("downstream failure")
    assert index.read_bytes() == published
    receipt = index.with_name(reference.rsplit("/", 1)[1] + ".json")
    assert receipt.is_file()
    assert json.loads(receipt.read_text())["publication_custody"]["kind"] == "agentic-workspace/proof-publication-custody/v1"


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
