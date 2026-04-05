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


def test_status_detects_installed_modules_by_default(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    descriptors = _fake_descriptors(tmp_path, calls)
    (tmp_path / "planning").mkdir()
    (tmp_path / "TODO.md").write_text("# TODO\n", encoding="utf-8")
    (tmp_path / ".agentic-workspace" / "planning").mkdir(parents=True)
    (tmp_path / ".agentic-workspace" / "planning" / "agent-manifest.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_module_operations", lambda: descriptors)

    assert cli.main(["status", "--target", str(tmp_path)]) == 0

    assert calls == [("planning", "status", {"target": str(tmp_path)})]


def test_status_requires_explicit_module_when_nothing_detected(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["status", "--target", str(tmp_path)])

    assert excinfo.value.code == 2


def test_install_uses_full_preset(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["install", "--preset", "full", "--target", str(tmp_path), "--format", "json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert [report["module"] for report in payload["reports"]] == ["memory", "planning"]


def test_status_uses_memory_preset(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(cli, "_module_operations", lambda: _fake_descriptors(tmp_path, calls))

    assert cli.main(["status", "--preset", "memory", "--target", str(tmp_path)]) == 0

    assert calls == [("memory", "status", {"target": str(tmp_path)})]


def test_preset_conflicts_with_explicit_modules(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["status", "--preset", "planning", "--module", "planning", "--target", str(tmp_path)])

    assert excinfo.value.code == 2


def test_install_real_planning_module_creates_payload(tmp_path: Path) -> None:
    target = tmp_path / "repo"

    assert cli.main(["install", "--module", "planning", "--target", str(target)]) == 0

    assert (target / ".agentic-workspace" / "planning" / "agent-manifest.json").exists()
    assert (target / "tools" / "AGENT_QUICKSTART.md").exists()


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
            detector=lambda detected_root, module_name=module_name: (detected_root / module_name).exists(),
        )
        for module_name in ("memory", "planning")
    }