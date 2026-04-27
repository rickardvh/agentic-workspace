"""Test that agentic-planning-bootstrap package artifacts contain required payload files."""

from __future__ import annotations

import json
import subprocess
import tarfile
import tempfile
import tomllib
from pathlib import Path
from zipfile import ZipFile

import pytest

from repo_planning_bootstrap import installer

PLANNING_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CLASSIFICATION_PATH = PLANNING_PACKAGE_ROOT / "payload-surface-classification.json"
EXPECTED_PAYLOAD_ENTRIES = {path.as_posix() for path in installer.REQUIRED_PAYLOAD_FILES}
EXPECTED_SKILL_ENTRIES = {
    path.relative_to(installer.PLANNING_SKILLS_MANAGED_ROOT).as_posix() for path in installer.PLANNING_BUNDLED_SKILL_FILES
}
ALLOWED_CLASSIFICATIONS = {
    "core daily-operation planning",
    "config-enabled extension",
    "discoverable-on-demand support",
    "maintainer/development only",
    "extraction candidate",
    "remove / obsolete",
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


def _load_payload_surface_classification() -> dict:
    payload = json.loads(CLASSIFICATION_PATH.read_text(encoding="utf-8"))
    assert payload["kind"] == "planning-payload-surface-classification/v1"
    assert set(payload["allowed_classifications"]) == ALLOWED_CLASSIFICATIONS
    return payload


def _classified_source_paths() -> set[str]:
    payload = _load_payload_surface_classification()
    sources = [surface["source_path"] for surface in payload["surfaces"]]
    assert len(sources) == len(set(sources)), "payload surface classification contains duplicate source paths"
    for surface in payload["surfaces"]:
        assert surface["classification"] in ALLOWED_CLASSIFICATIONS
        assert surface["owner"].strip()
        assert surface["rationale"].strip()
    return set(sources)


def _source_path(path: Path) -> str:
    return f"packages/planning/{path.relative_to(PLANNING_PACKAGE_ROOT).as_posix()}"


def _iter_tracked_payload_surface_files(root: Path) -> set[str]:
    return {_source_path(path) for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
def test_planning_artifacts_contain_required_contract_inventory(kind: str) -> None:
    """Verify that the built planning wheel and sdist contain the same contract inventory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact = _build_artifact(kind, Path(tmpdir))
        _assert_contract_inventory(artifact)


def test_payload_surface_classification_covers_package_payload_sources() -> None:
    classified = _classified_source_paths()
    expected = _iter_tracked_payload_surface_files(PLANNING_PACKAGE_ROOT / "bootstrap") | _iter_tracked_payload_surface_files(
        PLANNING_PACKAGE_ROOT / "skills"
    )
    missing = sorted(expected - classified)
    assert not missing, f"Payload surface classification is missing shipped package surfaces: {missing}"


def test_payload_surface_classification_covers_force_includes() -> None:
    classified = _classified_source_paths()
    pyproject = tomllib.loads((PLANNING_PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    force_includes = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]

    expected: set[str] = {"packages/planning/pyproject.toml"}
    for source in force_includes:
        path = PLANNING_PACKAGE_ROOT / source
        if path.is_dir():
            expected.update(_iter_tracked_payload_surface_files(path))
        else:
            expected.add(_source_path(path))

    missing = sorted(expected - classified)
    assert not missing, f"Payload surface classification is missing force-included surfaces: {missing}"


def test_payload_surface_classification_identifies_core_and_follow_up_sets() -> None:
    payload = _load_payload_surface_classification()
    classified = {surface["source_path"]: surface["classification"] for surface in payload["surfaces"]}
    default_core = set(payload["smallest_safe_default_install"]["source_paths"])

    assert default_core
    assert all(classified[path] == "core daily-operation planning" for path in default_core)
    assert classified["packages/planning/bootstrap/.agentic-workspace/planning/reviews/README.md"] == "extraction candidate"
    assert classified["packages/planning/bootstrap/.agentic-workspace/planning/upstream-task-intake.md"] == "extraction candidate"
    assert classified["packages/planning/bootstrap/tools/AGENT_QUICKSTART.md"] == "maintainer/development only"
    assert any(candidate["next_issue"].endswith("/463") for candidate in payload["compression_candidates"])
    assert any(candidate["next_issue"].endswith("/464") for candidate in payload["compression_candidates"])
