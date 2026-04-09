from __future__ import annotations

import json
import re
from pathlib import Path


def test_bundled_skills_catalog_lists_core_and_review_skills() -> None:
    skills_root = Path(__file__).resolve().parents[1] / "skills"
    readme_path = skills_root / "README.md"
    registry_path = skills_root / "REGISTRY.json"
    autopilot_skill = skills_root / "planning-autopilot" / "SKILL.md"
    intake_skill = skills_root / "planning-intake-upstream-task" / "SKILL.md"
    review_pass_skill = skills_root / "planning-review-pass" / "SKILL.md"
    promote_review_findings_skill = skills_root / "planning-promote-review-findings" / "SKILL.md"

    assert autopilot_skill.exists()
    assert intake_skill.exists()
    assert review_pass_skill.exists()
    assert promote_review_findings_skill.exists()
    assert readme_path.exists()
    assert registry_path.exists()
    readme_text = readme_path.read_text(encoding="utf-8")
    registry_text = registry_path.read_text(encoding="utf-8")
    registry_payload = json.loads(registry_text)
    assert "planning-autopilot" in readme_text
    assert "planning-intake-upstream-task" in readme_text
    assert "planning-review-pass" in readme_text
    assert "planning-promote-review-findings" in readme_text
    assert "planning-autopilot" in registry_text
    assert "planning-review-pass" in registry_text
    autopilot_entry = next(entry for entry in registry_payload["skills"] if entry["id"] == "planning-autopilot")
    review_entry = next(entry for entry in registry_payload["skills"] if entry["id"] == "planning-review-pass")
    assert "run autopilot" in autopilot_entry["activation_hints"]["phrases"]
    assert "perform a review" in review_entry["activation_hints"]["phrases"]


def test_bundled_skills_catalog_readme_matches_registry_ids() -> None:
    skills_root = Path(__file__).resolve().parents[1] / "skills"
    readme_text = (skills_root / "README.md").read_text(encoding="utf-8")
    registry_payload = json.loads((skills_root / "REGISTRY.json").read_text(encoding="utf-8"))

    readme_ids = re.findall(r"- `([^`]+)`", readme_text)
    registry_ids = [entry["id"] for entry in registry_payload["skills"]]

    assert readme_ids == registry_ids
