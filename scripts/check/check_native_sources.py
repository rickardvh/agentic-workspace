"""Check the source/native boundary without retaining former runtime ownership rules."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from check_language_facade import check_python

ROOT = Path(__file__).resolve().parents[2]
PRODUCT = ROOT / "src/agentic_workspace"
MODULES = {"__init__", "_binding", "cli", "native_core", "codex_provider", "sealed_codex_transport"}


def check(root: Path = ROOT) -> None:
    product = root / "src/agentic_workspace"
    actual = {path.stem for path in product.glob("*.py")}
    if actual != MODULES:
        raise ValueError(f"Python product source differs from its native binding/provider boundary: {actual ^ MODULES}")
    # Tooling may use the public binding and provider mechanics, but cannot keep
    # source-only semantic imports alive after the implementation is removed.
    for directory in (root / "src", root / "scripts"):
        for path in directory.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    parts = name.split(".")
                    if len(parts) > 1 and parts[0] == "agentic_workspace" and parts[1] not in MODULES:
                        raise ValueError(f"{path.relative_to(root)} imports unsupported product module {name}")
    contract = json.loads((ROOT / "src/core/contracts/source_decision_contract.json").read_text(encoding="utf-8"))
    check_python(contract["language_facade"])


if __name__ == "__main__":
    check()
    print("Native Python source boundary and public facade are current")
