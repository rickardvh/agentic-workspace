from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from agentic_workspace import cli


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


def test_modules_command_lists_available_modules_as_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(Path("C:/repo"), []))

    assert cli.main(["modules", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert [entry["name"] for entry in payload["modules"]] == ["memory", "planning"]


def test_install_dispatches_to_all_modules_by_default(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["install", "--target", str(tmp_path), "--dry-run", "--force", "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert [report["module"] for report in payload["reports"]] == ["memory", "planning"]
    assert calls == [
        ("memory", "install", {"target": str(tmp_path), "dry_run": True, "force": True}),
        ("planning", "install", {"target": str(tmp_path), "dry_run": True, "force": True}),
    ]


def test_status_dispatches_only_selected_modules(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["status", "--module", "planning", "--module", "planning", "--target", str(tmp_path)]) == 0

    assert calls == [("planning", "status", {"target": str(tmp_path)})]


def test_install_real_planning_module_creates_payload(tmp_path: Path) -> None:
    target = tmp_path / "repo"

    assert cli.main(["install", "--module", "planning", "--target", str(target)]) == 0

    assert (target / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert (target / "tools" / "AGENT_QUICKSTART.md").exists()


def _fake_descriptors(target_root: Path, calls: list[tuple[str, str, dict[str, object]]]) -> dict[str, cli.ModuleDescriptor]:
    def _build_handler(module_name: str, command_name: str):
        def _handler(**kwargs):
            calls.append((module_name, command_name, kwargs))
            return FakeResult(
                target_root=target_root,
                message=f"{command_name} {module_name}",
                dry_run=bool(kwargs.get("dry_run", False)),
                actions=[FakeAction(kind="recorded", path=target_root / module_name, detail=f"ran {command_name}")],
                warnings=[],
            )

        return _handler

    commands = ("install", "adopt", "upgrade", "uninstall", "doctor", "status")
    return {
        module_name: cli.ModuleDescriptor(
            name=module_name,
            description=f"{module_name} module",
            commands={command_name: _build_handler(module_name, command_name) for command_name in commands},
        )
        for module_name in ("memory", "planning")
    }