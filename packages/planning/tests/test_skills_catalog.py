from __future__ import annotations

from pathlib import Path


def test_bundled_skills_catalog_lists_core_and_review_skills() -> None:
    skills_root = Path(__file__).resolve().parents[1] / "skills"
    readme_path = skills_root / "README.md"
    autopilot_skill = skills_root / "planning-autopilot" / "SKILL.md"
    review_pass_skill = skills_root / "planning-review-pass" / "SKILL.md"
    promote_review_findings_skill = skills_root / "planning-promote-review-findings" / "SKILL.md"

    assert autopilot_skill.exists()
    assert review_pass_skill.exists()
    assert promote_review_findings_skill.exists()
    assert readme_path.exists()
    readme_text = readme_path.read_text(encoding="utf-8")
    assert "planning-autopilot" in readme_text
    assert "planning-review-pass" in readme_text
    assert "planning-promote-review-findings" in readme_text
