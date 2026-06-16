"""Test that agentic-verification package artifacts include generated contracts."""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
from pathlib import Path
from zipfile import ZipFile

import pytest

VERIFICATION_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def verification_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_dir = tmp_path_factory.mktemp("verification-artifacts")
    result = subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(output_dir)],
        cwd=VERIFICATION_PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    wheels = sorted(output_dir.glob("*.whl"))
    assert len(wheels) == 1
    return wheels[0]


@pytest.fixture(scope="module")
def verification_sdist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_dir = tmp_path_factory.mktemp("verification-sdist-artifacts")
    result = subprocess.run(
        ["uv", "build", "--sdist", "--out-dir", str(output_dir)],
        cwd=VERIFICATION_PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    sdists = sorted(output_dir.glob("*.tar.gz"))
    assert len(sdists) == 1
    return sdists[0]


def _raw_artifact_inventory(path: Path) -> set[str]:
    with ZipFile(path) as archive:
        return set(archive.namelist())


def _raw_sdist_inventory(path: Path) -> set[str]:
    with tarfile.open(path) as archive:
        return {name.partition("/")[2] for name in archive.getnames()}


def test_verification_wheel_ships_generated_contract_resources(verification_wheel: Path) -> None:
    inventory = _raw_artifact_inventory(verification_wheel)

    assert "repo_verification_bootstrap/_generated_cli_package_impl/_contracts/operations/verification.report.report.json" in inventory
    assert "repo_verification_bootstrap/_generated_cli_package_impl/_contracts/conformance/verification.report.process.json" in inventory


def test_verification_sdist_ships_generated_contract_resources(verification_sdist: Path) -> None:
    inventory = _raw_sdist_inventory(verification_sdist)

    assert "src/repo_verification_bootstrap/_generated_cli_package_impl/_contracts/operations/verification.report.report.json" in inventory
    assert (
        "src/repo_verification_bootstrap/_generated_cli_package_impl/_contracts/conformance/verification.report.process.json" in inventory
    )


def test_installed_verification_wheel_resolves_generated_contract_root(verification_wheel: Path, tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    subprocess.run(
        ["uv", "pip", "install", "--no-deps", "--target", str(install_root), str(verification_wheel)],
        cwd=VERIFICATION_PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from repo_verification_bootstrap._generated_cli_package_impl.primitives.operation_executor import "
                "_handle_context_root_verification_contracts; "
                "root = _handle_context_root_verification_contracts(); "
                "assert (root / 'operations' / 'verification.report.report.json').is_file()"
            ),
        ],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(install_root)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
