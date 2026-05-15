from __future__ import annotations

import sys as _sys

# ruff: noqa: F403,F405
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from memory_test_support import *
from repo_memory_bootstrap import runtime_primitives


def test_build_install_prompt_mentions_local_bootstrap_skills_and_target(
    monkeypatch,
) -> None:
    monkeypatch.setattr(runtime_primitives.shutil, "which", lambda name: f"./tools/{name}")
    prompt = cli._build_agent_prompt("install", target="./repo")

    assert prompt.startswith("Do not ask the user to install or clone anything locally first.")
    assert f"uvx --from {MEMORY_GIT_SOURCE_REF} agentic-memory init --target ./repo" in prompt
    assert "`install` skill at `./repo/.agentic-workspace/memory/bootstrap/skills`" in prompt
    assert "bootstrap-cleanup --target ./repo" in prompt
    assert ".agentic-workspace/memory/" in prompt
    assert "memory notes stay under `.agentic-workspace/memory/repo/`" in prompt


def test_build_adopt_prompt_mentions_local_bootstrap_skills_and_target(
    monkeypatch,
) -> None:
    monkeypatch.setattr(runtime_primitives.shutil, "which", lambda name: f"./tools/{name}")
    prompt = cli._build_agent_prompt("adopt", target="./repo")

    assert prompt.startswith("Do not ask the user to install or clone anything locally first.")
    assert f"uvx --from {MEMORY_GIT_SOURCE_REF} agentic-memory adopt --target ./repo" in prompt
    assert "`install` skill at `./repo/.agentic-workspace/memory/bootstrap/skills`" in prompt
    assert "`populate` from the same path" not in prompt
    assert "bootstrap-cleanup --target ./repo" in prompt
    assert ".agentic-workspace/memory/" in prompt
    assert "memory notes stay under `.agentic-workspace/memory/repo/`" in prompt
    assert "./repo" in prompt


def test_build_populate_prompt_mentions_task_context_heuristic(monkeypatch) -> None:
    monkeypatch.setattr(runtime_primitives.shutil, "which", lambda name: f"./tools/{name}")
    prompt = cli._build_agent_prompt("populate", target="./repo")

    assert f"uvx --from {MEMORY_GIT_SOURCE_REF} agentic-memory current show --target ./repo" in prompt
    assert "migration residue" in prompt
    assert "active state into planning/status" in prompt
    assert "./repo" in prompt


def test_build_upgrade_prompt_mentions_local_bootstrap_skills(monkeypatch) -> None:
    monkeypatch.setattr(runtime_primitives.shutil, "which", lambda name: f"./tools/{name}")
    prompt = cli._build_agent_prompt("upgrade", target="./repo")

    assert prompt.startswith("Do not ask the user to install or clone anything locally first.")
    assert "Use the checked-in `memory-upgrade` skill" in prompt
    assert "memory-upgrade" in prompt
    assert "./repo/.agentic-workspace/memory/skills/" in prompt
    assert "recorded upgrade source automatically" in prompt
    assert "packaged upgrade flow for this repo" in prompt
    assert "prefer the installed `agentic-memory` CLI when available" in prompt
    assert f"uvx --from {MEMORY_GIT_SOURCE_REF} agentic-memory upgrade --target <repo>" in prompt
    assert "bootstrap-cleanup --target ./repo" not in prompt
    assert not prompt.startswith("Run `")


def test_build_upgrade_prompt_uses_local_source_when_recorded(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runtime_primitives.shutil, "which", lambda name: f"./tools/{name}")
    target = tmp_path / "repo"
    (target / ".git").mkdir(parents=True, exist_ok=True)
    installer.install_bootstrap(target=target)
    (target / ".agentic-workspace/memory" / "UPGRADE-SOURCE.toml").write_text(
        'source_type = "local"\nsource_ref = "./local/agentic-memory"\n',
        encoding="utf-8",
    )

    prompt = cli._build_agent_prompt("upgrade", target=str(target))

    assert prompt.startswith("Do not ask the user to install or clone anything locally first.")
    assert "Use the checked-in `memory-upgrade` skill" in prompt
    assert "recorded upgrade source automatically" in prompt
    assert "packaged upgrade flow for this repo" in prompt
    assert "uvx --from ./local/agentic-memory agentic-memory upgrade --target <repo>" in prompt
    assert MEMORY_GIT_SOURCE_REF not in prompt


def test_build_uninstall_prompt_mentions_bundled_skill(monkeypatch) -> None:
    monkeypatch.setattr(runtime_primitives.shutil, "which", lambda name: f"./tools/{name}")
    prompt = cli._build_agent_prompt("uninstall", target="./repo")

    assert f"uvx --from {MEMORY_GIT_SOURCE_REF} agentic-memory uninstall --target ./repo" in prompt
    assert "bootstrap-uninstall" in prompt


def test_build_prompt_falls_back_to_pipx_when_uvx_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(runtime_primitives.shutil, "which", lambda name: None if name == "uvx" else "./tools/pipx")

    prompt = cli._build_agent_prompt("upgrade", target="./repo")

    assert prompt.startswith("Do not ask the user to install or clone anything locally first.")
    assert "Use the checked-in `memory-upgrade` skill" in prompt
    assert "./repo/.agentic-workspace/memory/skills/" in prompt
    assert "recorded upgrade source automatically" in prompt
    assert f"pipx run --spec {MEMORY_GIT_SOURCE_REF} agentic-memory upgrade --target <repo>" in prompt
    assert "uvx --from" not in prompt


def test_memory_upgrade_skill_includes_module_fallback() -> None:
    text = (installer.payload_root() / ".agentic-workspace" / "memory" / "skills" / "memory-upgrade" / "SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "agentic-memory upgrade --target <repo>" in text
    assert "uvx --from <recorded-source> agentic-memory upgrade --target <repo>" in text
    assert "pipx run --spec <recorded-source> agentic-memory upgrade --target <repo>" in text
    assert "prefer a runner command from the recorded source" in text
