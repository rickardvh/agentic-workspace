from __future__ import annotations

import json
from pathlib import Path

from repo_planning_bootstrap.installer import adopt_bootstrap, collect_status, install_bootstrap, verify_payload


def test_install_bootstrap_copies_required_files(tmp_path: Path) -> None:
    result = install_bootstrap(target=tmp_path)
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / "TODO.md").exists()
    assert (tmp_path / "ROADMAP.md").exists()
    assert (tmp_path / "tools" / "AGENT_QUICKSTART.md").exists()
    assert any(action.kind in {"copied", "created", "updated"} for action in result.actions)


def test_adopt_bootstrap_preserves_existing_agents(tmp_path: Path) -> None:
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text("repo-owned agents\n", encoding="utf-8")
    result = adopt_bootstrap(target=tmp_path)
    assert agents_path.read_text(encoding="utf-8") == "repo-owned agents\n"
    assert any(action.kind == "skipped" and action.path == agents_path for action in result.actions)


def test_status_reports_missing_and_present_files(tmp_path: Path) -> None:
    install_bootstrap(target=tmp_path)
    result = collect_status(target=tmp_path)
    assert any(action.kind == "present" for action in result.actions)


def test_verify_payload_quickstart_matches_manifest() -> None:
    result = verify_payload()
    quickstart_actions = [action for action in result.actions if action.path.name == "AGENT_QUICKSTART.md"]
    assert quickstart_actions
    assert any(action.kind == "current" for action in quickstart_actions)
