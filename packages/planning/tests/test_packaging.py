"""Test that agentic-planning-bootstrap package artifacts contain required payload files."""

from __future__ import annotations

import subprocess
import tarfile
import tempfile
from pathlib import Path
from zipfile import ZipFile

import pytest

from repo_planning_bootstrap import installer

PLANNING_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PAYLOAD_ENTRIES = {path.as_posix() for path in installer.REQUIRED_PAYLOAD_FILES}
EXPECTED_SKILL_ENTRIES = {
    path.relative_to(installer.PLANNING_SKILLS_MANAGED_ROOT).as_posix() for path in installer.PLANNING_BUNDLED_SKILL_FILES
}


def _build_artifact(kind: str, output_dir: Path) -> Path:
    subprocess.run(
        ["uv", "build", f"--{kind}", "-o", str(output_dir)],
        cwd=PLANNING_PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    pattern = "agentic_planning_bootstrap-*.whl" if kind == "wheel" else "agentic_planning_bootstrap-*.tar.gz"
    artifacts = list(output_dir.glob(pattern))
    assert len(artifacts) == 1, f"Expected exactly 1 {kind}, found {len(artifacts)}"
    return artifacts[0]


def _artifact_entries(path: Path) -> set[str]:
    if path.name.endswith(".whl"):
        with ZipFile(path) as whl:
            names = whl.namelist()
            return _normalized_contract_entries(
                names, payload_prefix="repo_planning_bootstrap/_payload/", skills_prefix="repo_planning_bootstrap/_skills/"
            )

    with tarfile.open(path, "r:gz") as tar:
        names = tar.getnames()
        root_dir = next(name.split("/", 1)[0] for name in names if name.startswith("agentic_planning_bootstrap-"))
        return _normalized_contract_entries(names, payload_prefix=f"{root_dir}/bootstrap/", skills_prefix=f"{root_dir}/skills/")


def _normalized_contract_entries(names: list[str], *, payload_prefix: str, skills_prefix: str) -> set[str]:
    entries: set[str] = set()
    for name in names:
        if name.startswith(payload_prefix):
            entries.add(name.removeprefix(payload_prefix))
        elif name.startswith(skills_prefix):
            entries.add(name.removeprefix(skills_prefix))
    return entries


def _assert_contract_inventory(artifact: Path) -> None:
    entries = _artifact_entries(artifact)
    expected_entries = EXPECTED_PAYLOAD_ENTRIES | EXPECTED_SKILL_ENTRIES
    assert entries == expected_entries, (
        f"Artifact inventory mismatch for {artifact.name}. "
        f"Missing: {sorted(expected_entries - entries)}. "
        f"Unexpected: {sorted(entries - expected_entries)}."
    )


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
def test_planning_artifacts_contain_required_contract_inventory(kind: str) -> None:
    """Verify that the built planning wheel and sdist contain the same contract inventory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact = _build_artifact(kind, Path(tmpdir))
        _assert_contract_inventory(artifact)
