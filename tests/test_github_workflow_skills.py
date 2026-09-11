from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHAPING = ROOT / "tools" / "skills" / "github-issue-shaping" / "SKILL.md"
CREATION = ROOT / "tools" / "skills" / "github-issue-creation" / "SKILL.md"
REVIEW = ROOT / "tools" / "skills" / "pr-review-recheck" / "SKILL.md"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_issue_workflow_skills_share_the_three_closure_shapes() -> None:
    shaping = _text(SHAPING)
    creation = _text(CREATION)
    review = _text(REVIEW)

    for document in (shaping, creation, review):
        assert "parent outcome" in document
        assert "bounded implementation leaf" in document
        assert "later evidence" in document or "later-evidence" in document


def test_bounded_leaf_is_one_coherent_pr_with_immediate_proof() -> None:
    shaping = _text(SHAPING)
    creation = _text(CREATION)
    review = _text(REVIEW)

    assert "one coherent bounded PR" in shaping
    assert "split" in shaping and "before implementation" in shaping
    assert "one coherent bounded PR" in creation
    assert "whole bounded leaf" in review
    assert "after-the-fact" in review


def test_later_evidence_does_not_become_implementation_backlog_or_leaf_blocker() -> None:
    shaping = _text(SHAPING)
    creation = _text(CREATION)
    review = _text(REVIEW)

    assert "evidence issues do not become implementation backlogs" in shaping.lower()
    assert "no product-code" in creation
    assert "route concrete defects" in creation
    assert "Do not hold a complete bounded implementation leaf open" in review


def test_parent_closes_administratively_without_giant_pr() -> None:
    shaping = _text(SHAPING)
    creation = _text(CREATION)
    review = _text(REVIEW)

    assert "closes administratively" in shaping
    assert "giant parent-closing PR" in shaping
    assert "administrative closure" in creation
    assert "Do not require a giant parent-closing PR" in review
