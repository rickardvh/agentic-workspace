"""Test lifecycle operations for root agentic-workspace orchestrator package."""

import subprocess
import tempfile
from pathlib import Path


def test_workspace_init_clean() -> None:
    """Test initializing workspace bootstrap into a clean repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()

        # Initialize git repo (required by workspace CLI)
        subprocess.run(
            ["git", "init"],
            cwd=target,
            capture_output=True,
            check=True,
        )

        workspace_root = Path(__file__).resolve().parents[1]

        # Initialize workspace with planning and memory modules
        result = subprocess.run(
            ["uv", "run", "agentic-workspace", "init", "--target", str(target), "--preset", "full", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=workspace_root,
            check=True,
        )

        assert result.returncode == 0, f"Workspace init failed: {result.stderr}"

        # Verify planning bootstrap files exist
        assert (target / "TODO.md").exists(), "TODO.md not found after workspace init"
        assert (target / "ROADMAP.md").exists(), "ROADMAP.md not found after workspace init"

        # Verify memory bootstrap files exist
        assert (target / "memory").exists(), "memory directory not found after workspace init"
        assert (target / "memory" / "index.md").exists(), "memory/index.md not found after workspace init"


def test_workspace_init_dry_run() -> None:
    """Test dry-run mode does not create files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()

        # Initialize git repo (required by workspace CLI)
        subprocess.run(
            ["git", "init"],
            cwd=target,
            capture_output=True,
            check=True,
        )

        workspace_root = Path(__file__).resolve().parents[1]

        # Initialize with dry-run
        subprocess.run(
            ["uv", "run", "agentic-workspace", "init", "--target", str(target), "--preset", "full", "--dry-run"],
            capture_output=True,
            text=True,
            cwd=workspace_root,
            check=True,
        )

        # Verify no files created
        assert not (target / "TODO.md").exists(), "TODO.md created during dry-run"
        assert not (target / "memory").exists(), "memory directory created during dry-run"


def test_workspace_status_after_init() -> None:
    """Test status command after init."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()

        # Initialize git repo (required by workspace CLI)
        subprocess.run(
            ["git", "init"],
            cwd=target,
            capture_output=True,
            check=True,
        )

        workspace_root = Path(__file__).resolve().parents[1]

        # Initialize
        subprocess.run(
            ["uv", "run", "agentic-workspace", "init", "--target", str(target), "--preset", "full"],
            capture_output=True,
            text=True,
            cwd=workspace_root,
            check=True,
        )

        # Check status
        result = subprocess.run(
            ["uv", "run", "agentic-workspace", "status", "--target", str(target), "--preset", "full", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=workspace_root,
            check=True,
        )

        # Status should succeed
        assert result.returncode == 0, "Status command failed after init"


def test_workspace_modules_list() -> None:
    """Test modules command lists available modules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace_root = Path(__file__).resolve().parents[1]

        # List available modules
        result = subprocess.run(
            ["uv", "run", "agentic-workspace", "modules", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=workspace_root,
            check=True,
        )

        # Should succeed
        assert result.returncode == 0, "Modules command failed"
        # Should list modules
        assert "planning" in result.stdout or "memory" in result.stdout, "No modules found in output"
