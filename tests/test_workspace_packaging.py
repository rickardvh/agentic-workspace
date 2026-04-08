"""Validate agentic-workspace artifacts against the checked-in payload inventory."""

from __future__ import annotations

import subprocess
import tarfile
import tempfile
from pathlib import Path
from zipfile import ZipFile


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_ROOT = WORKSPACE_ROOT / "src" / "agentic_workspace" / "_payload"
PACKAGE_PREFIX = Path("agentic_workspace") / "_payload"


def _source_inventory() -> set[str]:
    return {
        path.relative_to(PAYLOAD_ROOT).as_posix()
        for path in PAYLOAD_ROOT.rglob("*")
        if path.is_file()
    }


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
    return {
        path.relative_to(installed_payload).as_posix()
        for path in installed_payload.rglob("*")
        if path.is_file()
    }


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
