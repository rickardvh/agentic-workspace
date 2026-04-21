"""Test lifecycle operations for agentic-memory-bootstrap package."""

import subprocess
import tempfile
from pathlib import Path


def test_memory_clean_install() -> None:
    """Test installing memory bootstrap into a clean repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()
        memory_root = Path(__file__).resolve().parents[1]

        # Install memory bootstrap
        subprocess.run(
            ["uv", "run", "agentic-memory-bootstrap", "install", "--target", str(target)],
            capture_output=True,
            text=True,
            cwd=memory_root,
            check=True,
        )

        # Verify required files exist
        assert (target / ".agentic-workspace" / "memory" / "repo").exists(), "repo memory directory not found after install"
        assert (target / ".agentic-workspace" / "memory" / "repo" / "index.md").exists(), (
            ".agentic-workspace/memory/repo/index.md not found after install"
        )
        assert (target / ".agentic-workspace" / "memory" / "repo" / "manifest.toml").exists(), (
            ".agentic-workspace/memory/repo/manifest.toml not found after install"
        )
        assert (target / "AGENTS.md").exists(), "AGENTS.md not found after install"


def test_memory_install_dry_run() -> None:
    """Test dry-run mode does not create files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()
        memory_root = Path(__file__).resolve().parents[1]

        # Install with dry-run
        subprocess.run(
            ["uv", "run", "agentic-memory-bootstrap", "install", "--target", str(target), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=memory_root,
            check=True,
        )

        # Verify no files created
        assert not (target / ".agentic-workspace" / "memory" / "repo").exists(), "repo memory directory created during dry-run"
        assert not (target / "AGENTS.md").exists(), "AGENTS.md created during dry-run"


def test_memory_install_idempotent() -> None:
    """Test installing twice produces same state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()
        memory_root = Path(__file__).resolve().parents[1]

        # First install
        subprocess.run(
            ["uv", "run", "agentic-memory-bootstrap", "install", "--target", str(target)],
            capture_output=True,
            text=True,
            cwd=memory_root,
            check=True,
        )

        # Get first state
        index_content_1 = (target / ".agentic-workspace" / "memory" / "repo" / "index.md").read_text()

        # Second install (should fail or overwrite with --force)
        result = subprocess.run(
            ["uv", "run", "agentic-memory-bootstrap", "install", "--target", str(target)],
            capture_output=True,
            text=True,
            cwd=memory_root,
        )

        # If it succeeded, verify state is unchanged
        if result.returncode == 0:
            index_content_2 = (target / ".agentic-workspace" / "memory" / "repo" / "index.md").read_text()
            assert index_content_1 == index_content_2, "File content changed on second install"


def test_memory_status_after_install() -> None:
    """Test status command after install."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()
        memory_root = Path(__file__).resolve().parents[1]

        # Install
        subprocess.run(
            ["uv", "run", "agentic-memory-bootstrap", "install", "--target", str(target)],
            capture_output=True,
            text=True,
            cwd=memory_root,
            check=True,
        )

        # Check status
        result = subprocess.run(
            ["uv", "run", "agentic-memory-bootstrap", "status", "--target", str(target), "--format", "json"],
            capture_output=True,
            text=True,
            cwd=memory_root,
        )

        # Status should indicate bootstrap is installed
        assert result.returncode == 0, "Status command failed after install"


def test_memory_install_with_force() -> None:
    """Test --force flag allows overwriting existing bootstrap."""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / "test_repo"
        target.mkdir()
        memory_root = Path(__file__).resolve().parents[1]

        # First install
        subprocess.run(
            ["uv", "run", "agentic-memory-bootstrap", "install", "--target", str(target)],
            capture_output=True,
            text=True,
            cwd=memory_root,
            check=True,
        )

        # Modify a file
        index_path = target / ".agentic-workspace" / "memory" / "repo" / "index.md"
        original_content = index_path.read_text()
        index_path.write_text("# Modified\n")

        # Install with force
        subprocess.run(
            ["uv", "run", "agentic-memory-bootstrap", "install", "--target", str(target), "--force"],
            capture_output=True,
            text=True,
            cwd=memory_root,
            check=True,
        )

        # Verify file was restored
        restored_content = index_path.read_text()
        assert restored_content == original_content, "File was not restored by --force"
