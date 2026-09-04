from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

BANNED_PUBLIC_CONCEPTS = {
    "autopilot",
    "checkpoint",
    "final-response",
    "work-thread",
    "upgrade",
    "implement",
    "summary",
    "proof",
    "report",
}


def test_public_cli_contains_only_start_and_invoke() -> None:
    source = Path("src/agentic_workspace/cli.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    literals = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    assert "start" in literals
    assert "invoke" in literals
    assert not BANNED_PUBLIC_CONCEPTS.intersection(literals)


def test_pre_v1_runtime_and_generated_surfaces_are_absent() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "generated", "packages"], capture_output=True, text=True, check=True
    ).stdout
    assert tracked == ""
    assert not Path("src/agentic_workspace/runtime_compatibility.py").exists()
    assert not Path("src/agentic_workspace/operating_decision.py").exists()
    assert not Path("src/agentic_workspace/contracts/context_authority_registry.json").exists()
    assert not Path(".agentic-workspace/fallback/no_cli_startup.py").exists()


def test_github_actions_are_immutable_node24_generation_pins() -> None:
    workflows = "\n".join(path.read_text(encoding="utf-8") for path in sorted(Path(".github/workflows").glob("*.yml")))
    external_uses = re.findall(r"uses:\s+([^\s#]+)", workflows)
    assert external_uses
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", value) for value in external_uses if not value.startswith("./"))
    assert "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in workflows
    assert "astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d" in workflows


def test_ci_reports_the_repository_required_promotion_context() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "name: Support-bearing promotion" in workflow
    assert "needs: [check, release-admission]" in workflow
    assert "if: ${{ always() }}" in workflow
