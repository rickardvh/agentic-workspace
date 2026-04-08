"""Test lifecycle operations for agentic-planning-bootstrap package."""

import subprocess
import tempfile
from pathlib import Path


def test_planning_clean_install() -> None:
    """Test installing planning bootstrap into a clean repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()
        planning_root = Path(__file__).resolve().parents[1]
        
        # Install planning bootstrap
        result = subprocess.run(
            ["uv", "run", "agentic-planning-bootstrap", "install", "--target", str(target), "--format", "json"],
            capture_output=True,
            text=True,
            cwd=planning_root,
            check=True,
        )
        
        # Verify required files exist
        assert (target / "TODO.md").exists(), "TODO.md not found after install"
        assert (target / "ROADMAP.md").exists(), "ROADMAP.md not found after install"
        assert (target / "AGENTS.md").exists(), "AGENTS.md not found after install"


def test_planning_install_dry_run() -> None:
    """Test dry-run mode does not create files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()
        planning_root = Path(__file__).resolve().parents[1]
        
        # Install with dry-run
        subprocess.run(
            ["uv", "run", "agentic-planning-bootstrap", "install", "--target", str(target), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=planning_root,
            check=True,
        )
        
        # Verify no files created
        assert not (target / "TODO.md").exists(), "TODO.md created during dry-run"
        assert not (target / "ROADMAP.md").exists(), "ROADMAP.md created during dry-run"


def test_planning_install_idempotent() -> None:
    """Test installing twice produces same state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()
        planning_root = Path(__file__).resolve().parents[1]
        
        # First install
        subprocess.run(
            ["uv", "run", "agentic-planning-bootstrap", "install", "--target", str(target)],
            capture_output=True,
            text=True,
            cwd=planning_root,
            check=True,
        )
        
        # Get first state
        todo_content_1 = (target / "TODO.md").read_text()
        
        # Second install (should fail or overwrite with --force)
        result = subprocess.run(
            ["uv", "run", "agentic-planning-bootstrap", "install", "--target", str(target)],
            capture_output=True,
            text=True,
            cwd=planning_root,
        )
        
        # If it succeeded, verify state is unchanged
        if result.returncode == 0:
            todo_content_2 = (target / "TODO.md").read_text()
            assert todo_content_1 == todo_content_2, "File content changed on second install"


def test_planning_status_after_install() -> None:
    """Test status command after install."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()
        planning_root = Path(__file__).resolve().parents[1]
        
        # Install
        subprocess.run(
            ["uv", "run", "agentic-planning-bootstrap", "install", "--target", str(target)],
            capture_output=True,
            text=True,
            cwd=planning_root,
            check=True,
        )
        
        # Check status
        result = subprocess.run(
            ["uv", "run", "agentic-planning-bootstrap", "status", "--target", str(target), "--format", "json"],
            capture_output=True,
            text=True,
            cwd=planning_root,
        )
        
        # Status should indicate bootstrap is installed
        assert result.returncode == 0, "Status command failed after install"


def test_planning_install_with_force() -> None:
    """Test --force flag allows overwriting existing bootstrap."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()
        planning_root = Path(__file__).resolve().parents[1]
        
        # First install
        subprocess.run(
            ["uv", "run", "agentic-planning-bootstrap", "install", "--target", str(target)],
            capture_output=True,
            text=True,
            cwd=planning_root,
            check=True,
        )
        
        # Modify a file
        todo_path = target / "TODO.md"
        original_content = todo_path.read_text()
        todo_path.write_text("# Modified\n")
        
        # Install with force
        subprocess.run(
            ["uv", "run", "agentic-planning-bootstrap", "install", "--target", str(target), "--force"],
            capture_output=True,
            text=True,
            cwd=planning_root,
            check=True,
        )
        
        # Verify file was restored
        restored_content = todo_path.read_text()
        assert restored_content == original_content, "File was not restored by --force"
