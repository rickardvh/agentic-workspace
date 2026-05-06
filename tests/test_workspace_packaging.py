"""Validate agentic-workspace artifacts against the checked-in payload inventory."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from zipfile import ZipFile

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_ROOT = WORKSPACE_ROOT / "src" / "agentic_workspace" / "_payload"
PACKAGE_PREFIX = Path("agentic_workspace") / "_payload"


def _source_inventory() -> set[str]:
    return {path.relative_to(PAYLOAD_ROOT).as_posix() for path in PAYLOAD_ROOT.rglob("*") if path.is_file()}


def _build_artifact(tmpdir: str, artifact: str) -> Path:
    subprocess.run(
        ["uv", "build", f"--{artifact}", "-o", tmpdir],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    pattern = "*.whl" if artifact == "wheel" else "*.tar.gz"
    artifacts = list(Path(tmpdir).glob(pattern))
    assert len(artifacts) == 1, f"Expected exactly 1 {artifact}, found {len(artifacts)}"
    return artifacts[0]


def _wheel_inventory(path: Path) -> set[str]:
    with ZipFile(path) as wheel:
        return {
            Path(name).relative_to(PACKAGE_PREFIX).as_posix()
            for name in wheel.namelist()
            if name.startswith(f"{PACKAGE_PREFIX.as_posix()}/") and not name.endswith("/")
        }


def _sdist_inventory(path: Path) -> set[str]:
    with tarfile.open(path, "r:gz") as archive:
        root_dir = archive.getnames()[0].split("/")[0]
        prefix = Path(root_dir) / "src" / PACKAGE_PREFIX
        return {
            Path(name).relative_to(prefix).as_posix()
            for name in archive.getnames()
            if name.startswith(f"{prefix.as_posix()}/") and not name.endswith("/")
        }


def _installed_inventory(wheel_path: Path, tmpdir: str) -> set[str]:
    install_root = Path(tmpdir) / "installed"
    subprocess.run(
        ["uv", "pip", "install", "--no-deps", "--target", str(install_root), str(wheel_path)],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    installed_payload = install_root / PACKAGE_PREFIX
    return {path.relative_to(installed_payload).as_posix() for path in installed_payload.rglob("*") if path.is_file()}


def _raw_wheel_inventory(path: Path) -> set[str]:
    with ZipFile(path) as wheel:
        return {name for name in wheel.namelist() if not name.endswith("/")}


def _raw_sdist_inventory(path: Path) -> set[str]:
    with tarfile.open(path, "r:gz") as archive:
        return {name for name in archive.getnames() if not name.endswith("/")}


def test_workspace_artifacts_match_checked_in_payload_inventory() -> None:
    expected_inventory = _source_inventory()

    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_path = _build_artifact(tmpdir, "wheel")
        sdist_path = _build_artifact(tmpdir, "sdist")

        wheel_inventory = _wheel_inventory(wheel_path)
        sdist_inventory = _sdist_inventory(sdist_path)
        installed_inventory = _installed_inventory(wheel_path, tmpdir)

    assert wheel_inventory == expected_inventory
    assert sdist_inventory == expected_inventory
    assert installed_inventory == expected_inventory


def test_workspace_surface_manifest_payload_entries_exist_in_source_payload() -> None:
    manifest = json.loads((WORKSPACE_ROOT / "src" / "agentic_workspace" / "contracts" / "workspace_surfaces.json").read_text())

    missing = [path for path in manifest["payload_files"] if not (PAYLOAD_ROOT / path).is_file()]

    assert missing == []


def test_workspace_artifacts_ship_generated_cli_package_import_dependency() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_path = _build_artifact(tmpdir, "wheel")
        sdist_path = _build_artifact(tmpdir, "sdist")

        wheel_inventory = _raw_wheel_inventory(wheel_path)
        sdist_inventory = _raw_sdist_inventory(sdist_path)

        assert "agentic_workspace/generated_cli_package/__init__.py" in wheel_inventory
        assert any(name.endswith("/src/agentic_workspace/generated_cli_package/__init__.py") for name in sdist_inventory)


def test_root_wheel_ships_generated_cli_package_import_dependency() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_path = _build_artifact(tmpdir, "wheel")
        inventory = _raw_wheel_inventory(wheel_path)

    assert "agentic_workspace/generated_command_adapters.py" in inventory
    assert "agentic_workspace/generated_cli_package/__init__.py" in inventory


def test_root_sdist_ships_generated_cli_package_import_dependency() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sdist_path = _build_artifact(tmpdir, "sdist")
        inventory = _raw_sdist_inventory(sdist_path)

    assert any(name.endswith("/src/agentic_workspace/generated_command_adapters.py") for name in inventory)
    assert any(name.endswith("/src/agentic_workspace/generated_cli_package/__init__.py") for name in inventory)


def test_installed_workspace_wheel_imports_cli_module() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_path = _build_artifact(tmpdir, "wheel")
        install_root = Path(tmpdir) / "installed"
        subprocess.run(
            ["uv", "pip", "install", "--no-deps", "--target", str(install_root), str(wheel_path)],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import agentic_workspace.cli; from agentic_workspace.generated_cli_package import build_generated_parser",
            ],
            cwd=Path(tmpdir),
            env={**os.environ, "PYTHONPATH": str(install_root)},
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0, result.stderr


def test_installed_workspace_stack_runs_fresh_repo_cli_sequence() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        wheel_path = _build_artifact(tmpdir, "wheel")
        workspace_exe = _install_workspace_stack_venv(wheel_path=wheel_path, tmpdir_path=tmpdir_path)
        target = tmpdir_path / "repo"
        target.mkdir()
        subprocess.run(["git", "init"], cwd=target, capture_output=True, text=True, check=True)

        init_payload = _run_workspace_console_json(
            workspace_exe,
            tmpdir_path,
            "init",
            "--target",
            str(target),
            "--preset",
            "full",
            "--format",
            "json",
        )
        start_payload = _run_workspace_console_json(
            workspace_exe,
            tmpdir_path,
            "start",
            "--target",
            str(target),
            "--profile",
            "tiny",
            "--task",
            "fresh package proof",
            "--format",
            "json",
        )
        summary_payload = _run_workspace_console_json(
            workspace_exe,
            tmpdir_path,
            "summary",
            "--target",
            str(target),
            "--profile",
            "compact",
            "--format",
            "json",
        )
        implement_payload = _run_workspace_console_json(
            workspace_exe,
            tmpdir_path,
            "implement",
            "--target",
            str(target),
            "--profile",
            "tiny",
            "--changed",
            "README.md",
            "--task",
            "fresh package proof",
            "--format",
            "json",
        )
        proof_payload = _run_workspace_console_json(
            workspace_exe,
            tmpdir_path,
            "proof",
            "--target",
            str(target),
            "--profile",
            "tiny",
            "--changed",
            "README.md",
            "--format",
            "json",
        )
        doctor_payload = _run_workspace_console_json(
            workspace_exe,
            tmpdir_path,
            "doctor",
            "--target",
            str(target),
            "--format",
            "json",
        )

    assert init_payload["command"] == "init"
    assert init_payload["preset"] == "full"
    assert start_payload["kind"] == "startup-context/v1"
    assert start_payload["invoked_cli_identity"]["source_class"] == "installed-package"
    assert summary_payload["kind"] == "planning-summary/v1"
    assert summary_payload["profile"] == "compact"
    assert implement_payload["kind"] == "implementer-context-tiny/v1"
    assert proof_payload["kind"] == "proof-next-decision/v1"
    assert doctor_payload["health"] == "healthy"


def _install_workspace_stack_venv(*, wheel_path: Path, tmpdir_path: Path) -> Path:
    venv_path = tmpdir_path / ".venv"
    subprocess.run(
        ["uv", "venv", str(venv_path)],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    python_path = _venv_python(venv_path)
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python_path),
            str(WORKSPACE_ROOT / "packages" / "memory"),
            str(WORKSPACE_ROOT / "packages" / "planning"),
            str(wheel_path),
        ],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return _venv_script(venv_path, "agentic-workspace")


def _run_workspace_console_json(workspace_exe: Path, cwd: Path, *args: str) -> dict[str, object]:
    result = subprocess.run(
        [str(workspace_exe), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _venv_python(venv_path: Path) -> Path:
    if os.name == "nt":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def _venv_script(venv_path: Path, name: str) -> Path:
    if os.name == "nt":
        return venv_path / "Scripts" / f"{name}.exe"
    return venv_path / "bin" / name
