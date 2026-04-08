"""Test that agentic-workspace package artifacts contain required payload files."""

import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile


def test_workspace_wheel_contains_required_payload_files() -> None:
    """Verify that the built wheel contains workspace payload files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Build the wheel
        build_result = subprocess.run(
            ["uv", "build", "--wheel", "-o", tmpdir],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            check=True,
        )

        # Find the built wheel
        wheels = list(tmpdir_path.glob("agentic_workspace-*.whl"))
        assert len(wheels) == 1, f"Expected exactly 1 wheel, found {len(wheels)}"
        wheel_path = wheels[0]

        # Extract and verify payload files are present
        with ZipFile(wheel_path) as whl:
            names = whl.namelist()

            # Check for required workspace payload files
            required_files = [
                "agentic_workspace/_payload/.agentic-workspace/WORKFLOW.md",
                "agentic_workspace/_payload/.agentic-workspace/OWNERSHIP.toml",
            ]

            for req_file in required_files:
                assert req_file in names, (
                    f"Required payload file '{req_file}' not found in wheel. "
                    f"Available files: {[n for n in names if 'agentic-workspace' in n]}"
                )


def test_workspace_sdist_contains_required_payload_files() -> None:
    """Verify that the built sdist contains workspace payload files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Build the sdist
        build_result = subprocess.run(
            ["uv", "build", "--sdist", "-o", tmpdir],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            check=True,
        )

        # Find the built sdist
        sdists = list(tmpdir_path.glob("agentic_workspace-*.tar.gz"))
        assert len(sdists) == 1, f"Expected exactly 1 sdist, found {len(sdists)}"
        sdist_path = sdists[0]

        # Extract and verify payload files are present
        import tarfile

        with tarfile.open(sdist_path, "r:gz") as tar:
            names = tar.getnames()

            # Check for required workspace payload files
            # Note: sdist uses underscores in the directory name, not hyphens
            required_files = [
                "agentic_workspace-0.0.0/src/agentic_workspace/_payload/.agentic-workspace/WORKFLOW.md",
                "agentic_workspace-0.0.0/src/agentic_workspace/_payload/.agentic-workspace/OWNERSHIP.toml",
            ]

            for req_file in required_files:
                assert req_file in names, (
                    f"Required payload file '{req_file}' not found in sdist. "
                    f"Available payload files: {[n for n in names if '.agentic-workspace' in n]}"
                )
