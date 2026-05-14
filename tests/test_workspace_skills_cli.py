from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_skills_command_lists_registered_workspace_skills(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["skills", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    skill_ids = {entry["id"] for entry in payload["skills"]}
    assert "workspace-startup" in skill_ids
    assert "workspace-setup-jumpstart" in skill_ids
    assert "planning-autopilot" in skill_ids
    assert "memory-router" in skill_ids
    assert "planning-reporting" in skill_ids
    assert all(entry["registration"] == "explicit" for entry in payload["skills"])
    workspace_startup = next(entry for entry in payload["skills"] if entry["id"] == "workspace-startup")
    assert workspace_startup["source_kind"] == "installed-workspace-skills"
    assert "workspace startup" in workspace_startup["activation_hints"]["phrases"]
    setup_jumpstart = next(entry for entry in payload["skills"] if entry["id"] == "workspace-setup-jumpstart")
    assert setup_jumpstart["source_kind"] == "installed-workspace-skills"
    assert "lived-in repo" in setup_jumpstart["activation_hints"]["phrases"]
    assert "mature repo" in setup_jumpstart["activation_hints"]["nouns"]
    autopilot = next(entry for entry in payload["skills"] if entry["id"] == "planning-autopilot")
    assert "run autopilot" in autopilot["activation_hints"]["phrases"]


def test_skills_command_recommends_matching_agent_aids_without_retired_aids(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    aid_root = target / ".agentic-workspace" / "agent-aids" / "scripts"
    manifest = {
        "kind": "agentic-workspace/agent-aid/v1",
        "id": "workspace-validation-wrapper",
        "type": "script",
        "status": "candidate",
        "scope": "repo-shared",
        "portability": "cross-platform",
        "proof_role": "candidate-aid",
        "owner": "workspace",
        "created_because": "Agents repeatedly need a bounded validation wrapper.",
        "use_when": ["validating workspace CLI and contract changes"],
        "entrypoint": ".agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py",
        "safety": {
            "read_only": True,
            "writes_repo": False,
            "destructive": False,
            "network": False,
            "hidden_required_workflow": False,
            "requires_review": False,
        },
        "validation": {"commands": ["uv run python .agentic-workspace/agent-aids/scripts/workspace-validation/workspace_validation.py"]},
        "promotion": {
            "target_kind": "check",
            "target": "scripts/check/check_workspace_validation.py",
            "discovery_route": "repo-check",
            "trigger": "used successfully across multiple closeouts",
            "retention_after_promotion": "delete",
        },
        "retirement": {"trigger": "obsolete", "retention_after_retirement": "delete"},
    }
    (aid_root / "workspace-validation" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (aid_root / "old-helper" / "manifest.json").write_text(
        json.dumps({**manifest, "id": "old-helper", "status": "retired"}),
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "validate workspace CLI contracts",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert [entry["id"] for entry in payload["agent_aids"]] == ["workspace-validation-wrapper"]
    assert payload["agent_aids"][0]["canonical_proof_route"] is False
    assert payload["agent_aids"][0]["safety_summary"]["read_only"] is True
    assert payload["agent_aid_recommendations"][0]["id"] == "workspace-validation-wrapper"
    assert payload["agent_aid_source"]["section_command"] == ("agentic-workspace report --target ./repo --section agent_aids --format json")


def test_skills_command_recommends_planning_autopilot_for_active_milestone_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "run autopilot and implement the current active milestone from the execplan",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "planning-autopilot"
    assert payload["recommendations"][0]["score"] > 0
    assert any("phrase match" in reason for reason in payload["recommendations"][0]["reasons"])


def test_skills_command_select_returns_compact_recommendations_without_inventory(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "run autopilot and implement the current active milestone from the execplan",
                "--select",
                "recommendations,warnings",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["kind"] == "agentic-workspace/selected-output/v1"
    assert payload["source_command"] == "skills"
    assert "recommendations" in payload["values"]
    assert "warnings" in payload["values"]
    assert payload["values"]["recommendations"][0]["id"] == "planning-autopilot"
    assert "skills" not in payload["values"]


def test_skills_command_select_supports_top_recommendations_alias(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "run autopilot and implement the current active milestone from the execplan",
                "--select",
                "top_recommendations,warnings",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["values"]["top_recommendations"][0]["id"] == "planning-autopilot"
    assert payload["values"]["warnings"] == []


def test_skills_command_recommends_planning_reporting_for_setup_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "setup the repo after bootstrap without widening init",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "workspace-setup-jumpstart"
    assert payload["recommendations"][0]["score"] > 10
    assert "workspace setup jumpstart route" in payload["recommendations"][0]["reasons"][0]


def test_skills_command_recommends_setup_jumpstart_for_mature_repo_seeding(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "populate surfaces after newly installed workspace in a lived-in repo",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "workspace-setup-jumpstart"
    assert payload["recommendations"][0]["source_kind"] == "installed-workspace-skills"
    assert "pre-write and pre-seed discovery" in Path("docs/jumpstart-contract.md").read_text(encoding="utf-8")


def test_skills_command_recommends_memory_router_for_note_selection_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "find the smallest memory note set and route memory for this task",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "memory-router"
    assert payload["recommendations"][0]["source_kind"] == "installed-core-skills"


def test_skills_command_recommends_review_skill_for_natural_review_request(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "perform a review of the planning package",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "planning-review-pass"
    assert any("verb match" in reason or "phrase match" in reason for reason in payload["recommendations"][0]["reasons"])


def test_skills_command_discovers_temporary_memory_bootstrap_skills(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target), "--preset", "memory", "--format", "json"]) == 0
    capsys.readouterr()

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "finish bootstrap installation review for memory",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    install_skill = next(entry for entry in payload["skills"] if entry["id"] == "install")

    assert install_skill["source_kind"] == "temporary-memory-bootstrap-skills"
    assert install_skill["scope"] == "temporary-bootstrap"
    assert install_skill["path"] == ".agentic-workspace/memory/bootstrap/skills/install/SKILL.md"
    assert payload["recommendations"][0]["id"] == "install"
    assert not payload["warnings"]
    assert any(source["name"] == "memory-bootstrap-temporary" and source["state"] == "registry" for source in payload["sources"])


def test_skills_command_recommends_high_risk_workflow_decision_skills(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    cases = [
        ("large vague feature request classify shape before implementation", "workspace-work-shape"),
        ("decompose an epic into lanes before execplans", "planning-decompose"),
        ("tighten a new execplan before coding", "planning-new-plan-tighten"),
        ("assurance classification and delegation posture before implementation", "planning-assurance-delegation"),
        ("high assurance planning lifecycle preserve intent satisfaction across a whole epic", "planning-high-assurance-lifecycle"),
        ("closeout trust and residue distillation after implementation", "planning-closeout-trust"),
    ]
    for task, expected in cases:
        assert cli.main(["skills", "--target", str(target), "--task", task, "--format", "json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["recommendations"], task
        assert payload["recommendations"][0]["id"] == expected


def test_skills_command_recommends_repo_dogfooding_for_skill_optimisation_loop(capsys) -> None:
    assert (
        cli.main(
            [
                "skills",
                "--target",
                ".",
                "--task",
                "run skill optimisation evaluation loops",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"]
    assert payload["recommendations"][0]["id"] == "self-improvement-dogfooding"


def test_skills_command_prefers_dogfooding_for_evaluation_scenarios(capsys) -> None:
    assert (
        cli.main(
            [
                "skills",
                "--target",
                ".",
                "--task",
                "Run exploratory evaluation scenarios and file findings as issues",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"]
    assert payload["recommendations"][0]["id"] == "self-improvement-dogfooding"


def test_skills_command_recommends_self_improvement_for_hyphenated_dogfooding_task(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / "tools" / "skills" / "REGISTRY.json",
        {
            "schema_version": "skill-registry.v1",
            "owner": "repo-local-tool-skills",
            "source_kind": "repo-owned-tool-skills",
            "skills": [
                {
                    "id": "self-improvement-dogfooding",
                    "path": "self-improvement-dogfooding/SKILL.md",
                    "summary": "run bounded repo-local improvement cycles that dogfood package surfaces",
                    "activation_hints": {
                        "verbs": ["continue", "repeat", "improve", "dogfood", "autopilot"],
                        "nouns": ["self-improvement", "dogfooding", "improvement lane", "system intent"],
                        "phrases": ["run self-improvement", "repeat improvement work", "dogfood the package"],
                        "when": ["repo-local improvement loop", "system-intent follow-through"],
                    },
                }
            ],
        },
    )
    _write(target / "tools" / "skills" / "self-improvement-dogfooding" / "SKILL.md", "# Self-improvement\n")

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "create a system-intent review and use it to run self-improvement until findings are addressed",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "self-improvement-dogfooding"
    assert any("phrase match: run self-improvement" in reason for reason in payload["recommendations"][0]["reasons"])
    assert any("noun match" in reason and "self-improvement" in reason for reason in payload["recommendations"][0]["reasons"])


def test_skills_command_prioritizes_self_improvement_for_system_wide_improvement_review(
    tmp_path: Path,
    capsys,
) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()
    _write_json(
        target / "tools" / "skills" / "REGISTRY.json",
        {
            "schema_version": "skill-registry.v1",
            "owner": "repo-local-tool-skills",
            "source_kind": "repo-owned-tool-skills",
            "skills": [
                {
                    "id": "self-improvement-dogfooding",
                    "path": "self-improvement-dogfooding/SKILL.md",
                    "summary": "run bounded repo-local improvement cycles that dogfood package surfaces",
                    "activation_hints": {
                        "nouns": ["self-improvement", "dogfooding", "system intent"],
                    },
                }
            ],
        },
    )
    _write(target / "tools" / "skills" / "self-improvement-dogfooding" / "SKILL.md", "# Self-improvement\n")

    assert (
        cli.main(
            [
                "skills",
                "--target",
                str(target),
                "--task",
                "make a full review of the system as a whole to drive self-improvement",
                "--format",
                "json",
            ]
        )
        == 0
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["recommendations"][0]["id"] == "self-improvement-dogfooding"
    assert any("id match: self improvement" in reason for reason in payload["recommendations"][0]["reasons"])


def test_skills_command_keeps_repo_owned_memory_and_general_skill_sources_distinct(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    _write_json(
        target / ".agentic-workspace" / "memory" / "repo" / "skills" / "REGISTRY.json",
        {
            "schema_version": "skill-registry.v1",
            "owner": "repo-local-memory-skills",
            "source_kind": "repo-owned-memory-skills",
            "skills": [
                {
                    "id": "package-context-inspection",
                    "path": "package-context-inspection/SKILL.md",
                    "summary": "inspect package context notes",
                },
                {
                    "id": "memory-reporting",
                    "path": "memory-reporting/SKILL.md",
                    "summary": "report memory freshness and cleanup signals",
                },
            ],
        },
    )
    _write(
        target / ".agentic-workspace" / "memory" / "repo" / "skills" / "README.md",
        "# Memory skills\n",
    )
    _write(
        target / ".agentic-workspace" / "memory" / "repo" / "skills" / "package-context-inspection" / "SKILL.md",
        "# Skill\n",
    )
    _write(
        target / ".agentic-workspace" / "memory" / "repo" / "skills" / "memory-reporting" / "SKILL.md",
        "# Skill\n",
    )
    _write_json(
        target / "tools" / "skills" / "REGISTRY.json",
        {
            "schema_version": "skill-registry.v1",
            "owner": "repo-local-tool-skills",
            "source_kind": "repo-owned-tool-skills",
            "skills": [
                {
                    "id": "foundation-stability-check",
                    "path": "foundation-stability-check/SKILL.md",
                    "summary": "recheck operational authority",
                }
            ],
        },
    )
    _write(target / "tools" / "skills" / "README.md", "# Tool skills\n")
    _write(target / "tools" / "skills" / "foundation-stability-check" / "SKILL.md", "# Skill\n")

    assert cli.main(["skills", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    memory_skill = next(entry for entry in payload["skills"] if entry["id"] == "package-context-inspection")
    memory_reporting_skill = next(entry for entry in payload["skills"] if entry["id"] == "memory-reporting")
    tool_skill = next(entry for entry in payload["skills"] if entry["id"] == "foundation-stability-check")

    assert memory_skill["source_kind"] == "repo-owned-memory-skills"
    assert memory_skill["path"] == ".agentic-workspace/memory/repo/skills/package-context-inspection/SKILL.md"
    assert memory_reporting_skill["source_kind"] == "repo-owned-memory-skills"
    assert memory_reporting_skill["path"] == ".agentic-workspace/memory/repo/skills/memory-reporting/SKILL.md"
    assert tool_skill["source_kind"] == "repo-owned-tool-skills"
    assert tool_skill["path"] == "tools/skills/foundation-stability-check/SKILL.md"
