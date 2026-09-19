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


def test_delegation_skills_have_one_post_assignment_owner_and_current_target_exclusion() -> None:
    root = Path(__file__).resolve().parents[3]
    skills_root = root / "packages" / "planning" / "skills"
    orchestrator = (skills_root / "planning-orchestrator-workflow" / "SKILL.md").read_text(encoding="utf-8")
    assurance = (skills_root / "planning-assurance-delegation" / "SKILL.md").read_text(encoding="utf-8")
    lifecycle = (skills_root / "planning-high-assurance-lifecycle" / "SKILL.md").read_text(encoding="utf-8")
    contract = (root / ".agentic-workspace" / "docs" / "orchestrator-workflow-contract.md").read_text(encoding="utf-8")
    registry = json.loads((skills_root / "REGISTRY.json").read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in registry["skills"]}

    assert "sole primary post-assignment orchestrator procedure" in orchestrator
    assert "binding non-local assignment forbids local implementation" in orchestrator
    assert "do not load this skill" in orchestrator
    assert "only before a canonical assignment exists" in assurance
    assert "A binding assignment ends this skill's authority" in assurance
    assert "routing wrapper and owns lifecycle sequencing only" in lifecycle
    assert "without loading `planning-orchestrator-workflow`" in lifecycle
    assert "free-form task wording does not" in contract
    assert "never implement the worker slice locally as fallback" in contract

    obsolete_branches = (
        "not worthwhile",
        "delegation is worthwhile",
        "stay direct",
        "direct single-agent fallback",
        "cost more than it saves",
        "weaker or cheaper implementer",
    )
    for text in (orchestrator, assurance, lifecycle, contract):
        lowered = text.lower()
        for branch in obsolete_branches:
            assert branch not in lowered

    orchestrator_activation = entries["planning-orchestrator-workflow"]["activation_contract"]
    assert orchestrator_activation["authority"] == "canonical current decision"
    assert "selected current target" in orchestrator_activation["excludes"]
    assert "absent or unresolved assignment" in orchestrator_activation["excludes"]
    assurance_activation = entries["planning-assurance-delegation"]["activation_contract"]
    assert assurance_activation["authority"] == "canonical assignment owner"
    assert "binding assignment" in assurance_activation["excludes"]
    assert entries["planning-high-assurance-lifecycle"]["activation_contract"]["role"] == "umbrella-router"


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
