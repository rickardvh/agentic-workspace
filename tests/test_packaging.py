"""Test root package shipped artifact boundaries."""

from __future__ import annotations

import subprocess
import tarfile
import tempfile
from pathlib import Path
from zipfile import ZipFile

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


def test_root_wheel_ships_generated_cli_package_import_dependency() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_path = _build_artifact("wheel", Path(tmpdir))
        inventory = _artifact_inventory(wheel_path)

    assert "agentic_workspace/generated_command_adapters.py" in inventory
    assert "agentic_workspace/generated_cli_package/__init__.py" in inventory


def test_root_sdist_ships_generated_cli_package_import_dependency() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sdist_path = _build_artifact("sdist", Path(tmpdir))
        inventory = _artifact_inventory(sdist_path)

    assert "src/agentic_workspace/generated_command_adapters.py" in inventory
    assert "src/agentic_workspace/generated_cli_package/__init__.py" in inventory


def _build_artifact(kind: str, output_dir: Path) -> Path:
    subprocess.run(
        ["uv", "build", f"--{kind}", "-o", str(output_dir)],
        cwd=WORKSPACE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    pattern = "agentic_workspace-*.whl" if kind == "wheel" else "agentic_workspace-*.tar.gz"
    matches = list(output_dir.glob(pattern))
    assert len(matches) == 1, f"Expected exactly 1 {kind}, found {len(matches)}"
    return matches[0]


def _artifact_inventory(artifact_path: Path) -> set[str]:
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
