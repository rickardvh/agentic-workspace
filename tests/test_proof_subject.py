from __future__ import annotations

from pathlib import Path

from agentic_workspace.proof_subject import build_proof_subject, classify_proof_subject, compare_proof_subjects


def _receipt(root: Path, paths: list[str]) -> dict[str, object]:
    return {
        "proof_subject": build_proof_subject(target_root=root, changed_paths=paths, command="make test"),
    }


def test_proof_subject_reuses_equivalent_content(tmp_path: Path) -> None:
    source = tmp_path / "src/app.py"
    source.parent.mkdir(parents=True)
    source.write_text("print('ok')\n", encoding="utf-8")

    decision = classify_proof_subject(
        target_root=tmp_path, receipt=_receipt(tmp_path, ["src/app.py"]), changed_paths=["src/app.py"], command="make test"
    )

    assert decision["status"] == "reusable"
    assert decision["minimum_rerun_command"] == ""


def test_proof_subject_marks_changed_dependency_stale(tmp_path: Path) -> None:
    source = tmp_path / "src/app.py"
    source.parent.mkdir(parents=True)
    source.write_text("print('old')\n", encoding="utf-8")
    receipt = _receipt(tmp_path, ["src/app.py"])
    source.write_text("print('new')\n", encoding="utf-8")

    decision = classify_proof_subject(target_root=tmp_path, receipt=receipt, changed_paths=["src/app.py"], command="make test")

    assert decision == {"status": "stale", "reasons": ["dependency-input-changed"], "minimum_rerun_command": "make test"}


def test_proof_subject_never_reuses_incomplete_identity(tmp_path: Path) -> None:
    receipt = _receipt(tmp_path, ["missing.py"])

    decision = classify_proof_subject(target_root=tmp_path, receipt=receipt, changed_paths=["missing.py"], command="make test")

    assert decision["status"] == "unverifiable"
    assert decision["reasons"] == ["incomplete-subject-identity"]


def test_proof_subject_marks_independent_scope_partially_reusable(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.py").write_text("a\n", encoding="utf-8")
    (tmp_path / "src/b.py").write_text("b\n", encoding="utf-8")

    decision = classify_proof_subject(
        target_root=tmp_path, receipt=_receipt(tmp_path, ["src/a.py"]), changed_paths=["src/b.py"], command="make test"
    )

    assert decision["status"] == "partially-reusable"
    assert decision["reasons"] == ["independent-subject-scope"]


def test_proof_receipt_publication_reaches_fixed_point_without_hiding_source_changes(tmp_path: Path) -> None:
    source = tmp_path / "src/app.py"
    receipt_path = tmp_path / ".agentic-workspace/proof/receipts/proof.json"
    source.parent.mkdir(parents=True)
    source.write_text("print('stable')\n", encoding="utf-8")
    paths = ["src/app.py", ".agentic-workspace/proof/receipts/proof.json"]
    stored = build_proof_subject(target_root=tmp_path, changed_paths=paths, command="make test")

    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text('{"status":"published"}\n', encoding="utf-8")
    published = build_proof_subject(target_root=tmp_path, changed_paths=paths, command="make test")
    assert published["fingerprint"] == stored["fingerprint"]
    assert published["evidence_outputs"] == [
        {
            "path": ".agentic-workspace/proof/receipts/proof.json",
            "owner": "canonical-proof-receipt-publication",
            "role": "evidence-output",
            "reason": "proof-owned-publication-output",
        }
    ]

    source.write_text("print('changed')\n", encoding="utf-8")
    changed = build_proof_subject(target_root=tmp_path, changed_paths=paths, command="make test")
    assert compare_proof_subjects(stored=stored, current=changed)["status"] == "stale"


def test_planning_closeout_evidence_is_a_second_idempotent_publication_class(tmp_path: Path) -> None:
    source = tmp_path / "src/app.py"
    evidence = tmp_path / ".agentic-workspace/planning/closeout-evidence/lane.json"
    source.parent.mkdir(parents=True)
    source.write_text("stable\n", encoding="utf-8")
    paths = ["src/app.py", ".agentic-workspace/planning/closeout-evidence/lane.json"]
    before = build_proof_subject(target_root=tmp_path, changed_paths=paths, command="make test")
    evidence.parent.mkdir(parents=True)
    evidence.write_text('{"proof":"current"}\n', encoding="utf-8")
    after = build_proof_subject(target_root=tmp_path, changed_paths=paths, command="make test")

    assert after["fingerprint"] == before["fingerprint"]
    assert after["evidence_outputs"][0]["owner"] == "planning-closeout-evidence-publication"


def test_evidence_artifact_explicitly_declared_as_another_claim_input_remains_invalidating(tmp_path: Path) -> None:
    evidence_path = ".agentic-workspace/proof/receipts/upstream.json"
    evidence = tmp_path / evidence_path
    evidence.parent.mkdir(parents=True)
    evidence.write_text('{"revision":1}\n', encoding="utf-8")
    stored = build_proof_subject(
        target_root=tmp_path,
        changed_paths=[evidence_path],
        command="verify upstream receipt",
        semantic_input_paths=[evidence_path],
    )
    evidence.write_text('{"revision":2}\n', encoding="utf-8")
    current = build_proof_subject(
        target_root=tmp_path,
        changed_paths=[evidence_path],
        command="verify upstream receipt",
        semantic_input_paths=[evidence_path],
    )

    assert stored["dependency_roles"][0]["reason"] == "explicit-claim-dependency"
    assert compare_proof_subjects(stored=stored, current=current)["status"] == "stale"
