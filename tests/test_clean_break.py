from __future__ import annotations

import ast
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
