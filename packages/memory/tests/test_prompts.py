from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from memory_test_support import *
from repo_memory_bootstrap import runtime_primitives


@pytest.mark.parametrize("command", ["install", "adopt", "upgrade", "uninstall"])
def test_lifecycle_prompts_share_current_owner_method(command, monkeypatch):
    monkeypatch.setattr(runtime_primitives.shutil, "which", lambda name: None)
    prompt = cli._build_agent_prompt(command, target="./repo")
    assert "./repo/.agentic-workspace/skills/workspace-setup-jumpstart/SKILL.md" in prompt
    assert "references/package.md" in prompt
    assert "optional Memory state" in prompt
    assert "unavailable, preserve material" in prompt
    assert "uvx" not in prompt and "pipx" not in prompt


def test_build_populate_prompt_mentions_task_context_heuristic(monkeypatch) -> None:
    monkeypatch.setattr(runtime_primitives.shutil, "which", lambda name: f"./tools/{name}")
    prompt = cli._build_agent_prompt("populate", target="./repo")

    assert f"uvx --from {MEMORY_GIT_SOURCE_REF} agentic-memory current show --target ./repo" in prompt
    assert "migration residue" in prompt
    assert "active state into planning/status" in prompt
    assert "./repo" in prompt


def test_memory_upgrade_skill_delegates_to_same_shared_method():
    text = (installer.payload_root() / ".agentic-workspace/memory/skills/memory-upgrade/SKILL.md").read_text(encoding="utf-8")
    assert "workspace-setup-jumpstart/" in text
    assert "references/package.md" in text
    assert "agentic-memory upgrade" not in text
    assert "does not imply deleting domain state" in text
