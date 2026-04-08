"""Test that agentic-memory-bootstrap package artifacts contain required payload files."""

from __future__ import annotations

import subprocess
import tarfile
import tempfile
from pathlib import Path
from zipfile import ZipFile

MEMORY_PACKAGE_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_MANAGED_PATHS = {
    "bootstrap/AGENTS.md",
    "bootstrap/README.md",
    "bootstrap/memory/index.md",
    "bootstrap/memory/manifest.toml",
    "bootstrap/memory/current/project-state.md",
    "bootstrap/memory/current/task-context.md",
    "bootstrap/memory/current/routing-feedback.md",
    "bootstrap/memory/mistakes/recurring-failures.md",
    "bootstrap/memory/skills/README.md",
    "bootstrap/scripts/check/check_memory_freshness.py",
    "skills/README.md",
    "skills/bootstrap-adoption/SKILL.md",
    "skills/bootstrap-populate/SKILL.md",
    "skills/bootstrap-upgrade/SKILL.md",
    "skills/bootstrap-uninstall/SKILL.md",
}


def test_memory_wheel_contains_required_payload_files_and_skills() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        wheel_path = _build_artifact("wheel", Path(tmpdir))
        inventory = _artifact_inventory(wheel_path)

        assert REQUIRED_MANAGED_PATHS <= inventory, _missing_paths(inventory, REQUIRED_MANAGED_PATHS)


def test_memory_sdist_contains_required_payload_files_and_skills() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sdist_path = _build_artifact("sdist", Path(tmpdir))
        inventory = _artifact_inventory(sdist_path)

        assert REQUIRED_MANAGED_PATHS <= inventory, _missing_paths(inventory, REQUIRED_MANAGED_PATHS)


def test_memory_wheel_and_sdist_share_the_same_managed_inventory() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        wheel_path = _build_artifact("wheel", tmpdir_path)
        sdist_path = _build_artifact("sdist", tmpdir_path)

        assert _artifact_inventory(wheel_path) == _artifact_inventory(sdist_path)


def _build_artifact(kind: str, output_dir: Path) -> Path:
    subprocess.run(
        ["uv", "build", f"--{kind}", "-o", str(output_dir)],
        cwd=MEMORY_PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    pattern = "agentic_memory_bootstrap-*.whl" if kind == "wheel" else "agentic_memory_bootstrap-*.tar.gz"
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
