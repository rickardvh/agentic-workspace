from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from agentic_workspace import cli
from agentic_workspace.result_adapter import adapt_action, adapt_module_result


@dataclass
class FakeAction:
    kind: str
    path: Path
    detail: str


@dataclass
class FakeResult:
    target_root: Path
    message: str
    dry_run: bool
    actions: list[FakeAction] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class SlottedAction:
    kind: str
    path: Path
    detail: str


class DictAction:
    def __init__(self, path: Path) -> None:
        self.path = path

    def to_dict(self, target_root: Path) -> dict[str, object]:
        return {
            "kind": "converted",
            "path": self.path.relative_to(target_root),
            "detail": "used to_dict",
        }


def test_modules_command_lists_available_modules_as_json(monkeypatch, capsys) -> None:
    repo_root = Path("C:/repo")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(repo_root, []))

    assert cli.main(["modules", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert [entry["name"] for entry in payload["modules"]] == ["planning", "memory"]
    planning_module = next(entry for entry in payload["modules"] if entry["name"] == "planning")
    assert planning_module["install_signals"] == ["TODO.md", "docs/execplans", ".agentic-workspace/planning"]
    assert planning_module["workflow_surfaces"] == [
        "AGENTS.md",
        "TODO.md",
        "ROADMAP.md",
        "docs/execplans",
        "docs/contributor-playbook.md",
        "docs/maintainer-commands.md",
        ".agentic-workspace/planning",
        "tools/AGENT_QUICKSTART.md",
        "tools/AGENT_ROUTING.md",
    ]
    assert planning_module["generated_artifacts"] == [
        "tools/agent-manifest.json",
        "tools/AGENT_QUICKSTART.md",
        "tools/AGENT_ROUTING.md",
    ]
    assert planning_module["autodetects_installation"] is True
    assert planning_module["installed"] is None
    assert planning_module["dry_run_commands"] == ["adopt", "install", "uninstall", "upgrade"]
    assert planning_module["force_commands"] == ["install"]
    assert planning_module["command_args"]["install"] == ["target", "dry_run", "force"]
    assert planning_module["command_args"]["doctor"] == ["target"]


def test_modules_command_reports_installation_state_for_target(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "TODO.md").write_text("# TODO\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace" / "planning").mkdir(parents=True)
    (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["modules", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    planning_module = next(entry for entry in payload["modules"] if entry["name"] == "planning")
    memory_module = next(entry for entry in payload["modules"] if entry["name"] == "memory")
    assert planning_module["installed"] is True
    assert memory_module["installed"] is False


def test_init_dispatches_to_full_preset_by_default(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["preset"] == "full"
    assert payload["modules"] == ["planning", "memory"]
    assert payload["mode"] == "install"
    assert calls == [
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
        ("memory", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
    ]


def test_init_uses_explicit_modules_csv(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--modules", "memory", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["modules"] == ["memory"]
    assert calls == [("memory", "install", {"target": str(tmp_path), "dry_run": False, "force": False})]


def test_init_reports_required_prompt_for_high_ambiguity_repo(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    (tmp_path / "TODO.md").write_text("# Existing TODO\n", encoding="utf-8")
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "index.md").write_text("# Memory\n", encoding="utf-8")
    (tmp_path / "docs" / "execplans").mkdir(parents=True)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert sorted(payload["detected_surfaces"]) == ["AGENTS.md", "TODO.md", "docs/execplans", "memory/index.md"]
    assert "handoff_prompt" in payload
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_can_write_prompt_file(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    prompt_path = tmp_path / ".agentic-workspace" / "bootstrap-handoff.md"
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--write-prompt", str(prompt_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["handoff_prompt_path"] == prompt_path.as_posix()
    assert prompt_path.exists()
    assert "Finish the Agentic Workspace bootstrap" in prompt_path.read_text(encoding="utf-8")


def test_prompt_init_uses_dry_run_workspace_bootstrap(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["prompt", "init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "prompt"
    assert payload["prompt_command"] == "init"
    assert payload["dry_run"] is True
    assert "handoff_prompt" in payload
    assert "Finish the Agentic Workspace bootstrap" in payload["handoff_prompt"]
    assert calls == [
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
        ("memory", "install", {"target": str(tmp_path), "dry_run": True, "force": False}),
    ]


def test_prompt_upgrade_builds_workspace_handoff_prompt(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["prompt", "upgrade", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "prompt"
    assert payload["prompt_command"] == "upgrade"
    assert payload["dry_run"] is True
    assert "Use the workspace CLI as the lifecycle entrypoint" in payload["handoff_prompt"]
    assert "README.md: inspect manually" in payload["handoff_prompt"]


def test_init_uses_recommended_prompt_for_single_existing_surface(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "adopt"
    assert payload["prompt_requirement"] == "recommended"
    assert payload["detected_surfaces"] == ["AGENTS.md"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_reports_docs_heavy_repo_as_high_ambiguity(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    (tmp_path / "TODO.md").write_text("# Existing TODO\n", encoding="utf-8")
    (tmp_path / "ROADMAP.md").write_text("# Existing Roadmap\n", encoding="utf-8")
    (tmp_path / "docs" / "contributor-playbook.md").parent.mkdir(parents=True)
    (tmp_path / "docs" / "contributor-playbook.md").write_text("# Contributor Playbook\n", encoding="utf-8")
    (tmp_path / "docs" / "maintainer-commands.md").write_text("# Maintainer Commands\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert sorted(payload["detected_surfaces"]) == [
        "AGENTS.md",
        "ROADMAP.md",
        "TODO.md",
        "docs/contributor-playbook.md",
        "docs/maintainer-commands.md",
    ]
    assert "AGENTS.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert "docs/contributor-playbook.md: reconcile existing workflow surface ownership" in payload["needs_review"]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_marks_partial_module_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "index.md").write_text("# Memory\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        "memory/index.md: partial module state detected",
        "memory/index.md: reconcile existing workflow surface ownership",
    ]


def test_init_marks_partial_planning_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "TODO.md").write_text("# Existing TODO\n", encoding="utf-8")
    (tmp_path / "docs" / "execplans").mkdir(parents=True)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--modules", "planning", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        "TODO.md: partial module state detected",
        "docs/execplans: partial module state detected",
        "TODO.md: reconcile existing workflow surface ownership",
        "docs/execplans: reconcile existing workflow surface ownership",
    ]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_init_marks_mixed_module_partial_state_for_review(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / "TODO.md").write_text("# Existing TODO\n", encoding="utf-8")
    (tmp_path / "docs" / "execplans").mkdir(parents=True)
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "index.md").write_text("# Existing memory index\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_install_signals(tmp_path, calls))

    assert cli.main(["init", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "adopt_high_ambiguity"
    assert payload["prompt_requirement"] == "required"
    assert payload["needs_review"] == [
        "TODO.md: partial module state detected",
        "docs/execplans: partial module state detected",
        "memory/index.md: partial module state detected",
        "TODO.md: reconcile existing workflow surface ownership",
        "docs/execplans: reconcile existing workflow surface ownership",
        "memory/index.md: reconcile existing workflow surface ownership",
    ]
    assert calls == [
        ("planning", "adopt", {"target": str(tmp_path), "dry_run": False}),
        ("memory", "adopt", {"target": str(tmp_path), "dry_run": False}),
    ]


def test_status_detects_installed_modules_by_default(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    descriptors = _fake_descriptors(tmp_path, calls)
    (tmp_path / "planning").mkdir()
    (tmp_path / "TODO.md").write_text("# TODO\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace" / "planning").mkdir(parents=True)
    (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: descriptors)

    assert cli.main(["status", "--target", str(tmp_path)]) == 0

    assert calls == [("planning", "status", {"target": str(tmp_path)})]


def test_init_requires_git_repo(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["init", "--target", str(tmp_path)])

    assert excinfo.value.code == 2


def test_preset_conflicts_with_modules(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["init", "--preset", "planning", "--modules", "planning", "--target", str(tmp_path)])

    assert excinfo.value.code == 2


def test_install_real_init_creates_combined_memory_and_planning_surfaces(tmp_path: Path) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0

    assert (target / ".agentic-workspace" / "WORKFLOW.md").exists()
    assert (target / ".agentic-workspace" / "OWNERSHIP.toml").exists()
    assert (target / "memory" / "index.md").exists()
    assert (target / ".agentic-workspace" / "memory" / "WORKFLOW.md").exists()
    assert (target / "TODO.md").exists()
    assert (target / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    agents_text = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "<!-- agentic-workspace:workflow:start -->" in agents_text
    assert "Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules." in agents_text
    assert "Read `.agentic-workspace/memory/WORKFLOW.md` only when changing memory behavior or the memory workflow itself." in agents_text
    assert "<!-- agentic-memory:workflow:start -->" not in agents_text
    assert "<PROJECT_NAME>" not in agents_text


def test_status_real_init_reports_workspace_shared_layer_surfaces(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    workspace_report = next(report for report in payload["reports"] if report["module"] == "workspace")
    assert any(
        action["path"] == ".agentic-workspace/WORKFLOW.md" and action["kind"] == "current"
        for action in workspace_report["actions"]
    )
    assert any(
        action["path"] == ".agentic-workspace/OWNERSHIP.toml" and action["kind"] == "current"
        for action in workspace_report["actions"]
    )


def test_status_real_init_reports_workspace_health(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "status"
    assert payload["modules"] == ["planning", "memory"]
    assert "health" in payload
    assert payload["registry"][0]["name"] == "planning"
    assert payload["registry"][1]["installed"] is True
    assert not any(".agentic-workspace/WORKFLOW.md" in warning for warning in payload["warnings"])
    assert not any(".agentic-workspace/OWNERSHIP.toml" in warning for warning in payload["warnings"])


def test_status_flags_missing_workspace_shared_layer(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    (target / ".agentic-workspace" / "WORKFLOW.md").unlink()
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(".agentic-workspace/WORKFLOW.md" in warning for warning in payload["warnings"])


def test_doctor_flags_missing_workspace_shared_layer(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    (target / ".agentic-workspace" / "OWNERSHIP.toml").unlink()
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(".agentic-workspace/OWNERSHIP.toml" in warning for warning in payload["warnings"])


def test_doctor_json_exposes_standardised_summary_fields(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    (tmp_path / ".agentic-workspace").mkdir(parents=True)
    (tmp_path / ".agentic-workspace" / "WORKFLOW.md").write_text("# Workflow\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace" / "OWNERSHIP.toml").write_text("schema_version = 1\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text(
        "# Agent Instructions\n\n"
        "<!-- agentic-workspace:workflow:start -->\n"
        "Read `.agentic-workspace/WORKFLOW.md` for shared workflow rules.\n"
        "<!-- agentic-workspace:workflow:end -->\n\n"
        "Local repo instructions.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["doctor", "--modules", "planning,memory", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "doctor"
    assert payload["created"] == ["planning", "memory"]
    assert payload["updated_managed"] == []
    assert payload["preserved_existing"] == []
    assert payload["needs_review"] == []
    assert payload["generated_artifacts"] == []
    assert payload["registry"][0]["name"] == "planning"


def test_status_warns_when_redundant_memory_pointer_block_remains(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)
    assert cli.main(["init", "--target", str(target)]) == 0
    agents_path = target / "AGENTS.md"
    agents_path.write_text(
        agents_path.read_text(encoding="utf-8").replace(
            "<!-- agentic-workspace:workflow:end -->\n",
            "<!-- agentic-workspace:workflow:end -->\n\n"
            "<!-- agentic-memory:workflow:start -->\n"
            "Read `.agentic-workspace/memory/WORKFLOW.md` for shared workflow rules.\n"
            "<!-- agentic-memory:workflow:end -->\n",
        ),
        encoding="utf-8",
    )
    capsys.readouterr()

    assert cli.main(["status", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any("redundant top-level memory workflow pointer block still present" in warning for warning in payload["warnings"])


def test_doctor_real_init_preserves_package_contract_shortlists_in_reports(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    planning_report = next(report for report in payload["reports"] if report["module"] == "planning")
    memory_report = next(report for report in payload["reports"] if report["module"] == "memory")

    assert any(
        action["path"] == ".agentic-workspace/planning/agent-manifest.json"
        and "compatibility contract files:" in action["detail"]
        and "AGENTS.md" in action["detail"]
        for action in planning_report["actions"]
    )
    assert any(
        action["path"] == ".agentic-workspace/memory/UPGRADE-SOURCE.toml"
        and "lower-stability helper files:" in action["detail"]
        and "scripts/check/check_memory_freshness.py" in action["detail"]
        for action in memory_report["actions"]
    )


def test_doctor_text_output_shows_package_contract_shortlists(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target)]) == 0

    output = capsys.readouterr().out
    assert "[planning] Doctor report" in output
    assert "[memory] Doctor report" in output
    assert "compatibility contract files:" in output
    assert "lower-stability helper files:" in output


def test_doctor_real_init_reports_stale_planning_generated_residue(tmp_path: Path, capsys) -> None:
    target = tmp_path / "repo"
    target.mkdir()
    _init_git_repo(target)

    assert cli.main(["init", "--target", str(target)]) == 0
    (target / "tools" / "AGENT_ROUTING.md").write_text("stale generated routing\n", encoding="utf-8")
    capsys.readouterr()

    assert cli.main(["doctor", "--target", str(target), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["health"] == "attention-needed"
    assert any(
        item == "tools/AGENT_ROUTING.md: routing guide is out of sync with .agentic-workspace/planning/agent-manifest.json; run python scripts/render_agent_docs.py"
        for item in payload["needs_review"]
    )


def test_upgrade_json_collects_summary_categories(monkeypatch, tmp_path: Path, capsys) -> None:
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _descriptors_with_mixed_actions(tmp_path))

    assert cli.main(["upgrade", "--modules", "planning", "--target", str(tmp_path), "--dry-run", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "upgrade"
    assert payload["updated_managed"] == ["tools/AGENT_QUICKSTART.md"]
    assert payload["preserved_existing"] == ["AGENTS.md"]
    assert payload["generated_artifacts"] == ["tools/AGENT_QUICKSTART.md"]
    assert payload["needs_review"] == ["README.md: inspect manually"]
    assert payload["warnings"] == []
    assert payload["stale_generated_surfaces"] == ["tools/AGENT_QUICKSTART.md"]


def test_adapt_action_supports_slotted_dataclass(tmp_path: Path) -> None:
    action = SlottedAction(kind="copied", path=tmp_path / "demo.txt", detail="ok")

    payload = adapt_action(action=action, target_root=tmp_path)

    assert payload == {"kind": "copied", "path": "demo.txt", "detail": "ok"}


def test_adapt_action_prefers_to_dict_protocol(tmp_path: Path) -> None:
    action = DictAction(tmp_path / "nested" / "demo.txt")

    payload = adapt_action(action=action, target_root=tmp_path)

    assert payload == {"kind": "converted", "path": "nested/demo.txt", "detail": "used to_dict"}


def test_adapt_module_result_handles_optional_warnings(tmp_path: Path) -> None:
    result = FakeResult(
        target_root=tmp_path,
        message="status memory",
        dry_run=False,
        actions=[FakeAction(kind="recorded", path=tmp_path / "memory", detail="ran status")],
    )
    delattr(result, "warnings")

    report = adapt_module_result(module="memory", result=result)

    assert report.to_dict()["warnings"] == []


def test_invoke_module_command_uses_descriptor_command_args(tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _doctor_handler(**kwargs):
        captured.update(kwargs)
        return FakeResult(
            target_root=tmp_path,
            message="doctor planning",
            dry_run=False,
            actions=[],
            warnings=[],
        )

    descriptor = cli.ModuleDescriptor(
        name="planning",
        description="planning module",
        commands={"doctor": _doctor_handler},
        detector=lambda detected_root: True,
        install_signals=(Path("TODO.md"),),
        workflow_surfaces=(Path("TODO.md"),),
        generated_artifacts=(),
        command_args={"doctor": ("target",)},
    )

    report = cli._invoke_module_command(
        command_name="doctor",
        module_name="planning",
        descriptor=descriptor,
        target_root=tmp_path,
        dry_run=True,
        force=True,
    )

    assert captured == {"target": str(tmp_path)}
    assert report["module"] == "planning"


def _fake_descriptors(target_root: Path, calls: list[tuple[str, str, dict[str, object]]]) -> dict[str, cli.ModuleDescriptor]:
    def _build_handler(module_name: str, command_name: str):
        def _handler(**kwargs):
            calls.append((module_name, command_name, kwargs))
            return FakeResult(
                target_root=target_root,
                message=f"{command_name} {module_name}",
                dry_run=bool(kwargs.get("dry_run", False)),
                actions=[FakeAction(kind="created", path=target_root / module_name, detail=f"ran {command_name}")],
                warnings=[],
            )

        return _handler

    commands = ("install", "adopt", "upgrade", "uninstall", "doctor", "status")
    return {
        module_name: cli.ModuleDescriptor(
            name=module_name,
            description=f"{module_name} module",
            commands={command_name: _build_handler(module_name, command_name) for command_name in commands},
            detector=lambda detected_root, module_name=module_name: (detected_root / module_name).exists(),
            install_signals=cli.MODULE_SIGNAL_PATHS.get(module_name, (Path(module_name),)),
            workflow_surfaces=(
                (
                    Path("AGENTS.md"),
                    Path("TODO.md"),
                    Path("ROADMAP.md"),
                    Path("docs/execplans"),
                    Path("docs/contributor-playbook.md"),
                    Path("docs/maintainer-commands.md"),
                    Path(".agentic-workspace/planning"),
                    Path("tools/AGENT_QUICKSTART.md"),
                    Path("tools/AGENT_ROUTING.md"),
                )
                if module_name == "planning"
                else (
                    Path("AGENTS.md"),
                    Path("memory/index.md"),
                    Path("memory/current"),
                    Path(".agentic-workspace/memory"),
                )
            ),
            generated_artifacts=(
                (Path("tools/agent-manifest.json"), Path("tools/AGENT_QUICKSTART.md"), Path("tools/AGENT_ROUTING.md"))
                if module_name == "planning"
                else ()
            ),
            command_args={
                "install": ("target", "dry_run", "force"),
                "adopt": ("target", "dry_run"),
                "upgrade": ("target", "dry_run"),
                "uninstall": ("target", "dry_run"),
                "doctor": ("target",),
                "status": ("target",),
            },
        )
        for module_name in ("planning", "memory")
    }


def _descriptors_with_mixed_actions(target_root: Path) -> dict[str, cli.ModuleDescriptor]:
    def _upgrade_handler(**kwargs):
        return FakeResult(
            target_root=target_root,
            message="upgrade planning",
            dry_run=bool(kwargs.get("dry_run", False)),
            actions=[
                FakeAction(
                    kind="would update",
                    path=target_root / "tools" / "AGENT_QUICKSTART.md",
                    detail="render quickstart from manifest",
                ),
                FakeAction(kind="skipped", path=target_root / "AGENTS.md", detail="repo-owned surface left unchanged"),
                FakeAction(kind="manual review", path=target_root / "README.md", detail="inspect manually"),
            ],
            warnings=[],
        )

    return {
        "planning": cli.ModuleDescriptor(
            name="planning",
            description="planning module",
            commands={
                "install": _upgrade_handler,
                "adopt": _upgrade_handler,
                "upgrade": _upgrade_handler,
                "uninstall": _upgrade_handler,
                "doctor": _upgrade_handler,
                "status": _upgrade_handler,
            },
            detector=lambda detected_root: True,
            install_signals=cli.MODULE_SIGNAL_PATHS["planning"],
            workflow_surfaces=(Path("AGENTS.md"), Path("tools/AGENT_QUICKSTART.md")),
            generated_artifacts=(Path("tools/AGENT_QUICKSTART.md"),),
            command_args={
                "install": ("target", "dry_run", "force"),
                "adopt": ("target", "dry_run"),
                "upgrade": ("target", "dry_run"),
                "uninstall": ("target", "dry_run"),
                "doctor": ("target",),
                "status": ("target",),
            },
        )
    }


def _descriptors_with_install_signals(
    target_root: Path, calls: list[tuple[str, str, dict[str, object]]]
) -> dict[str, cli.ModuleDescriptor]:
    descriptors = _fake_descriptors(target_root, calls)
    return {
        "planning": cli.ModuleDescriptor(
            name="planning",
            description=descriptors["planning"].description,
            commands=descriptors["planning"].commands,
            detector=lambda detected_root: (
                (detected_root / "TODO.md").exists()
                and (detected_root / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
            ),
            install_signals=cli.MODULE_SIGNAL_PATHS["planning"],
            workflow_surfaces=descriptors["planning"].workflow_surfaces,
            generated_artifacts=descriptors["planning"].generated_artifacts,
            command_args=descriptors["planning"].command_args,
        ),
        "memory": cli.ModuleDescriptor(
            name="memory",
            description=descriptors["memory"].description,
            commands=descriptors["memory"].commands,
            detector=lambda detected_root: (
                (detected_root / "memory" / "index.md").exists() and (detected_root / ".agentic-workspace" / "memory").exists()
            ),
            install_signals=cli.MODULE_SIGNAL_PATHS["memory"],
            workflow_surfaces=descriptors["memory"].workflow_surfaces,
            generated_artifacts=descriptors["memory"].generated_artifacts,
            command_args=descriptors["memory"].command_args,
        ),
    }


def _init_git_repo(target: Path) -> None:
    (target / ".git").mkdir(exist_ok=True)
