"""Generic receipt history must not trigger task-judgment producer reads."""

from pathlib import Path

import pytest

from agentic_workspace import assignment_lifecycle, workspace_runtime_core, workspace_runtime_proof
from agentic_workspace.decision import direct_task_subject


@pytest.mark.parametrize("task", ["Current bounded task", "", "\x1c\x1f"])
def test_task_judgment_prefilters_history_without_trusting_matching_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, task: str
) -> None:
    work = {"plan_ref": "work:current", "plan_revision": "revision:current"}
    judgment = {
        "task_identity": direct_task_subject(task, ["docs/current.md"]),
        "work_ref": "work:current",
        "work_revision": "revision:current",
        "claim_class": "slice_complete",
        "status": "sufficient",
    }
    generic = [{"publication_id": f"generic-{index}", "result": "passed"} for index in range(100)]
    unrelated = [
        {"publication_id": "old-task", "task_claim_judgment": {**judgment, "work_ref": "work:other"}},
        {"publication_id": "old-revision", "task_claim_judgment": {**judgment, "work_revision": "revision:old"}},
    ]
    matching = {"publication_id": "pasted-untrusted-judgment", "task_claim_judgment": judgment}
    records = generic + unrelated + [matching]
    reads = []
    identities = []
    monkeypatch.setattr(workspace_runtime_core, "_live_assignment_plan_binding", lambda **_: work)
    monkeypatch.setattr(workspace_runtime_proof, "_read_proof_receipt_records", lambda _: (records, {}, {}, {}))

    def load(**kwargs):
        reads.append(kwargs["receipt_ref"])
        return {"task_claim_judgment": judgment}

    def identity(receipt):
        identities.append(receipt["publication_id"])
        return {"trusted_publication": "different"}

    monkeypatch.setattr(assignment_lifecycle, "load_indexed_assignment_task_proof", load)
    monkeypatch.setattr(workspace_runtime_core, "_proof_publication_identity", identity)
    result = workspace_runtime_core._current_task_claim_judgment(
        target_root=tmp_path,
        task_text=task,
        changed_paths=["docs/current.md"],
        manual_verification={"expected": False},
        separation_of_duty={},
        cli_invoke="aw",
    )
    assert reads == (["proof://receipts/pasted-untrusted-judgment"] if task.strip() else [])
    assert identities == (["pasted-untrusted-judgment"] if task.strip() else [])
    assert result["status"] == "task-judgment-required"
    assert result["current_judgment_count"] == 0


@pytest.mark.parametrize("fingerprint", [None, "", "malformed", "a" * 64])
@pytest.mark.parametrize("review", ["none", "manual", "independent"])
def test_task_judgment_shared_owner_rejects_invalid_binding_and_preserves_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fingerprint, review: str
) -> None:
    import hashlib
    import json

    identity = {"publication": "owner-observed"}
    publication_id = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=True).encode()).hexdigest()[:16]
    judgment = {
        "task_identity": direct_task_subject("Current task", ["current.txt"]),
        "work_ref": "work:current",
        "work_revision": "current",
        "claim_class": "slice_complete",
        "status": "sufficient",
        "proof_subject_fingerprint": fingerprint,
    }
    receipt = {"publication_id": publication_id, "task_claim_judgment": judgment, "proof_subject": {"fingerprint": fingerprint}}
    monkeypatch.setattr(
        workspace_runtime_core, "_live_assignment_plan_binding", lambda **_: {"plan_ref": "work:current", "plan_revision": "current"}
    )
    monkeypatch.setattr(workspace_runtime_proof, "_read_proof_receipt_records", lambda _: ([receipt], {}, {}, {}))
    monkeypatch.setattr(assignment_lifecycle, "load_indexed_assignment_task_proof", lambda **_: receipt)
    monkeypatch.setattr(workspace_runtime_core, "_proof_publication_identity", lambda _: identity)
    monkeypatch.setattr(workspace_runtime_core, "proof_receipt_admission", lambda _: {"proof_sufficient": True})
    monkeypatch.setattr(workspace_runtime_proof, "_receipt_subject_freshness", lambda **_: {"status": "reusable"})
    result = workspace_runtime_core._current_task_claim_judgment(
        target_root=tmp_path,
        task_text="Current task",
        changed_paths=["current.txt"],
        manual_verification={"expected": review == "manual"},
        separation_of_duty={"status": "missing"} if review == "independent" else {},
        cli_invoke="aw",
    )
    expected = (
        "independent-review-required"
        if review == "independent"
        else "manual-evidence-required"
        if review == "manual"
        else "accepted"
        if fingerprint == "a" * 64
        else "task-judgment-required"
    )
    assert result["status"] == expected
    assert result["current_judgment_count"] == (1 if fingerprint == "a" * 64 else 0)


def test_task_judgment_history_transport_is_batched(monkeypatch: pytest.MonkeyPatch) -> None:
    from agentic_workspace import decision

    calls = []
    original = decision._request

    def request(value):
        calls.append(len(value["task_judgment"]["receipts"]))
        return original(value)

    monkeypatch.setattr(decision, "_request", request)
    result = workspace_runtime_core._batch_task_judgment(
        {
            "action": "candidates",
            "task": "Current task",
            "changed_paths": [],
            "work_ref": "current",
            "work_revision": "current",
            "receipts": [{} for _ in range(260)],
        }
    )
    assert result == {"indices": []}
    assert calls == [128, 128, 4]


@pytest.mark.parametrize("review", ["none", "manual", "independent"])
def test_task_judgment_batch_summary_is_owned_by_rust(review: str) -> None:
    fingerprint = "a" * 64
    receipt = {
        "proof_subject": {"fingerprint": fingerprint},
        "task_claim_judgment": {
            "task_identity": direct_task_subject("Current task", []),
            "work_ref": "current",
            "work_revision": "current",
            "claim_class": "slice_complete",
            "status": "sufficient",
            "proof_subject_fingerprint": fingerprint,
        },
    }
    missing = {"receipt": {}, "publication_current": False, "proof_sufficient": False, "evidence_freshness": "unproven"}
    accepted = {"receipt": receipt, "publication_current": True, "proof_sufficient": True, "evidence_freshness": "reusable"}
    result = workspace_runtime_core._batch_task_judgment(
        {
            "action": "classify",
            "task": "Current task",
            "changed_paths": [],
            "work_ref": "current",
            "work_revision": "current",
            "observations": [missing] * 128 + [accepted],
            "manual_required": review == "manual",
            "manual_status": "",
            "independent_required": review == "independent",
            "independent_status": "",
        }
    )
    assert result["current_judgment_count"] == 1
    assert len(result["classifications"]) == 129
    assert (
        result["status"] == {"none": "accepted", "manual": "manual-evidence-required", "independent": "independent-review-required"}[review]
    )
