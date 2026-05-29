from __future__ import annotations

import subprocess
from pathlib import Path

from agentic_workspace.repository_scanning import repository_scan_files


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _relatives(root: Path, paths: list[Path]) -> list[str]:
    return [path.relative_to(root).as_posix() for path in paths]


def test_repository_scan_uses_gitignore_and_keeps_managed_workspace_exception(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _write(tmp_path / ".gitignore", "ignored/\n.agentic-workspace/\n")
    _write(tmp_path / "tracked.py", "TRACKED = True\n")
    _write(tmp_path / "untracked.py", "UNTRACKED = True\n")
    _write(tmp_path / "ignored" / "hidden.py", "HIDDEN = True\n")
    _write(tmp_path / ".agentic-workspace" / "local" / "managed.md", "managed\n")
    _write(tmp_path / ".agentic-workspace" / "local" / "scratch" / "transient.py", "TRANSIENT = True\n")
    _git(tmp_path, "add", ".gitignore", "tracked.py")

    paths = _relatives(tmp_path, repository_scan_files(tmp_path, suffixes={".py", ".md"}))
    filtered_paths = _relatives(
        tmp_path,
        repository_scan_files(
            tmp_path,
            exclude_relative_roots=[".agentic-workspace/local/scratch"],
            suffixes={".py", ".md"},
        ),
    )

    assert "tracked.py" in paths
    assert "untracked.py" in paths
    assert "ignored/hidden.py" not in paths
    assert ".agentic-workspace/local/managed.md" in paths
    assert ".agentic-workspace/local/scratch/transient.py" in paths
    assert ".agentic-workspace/local/scratch/transient.py" not in filtered_paths


def test_repository_scan_fallback_prunes_dependency_caches(tmp_path: Path) -> None:
    _write(tmp_path / "src" / "app.py", "APP = True\n")
    _write(tmp_path / ".venv" / "Lib" / "site-packages" / "dependency.py", "DEP = True\n")
    _write(tmp_path / "node_modules" / "dependency" / "index.py", "DEP = True\n")
    _write(tmp_path / ".agentic-workspace" / "config.toml", "schema_version = 1\n")

    paths = _relatives(tmp_path, repository_scan_files(tmp_path, suffixes={".py", ".toml"}))

    assert "src/app.py" in paths
    assert ".venv/Lib/site-packages/dependency.py" not in paths
    assert "node_modules/dependency/index.py" not in paths
    assert ".agentic-workspace/config.toml" in paths
