"""Test that agentic-memory package artifacts contain required payload files."""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from zipfile import ZipFile

from repo_memory_bootstrap._installer_shared import (
    CURRENT_MEMORY_BASELINE,
    OPTIONAL_CURRENT_MEMORY_FILES,
    PAYLOAD_REQUIRED_FILES,
)

MEMORY_PACKAGE_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_CORE_MANAGED_PATHS = {
    "bootstrap/AGENTS.template.md",
    "bootstrap/README.md",
    "bootstrap/.agentic-workspace/memory/repo/index.md",
    "bootstrap/.agentic-workspace/memory/repo/manifest.toml",
    "bootstrap/.agentic-workspace/memory/repo/templates/memory-note.template.md",
    "bootstrap/.agentic-workspace/memory/repo/templates/invariant.template.md",
    "bootstrap/.agentic-workspace/memory/repo/templates/runbook.template.md",
    "skills/README.md",
    "skills/bootstrap-adoption/SKILL.md",
    "skills/bootstrap-upgrade/SKILL.md",
    "skills/bootstrap-uninstall/SKILL.md",
}
EXECUTABLE_PAYLOAD_SUFFIXES = {
    ".bat",
    ".bash",
    ".cmd",
    ".cjs",
    ".class",
    ".cs",
    ".dll",
    ".dylib",
    ".exe",
    ".fs",
    ".go",
    ".jar",
    ".java",
    ".js",
    ".jsx",
    ".lua",
    ".mjs",
    ".php",
    ".pl",
    ".ps1",
    ".psm1",
    ".py",
    ".pyc",
    ".pyo",
    ".pyw",
    ".rb",
    ".rs",
    ".sh",
    ".so",
    ".ts",
    ".tsx",
    ".vb",
    ".zsh",
}


def test_memory_wheel_contains_required_payload_files_and_skills() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_path = _build_artifact("wheel", Path(tmpdir))
        inventory = _artifact_inventory(wheel_path)

        assert EXPECTED_CORE_MANAGED_PATHS <= inventory, _missing_paths(inventory, EXPECTED_CORE_MANAGED_PATHS)
        assert "bootstrap/.agentic-workspace/memory/repo/current/routing-feedback.md" not in inventory


def test_memory_sdist_contains_required_payload_files_and_skills() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sdist_path = _build_artifact("sdist", Path(tmpdir))
        inventory = _artifact_inventory(sdist_path)

        assert EXPECTED_CORE_MANAGED_PATHS <= inventory, _missing_paths(inventory, EXPECTED_CORE_MANAGED_PATHS)
        assert "bootstrap/.agentic-workspace/memory/repo/current/routing-feedback.md" not in inventory


def test_memory_wheel_and_sdist_share_the_same_managed_inventory() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        wheel_path = _build_artifact("wheel", tmpdir_path)
        sdist_path = _build_artifact("sdist", tmpdir_path)

        assert _artifact_inventory(wheel_path) == _artifact_inventory(sdist_path)


def test_current_memory_has_no_required_shipped_baseline() -> None:
    assert CURRENT_MEMORY_BASELINE == ()
    assert Path(".agentic-workspace/memory/repo/current/routing-feedback.md") in OPTIONAL_CURRENT_MEMORY_FILES
    assert all(not path.as_posix().startswith(".agentic-workspace/memory/repo/current/") for path in PAYLOAD_REQUIRED_FILES)


def test_memory_bootstrap_repo_payload_excludes_repo_specific_content() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_path = _build_artifact("wheel", Path(tmpdir))
        inventory = _artifact_inventory(wheel_path)

    repo_payload = sorted(
        path.removeprefix("bootstrap/.agentic-workspace/memory/repo/")
        for path in inventory
        if path.startswith("bootstrap/.agentic-workspace/memory/repo/")
    )
    disallowed = [
        path
        for path in repo_payload
        if not (path == "index.md" or path == "manifest.toml" or path.endswith("/README.md") or path.endswith(".template.md"))
    ]

    assert disallowed == []
    assert "runbooks/dogfooding-usage-ledger.md" not in repo_payload
    assert not any(path.startswith("skills/") for path in repo_payload)


def test_memory_artifacts_do_not_ship_root_level_bootstrap_helpers() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        wheel_path = _build_artifact("wheel", tmpdir_path)
        sdist_path = _build_artifact("sdist", tmpdir_path)

        for inventory in (_artifact_inventory(wheel_path), _artifact_inventory(sdist_path)):
            assert not any(path.startswith("bootstrap/scripts/") for path in inventory)
            assert not any(path.startswith("bootstrap/optional/") for path in inventory)


def test_memory_artifacts_do_not_ship_executable_bootstrap_payload() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        wheel_path = _build_artifact("wheel", tmpdir_path)
        sdist_path = _build_artifact("sdist", tmpdir_path)

        for inventory in (_artifact_inventory(wheel_path), _artifact_inventory(sdist_path)):
            executable_entries = sorted(path for path in inventory if Path(path).suffix.lower() in EXECUTABLE_PAYLOAD_SUFFIXES)
            assert executable_entries == []


def test_memory_wheel_ships_generated_cli_package_import_dependency() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_path = _build_artifact("wheel", Path(tmpdir))
        inventory = _raw_artifact_inventory(wheel_path)

    assert "repo_memory_bootstrap/generated_command_adapters.py" in inventory
    assert "repo_memory_bootstrap/generated_cli_package/__init__.py" in inventory
    assert "repo_memory_bootstrap/_generated_cli_package_impl/__init__.py" in inventory
    assert "repo_memory_bootstrap/_generated_cli_package_impl/command_package.json" in inventory
    assert "repo_memory_bootstrap/_generated_cli_package_impl/adapter_commands.json" in inventory


def test_memory_sdist_ships_generated_cli_package_import_dependency() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sdist_path = _build_artifact("sdist", Path(tmpdir))
        inventory = _raw_artifact_inventory(sdist_path)

    assert "src/repo_memory_bootstrap/generated_command_adapters.py" in inventory
    assert "src/repo_memory_bootstrap/generated_cli_package/__init__.py" in inventory
    assert "src/repo_memory_bootstrap/_generated_cli_package_impl/__init__.py" in inventory
    assert "src/repo_memory_bootstrap/_generated_cli_package_impl/command_package.json" in inventory
    assert "src/repo_memory_bootstrap/_generated_cli_package_impl/adapter_commands.json" in inventory


def test_installed_memory_wheel_imports_cli_module() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        wheel_path = _build_artifact("wheel", tmpdir_path)
        install_root = tmpdir_path / "installed"
        subprocess.run(
            ["uv", "pip", "install", "--no-deps", "--target", str(install_root), str(wheel_path)],
            cwd=MEMORY_PACKAGE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import repo_memory_bootstrap._runtime_cli; from repo_memory_bootstrap.generated_cli_package import build_generated_parser",
            ],
            cwd=tmpdir_path,
            env={**os.environ, "PYTHONPATH": str(install_root)},
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0, result.stderr


def _build_artifact(kind: str, output_dir: Path) -> Path:
    subprocess.run(
        ["uv", "build", f"--{kind}", "-o", str(output_dir)],
        cwd=MEMORY_PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    pattern = "agentic_memory-*.whl" if kind == "wheel" else "agentic_memory-*.tar.gz"
    matches = list(output_dir.glob(pattern))
    assert len(matches) == 1, f"Expected exactly 1 {kind}, found {len(matches)}"
    return matches[0]


def _artifact_inventory(artifact_path: Path) -> set[str]:
    if artifact_path.suffix == ".whl":
        return _wheel_inventory(artifact_path)
    return _sdist_inventory(artifact_path)


def _wheel_inventory(wheel_path: Path) -> set[str]:
    entries: set[str] = set()
    with ZipFile(wheel_path) as whl:
        for name in whl.namelist():
            if name.endswith("/"):
                continue
            if name.startswith("repo_memory_bootstrap/_payload/"):
                entries.add("bootstrap/" + name.removeprefix("repo_memory_bootstrap/_payload/"))
            elif name.startswith("repo_memory_bootstrap/_skills/"):
                entries.add("skills/" + name.removeprefix("repo_memory_bootstrap/_skills/"))
    return entries


def _sdist_inventory(sdist_path: Path) -> set[str]:
    with tarfile.open(sdist_path, "r:gz") as tar:
        members = [member for member in tar.getmembers() if member.isfile()]
        root_dirs = {Path(member.name).parts[0] for member in members if member.name}
        assert len(root_dirs) == 1, f"Expected exactly 1 root directory in sdist, found {root_dirs}"
        root_dir = next(iter(root_dirs))

        entries: set[str] = set()
        prefix = f"{root_dir}/"
        for member in members:
            if not member.name.startswith(prefix):
                continue
            relative = member.name.removeprefix(prefix)
            if relative.startswith("bootstrap/") or relative.startswith("skills/"):
                entries.add(relative)
        return entries


def _missing_paths(inventory: set[str], required: set[str]) -> str:
    missing = sorted(required - inventory)
    return f"Missing artifact paths: {missing}"


def _raw_artifact_inventory(artifact_path: Path) -> set[str]:
    if artifact_path.suffix == ".whl":
        with ZipFile(artifact_path) as whl:
            return {name for name in whl.namelist() if not name.endswith("/")}
    with tarfile.open(artifact_path, "r:gz") as tar:
        members = [member for member in tar.getmembers() if member.isfile()]
    root_dirs = {Path(member.name).parts[0] for member in members if member.name}
    assert len(root_dirs) == 1, f"Expected exactly 1 root directory in sdist, found {root_dirs}"
    root_dir = next(iter(root_dirs))
    prefix = f"{root_dir}/"
    return {member.name.removeprefix(prefix) for member in members if member.name.startswith(prefix)}
