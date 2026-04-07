"""Test that agentic-planning-bootstrap package artifacts contain required payload files."""

import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile


PLANNING_PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_planning_wheel_contains_required_payload_files() -> None:
    """Verify that the built planning wheel contains required payload files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Build the wheel
        subprocess.run(
            ["uv", "build", "--wheel", "-o", tmpdir],
            cwd=PLANNING_PACKAGE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        # Find the built wheel
        wheels = list(tmpdir_path.glob("agentic_planning_bootstrap-*.whl"))
        assert len(wheels) == 1, f"Expected exactly 1 wheel, found {len(wheels)}"
        wheel_path = wheels[0]

        # Extract and verify payload files are present
        with ZipFile(wheel_path) as whl:
            names = whl.namelist()

            # Check for required planning payload files
            required_files = [
                "repo_planning_bootstrap/_payload/AGENTS.md",
                "repo_planning_bootstrap/_payload/TODO.md",
                "repo_planning_bootstrap/_payload/ROADMAP.md",
                "repo_planning_bootstrap/_payload/docs/execplans/README.md",
                "repo_planning_bootstrap/_payload/docs/execplans/TEMPLATE.md",
                "repo_planning_bootstrap/_payload/.agentic-workspace/planning/agent-manifest.json",
                "repo_planning_bootstrap/_payload/tools/AGENT_QUICKSTART.md",
                "repo_planning_bootstrap/_payload/tools/AGENT_ROUTING.md",
            ]

            for req_file in required_files:
                assert req_file in names, (
                    f"Required payload file '{req_file}' not found in wheel. "
                    f"Available payload files: {[n for n in names if 'payload' in n and (n.endswith('.md') or n.endswith('.json') or n.endswith('.toml'))][:10]}"
                )


def test_planning_sdist_contains_required_payload_files() -> None:
    """Verify that the built planning sdist contains required payload files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Build the sdist
        subprocess.run(
            ["uv", "build", "--sdist", "-o", tmpdir],
            cwd=PLANNING_PACKAGE_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )

        # Find the built sdist
        sdists = list(tmpdir_path.glob("agentic_planning_bootstrap-*.tar.gz"))
        assert len(sdists) == 1, f"Expected exactly 1 sdist, found {len(sdists)}"
        sdist_path = sdists[0]

        # Extract and verify payload files are present
        import tarfile

        with tarfile.open(sdist_path, "r:gz") as tar:
            names = tar.getnames()

            # Get the root directory of the sdist (e.g., "agentic_planning_bootstrap-0.1.2")
            root_dirs = set()
            for name in names:
                parts = name.split("/")
                if len(parts) > 0:
                    root_dirs.add(parts[0])

            assert len(root_dirs) == 1, f"Expected exactly 1 root directory in sdist, found {root_dirs}"
            root_dir = list(root_dirs)[0]

            # Check for required planning payload files
            required_files = [
                f"{root_dir}/bootstrap/AGENTS.md",
                f"{root_dir}/bootstrap/TODO.md",
                f"{root_dir}/bootstrap/ROADMAP.md",
                f"{root_dir}/bootstrap/docs/execplans/README.md",
                f"{root_dir}/bootstrap/docs/execplans/TEMPLATE.md",
                f"{root_dir}/bootstrap/.agentic-workspace/planning/agent-manifest.json",
                f"{root_dir}/bootstrap/tools/AGENT_QUICKSTART.md",
                f"{root_dir}/bootstrap/tools/AGENT_ROUTING.md",
            ]

            for req_file in required_files:
                assert req_file in names, (
                    f"Required payload file '{req_file}' not found in sdist. "
                    f"Available payload files: {[n for n in names if 'bootstrap' in n and (n.endswith('.md') or n.endswith('.json') or n.endswith('.toml'))][:10]}"
                )
