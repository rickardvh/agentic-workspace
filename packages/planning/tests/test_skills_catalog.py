from __future__ import annotations

import json
import re
from pathlib import Path


def test_bundled_skills_catalog_resolves_selected_resources() -> None:
    skills_root = Path(__file__).resolve().parents[1] / "skills"
    registry = json.loads((skills_root / "REGISTRY.json").read_text())
    for skill in registry["skills"]:
        entry = skills_root / skill["path"]
        assert entry.is_file()
        if resource := skill.get("procedure_resource"):
            question = entry.parent / resource
            text = question.read_text()
            control = json.loads(text.split("```agentic-procedure\n", 1)[1].split("```", 1)[0])
            assert control["kind"] == "agentic-workspace/procedure/v1"
            for branch in control["branches"]:
                assert (question.parent / branch["next"]).is_file()
    assert not {
        "planning-decompose",
        "planning-intake-upstream-task",
        "planning-new-plan-tighten",
        "planning-intent-verification",
    }.intersection(r["id"] for r in registry["skills"])


def test_bundled_skills_catalog_readme_matches_registry_ids() -> None:
    skills_root = Path(__file__).resolve().parents[1] / "skills"
    readme_text = (skills_root / "README.md").read_text(encoding="utf-8")
    registry_payload = json.loads((skills_root / "REGISTRY.json").read_text(encoding="utf-8"))

    readme_ids = re.findall(r"- `([^`]+)`", readme_text)
    registry_ids = [entry["id"] for entry in registry_payload["skills"]]

    assert readme_ids == registry_ids


def test_bundled_skill_resource_dependencies_are_declared_and_resolvable() -> None:
    skills_root = Path(__file__).resolve().parents[1] / "skills"
    registry_payload = json.loads((skills_root / "REGISTRY.json").read_text(encoding="utf-8"))
    resources = registry_payload.get("resources", {})

    assert isinstance(resources, dict)
    for skill in registry_payload["skills"]:
        for resource_id in skill.get("required_resources", []):
            assert resource_id in resources, f"{skill['id']} references unknown resource {resource_id}"
            resource = resources[resource_id]
            package_path = resource.get("package_path")
            assert package_path, f"{resource_id} lacks a package-owned resource path"
            assert (skills_root / package_path).is_file(), f"{resource_id} is missing from the package"


def test_assignment_procedure_keeps_domain_identity_references():
    skills = Path(__file__).resolve().parents[1] / "skills"
    registry = json.loads((skills / "REGISTRY.json").read_text())
    ids = {r["id"] for r in registry["skills"]}
    assert "planning-assignment" in ids
    assert not {"planning-assurance-delegation", "planning-manual-delegation", "planning-returned-result"} & ids
    for path in (skills / "planning-assignment/references").glob("*.md"):
        text = path.read_text()
        if "```agentic-owner-reference" in text:
            identity = json.loads(text.split("```agentic-owner-reference\n", 1)[1].split("```", 1)[0])
            assert set(identity) == {"kind", "owner", "id"}
            assert identity["owner"] in {"assignment", "delegation"}


def test_skill_package_installed_and_generated_mirrors_match() -> None:
    root = Path(__file__).resolve().parents[3]
    source_root = root / "packages" / "planning" / "skills"
    mirror_roots = (
        root / ".agentic-workspace" / "planning" / "skills",
        root / "generated" / "planning" / "python" / "_skills",
        root / "generated" / "planning" / "typescript" / "resources" / "_skills",
    )
    relative_paths = [path.relative_to(source_root) for path in source_root.rglob("*") if path.is_file()]

    for relative in relative_paths:
        expected = (source_root / relative).read_bytes()
        for mirror_root in mirror_roots:
            assert (mirror_root / relative).read_bytes() == expected
