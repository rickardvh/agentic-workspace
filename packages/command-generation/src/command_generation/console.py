from __future__ import annotations

import sys
from pathlib import Path

from command_generation.generated_package_loader import load_generated_command_package_for_entrypoint


def main_for_entrypoint(entrypoint: str, argv: list[str] | None = None) -> int:
    generated = load_generated_command_package_for_entrypoint(entrypoint)
    return int(generated.main(sys.argv[1:] if argv is None else argv))


def main(argv: list[str] | None = None) -> int:
    return main_for_entrypoint(Path(sys.argv[0]).name, argv)
