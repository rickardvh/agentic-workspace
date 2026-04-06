from __future__ import annotations

from pathlib import Path


def test_bundled_skills_catalog_includes_planning_autopilot() -> None:
    skills_root = Path(__file__).resolve().parents[1] / "skills"
    skill_file = skills_root / "planning-autopilot" / "SKILL.md"
    readme_path = skills_root / "README.md"

    assert skill_file.exists()
    assert readme_path.exists()
    assert "planning-autopilot" in readme_path.read_text(encoding="utf-8")
