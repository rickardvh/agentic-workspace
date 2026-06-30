"""Subprocess lifecycle smoke tests for installed command entrypoints."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _git_init(target: Path) -> None:
    subprocess.run(["git", "init"], cwd=target, capture_output=True, text=True, check=True)


def test_workspace_lifecycle_smoke() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "repo"
        target.mkdir()
        _git_init(target)

        dry_run = _run(
            "agentic-workspace",
            "init",
            "--target",
            str(target),
            "--modules",
            "planning,memory",
            "--non-interactive",
            "--dry-run",
            "--format",
            "json",
            cwd=WORKSPACE_ROOT,
        )
        assert json.loads(dry_run.stdout)["dry_run"] is True
        assert not (target / ".agentic-workspace/planning/state.toml").exists()

        init = _run(
            "agentic-workspace",
            "init",
            "--target",
            str(target),
            "--modules",
            "planning,memory",
            "--non-interactive",
            "--format",
            "json",
            cwd=WORKSPACE_ROOT,
        )
        assert json.loads(init.stdout)["command"] == "init"
        assert (target / ".agentic-workspace/planning/state.toml").exists()
        assert (target / ".agentic-workspace/memory/repo/index.md").exists()

        status = _run(
            "agentic-workspace",
            "status",
            "--target",
            str(target),
            "--modules",
            "planning,memory",
            "--non-interactive",
            "--format",
            "json",
            cwd=WORKSPACE_ROOT,
        )
        assert json.loads(status.stdout)["health"] == "healthy"

        upgrade_dry_run = _run(
            "agentic-workspace",
            "upgrade",
            "--target",
            str(target),
            "--modules",
            "planning,memory",
            "--non-interactive",
            "--dry-run",
            "--format",
            "json",
            cwd=WORKSPACE_ROOT,
        )
        assert json.loads(upgrade_dry_run.stdout)["dry_run"] is True
        assert (target / ".agentic-workspace/planning/state.toml").exists()
        assert (target / ".agentic-workspace/memory/repo/index.md").exists()

        uninstall_dry_run = _run(
            "agentic-workspace",
            "uninstall",
            "--target",
            str(target),
            "--modules",
            "planning,memory",
            "--non-interactive",
            "--dry-run",
            "--format",
            "json",
            cwd=WORKSPACE_ROOT,
        )
        assert json.loads(uninstall_dry_run.stdout)["dry_run"] is True
        assert (target / ".agentic-workspace/planning/state.toml").exists()
        assert (target / ".agentic-workspace/memory/repo/index.md").exists()

    modules = _run("agentic-workspace", "modules", "--verbose", "--format", "json", cwd=WORKSPACE_ROOT)
    module_payload = json.loads(modules.stdout)
    assert {entry["name"] for entry in module_payload["modules"]} >= {"planning", "memory"}


def test_planning_lifecycle_smoke() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "repo"
        target.mkdir()

        dry_run = _run("agentic-planning", "install", "--target", str(target), "--dry-run", "--format", "json", cwd=WORKSPACE_ROOT)
        assert json.loads(dry_run.stdout)["dry_run"] is True
        assert not (target / ".agentic-workspace/planning/state.toml").exists()

        _run("agentic-planning", "install", "--target", str(target), "--format", "json", cwd=WORKSPACE_ROOT)
        state_path = target / ".agentic-workspace/planning/state.toml"
        original = state_path.read_text(encoding="utf-8")
        assert state_path.exists()
        assert (target / "AGENTS.md").exists()
        assert not (target / ".agentic-workspace/planning/TODO.md").exists()

        status = _run("agentic-planning", "status", "--target", str(target), "--format", "json", cwd=WORKSPACE_ROOT)
        assert json.loads(status.stdout)["target_root"]

        upgrade_dry_run = _run(
            "agentic-planning",
            "upgrade",
            "--target",
            str(target),
            "--dry-run",
            "--format",
            "json",
            cwd=WORKSPACE_ROOT,
        )
        assert json.loads(upgrade_dry_run.stdout)["dry_run"] is True
        assert state_path.exists()

        uninstall_dry_run = _run(
            "agentic-planning",
            "uninstall",
            "--target",
            str(target),
            "--dry-run",
            "--format",
            "json",
            cwd=WORKSPACE_ROOT,
        )
        assert json.loads(uninstall_dry_run.stdout)["dry_run"] is True
        assert state_path.exists()

        second = _run("agentic-planning", "install", "--target", str(target), cwd=WORKSPACE_ROOT, check=False)
        if second.returncode == 0:
            assert state_path.read_text(encoding="utf-8") == original

        state_path.write_text("# Modified\n", encoding="utf-8")
        _run("agentic-planning", "install", "--target", str(target), "--force", cwd=WORKSPACE_ROOT)
        assert state_path.read_text(encoding="utf-8") == original


def test_memory_lifecycle_smoke() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "repo"
        target.mkdir()

        dry_run = _run("agentic-memory", "install", "--target", str(target), "--dry-run", "--format", "json", cwd=WORKSPACE_ROOT)
        assert json.loads(dry_run.stdout)["dry_run"] is True
        assert not (target / ".agentic-workspace/memory/repo").exists()

        _run("agentic-memory", "install", "--target", str(target), "--format", "json", cwd=WORKSPACE_ROOT)
        index_path = target / ".agentic-workspace/memory/repo/index.md"
        original = index_path.read_text(encoding="utf-8")
        assert index_path.exists()
        assert (target / ".agentic-workspace/memory/repo/manifest.toml").exists()
        assert (target / "AGENTS.md").exists()

        status = _run("agentic-memory", "status", "--target", str(target), "--format", "json", cwd=WORKSPACE_ROOT)
        assert json.loads(status.stdout)["target_root"]

        upgrade_dry_run = _run(
            "agentic-memory",
            "upgrade",
            "--target",
            str(target),
            "--dry-run",
            "--format",
            "json",
            cwd=WORKSPACE_ROOT,
        )
        assert json.loads(upgrade_dry_run.stdout)["dry_run"] is True
        assert index_path.exists()

        uninstall_dry_run = _run(
            "agentic-memory",
            "uninstall",
            "--target",
            str(target),
            "--dry-run",
            "--format",
            "json",
            cwd=WORKSPACE_ROOT,
        )
        assert json.loads(uninstall_dry_run.stdout)["dry_run"] is True
        assert index_path.exists()

        second = _run("agentic-memory", "install", "--target", str(target), cwd=WORKSPACE_ROOT, check=False)
        if second.returncode == 0:
            assert index_path.read_text(encoding="utf-8") == original

        index_path.write_text("# Modified\n", encoding="utf-8")
        _run("agentic-memory", "install", "--target", str(target), "--force", cwd=WORKSPACE_ROOT)
        assert index_path.read_text(encoding="utf-8") == original
