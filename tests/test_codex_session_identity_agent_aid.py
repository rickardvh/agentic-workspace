from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AID_ROOT = REPO_ROOT / ".agentic-workspace" / "agent-aids" / "scripts" / "codex-session-identity"
LAUNCHER = REPO_ROOT / "scripts" / "run_agentic_workspace.py"


def test_codex_identity_candidate_aid_is_retired() -> None:
    assert not (AID_ROOT / "manifest.json").exists()
    assert not (AID_ROOT / "codex_session_identity.py").exists()


def test_canonical_configured_launcher_owns_codex_identity_bridge() -> None:
    launcher = LAUNCHER.read_text(encoding="utf-8")
    shared_config = (REPO_ROOT / ".agentic-workspace" / "config.toml").read_text(encoding="utf-8")
    local_config = (REPO_ROOT / ".agentic-workspace" / "config.local.toml").read_text(encoding="utf-8")

    assert "def _bridge_codex_session_identity()" in launcher
    assert 'CODEX_SESSION_IDENTITY_ENV = "CODEX_THREAD_ID"' in launcher
    assert 'AW_SESSION_IDENTITY_ENV = "AW_SESSION_LOGICAL_IDENTITY"' in launcher
    assert 'cli_invoke = "uv run --frozen --active --no-sync python scripts/run_agentic_workspace.py"' in shared_config
    assert 'cli_invoke = "uv run --frozen --active --no-sync python scripts/run_agentic_workspace.py"' in local_config
