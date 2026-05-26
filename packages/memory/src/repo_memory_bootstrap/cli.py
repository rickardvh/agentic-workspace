from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _load_main():
    try:
        return importlib.import_module("repo_memory_bootstrap._generated_cli_package_impl.cli").main
    except ModuleNotFoundError as exc:
        if exc.name != "repo_memory_bootstrap._generated_cli_package_impl":
            raise
        repo_root = Path(__file__).resolve().parents[4]
        sys.path.insert(0, str(repo_root))
        return importlib.import_module("generated.memory.python.cli").main


main = _load_main()

__all__ = ["main"]
