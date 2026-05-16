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
    reporting_skill = skills_root / "planning-reporting" / "SKILL.md"
    lifecycle_skill = skills_root / "planning-high-assurance-lifecycle" / "SKILL.md"
    intent_skill = skills_root / "planning-intent-verification" / "SKILL.md"

    assert autopilot_skill.exists()
    assert intake_skill.exists()
    assert review_pass_skill.exists()
    assert promote_review_findings_skill.exists()
    assert reporting_skill.exists()
    assert lifecycle_skill.exists()
    assert intent_skill.exists()
    assert readme_path.exists()
    assert registry_path.exists()
    readme_text = readme_path.read_text(encoding="utf-8")
    registry_text = registry_path.read_text(encoding="utf-8")
    registry_payload = json.loads(registry_text)
    assert "planning-autopilot" in readme_text
    assert "planning-intake-upstream-task" in readme_text
    assert "planning-review-pass" in readme_text
    assert "planning-promote-review-findings" in readme_text
    assert "planning-reporting" in readme_text
    assert "planning-high-assurance-lifecycle" in readme_text
    assert "planning-intent-verification" in readme_text
    assert "planning-autopilot" in registry_text
    assert "planning-review-pass" in registry_text
    assert "planning-reporting" in registry_text
    assert "planning-high-assurance-lifecycle" in registry_text
    assert "planning-intent-verification" in registry_text
    autopilot_entry = next(entry for entry in registry_payload["skills"] if entry["id"] == "planning-autopilot")
    review_entry = next(entry for entry in registry_payload["skills"] if entry["id"] == "planning-review-pass")
    reporting_entry = next(entry for entry in registry_payload["skills"] if entry["id"] == "planning-reporting")
    lifecycle_entry = next(entry for entry in registry_payload["skills"] if entry["id"] == "planning-high-assurance-lifecycle")
    intent_entry = next(entry for entry in registry_payload["skills"] if entry["id"] == "planning-intent-verification")
    assert "run autopilot" in autopilot_entry["activation_hints"]["phrases"]
    assert "perform a review" in review_entry["activation_hints"]["phrases"]
    assert "planning report" in reporting_entry["activation_hints"]["phrases"]
    assert "high assurance planning lifecycle" in lifecycle_entry["activation_hints"]["phrases"]
    assert "intent verification" in intent_entry["activation_hints"]["phrases"]
    assert "negative invariants" in intent_entry["activation_hints"]["phrases"]


def test_bundled_skills_catalog_readme_matches_registry_ids() -> None:
    skills_root = Path(__file__).resolve().parents[1] / "skills"
    readme_text = (skills_root / "README.md").read_text(encoding="utf-8")
    registry_payload = json.loads((skills_root / "REGISTRY.json").read_text(encoding="utf-8"))

    readme_ids = re.findall(r"- `([^`]+)`", readme_text)
    registry_ids = [entry["id"] for entry in registry_payload["skills"]]

    assert readme_ids == registry_ids
