from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "src/tooling/generate/generate_contract_catalogues.py"


def test_active_executable_examples_agree_with_native_command_authority():
    contract = json.loads((REPO_ROOT / "src/core/contracts/source_decision_contract.json").read_text(encoding="utf-8"))
    commands = {row["name"] for row in contract["native_cli"]["commands"]}
    # Audit procedure sources AND delivered copies. History is evidence, not an
    # executable catalogue; exclude only its named homes, not reference docs.
    historical = ("docs/reviews/", "docs/decisions/", "docs/releases/")
    files = {
        *REPO_ROOT.glob("*.md"),
        *REPO_ROOT.glob("docs/**/*.md"),
        *REPO_ROOT.glob(".agentic-workspace/docs/**/*.md"),
        *REPO_ROOT.glob(".agentic-workspace/skills/**/*.md"),
        *REPO_ROOT.glob(".agentic-workspace/*/skills/**/*.md"),
        *REPO_ROOT.glob(".agentic-workspace/memory/repo/skills/**/*.md"),
        *REPO_ROOT.glob(".agentic-workspace/**/AGENTS.md"),
        *REPO_ROOT.glob(".agentic-workspace/*/WORKFLOW.md"),
        *REPO_ROOT.glob(".agentic-workspace/planning/*/README.md"),
        *REPO_ROOT.glob("packages/**/*.md"),
        *REPO_ROOT.glob("src/core/payload/**/*.md"),
        *REPO_ROOT.glob("generated/**/*.md"),
        *REPO_ROOT.glob("tools/skills/**/*.md"),
        *REPO_ROOT.glob("src/tooling/model-cli-harness/fixtures/**/*.md"),
    }
    # Executable maintenance targets and live diagnostic/recovery producers are
    # also guidance. Retained legacy parsers, archived fixtures and historical
    # records are not an alternative public command authority.
    producers = {
        *REPO_ROOT.glob("src/core/src/**/*.rs"),
        *REPO_ROOT.glob("src/cli/rust/src/**/*.rs"),
        *REPO_ROOT.glob("packages/**/Makefile"),
        REPO_ROOT / "Makefile",
        REPO_ROOT / "src/tooling/python/aw_maintainer/session_diagnostics.py",
    }
    files.update(producers)
    unsupported = []
    for path in sorted(files):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative.startswith(historical):
            continue
        # Inline code, fenced examples and quoted configuration values all
        # carry executable guidance. A bare product name in prose does not.
        text = path.read_text(encoding="utf-8")
        blocks = [text] if path in producers else re.findall(r"`+([^`]+)`+", text)
        for block in blocks:
            for command in re.findall(
                r"(?:\bagentic-workspace(?:\.exe)?|\brun_agentic_workspace\.py|<configured AW invocation>)[ \t]+([a-z][\w-]*)", block
            ):
                if command not in commands:
                    unsupported.append(f"{relative}: {command}")
    assert unsupported == [], "\n".join(unsupported)
    native_reference = (REPO_ROOT / "docs/reference/native-cli.md").read_text(encoding="utf-8")
    assert set(re.findall(r"^\| `([\w-]+)` \|", native_reference, re.M)) == commands


def _module():
    spec = importlib.util.spec_from_file_location("generate_contract_catalogues", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_catalogue_renders_current_values_and_local_effect_boundary() -> None:
    text = _module().render_cli_catalogue()
    for command in ["start", "invoke", "resources", "worker"]:
        assert f"`agentic-workspace {command}`" in text
    assert "`agentic-workspace planning new-plan`" not in text
    assert "Contract digest: `sha256:" in text


def test_surface_catalogue_separates_public_footprint_from_maintenance_profiles() -> None:
    text = _module().render_surface_catalogue()
    assert "configuration.repository-adoption" in text
    assert "### `necessary-surfaces`" not in text


@pytest.mark.parametrize("line_ending", [b"\n", b"\r\n"], ids=["lf-checkout", "crlf-checkout"])
def test_checked_in_catalogues_are_fresh(tmp_path: Path, line_ending: bytes) -> None:
    module = _module()
    for path in [module.CLI_PATH, module.SURFACES_PATH]:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO_ROOT / path).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", line_ending))
    module.REPO_ROOT = tmp_path
    assert (REPO_ROOT / module.CLI_OUTPUT).read_text(encoding="utf-8") == module.render_cli_catalogue()
    assert (REPO_ROOT / module.SURFACES_OUTPUT).read_text(encoding="utf-8") == module.render_surface_catalogue()
    content = module.render_surface_catalogue()
    module._write_or_check(module.SURFACES_OUTPUT, content, check=False)
    assert (tmp_path / module.SURFACES_OUTPUT).read_bytes() == content.encode("utf-8")
    source = tmp_path / module.SURFACES_PATH
    source.write_bytes(source.read_bytes().replace(b"adopted-host", b"changed-lifetime"))
    assert module.render_surface_catalogue() != content
