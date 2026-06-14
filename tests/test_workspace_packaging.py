"""Validate agentic-workspace artifacts against the checked-in payload inventory."""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
from pathlib import Path
from zipfile import ZipFile

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_ROOT = WORKSPACE_ROOT / "src" / "agentic_workspace" / "_payload"
PACKAGE_PREFIX = Path("agentic_workspace") / "_payload"
MODULE_PACKAGE_DIRS = (
    WORKSPACE_ROOT / "packages" / "memory",
    WORKSPACE_ROOT / "packages" / "planning",
    WORKSPACE_ROOT / "packages" / "verification",
)


@contextlib.contextmanager
def _package_build_lock():
    lock_path = WORKSPACE_ROOT / "scratch" / "package-build.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            lock_path.mkdir()
            break
        except FileExistsError:
            time.sleep(0.05)
    try:
        yield
    finally:
        lock_path.rmdir()


def _source_inventory() -> set[str]:
    return {path.relative_to(PAYLOAD_ROOT).as_posix() for path in PAYLOAD_ROOT.rglob("*") if path.is_file()}


def _build_artifact(tmpdir: str, artifact: str) -> Path:
    return _build_artifact_from(WORKSPACE_ROOT, tmpdir, artifact)


def _build_artifact_from(package_root: Path, tmpdir: str, artifact: str) -> Path:
    output_dir = Path(tmpdir)
    pattern = "*.whl" if artifact == "wheel" else "*.tar.gz"
    before = set(output_dir.glob(pattern))
    with _package_build_lock():
        subprocess.run(
            ["uv", "build", f"--{artifact}", "-o", tmpdir, str(package_root)],
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    artifacts = [path for path in output_dir.glob(pattern) if path not in before]
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


def test_workspace_package_declares_semver_identity() -> None:
    pyproject = tomllib.loads((WORKSPACE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert re.fullmatch(r"\d+\.\d+\.\d+", pyproject["project"]["version"])


def test_ci_builds_and_uploads_root_package_artifacts() -> None:
    ci_text = (WORKSPACE_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "workspace-package-artifacts:" in ci_text
    assert "uv build --wheel --sdist --out-dir dist" in ci_text
    assert "uv build --wheel --sdist --out-dir dist packages/memory" in ci_text
    assert "uv build --wheel --sdist --out-dir dist packages/planning" in ci_text
    assert "uv build --wheel --sdist --out-dir dist packages/verification" in ci_text
    assert "test_installed_workspace_stack_runs_fresh_repo_cli_sequence" in ci_text
    assert "actions/upload-artifact@v6.0.0" in ci_text


def test_release_workflow_publishes_tagged_root_package_artifacts() -> None:
    release_text = (WORKSPACE_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert '"v[0-9]+.[0-9]+.[0-9]+"' in release_text
    assert "Release tag {tag!r} must match pyproject.toml version {expected!r}" in release_text
    assert "uv build --wheel --sdist --out-dir dist" in release_text
    assert "uv build --wheel --sdist --out-dir dist packages/memory" in release_text
    assert "uv build --wheel --sdist --out-dir dist packages/planning" in release_text
    assert "uv build --wheel --sdist --out-dir dist packages/verification" in release_text
    assert "softprops/action-gh-release@v2.4.2" in release_text


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

        assert "agentic_workspace/generated_cli_package.py" not in wheel_inventory
        assert "agentic_workspace/generated_cli_package/__init__.py" not in wheel_inventory
        assert "agentic_workspace/_generated_cli_package_impl/__init__.py" in wheel_inventory
        assert "agentic_workspace/_generated_cli_package_impl/command_package.json" in wheel_inventory
        assert "agentic_workspace/_generated_cli_package_impl/adapter_commands.json" in wheel_inventory
        assert any(name.endswith("/generated/workspace/python/__init__.py") for name in sdist_inventory)
        assert any(name.endswith("/generated/workspace/python/command_package.json") for name in sdist_inventory)
        assert any(name.endswith("/generated/workspace/python/adapter_commands.json") for name in sdist_inventory)
        assert not any(name.endswith("/src/agentic_workspace/generated_cli_package.py") for name in sdist_inventory)
        assert not any(name.endswith("/src/agentic_workspace/generated_cli_package/__init__.py") for name in sdist_inventory)


def test_root_wheel_ships_generated_cli_package_import_dependency() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_path = _build_artifact(tmpdir, "wheel")
        inventory = _raw_wheel_inventory(wheel_path)

    assert "agentic_workspace/generated_command_adapters.py" not in inventory
    assert "agentic_workspace/generated_cli_package.py" not in inventory
    assert "agentic_workspace/generated_cli_package/__init__.py" not in inventory
    assert "agentic_workspace/_generated_cli_package_impl/__init__.py" in inventory
    assert "agentic_workspace/_generated_cli_package_impl/command_package.json" in inventory
    assert "agentic_workspace/_generated_cli_package_impl/adapter_commands.json" in inventory


def test_root_sdist_ships_generated_cli_package_import_dependency() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sdist_path = _build_artifact(tmpdir, "sdist")
        inventory = _raw_sdist_inventory(sdist_path)

    assert not any(name.endswith("/src/agentic_workspace/generated_command_adapters.py") for name in inventory)
    assert any(name.endswith("/generated/memory/python/generated_command_adapters.json") for name in inventory)
    assert any(name.endswith("/generated/planning/python/generated_command_adapters.json") for name in inventory)
    assert any(name.endswith("/generated/workspace/python/generated_command_adapters.json") for name in inventory)
    assert not any(name.endswith("/src/agentic_workspace/generated_cli_package.py") for name in inventory)
    assert not any(name.endswith("/src/agentic_workspace/generated_cli_package/__init__.py") for name in inventory)
    assert any(name.endswith("/generated/workspace/python/__init__.py") for name in inventory)
    assert any(name.endswith("/generated/workspace/python/command_package.json") for name in inventory)
    assert any(name.endswith("/generated/workspace/python/adapter_commands.json") for name in inventory)


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
                "from agentic_workspace._generated_cli_package_impl import build_generated_parser",
            ],
            cwd=Path(tmpdir),
            env={**os.environ, "PYTHONPATH": str(install_root)},
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0, result.stderr


def test_workspace_runtime_entrypoint_stays_off_command_generation() -> None:
    pyproject = tomllib.loads((WORKSPACE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "command-generation" not in pyproject["project"]["dependencies"]
    assert pyproject["project"]["scripts"]["agentic-workspace"] == "agentic_workspace.cli:main"


def test_installed_workspace_stack_runs_fresh_repo_cli_sequence() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        wheelhouse = _build_workspace_wheelhouse(tmpdir)
        workspace_exe = _install_workspace_stack_venv(wheelhouse=wheelhouse, tmpdir_path=tmpdir_path)
        assert _venv_site_package_entry_names(tmpdir_path / ".venv", "command_generation") == []
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
            "--task",
            "fresh package proof",
            "--select",
            "invoked_cli_identity,active_state_summary,immediate_next_allowed_action",
            "--format",
            "json",
        )
        summary_payload = _run_workspace_console_json(
            workspace_exe,
            tmpdir_path,
            "summary",
            "--target",
            str(target),
            "--verbose",
            "--format",
            "json",
        )
        implement_payload = _run_workspace_console_json(
            workspace_exe,
            tmpdir_path,
            "implement",
            "--target",
            str(target),
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
    assert start_payload["kind"] == "agentic-workspace/selected-output/v1"
    assert start_payload["values"]["invoked_cli_identity"]["source_class"] == "installed-package"
    assert summary_payload["kind"] == "planning-summary/v1"
    assert summary_payload["profile"] == "full"
    assert implement_payload["kind"] == "implementer-context-tiny/v1"
    assert proof_payload["kind"] == "proof-next-decision/v1"
    assert doctor_payload["health"] == "healthy"


def _build_workspace_wheelhouse(tmpdir: str) -> list[Path]:
    wheel_paths = [_build_artifact(tmpdir, "wheel")]
    wheel_paths.extend(_build_artifact_from(package_dir, tmpdir, "wheel") for package_dir in MODULE_PACKAGE_DIRS)
    names = {path.name for path in wheel_paths}
    assert any(name.startswith("agentic_workspace-") for name in names)
    assert any(name.startswith("agentic_memory-") for name in names)
    assert any(name.startswith("agentic_planning-") for name in names)
    assert any(name.startswith("agentic_verification-") for name in names)
    return wheel_paths


def _install_workspace_stack_venv(*, wheelhouse: list[Path], tmpdir_path: Path) -> Path:
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
            *(str(path) for path in wheelhouse),
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


def _venv_site_package_entry_names(venv_path: Path, prefix: str) -> list[str]:
    if os.name == "nt":
        site_packages = venv_path / "Lib" / "site-packages"
    else:
        candidates = sorted((venv_path / "lib").glob("python*/site-packages"))
        assert candidates, f"site-packages not found under {venv_path}"
        site_packages = candidates[0]
    pattern = f"{prefix}*"
    return sorted(path.name for path in site_packages.glob(pattern) if path.exists())
