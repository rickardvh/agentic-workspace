from __future__ import annotations

# ruff: noqa: F403,F405
from tests.workspace_cli_support import *


def test_external_agent_handoff_text_names_target_repository_and_no_install_assumption() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning"])

    assert "Authority marker:" in text
    assert "- authority: generated-adapter" in text
    assert "- safe_to_edit: false" in text
    assert "Generated compatibility adapter" in text
    assert "Ordinary path:" in text
    assert 'agentic-workspace start --profile tiny --task "<task>" --format json' in text
    assert "agentic-workspace preflight --format json" in text
    assert "agentic-workspace config --target ./repo --profile tiny --format json" in text
    assert "agentic-workspace summary --format json" in text
    assert "agentic-workspace proof --profile tiny --changed <paths> --format json" in text
    assert "Prefer an installed `agentic-workspace` CLI from the target repo's environment." in text
    assert "Use `uvx` or `pipx run` only as temporary/debug fallbacks." in text
    assert "agentic-workspace defaults --section install_profiles --format json" in text
    assert "Use `full` only when both Memory and Planning are explicitly desired." not in text
    assert "`AGENTS.md` remains the repo startup entrypoint" in text
    assert "Compact routing docs when present" not in text
    assert text.count("Read `AGENTS.md` first.") == 1
    assert text.count("`AGENTS.md` remains the repo startup entrypoint") == 1


def test_external_agent_handoff_text_demotes_broad_routing_until_compact_startup_fails() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning"])

    start_index = text.index('agentic-workspace start --profile tiny --task "<task>" --format json')
    preflight_index = text.index("agentic-workspace preflight --format json")
    config_index = text.index("agentic-workspace config --target ./repo --profile tiny --format json")
    summary_index = text.index("agentic-workspace summary --format json")

    assert start_index < preflight_index
    assert start_index < config_index
    assert start_index < summary_index
    assert "When needed:" in text
    assert "Open raw planning or contract files only when compact commands point there." in text


def test_external_agent_handoff_text_does_not_default_combined_install_to_full() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning", "memory"])

    selector_index = text.index("agentic-workspace defaults --section install_profiles --format json")
    memory_index = text.index("agentic-workspace install --target ./repo --preset memory")
    planning_index = text.index("agentic-workspace install --target ./repo --preset planning")
    full_index = text.index("agentic-workspace install --target ./repo --preset full")

    assert selector_index < memory_index < planning_index < full_index
    assert "Use `full` only when both Memory and Planning are explicitly desired." in text


def test_external_agent_handoff_text_uses_configured_agent_instructions_filename() -> None:
    text = cli._external_agent_handoff_text(selected_modules=["planning"], agent_instructions_file="GEMINI.md")

    assert "Read `GEMINI.md` first." in text
    assert "`GEMINI.md` remains the repo startup entrypoint" in text


def test_external_agent_handoff_text_reports_workflow_artifact_profile() -> None:
    text = cli._external_agent_handoff_text(
        selected_modules=["planning"],
        agent_instructions_file="GEMINI.md",
        workflow_artifact_profile="gemini",
    )

    assert "Workflow artifact profile: gemini." in text
    assert "Generated compatibility adapter" in text
    assert 'agentic-workspace start --profile tiny --task "<task>" --format json' in text
    assert "Keep canonical authority in contracts, config, planning, Memory, and checks, not this adapter." in text
