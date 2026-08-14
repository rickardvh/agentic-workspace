from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_public_install_rehearsal_receipt_retains_exact_resolution_and_second_process_proof() -> None:
    path = ROOT / "docs" / "maintainer" / "public-install-rehearsal-v0.40.1.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))

    assert receipt["kind"] == "agentic-workspace/public-install-rehearsal/v1"
    assert receipt["status"] == "passed"
    assert receipt["readiness_receipt"]["sha256"] == "174ef14c13edf9a5757ef10fe91aa5a9095928a13f5386338e055d6790b177e6"
    controlled = receipt["resolution"]["controlled_distributions"]
    assert {item["name"] for item in controlled} == {
        "agentic-workspace",
        "agentic-workspace-memory",
        "agentic-workspace-planning",
        "agentic-workspace-verification",
    }
    assert {item["version"] for item in controlled} == {"0.40.1"}
    assert all(item["url"].startswith("https://github.com/rickardvh/agentic-workspace/releases/download/v0.40.1/") for item in controlled)
    assert all(len(item["sha256"]) == 64 for item in controlled)
    assert receipt["resolution"]["forbidden_identity_match_count"] == 0
    assert receipt["resolution"]["registry_resolution_used_for_controlled_distributions"] is False
    second_process = receipt["second_process"]
    assert second_process["bootstrap_process_exited_before_invocation"] is True
    assert second_process["installed_executable_identity"] == {
        "entry_point": "agentic-workspace",
        "distribution": "agentic-workspace",
        "version": "0.40.1",
        "origin": "ephemeral rehearsal environment Scripts directory",
    }
    assert second_process["exit_code"] == 0
    assert second_process["result_kind"] == "startup-context/v1"
    assert second_process["durable_machine_local_path_match_count"] == 0
    assert re.search(r"[A-Za-z]:\\\\", json.dumps(receipt)) is None


UV = shutil.which("uv") or "uv"
NPM = shutil.which("npm") or "npm"


def _load_checker():
    spec = importlib.util.spec_from_file_location("package_identity_checker_under_test", ROOT / "scripts/check/check_package_identity.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECKER = _load_checker()


def _run(command: list[str], *, cwd: Path = ROOT) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def _copy_source_fixture(target_root: Path) -> None:
    for relative in (
        ".github/release-ownership.json",
        "LICENSE",
        "README.md",
        "docs/agentic-workspace-install.md",
        "pyproject.toml",
        "packages/memory/pyproject.toml",
        "packages/memory/README.md",
        "packages/memory/LICENSE",
        "packages/planning/pyproject.toml",
        "packages/planning/README.md",
        "packages/planning/LICENSE",
        "packages/verification/pyproject.toml",
        "packages/verification/LICENSE",
    ):
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    ownership = json.loads((ROOT / ".github/release-ownership.json").read_text(encoding="utf-8"))
    for package in ownership["typescript_packages"]:
        for relative in (package["package_json"], str(Path(package["package_json"]).parent / "LICENSE")):
            target = target_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)


def test_source_package_identity_is_coordinated() -> None:
    assert CHECKER.source_identity_errors(ROOT) == []


def test_source_package_identity_rejects_conflicting_license(tmp_path: Path) -> None:
    _copy_source_fixture(tmp_path)
    (tmp_path / "packages/planning/LICENSE").write_text("not MIT\n", encoding="utf-8")
    assert any("packages/planning/pyproject.toml does not project" in error for error in CHECKER.source_identity_errors(tmp_path))


@pytest.fixture(scope="module")
def coordinated_artifacts(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("coordinated-package-identity")
    local_dist = root / "local"
    release_dist = root / "release"
    local_dist.mkdir()
    release_dist.mkdir()
    _run([UV, "build", "--wheel", "--sdist", "--out-dir", str(local_dist)])
    for package in ("packages/memory", "packages/planning", "packages/verification"):
        _run([UV, "build", "--wheel", "--sdist", "--out-dir", str(local_dist), package])
    for artifact in local_dist.iterdir():
        shutil.copy2(artifact, release_dist / artifact.name)
    version = json.loads((ROOT / "generated/workspace/typescript/package.json").read_text(encoding="utf-8"))["version"]
    _run(
        [
            sys.executable,
            "scripts/release/patch_workspace_release_wheel.py",
            "--dist-dir",
            str(release_dist),
            "--version",
            version,
            "--release-asset-base-url",
            f"https://github.com/rickardvh/agentic-workspace/releases/download/v{version}",
        ]
    )
    for package_root in sorted((ROOT / "generated").glob("*/typescript")):
        _run([NPM, "pack", "--pack-destination", str(release_dist)], cwd=package_root)
    return local_dist, release_dist


@pytest.mark.parametrize(
    ("old", "new", "expected"),
    [
        ('{ name = "Rickard von Haugwitz" }', '{ name = "Unexpected Maintainer" }', "project.authors"),
        (
            'Issues = "https://github.com/rickardvh/agentic-workspace/issues"',
            'Issues = "https://example.invalid/issues"',
            "project.urls.Issues",
        ),
        (
            'Support = "https://github.com/rickardvh/agentic-workspace/issues"',
            'Support = "https://example.invalid/support"',
            "project.urls.Support",
        ),
        ('name = "agentic-workspace"', 'name = "unrelated-workspace"', "project.name"),
    ],
)
def test_source_package_identity_rejects_unexpected_owner_url_or_distribution(tmp_path: Path, old: str, new: str, expected: str) -> None:
    _copy_source_fixture(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    assert old in content
    pyproject.write_text(content.replace(old, new, 1), encoding="utf-8")
    assert any(expected in error for error in CHECKER.source_identity_errors(tmp_path))


def test_built_artifacts_carry_exact_identity(coordinated_artifacts: tuple[Path, Path]) -> None:
    _, release_dist = coordinated_artifacts
    assert CHECKER.artifact_identity_errors(ROOT, release_dist, require_exact_urls=True) == []


def test_redistributable_receipt_binds_exact_artifact_names_and_hashes(
    coordinated_artifacts: tuple[Path, Path],
) -> None:
    _, release_dist = coordinated_artifacts
    CHECKER.write_readiness_receipts(ROOT, release_dist)
    assert CHECKER.redistributable_receipt_errors(ROOT, release_dist) == []
    receipt_path = release_dist / "redistributable-package-readiness.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 12
    assert receipt["artifacts"] == sorted(receipt["artifacts"], key=lambda item: item["name"])
    assert all(set(artifact) == {"name", "sha256"} and len(artifact["sha256"]) == 64 for artifact in receipt["artifacts"])

    first_artifact = release_dist / receipt["artifacts"][0]["name"]
    original = first_artifact.read_bytes()
    try:
        first_artifact.write_bytes(original + b"tampered")
        assert CHECKER.redistributable_receipt_errors(ROOT, release_dist) == [
            "redistributable-package-readiness.json does not bind the exact artifact names and sha256 digests"
        ]
    finally:
        first_artifact.write_bytes(original)


def test_install_survives_into_fresh_second_process(coordinated_artifacts: tuple[Path, Path], tmp_path: Path) -> None:
    local_dist, _ = coordinated_artifacts
    environment = tmp_path / "tool-environment"
    host = tmp_path / "host"
    host.mkdir()
    _run(["git", "init", str(host)])
    _run([UV, "venv", "--python", sys.executable, str(environment)])
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    executable = environment / ("Scripts/agentic-workspace.exe" if sys.platform == "win32" else "bin/agentic-workspace")
    _run(
        [
            UV,
            "pip",
            "install",
            "--python",
            str(python),
            *(str(path) for path in sorted(local_dist.glob("*.whl"))),
        ]
    )
    first = subprocess.run(
        [str(executable), "init", "--target", str(host), "--modules", "memory", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(first.stdout)["decision"]["mutation"] == "applied"
    second = subprocess.run(
        [str(executable), "start", "--target", str(host), "--task", "second process proof", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(second.stdout)
    assert payload["kind"] == "startup-context/v1"
    config = (host / ".agentic-workspace/config.toml").read_text(encoding="utf-8")
    assert str(environment).replace("\\", "/") not in config.replace("\\", "/")
