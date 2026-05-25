"""Test that agentic-planning package artifacts contain required payload files."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path
from zipfile import ZipFile

import pytest
from jsonschema import Draft202012Validator

from repo_planning_bootstrap import installer

PLANNING_PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLANNING_PACKAGE_ROOT.parents[1]
CLASSIFICATION_PATH = PLANNING_PACKAGE_ROOT / "payload-surface-classification.json"
EXTRACTION_CANDIDATES_PATH = PLANNING_PACKAGE_ROOT / "extraction-candidates.json"
CLASSIFICATION_SCHEMA_PATH = PLANNING_PACKAGE_ROOT / "schemas" / "payload-surface-classification.schema.json"
EXTRACTION_CANDIDATES_SCHEMA_PATH = PLANNING_PACKAGE_ROOT / "schemas" / "extraction-candidates.schema.json"
EXPECTED_PAYLOAD_ENTRIES = {path.as_posix() for path in installer.PACKAGE_PAYLOAD_FILES}
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
ALLOWED_EXTRACTION_DECISIONS = {
    "extraction candidate",
    "optional extension for now",
    "keep internal / maintainer-development only",
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


def _build_artifact(kind: str, output_dir: Path) -> Path:
    subprocess.run(
        ["uv", "build", f"--{kind}", "-o", str(output_dir)],
        cwd=PLANNING_PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    pattern = "agentic_planning-*.whl" if kind == "wheel" else "agentic_planning-*.tar.gz"
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
        root_dir = next(name.split("/", 1)[0] for name in names if name.startswith("agentic_planning-"))
        return _normalized_contract_entries(names, payload_prefix=f"{root_dir}/bootstrap/", skills_prefix=f"{root_dir}/skills/")


def _raw_artifact_entries(path: Path) -> set[str]:
    if path.name.endswith(".whl"):
        with ZipFile(path) as whl:
            return {name for name in whl.namelist() if not name.endswith("/")}

    with tarfile.open(path, "r:gz") as tar:
        members = [member for member in tar.getmembers() if member.isfile()]
    root_dir = next(name.split("/", 1)[0] for name in (member.name for member in members) if name.startswith("agentic_planning-"))
    prefix = f"{root_dir}/"
    return {member.name.removeprefix(prefix) for member in members if member.name.startswith(prefix)}


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
    _assert_schema_valid(payload, CLASSIFICATION_SCHEMA_PATH)
    assert payload["kind"] == "planning-payload-surface-classification/v1"
    assert set(payload["allowed_classifications"]) == ALLOWED_CLASSIFICATIONS
    return payload


def _load_extraction_candidates() -> dict:
    payload = json.loads(EXTRACTION_CANDIDATES_PATH.read_text(encoding="utf-8"))
    _assert_schema_valid(payload, EXTRACTION_CANDIDATES_SCHEMA_PATH)
    assert payload["kind"] == "planning-extraction-candidates/v1"
    assert payload["issue"].endswith("/465")
    assert payload["parent_issue"].endswith("/461")
    assert payload["surface_value"]["ordinary_startup_surface"] is False
    return payload


def _assert_schema_valid(payload: dict, schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda error: list(error.path))
    assert not errors, f"{schema_path.name} validation failed at {list(errors[0].path)}: {errors[0].message}"


def test_package_local_artifact_schemas_validate_current_records() -> None:
    _load_payload_surface_classification()
    _load_extraction_candidates()


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
    resolved = path.resolve()
    if resolved.is_relative_to(PLANNING_PACKAGE_ROOT):
        return f"packages/planning/{resolved.relative_to(PLANNING_PACKAGE_ROOT).as_posix()}"
    return resolved.relative_to(REPO_ROOT).as_posix()


def _iter_tracked_payload_surface_files(root: Path) -> set[str]:
    return {_source_path(path) for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
def test_planning_artifacts_contain_required_contract_inventory(kind: str) -> None:
    """Verify that the built planning wheel and sdist contain the same contract inventory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact = _build_artifact(kind, Path(tmpdir))
        _assert_contract_inventory(artifact)


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
def test_planning_artifacts_ship_generated_cli_package_import_dependency(kind: str) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact = _build_artifact(kind, Path(tmpdir))
        entries = _raw_artifact_entries(artifact)

    assert not any(entry.endswith("repo_planning_bootstrap/generated_command_adapters.py") for entry in entries)
    assert not any(entry.endswith("repo_planning_bootstrap/generated_cli_package.py") for entry in entries)
    assert not any(entry.endswith("repo_planning_bootstrap/generated_cli_package/__init__.py") for entry in entries)
    if kind == "wheel":
        assert any(entry.endswith("repo_planning_bootstrap/_generated_cli_package_impl/__init__.py") for entry in entries)
        assert any(entry.endswith("repo_planning_bootstrap/_generated_cli_package_impl/command_package.json") for entry in entries)
        assert any(entry.endswith("repo_planning_bootstrap/_generated_cli_package_impl/adapter_commands.json") for entry in entries)
    else:
        assert any(entry.endswith("src/repo_planning_bootstrap/_generated_cli_package_impl/__init__.py") for entry in entries)
        assert any(entry.endswith("src/repo_planning_bootstrap/_generated_cli_package_impl/command_package.json") for entry in entries)
        assert any(entry.endswith("src/repo_planning_bootstrap/_generated_cli_package_impl/adapter_commands.json") for entry in entries)


def test_installed_planning_wheel_imports_cli_module() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        wheel_path = _build_artifact("wheel", tmpdir_path)
        install_root = tmpdir_path / "installed"
        subprocess.run(
            ["uv", "pip", "install", "--no-deps", "--target", str(install_root), str(wheel_path)],
            cwd=PLANNING_PACKAGE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import repo_planning_bootstrap.cli; from repo_planning_bootstrap._generated_cli_package_impl import build_generated_parser",
            ],
            cwd=tmpdir_path,
            env={**os.environ, "PYTHONPATH": str(install_root)},
            capture_output=True,
            text=True,
            check=False,
        )

    assert result.returncode == 0, result.stderr


def test_planning_runtime_entrypoint_stays_off_command_generation() -> None:
    pyproject = tomllib.loads((PLANNING_PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "command-generation" not in pyproject["project"]["dependencies"]
    assert pyproject["project"]["scripts"]["agentic-planning"] == "repo_planning_bootstrap.cli:main"


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
    assert "packages/planning/bootstrap/tools/AGENT_QUICKSTART.md" not in classified
    assert any(candidate["next_issue"].endswith("/463") for candidate in payload["compression_candidates"])
    assert any(candidate["next_issue"].endswith("/464") for candidate in payload["compression_candidates"])


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
def test_planning_artifacts_do_not_ship_bootstrap_helper_directories(kind: str) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact = _build_artifact(kind, Path(tmpdir))
        entries = _artifact_entries(artifact)

    assert not any(entry.startswith("scripts/") for entry in entries)
    assert not any(entry.startswith("tools/") for entry in entries)
    assert not any(entry.startswith(".agentic-workspace/planning/scripts/") for entry in entries)


@pytest.mark.parametrize("kind", ("wheel", "sdist"))
def test_planning_artifacts_do_not_ship_executable_bootstrap_payload(kind: str) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact = _build_artifact(kind, Path(tmpdir))
        entries = _artifact_entries(artifact)

    executable_entries = sorted(entry for entry in entries if Path(entry).suffix.lower() in EXECUTABLE_PAYLOAD_SUFFIXES)
    assert executable_entries == []


def test_extraction_candidates_define_boundaries_without_startup_surface() -> None:
    payload = _load_extraction_candidates()
    candidates = payload["decisions"]

    assert len(candidates) >= 5
    assert payload["follow_up_policy"]["created_new_issues"] == []
    for candidate in candidates:
        assert candidate["decision"] in ALLOWED_EXTRACTION_DECISIONS
        assert candidate["candidate_boundary"].strip()
        assert candidate["why_not_core_planning"].strip()
        assert candidate["evidence_required_before_extraction"]
        assert candidate["blockers"]
        assert candidate["candidate_surfaces"]
        assert candidate["existing_follow_up"]


def test_extraction_candidate_surfaces_exist_or_are_tracked_followups() -> None:
    payload = _load_extraction_candidates()
    classified_sources = _classified_source_paths()

    for candidate in payload["decisions"]:
        for surface in candidate["candidate_surfaces"]:
            if surface.startswith("packages/planning/"):
                path = Path(surface.removeprefix("packages/planning/"))
                assert (PLANNING_PACKAGE_ROOT / path).exists(), f"{candidate['id']} references missing surface {surface}"
                assert surface in classified_sources, f"{candidate['id']} references unclassified package surface {surface}"
        for follow_up in candidate["existing_follow_up"]:
            assert follow_up.startswith("https://github.com/rickardvh/agentic-workspace/issues/")
