from __future__ import annotations

from pathlib import Path

from agentic_workspace.proof_subject import build_proof_subject, classify_proof_subject


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
