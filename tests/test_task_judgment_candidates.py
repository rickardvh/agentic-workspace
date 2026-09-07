"""Generic receipt history must not trigger task-judgment producer reads."""

from pathlib import Path

import pytest

from agentic_workspace import assignment_lifecycle, workspace_runtime_core, workspace_runtime_proof


@pytest.mark.parametrize("task", ["Current bounded task", ""])
def test_task_judgment_prefilters_history_without_trusting_matching_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, task: str
) -> None:
    work = {"plan_ref": "work:current", "plan_revision": "revision:current"}
    judgment = {"work_ref": "work:current", "work_revision": "revision:current", "claim_class": "slice_complete", "status": "sufficient"}
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
    assert reads == (["proof://receipts/pasted-untrusted-judgment"] if task else [])
    assert identities == (["pasted-untrusted-judgment"] if task else [])
    assert result["status"] == "task-judgment-required"
    assert result["current_judgment_count"] == 0
