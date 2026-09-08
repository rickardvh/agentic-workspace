"""Current proof evaluation batches transport without retaining proof authority."""

import json
from pathlib import Path

from agentic_workspace import decision, proof_receipt_admission, proof_subject, workspace_runtime_proof


def test_subject_batch_bounds_transport_and_rechecks_changed_inputs(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "a.txt"
    source.write_text("one", encoding="utf-8")
    subject = proof_subject.build_proof_subject(target_root=tmp_path, changed_paths=["a.txt"], command="check a")
    receipts = [{"command": "check a", "proof_subject": subject}] * 129
    calls = []
    real = proof_subject.proof_subject

    def observe(request):
        calls.append(request["action"])
        return real(request)

    monkeypatch.setattr(proof_subject, "proof_subject", observe)
    current = proof_subject.classify_proof_subjects(target_root=tmp_path, receipts=receipts, changed_paths=["a.txt"])
    assert calls == ["classify-many", "classify-many"]
    assert all(item["status"] == "reusable" for item in current)
    source.write_text("two", encoding="utf-8")
    stale = proof_subject.classify_proof_subjects(target_root=tmp_path, receipts=receipts, changed_paths=["a.txt"])
    assert calls == ["classify-many"] * 4
    assert all(item["status"] == "stale" for item in stale)


def test_reconciliation_batches_current_candidates_once(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "a.txt").write_text("one", encoding="utf-8")
    commands = ["check a", "check b"]
    subjects = {
        command: proof_subject.build_proof_subject(target_root=tmp_path, changed_paths=["a.txt"], command=command) for command in commands
    }
    receipts = [
        {
            "kind": "agentic-workspace/proof-receipt/v1",
            "command": commands[index % 2],
            "proof_subject": subjects[commands[index % 2]],
            "result": "passed",
            "changed_paths": ["a.txt"],
            "recorded_at": "2026-09-07T00:00:00Z",
        }
        for index in range(20)
    ]
    monkeypatch.setattr(workspace_runtime_proof, "_read_proof_receipt_records", lambda _: (receipts, receipts[0], {}, ""))
    native_processes = []
    run = decision.subprocess.run

    def observe_process(args, **kwargs):
        if Path(args[0]).name.removesuffix(".exe") == "agentic-workspace-core":
            native_processes.append(args)
        return run(args, **kwargs)

    monkeypatch.setattr(decision.subprocess, "run", observe_process)
    calls = []
    for module, name in [(proof_subject, "proof_subject"), (proof_receipt_admission, "proof_receipt")]:
        real = getattr(module, name)

        def observe(request, real=real):
            calls.append(request["action"])
            return real(request)

        monkeypatch.setattr(module, name, observe)
    result = workspace_runtime_proof._proof_receipt_reconciliation_payload(
        target_root=tmp_path, required_commands=commands, changed_paths=["a.txt"]
    )
    assert result["status"] == "accepted"
    assert calls == ["admit-many", "classify-many"]
    assert len(native_processes) == 2


def test_history_batches_admission_preserving_deduplication_and_corruption(tmp_path: Path, monkeypatch) -> None:
    receipts = [
        {
            "kind": "agentic-workspace/proof-receipt/v1",
            "command": f"check {index}",
            "result": "passed",
            "changed_paths": ["a.txt"],
            "recorded_at": f"2026-09-07T00:{index:02}:00Z",
        }
        for index in range(20)
    ]
    latest = tmp_path / workspace_runtime_proof.PROOF_RECEIPT_RELATIVE_PATH
    history = tmp_path / workspace_runtime_proof.PROOF_RECEIPT_HISTORY_RELATIVE_PATH
    latest.parent.mkdir(parents=True, exist_ok=True)
    history.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(receipts[0]), encoding="utf-8")
    history.write_text("\n".join(json.dumps(item) for item in [*receipts, receipts[0], {"kind": "invalid"}]), encoding="utf-8")
    calls = []
    real = proof_receipt_admission.proof_receipt

    def observe(request):
        calls.append(request["action"])
        return real(request)

    monkeypatch.setattr(proof_receipt_admission, "proof_receipt", observe)
    records, newest, rejected, error = workspace_runtime_proof._read_proof_receipt_records(tmp_path)
    assert len(records) == 20
    assert newest == receipts[-1]
    assert rejected == {} and error == ""
    assert calls == ["admit", "admit-many"]
    history.write_text(history.read_text(encoding="utf-8") + "\ninvalid JSON", encoding="utf-8")
    records, newest, _, error = workspace_runtime_proof._read_proof_receipt_records(tmp_path)
    assert records is None and newest == receipts[0]
    assert "could not be read as JSON" in error
