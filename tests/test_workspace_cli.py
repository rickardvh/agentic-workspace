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

    assert (target / "memory" / "index.md").exists()
    assert (target / ".agentic-workspace" / "memory" / "WORKFLOW.md").exists()
    assert (target / "TODO.md").exists()
    assert (target / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()


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


def test_doctor_json_exposes_standardised_summary_fields(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    _init_git_repo(tmp_path)
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["doctor", "--modules", "planning,memory", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "doctor"
    assert payload["created"] == ["planning", "memory"]
    assert payload["updated_managed"] == []
    assert payload["preserved_existing"] == []
    assert payload["needs_review"] == []
    assert payload["generated_artifacts"] == []


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

    assert payload == {"kind": "copied", "path": (tmp_path / "demo.txt").as_posix(), "detail": "ok"}


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
                FakeAction(kind="would update", path=target_root / "tools" / "AGENT_QUICKSTART.md", detail="render quickstart from manifest"),
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
        ),
        "memory": cli.ModuleDescriptor(
            name="memory",
            description=descriptors["memory"].description,
            commands=descriptors["memory"].commands,
            detector=lambda detected_root: (
                (detected_root / "memory" / "index.md").exists() and (detected_root / ".agentic-workspace" / "memory").exists()
            ),
        ),
    }


def _init_git_repo(target: Path) -> None:
    (target / ".git").mkdir(exist_ok=True)
